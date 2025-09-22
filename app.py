from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import threading
import os
import select
import pty
import time
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import atexit
import signal
import sys
from datetime import datetime
import shutil

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Конфигурация
SCRIPTS_DIR = 'scripts'
HISTORY_DIR = 'history'
MAX_HISTORY_LINES = 500

# Глобальные переменные
processes = {}
process_outputs = {}

# Создаем необходимые папки
for directory in [SCRIPTS_DIR, HISTORY_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

shutdown_event = threading.Event()

def get_script_name_without_extension(filename):
    """Получить имя файла без расширения"""
    if '.' in filename:
        return '.'.join(filename.split('.')[:-1])
    return filename

def organize_scripts():
    """Организовать скрипты по папкам (без расширения)"""
    try:
        if not os.path.exists(SCRIPTS_DIR):
            os.makedirs(SCRIPTS_DIR)
            return
            
        # Сканируем корневую папку scripts на наличие файлов (не папок)
        for item in os.listdir(SCRIPTS_DIR):
            item_path = os.path.join(SCRIPTS_DIR, item)
            
            # Если это файл (а не папка) и он исполняемый
            if os.path.isfile(item_path) and os.access(item_path, os.X_OK):
                # Создаем папку с именем файла без расширения
                folder_name = get_script_name_without_extension(item)
                script_folder = os.path.join(SCRIPTS_DIR, folder_name)
                
                # Создаем папку если её нет
                if not os.path.exists(script_folder):
                    os.makedirs(script_folder)
                
                # Перемещаем файл в папку
                new_path = os.path.join(script_folder, item)
                if not os.path.exists(new_path):
                    shutil.move(item_path, new_path)
                    print(f"Скрипт {item} перемещен в папку {script_folder}")
                    
    except Exception as e:
        print(f"Ошибка организации скриптов: {e}")

def get_history_file_path(process_name):
    return os.path.join(HISTORY_DIR, f"{process_name}.log")

def load_history():
    """Загружаем последние 500 строк истории из файла"""
    global process_outputs
    try:
        if not os.path.exists(HISTORY_DIR):
            os.makedirs(HISTORY_DIR)
            return
            
        for filename in os.listdir(HISTORY_DIR):
            if filename.endswith('.log'):
                process_name = filename[:-4]
                file_path = get_history_file_path(process_name)
                
                if os.path.exists(file_path):
                    try:
                        lines = []
                        with open(file_path, 'r', encoding='utf-8') as f:
                            all_lines = f.readlines()
                            recent_lines = all_lines[-MAX_HISTORY_LINES:] if len(all_lines) > MAX_HISTORY_LINES else all_lines
                            
                            for line in recent_lines:
                                try:
                                    entry = json.loads(line.strip())
                                    lines.append(entry['data'])
                                except:
                                    continue
                                    
                        process_outputs[process_name] = ''.join(lines)
                    except Exception as e:
                        print(f"Ошибка загрузки истории для {process_name}: {e}")
                        process_outputs[process_name] = ""
                        
        print(f"История загружена из папки {HISTORY_DIR}")
    except Exception as e:
        print(f"Ошибка загрузки истории: {e}")
        process_outputs = {}

def append_to_history_file(process_name, data):
    """Добавляем запись в историю в формате JSON Lines"""
    try:
        file_path = get_history_file_path(process_name)
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
        limit_history_file_size(file_path)
            
    except Exception as e:
        print(f"Ошибка записи в историю для {process_name}: {e}")

def limit_history_file_size(file_path):
    """Ограничиваем размер файла истории до MAX_HISTORY_LINES строк"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if len(lines) > MAX_HISTORY_LINES:
                lines = lines[-MAX_HISTORY_LINES:]
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
    except Exception as e:
        print(f"Ошибка ограничения размера файла истории: {e}")

def save_current_history():
    print("История уже сохраняется построчно")
    pass

def cleanup():
    print("Завершение работы приложения...")
    for process_name in list(processes.keys()):
        if process_name in processes and processes[process_name].get('process'):
            try:
                process = processes[process_name]['process']
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    print(f"Процесс {process_name} остановлен")
            except Exception as e:
                print(f"Ошибка остановки процесса {process_name}: {e}")
    
    try:
        observer.stop()
        observer.join()
    except:
        pass
    
    print("Приложение завершено")

atexit.register(cleanup)
signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(0))

# Организуем скрипты при запуске
organize_scripts()
load_history()

class ScriptsFolderHandler(FileSystemEventHandler):
    def __init__(self, socketio):
        self.socketio = socketio
        self.last_event_time = 0
    
    def on_any_event(self, event):
        if event.is_directory or event.src_path.endswith(('.tmp', '.swp', '~')):
            return
            
        current_time = time.time()
        if current_time - self.last_event_time < 1:
            return
            
        self.last_event_time = current_time
        
        # Организуем скрипты при изменении в папке
        organize_scripts()
        
        try:
            self.socketio.emit('scripts_updated', {'message': 'Список скриптов обновлен'})
        except:
            pass

observer = Observer()
event_handler = ScriptsFolderHandler(socketio)
observer.schedule(event_handler, SCRIPTS_DIR, recursive=False)
observer.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/processes', methods=['GET'])
def get_processes():
    process_list = []
    
    if not os.path.exists(SCRIPTS_DIR):
        os.makedirs(SCRIPTS_DIR)
        return jsonify(process_list)
    
    try:
        # Сканируем папки внутри scripts
        for folder in os.listdir(SCRIPTS_DIR):
            folder_path = os.path.join(SCRIPTS_DIR, folder)
            if os.path.isdir(folder_path):
                # Ищем исполняемый файл внутри папки
                script_file = None
                for file in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, file)
                    if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                        script_file = file
                        break
                
                if script_file:
                    # Проверяем статус процесса
                    status = 'running' if folder in processes and processes[folder].get('process') and processes[folder]['process'].poll() is None else 'stopped'
                    process_list.append({
                        'name': folder,
                        'script_file': script_file,
                        'status': status
                    })
    except Exception as e:
        print(f"Ошибка при чтении папки scripts: {e}")
    
    return jsonify(process_list)

@app.route('/api/process/<process_name>/status', methods=['GET'])
def get_process_status(process_name):
    if process_name in processes and processes[process_name].get('process'):
        if processes[process_name]['process'].poll() is None:
            status = 'running'
        else:
            status = 'stopped'
            cleanup_process(process_name)
    else:
        status = 'stopped'
    
    return jsonify({'status': status, 'process': process_name})

@app.route('/api/process/<process_name>/start', methods=['POST'])
def start_process_api(process_name):
    success, message = start_process(process_name)
    return jsonify({'success': success, 'message': message})

@app.route('/api/process/<process_name>/stop', methods=['POST'])
def stop_process_api(process_name):
    success, message = stop_process(process_name)
    return jsonify({'success': success, 'message': message})

@socketio.on('connect')
def handle_connect():
    pass

def start_process(process_name):
    global processes, process_outputs
    
    # Путь к папке скрипта
    script_folder = os.path.join(SCRIPTS_DIR, process_name)
    
    print(f"Попытка запуска процесса: {process_name}")
    print(f"Путь к папке скрипта: {script_folder}")
    
    # Проверяем существование папки
    if not os.path.exists(script_folder):
        return False, f'Папка скрипта {script_folder} не существует'
    
    if not os.path.isdir(script_folder):
        return False, f'Путь {script_folder} не является папкой'
    
    # Ищем исполняемый файл в папке
    script_path = None
    script_file = None
    
    try:
        for file in os.listdir(script_folder):
            file_path = os.path.join(script_folder, file)
            print(f"Проверка файла: {file_path}, исполняемый: {os.path.isfile(file_path) and os.access(file_path, os.X_OK)}")
            if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                script_path = file_path
                script_file = file
                break
    except Exception as e:
        return False, f'Ошибка чтения папки {script_folder}: {str(e)}'
    
    if not script_path:
        return False, f'Исполняемый файл не найден в папке {script_folder}'
    
    print(f"Найден скрипт: {script_path}")
    
    # Проверяем существование файла
    if not os.path.exists(script_path):
        return False, f'Файл скрипта {script_path} не существует'
    
    if not os.access(script_path, os.X_OK):
        return False, f'Нет прав на выполнение файла {script_path}'
    
    if process_name in processes and processes[process_name].get('process') and processes[process_name]['process'].poll() is None:
        return False, f'Процесс {process_name} уже запущен'
    
    try:
        master, slave = pty.openpty()
        
        if process_name not in process_outputs:
            process_outputs[process_name] = ""
        
        print(f"Запуск скрипта с рабочей директорией: {script_folder}")
        
        # Определяем команду для запуска
        if script_file.endswith('.sh'):
            # Для shell скриптов используем /bin/bash с относительным путем
            cmd = ['/bin/bash', script_file]  # Относительный путь!
        elif script_file.endswith('.py'):
            # Для python скриптов используем python3 с относительным путем
            cmd = ['python3', script_file]  # Относительный путь!
        else:
            # Для других исполняемых файлов запускаем напрямую с относительным путем
            cmd = ['./' + script_file]  # Относительный путь!
        
        print(f"Команда запуска: {cmd}")
        
        processes[process_name] = {
            'process': subprocess.Popen(
                cmd,  # Используем правильную команду с относительными путями
                stdin=slave,
                stdout=slave,
                stderr=slave,
                universal_newlines=True,
                bufsize=0,
                cwd=script_folder  # Устанавливаем рабочую директорию на папку скрипта
            ),
            'master': master,
            'status': 'running',
            'thread_running': True
        }
        
        os.close(slave)
        
        status_thread = threading.Thread(target=check_process_status_background, args=(process_name,), daemon=True)
        status_thread.start()
        
        output_thread = threading.Thread(target=read_process_output, args=(process_name, master), daemon=True)
        output_thread.start()
        
        return True, f'Процесс {process_name} запущен (PID: {processes[process_name]["process"].pid})'
    except Exception as e:
        error_msg = f'Ошибка запуска: {str(e)}'
        print(f"Ошибка запуска процесса {process_name}: {error_msg}")
        return False, error_msg

def stop_process(process_name):
    global processes, process_outputs
    
    if process_name not in processes or not processes[process_name].get('process'):
        return False, f'Процесс {process_name} не запущен'
    
    if processes[process_name]['process'].poll() is not None:
        cleanup_process(process_name)
        return False, f'Процесс {process_name} уже завершен'
    
    try:
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
        
        if process_name in processes:
            processes[process_name]['status'] = 'stopped'
        
        return True, f'Процесс {process_name} остановлен'
    except:
        process.kill()
        process.wait()
        
        if process_name in processes and processes[process_name]['master']:
            try:
                os.close(processes[process_name]['master'])
            except:
                pass
        
        if process_name in processes:
            processes[process_name]['status'] = 'stopped'
        
        return True, f'Процесс {process_name} принудительно остановлен'

def cleanup_process(process_name):
    global processes
    
    if process_name in processes:
        processes[process_name]['status'] = 'stopped'

def check_process_status_background(process_name):
    global processes
    
    while process_name in processes and processes[process_name].get('thread_running', False) and not shutdown_event.is_set():
        if process_name in processes and processes[process_name].get('process'):
            process = processes[process_name]['process']
            if process.poll() is not None:
                if process_name in processes:
                    processes[process_name]['status'] = 'stopped'
                    processes[process_name]['thread_running'] = False
                try:
                    socketio.emit('process_status_update', {'process': process_name, 'status': 'stopped'})
                    output_msg = f'\n[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [Процесс {process_name} завершен]\n'
                    socketio.emit('process_output', {'process': process_name, 'data': output_msg})
                    
                    if process_name not in process_outputs:
                        process_outputs[process_name] = ""
                    process_outputs[process_name] += output_msg
                    append_to_history_file(process_name, output_msg)
                except:
                    pass
                break
        time.sleep(1)

def read_process_output(process_name, master_fd):
    global process_outputs
    
    try:
        while process_name in processes and processes[process_name].get('thread_running', False) and not shutdown_event.is_set():
            ready, _, _ = select.select([master_fd], [], [], 0.1)
            if ready:
                try:
                    output = os.read(master_fd, 4096)
                    if output:
                        output_str = output.decode('utf-8', errors='ignore')
                        
                        if process_name not in process_outputs:
                            process_outputs[process_name] = ""
                        process_outputs[process_name] += output_str
                        append_to_history_file(process_name, output_str)
                        
                        try:
                            socketio.emit('process_output', {'process': process_name, 'data': output_str})
                        except:
                            pass
                    else:
                        break
                except OSError:
                    break
            elif process_name in processes and processes[process_name].get('process'):
                process = processes[process_name]['process']
                if process.poll() is not None:
                    output_str = f'\n[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [Процесс {process_name} завершен]\n'
                    
                    if process_name not in process_outputs:
                        process_outputs[process_name] = ""
                    process_outputs[process_name] += output_str
                    append_to_history_file(process_name, output_str)
                    
                    try:
                        socketio.emit('process_output', {'process': process_name, 'data': output_str})
                        socketio.emit('process_status_update', {'process': process_name, 'status': 'stopped'})
                    except:
                        pass
                    
                    if process_name in processes:
                        processes[process_name]['status'] = 'stopped'
                        processes[process_name]['thread_running'] = False
                    break
    except Exception as e:
        error_msg = f'\n[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [Ошибка чтения: {str(e)}]\n'
        
        if process_name not in process_outputs:
            process_outputs[process_name] = ""
        process_outputs[process_name] += error_msg
        append_to_history_file(process_name, error_msg)
        
        try:
            socketio.emit('process_output', {'process': process_name, 'data': error_msg})
        except:
            pass

@socketio.on('process_input')
def handle_process_input(data):
    process_name = data.get('process')
    input_data = data.get('data')
    
    if process_name in processes and processes[process_name].get('process') and processes[process_name]['process'].poll() is None:
        master = processes[process_name]['master']
        try:
            os.write(master, input_data.encode('utf-8'))
        except OSError as e:
            try:
                error_msg = f'[Ошибка отправки: {str(e)}]\n'
                socketio.emit('process_output', {'process': process_name, 'data': error_msg})
                
                if process_name not in process_outputs:
                    process_outputs[process_name] = ""
                process_outputs[process_name] += error_msg
                append_to_history_file(process_name, error_msg)
            except:
                pass

@socketio.on('get_process_history')
def handle_get_process_history(data):
    process_name = data.get('process')
    if process_name in process_outputs:
        try:
            socketio.emit('process_history', {'process': process_name, 'data': process_outputs[process_name]})
        except:
            pass
    else:
        try:
            file_path = get_history_file_path(process_name)
            if os.path.exists(file_path):
                content = ""
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[-MAX_HISTORY_LINES:]
                    for line in lines:
                        try:
                            entry = json.loads(line.strip())
                            content += entry['data']
                        except:
                            continue
                socketio.emit('process_history', {'process': process_name, 'data': content})
            else:
                socketio.emit('process_history', {'process': process_name, 'data': ''})
        except Exception as e:
            print(f"Ошибка загрузки истории из файла для {process_name}: {e}")
            socketio.emit('process_history', {'process': process_name, 'data': ''})

@socketio.on('scripts_updated')
def handle_scripts_updated():
    pass

if __name__ == '__main__':
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("Получен сигнал завершения")
    finally:
        shutdown_event.set()
        cleanup()