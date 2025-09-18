from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import threading
import os
import select
import pty
import termios
import struct
import fcntl
import time
import json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Словарь для хранения информации о процессах
processes = {}  # {process_name: {process, master, status, thread_running}}
process_outputs = {}  # {process_name: [output_lines]}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/processes', methods=['GET'])
def get_processes():
    """Получить список доступных процессов/скриптов с их статусами"""
    process_list = []
    for file in os.listdir('.'):
        if os.path.isfile(file):
            if os.access(file, os.X_OK):
                status = 'running' if file in processes and processes[file].get('process') and processes[file]['process'].poll() is None else 'stopped'
                process_list.append({
                    'name': file,
                    'status': status
                })
    return jsonify(process_list)

@app.route('/api/process/<process_name>/status', methods=['GET'])
def get_process_status(process_name):
    """Получить статус конкретного процесса"""
    if process_name in processes and processes[process_name].get('process'):
        if processes[process_name]['process'].poll() is None:
            status = 'running'
        else:
            status = 'stopped'
            # Очищаем завершенный процесс
            cleanup_process(process_name)
    else:
        status = 'stopped'
    
    return jsonify({'status': status, 'process': process_name})

@app.route('/api/process/<process_name>/start', methods=['POST'])
def start_process_api(process_name):
    """Запустить процесс через API"""
    success, message = start_process(process_name)
    return jsonify({'success': success, 'message': message})

@app.route('/api/process/<process_name>/stop', methods=['POST'])
def stop_process_api(process_name):
    """Остановить процесс через API"""
    success, message = stop_process(process_name)
    return jsonify({'success': success, 'message': message})

@socketio.on('connect')
def handle_connect():
    pass

def start_process(process_name):
    global processes, process_outputs
    
    if not os.path.exists(process_name):
        return False, f'Файл {process_name} не найден'
    
    if not os.access(process_name, os.X_OK):
        return False, f'Нет прав на выполнение {process_name}'
    
    # Если процесс уже запущен
    if process_name in processes and processes[process_name].get('process') and processes[process_name]['process'].poll() is None:
        return False, f'Процесс {process_name} уже запущен'
    
    try:
        # Создаем псевдотерминал
        master, slave = pty.openpty()
        
        # Инициализируем хранилище вывода
        if process_name not in process_outputs:
            process_outputs[process_name] = []
        
        # Создаем запись о процессе
        processes[process_name] = {
            'process': subprocess.Popen(
                [f'./{process_name}'],
                stdin=slave,
                stdout=slave,
                stderr=slave,
                universal_newlines=True,
                bufsize=0
            ),
            'master': master,
            'status': 'running',
            'thread_running': True
        }
        
        os.close(slave)
        
        # Запускаем фоновую проверку статуса
        status_thread = threading.Thread(target=check_process_status_background, args=(process_name,), daemon=True)
        status_thread.start()
        
        # Запускаем чтение вывода
        output_thread = threading.Thread(target=read_process_output, args=(process_name, master), daemon=True)
        output_thread.start()
        
        return True, f'Процесс {process_name} запущен (PID: {processes[process_name]["process"].pid})'
    except Exception as e:
        return False, f'Ошибка запуска: {str(e)}'

def stop_process(process_name):
    global processes, process_outputs
    
    if process_name not in processes or not processes[process_name].get('process'):
        return False, f'Процесс {process_name} не запущен'
    
    if processes[process_name]['process'].poll() is not None:
        # Процесс уже завершен, очищаем
        cleanup_process(process_name)
        return False, f'Процесс {process_name} уже завершен'
    
    try:
        # Останавливаем проверку статуса
        if process_name in processes:
            processes[process_name]['thread_running'] = False
        
        process = processes[process_name]['process']
        master = processes[process_name]['master']
        
        process.terminate()
        process.wait(timeout=5)
        
        if master:
            try:
                os.close(master)
            except:
                pass
        
        # Очищаем данные процесса
        cleanup_process(process_name)
        
        return True, f'Процесс {process_name} остановлен'
    except:
        process.kill()
        process.wait()
        
        if process_name in processes and processes[process_name]['master']:
            try:
                os.close(processes[process_name]['master'])
            except:
                pass
        
        cleanup_process(process_name)
        return True, f'Процесс {process_name} принудительно остановлен'

def cleanup_process(process_name):
    """Очистка данных завершенного процесса"""
    global processes, process_outputs
    
    if process_name in processes:
        processes[process_name]['status'] = 'stopped'
        # Не удаляем из processes, чтобы сохранить историю вывода
        # processes.pop(process_name, None)

def check_process_status_background(process_name):
    """Фоновая проверка статуса процесса"""
    global processes
    
    while process_name in processes and processes[process_name].get('thread_running', False):
        if process_name in processes and processes[process_name].get('process'):
            process = processes[process_name]['process']
            if process.poll() is not None:
                # Процесс завершен
                if process_name in processes:
                    processes[process_name]['status'] = 'stopped'
                    processes[process_name]['thread_running'] = False
                socketio.emit('process_status_update', {'process': process_name, 'status': 'stopped'})
                socketio.emit('process_output', {'process': process_name, 'data': f'\n[Процесс {process_name} завершен]\n'})
                break
        time.sleep(1)

def read_process_output(process_name, master_fd):
    """Чтение вывода процесса"""
    global process_outputs
    
    try:
        while process_name in processes and processes[process_name].get('thread_running', False):
            ready, _, _ = select.select([master_fd], [], [], 0.1)
            if ready:
                try:
                    output = os.read(master_fd, 4096)
                    if output:
                        output_str = output.decode('utf-8', errors='ignore')
                        # Сохраняем вывод
                        if process_name not in process_outputs:
                            process_outputs[process_name] = []
                        process_outputs[process_name].append(output_str)
                        # Отправляем вывод
                        socketio.emit('process_output', {'process': process_name, 'data': output_str})
                    else:
                        break
                except OSError:
                    break
            # Проверяем статус процесса
            elif process_name in processes and processes[process_name].get('process'):
                process = processes[process_name]['process']
                if process.poll() is not None:
                    # Процесс завершен
                    socketio.emit('process_output', {'process': process_name, 'data': f'\n[Процесс {process_name} завершен]\n'})
                    socketio.emit('process_status_update', {'process': process_name, 'status': 'stopped'})
                    if process_name in processes:
                        processes[process_name]['status'] = 'stopped'
                        processes[process_name]['thread_running'] = False
                    break
    except Exception as e:
        error_msg = f'\n[Ошибка чтения: {str(e)}]\n'
        socketio.emit('process_output', {'process': process_name, 'data': error_msg})

@socketio.on('process_input')
def handle_process_input(data):
    """Отправка ввода в процесс"""
    process_name = data.get('process')
    input_data = data.get('data')
    
    if process_name in processes and processes[process_name].get('process') and processes[process_name]['process'].poll() is None:
        master = processes[process_name]['master']
        try:
            os.write(master, input_data.encode('utf-8'))
        except OSError as e:
            socketio.emit('process_output', {'process': process_name, 'data': f'[Ошибка отправки: {str(e)}]\n'})

@socketio.on('get_process_history')
def handle_get_process_history(data):
    """Получить историю вывода процесса"""
    process_name = data.get('process')
    if process_name in process_outputs:
        history = ''.join(process_outputs[process_name][-100:])  # Последние 100 записей
        socketio.emit('process_history', {'process': process_name, 'data': history})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)