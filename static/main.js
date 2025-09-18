const socket = io();
let currentProcess = null;
let processes = {};
let term = null;

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {
    loadProcesses();
    setupSocketHandlers();
    
    // Периодическое обновление статусов
    setInterval(loadProcesses, 5000);
});

// Загрузка списка процессов
async function loadProcesses() {
    try {
        const response = await fetch('/api/processes');
        const processList = await response.json();
        
        // Обновляем локальный список
        processList.forEach(proc => {
            processes[proc.name] = proc;
        });
        
        renderProcessesList(processList);
    } catch (error) {
        console.error('Ошибка загрузки процессов:', error);
    }
}

// Отображение списка процессов
function renderProcessesList(processList) {
    const container = document.getElementById('processes-list');
    container.innerHTML = '';
    
    processList.forEach(proc => {
        const item = document.createElement('div');
        item.className = `process-item ${currentProcess === proc.name ? 'active' : ''}`;
        item.innerHTML = `
            <div class="process-name">${proc.name}</div>
            <div class="process-status status-${proc.status}">${proc.status === 'running' ? 'Запущен' : 'Остановлен'}</div>
        `;
        item.onclick = () => selectProcess(proc.name);
        container.appendChild(item);
    });
}

// Выбор процесса
async function selectProcess(processName) {
    currentProcess = processName;
    
    // Обновляем UI
    document.querySelectorAll('.process-item').forEach(item => {
        item.classList.remove('active');
    });
    event?.target?.closest('.process-item')?.classList?.add('active');
    
    // Обновляем заголовок
    document.getElementById('current-process-title').textContent = processName;
    
    // Показываем терминал
    document.getElementById('terminal-placeholder').style.display = 'none';
    document.getElementById('terminal').style.display = 'block';
    
    // Инициализируем терминал если нужно
    if (!term) {
        initTerminal();
    }
    
    // Очищаем терминал
    term.clear();
    
    // Получаем историю вывода
    socket.emit('get_process_history', {process: processName});
    
    // Обновляем кнопки управления
    updateControlButtons();
    
    // Фокус на терминал
    setTimeout(() => {
        term.focus();
    }, 100);
}

// Инициализация терминала
function initTerminal() {
    term = new Terminal({
        cursorBlink: true,
        theme: {
            background: '#1e1e1e',
            foreground: '#ffffff'
        },
        rows: 30,
        cols: 100
    });
    
    term.open(document.getElementById('terminal'));
    
    // Обработчик ввода
    term.onData(e => {
        if (currentProcess) {
            socket.emit('process_input', {
                process: currentProcess,
                data: e
            });
        }
    });
    
    // Начальный фокус
    term.focus();
}

// Обновление кнопок управления
function updateControlButtons() {
    if (!currentProcess) {
        document.getElementById('start-btn').disabled = true;
        document.getElementById('stop-btn').disabled = true;
        document.getElementById('restart-btn').disabled = true;
        return;
    }
    
    const status = processes[currentProcess]?.status || 'stopped';
    
    if (status === 'running') {
        document.getElementById('start-btn').disabled = true;
        document.getElementById('stop-btn').disabled = false;
        document.getElementById('restart-btn').disabled = false;
    } else {
        document.getElementById('start-btn').disabled = false;
        document.getElementById('stop-btn').disabled = true;
        document.getElementById('restart-btn').disabled = true;
    }
}

// Запуск процесса
async function startProcess() {
    if (!currentProcess) return;
    
    try {
        const response = await fetch(`/api/process/${currentProcess}/start`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            // Обновляем статус
            processes[currentProcess] = {name: currentProcess, status: 'running'};
            updateControlButtons();
            loadProcesses(); // Обновляем список
        }
        
        // Фокус на терминал
        setTimeout(() => {
            if (term) term.focus();
        }, 100);
    } catch (error) {
        console.error('Ошибка запуска процесса:', error);
    }
}

// Остановка процесса
async function stopProcess() {
    if (!currentProcess) return;
    
    try {
        const response = await fetch(`/api/process/${currentProcess}/stop`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            // Обновляем статус
            processes[currentProcess] = {name: currentProcess, status: 'stopped'};
            updateControlButtons();
            loadProcesses(); // Обновляем список
        }
    } catch (error) {
        console.error('Ошибка остановки процесса:', error);
    }
}

// Перезапуск процесса
async function restartProcess() {
    if (!currentProcess) return;
    
    await stopProcess();
    setTimeout(() => {
        startProcess();
    }, 500);
}

// Настройка обработчиков WebSocket
function setupSocketHandlers() {
    // Обновление статуса процесса
    socket.on('process_status_update', function(data) {
        if (data.process in processes) {
            processes[data.process].status = data.status;
            loadProcesses(); // Обновляем отображение
            updateControlButtons();
        }
    });
    
    // Вывод от процесса
    socket.on('process_output', function(data) {
        if (data.process === currentProcess && term) {
            term.write(data.data);
        }
    });
    
    // История вывода процесса
    socket.on('process_history', function(data) {
        if (data.process === currentProcess && term) {
            term.write(data.data);
        }
    });
}