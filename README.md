# Web Terminal Manager

Web-based terminal interface for managing Linux scripts and processes.

## Features

- 🖥️ Web-based terminal interface
- 📋 Process management (start/stop/restart)
- 🎯 Multiple script support with tabs
- 🎨 Real-time terminal output with colors
- 🔧 Interactive script control
- 📊 Process status monitoring

## Installation

### On Debian/Ubuntu:
```bash
sudo apt update
sudo apt install -y python3 python3-pip git
sudo apt install -y python3-flask python3-flask-socketio

### Quick setup
```bash
git clone https://github.com/yourusername/web-terminal-manager.git
cd web-terminal-manager
python3 app.py

### Usage
Make your scripts executable: `chmod +x your_script.sh`  
Place scripts in the project directory  
Run the application: `python3 app.py`  
Access via browser: `http://server-address:5000`

### Requirements
Python 3.8+
Flask
Flask-SocketIO
Linux/Unix system

## License
MIT License