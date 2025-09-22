# [On English](https://github.com/MeteoraCD2/free-web-terminal-manager/#-english)  
# Описание на русском языке:
# free-web-terminal-manager

Универсальный веб-терминал для управления скриптами и процессами через браузер.

## 📖 Описание

free-web-terminal-manager - это мощное веб-приложение, которое позволяет управлять любыми скриптами и процессами через удобный веб-интерфейс. Приложение автоматически организует скрипты по папкам, сохраняет историю выполнения и предоставляет полноценный терминал в браузере.

## 🌟 Основные возможности

- **Веб-терминал** - полноценный терминал в браузере с поддержкой цветов и интерактивности
- **Управление процессами** - запуск, остановка, перезапуск скриптов одним кликом
- **Автоматическая организация** - скрипты автоматически перемещаются в папки с их именами
- **Сохранение истории** - история выполнения сохраняется между перезапусками приложения
- **Многозадачность** - одновременная работа с несколькими скриптами в отдельных вкладках
- **Автоматическое обнаружение** - автоматическое обнаружение новых скриптов без перезапуска
- **Правильная рабочая директория** - каждый скрипт работает в своей папке

## 📁 Структура проекта

```
free-web-terminal-manager/
├── app.py              # Основное приложение
├── static/
│   └── main.js         # Клиентский JavaScript
├── templates/
│   └── index.html      # HTML шаблон
├── scripts/            # Папка для скриптов (автоматически организуются)
├── history/            # Папка для истории выполнения
```

## 🚀 Установка

### Debian/Ubuntu:
```bash
# Установка зависимостей
apt install python3-flask python3-flask-socketio python3-watchdog

# Клонирование репозитория
git clone https://github.com/MeteoraCD2/free-web-terminal-manager.git
cd free-web-terminal-manager

# Создание структуры папок
mkdir scripts history

# Запуск приложения
python3 app.py
```

## 📖 Использование

1. Поместите исполняемый скрипт в папку `scripts/`
2. Сделайте скрипт исполняемым: `chmod +x script_name`
3. Откройте в браузере `http://ваш-ip:5000`
4. Выберите скрипт из списка и нажмите "Запустить"
5. Управляйте скриптом через веб-терминал

## 🛠 Технологии

- **Python 3** - основной язык программирования
- **Flask** - веб-фреймворк
- **Flask-SocketIO** - WebSocket для реального времени
- **xterm.js** - терминал в браузере
- **watchdog** - мониторинг файловой системы

## 📄 Лицензия

MIT License

---

### 🇬🇧 English

# free-web-terminal-manager

Universal web terminal for managing scripts and processes through a browser.

## 📖 Description

free-web-terminal-manager is a powerful web application that allows you to manage any scripts and processes through a convenient web interface. The application automatically organizes scripts into folders, saves execution history, and provides a full-featured terminal in the browser.

## 🌟 Key Features

- **Web Terminal** - full-featured terminal in browser with color and interactivity support
- **Process Management** - start, stop, restart scripts with one click
- **Automatic Organization** - scripts are automatically moved to folders with their names
- **History Saving** - execution history is saved between application restarts
- **Multitasking** - simultaneous work with multiple scripts in separate tabs
- **Automatic Detection** - automatic detection of new scripts without restart
- **Correct Working Directory** - each script runs in its own folder

## 📁 Project Structure

```
free-web-terminal-manager/
├── app.py              # Main application
├── static/
│   └── main.js         # Client JavaScript
├── templates/
│   └── index.html      # HTML template
├── scripts/            # Scripts folder (automatically organized)
├── history/            # Execution history folder
```

## 🚀 Installation

### Debian/Ubuntu:
```bash
# Install dependencies
apt install python3-flask python3-flask-socketio python3-watchdog

# Clone repository
git clone https://github.com/MeteoraCD2/free-web-terminal-manager.git
cd free-web-terminal-manager

# Create folder structure
mkdir scripts history

# Run application
python3 app.py
```

## 📖 Usage

1. Place executable script in `scripts/` folder
2. Make script executable: `chmod +x script_name`
3. Open `http://your-ip:5000` in browser
4. Select script from list and click "Start"
5. Manage script through web terminal

## 🛠 Technologies

- **Python 3** - main programming language
- **Flask** - web framework
- **Flask-SocketIO** - WebSocket for real-time
- **xterm.js** - terminal in browser
- **watchdog** - filesystem monitoring

## 📄 License

MIT License