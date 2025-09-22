const socket = io();
let currentProcess = null;
let processes = {};
let term = null;
let resizeTimeout = null;

document.addEventListener('DOMContentLoaded', function() {
    loadProcesses();
    setupSocketHandlers();
    
    setInterval(() => {
        loadProcesses();
    }, 10000);
    
    window.addEventListener('resize', handleWindowResize);
});

async function loadProcesses() {
    try {
        const response = await fetch('/api/processes');
        const processList = await response.json();
        
        const oldProcesses = {...processes};
        processes = {};
        processList.forEach(proc => {
            processes[proc.name] = proc;
        });
        
        renderProcessesList(processList);
        
        if (currentProcess && currentProcess in oldProcesses) {
            const oldStatus = oldProcesses[currentProcess].status;
            const newStatus = processes[currentProcess]?.status || 'stopped';
            if (oldStatus !== newStatus) {
                updateControlButtons();
            }
        }
        
    } catch (error) {
        console.error('Ошибка загрузки процессов:', error);
    }
}

function renderProcessesList(processList) {
    const container = document.getElementById('processes-list');
    container.innerHTML = '';
    
    if (processList.length === 0) {
        container.innerHTML = '<div style="color: #888; padding: 20px; text-align: center;">Нет доступных скриптов в папке scripts</div>';
        return;
    }
    
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

async function selectProcess(processName) {
    currentProcess = processName;
    
    document.querySelectorAll('.process-item').forEach(item => {
        item.classList.remove('active');
    });
    event?.target?.closest('.process-item')?.classList?.add('active');
    
    document.getElementById('current-process-title').textContent = processName;
    
    document.getElementById('terminal-placeholder').style.display = 'none';
    document.getElementById('terminal').style.display = 'block';
    
    if (!term) {
        initTerminal();
    } else {
        term.clear();
    }
    
    socket.emit('get_process_history', {process: processName});
    
    updateControlButtons();
    
    setTimeout(() => {
        if (term) {
            term.focus();
            updateTerminalSize();
        }
    }, 100);
}

function initTerminal() {
    const { rows, cols } = calculateTerminalSize();
    
    term = new Terminal({
        cursorBlink: true,
        theme: {
            background: '#1e1e1e',
            foreground: '#ffffff'
        },
        rows: rows,
        cols: cols
    });
    
    term.open(document.getElementById('terminal'));
    
    term.onData(e => {
        if (currentProcess) {
            socket.emit('process_input', {
                process: currentProcess,
                data: e
            });
        }
    });
    
    term.focus();
    
    setTimeout(updateTerminalSize, 100);
}

function calculateTerminalSize() {
    const terminalElement = document.getElementById('terminal');
    if (!terminalElement) return { rows: 24, cols: 80 };
    
    const containerWidth = terminalElement.clientWidth;
    const containerHeight = terminalElement.clientHeight;
    
    const charWidth = 8;
    const charHeight = 17;
    const padding = 20;
    
    const cols = Math.max(20, Math.floor((containerWidth - padding) / charWidth));
    const rows = Math.max(10, Math.floor((containerHeight - padding) / charHeight));
    
    return { rows, cols };
}

function updateTerminalSize() {
    if (!term) return;
    
    const { rows, cols } = calculateTerminalSize();
    
    if (term.rows !== rows || term.cols !== cols) {
        try {
            term.resize(cols, rows);
        } catch (error) {
            console.warn('Ошибка изменения размера терминала:', error);
        }
    }
}

function handleWindowResize() {
    if (resizeTimeout) {
        clearTimeout(resizeTimeout);
    }
    
    resizeTimeout = setTimeout(() => {
        updateTerminalSize();
    }, 250);
}

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

async function startProcess() {
    if (!currentProcess) return;
    
    try {
        const response = await fetch(`/api/process/${currentProcess}/start`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            processes[currentProcess] = {name: currentProcess, status: 'running'};
            updateControlButtons();
            loadProcesses();
        } else {
            if (term) {
                term.write(`\n[Ошибка запуска: ${result.message}]\n`);
            }
        }
        
        setTimeout(() => {
            if (term) term.focus();
        }, 100);
    } catch (error) {
        console.error('Ошибка запуска процесса:', error);
        if (term) {
            term.write('\n[Ошибка сети при запуске процесса]\n');
        }
    }
}

async function stopProcess() {
    if (!currentProcess) return;
    
    try {
        const response = await fetch(`/api/process/${currentProcess}/stop`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            processes[currentProcess] = {name: currentProcess, status: 'stopped'};
            updateControlButtons();
            loadProcesses();
        } else {
            if (term) {
                term.write(`\n[Ошибка остановки: ${result.message}]\n`);
            }
        }
    } catch (error) {
        console.error('Ошибка остановки процесса:', error);
        if (term) {
            term.write('\n[Ошибка сети при остановке процесса]\n');
        }
    }
}

async function restartProcess() {
    if (!currentProcess) return;
    
    if (term) {
        term.write('\n[Перезапуск процесса...]\n');
    }
    
    await stopProcess();
    setTimeout(() => {
        startProcess();
    }, 500);
}

function setupSocketHandlers() {
    socket.on('process_status_update', function(data) {
        if (data.process in processes) {
            processes[data.process].status = data.status;
            loadProcesses();
            updateControlButtons();
        }
    });
    
    socket.on('process_output', function(data) {
        if (data.process === currentProcess && term) {
            term.write(data.data);
        }
    });
    
    socket.on('process_history', function(data) {
        if (data.process === currentProcess && term) {
            term.write(data.data);
        }
    });
    
    socket.on('scripts_updated', function(data) {
        console.log('Список скриптов обновлен:', data.message);
        setTimeout(() => {
            loadProcesses();
        }, 500);
    });
}

function refreshScripts() {
    const btn = document.querySelector('.btn-refresh');
    const originalText = btn.textContent;
    btn.textContent = '🔄 Обновление...';
    btn.disabled = true;
    
    loadProcesses().finally(() => {
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 1000);
    });
}