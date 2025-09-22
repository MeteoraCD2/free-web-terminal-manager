#!/bin/bash

# Скрипт автоматического обновления сервера Valheim.
# Работает с сервисом systemd, но вы можете изменить службу на свой сценарий запуска сервера.
# Для обновления необходим SteamCMD. Установка SteamCMD:
# apt update; apt install software-properties-common; apt-add-repository non-free; dpkg --add-architecture i386; apt update && apt install steamcmd && export PATH="$PATH:/usr/games"
# Первый запуск steamcmd потребует авторизоваться в Steam. Можно войти анонимно с помощью 'login anonymous'

# Запустите скрипт, чтобы он циклически проверял обновления по расписанию.
# Проще всего сделать это с помощью systemd:

# [Unit]
# Description=Valheim update service
# After=network.target
# [Service]
# Type=simple
# User=root #замените на юзера, от имени которого у вас запускается сервер 
# ExecStart=/root/valheim_update.sh
# Restart=always
# RestartSec=30
# [Install]
# WantedBy=multi-user.target


## Переменные
STEAM_DIR="/root/.steam/root/steamcmd"              # полный путь к папке установки Steam
STEAM_USER="anonymous"                              # имя пользователя Steam
SERVER_LOG="/valheim_server/logs/valheim.log"       # файл лога сервера Valheim
SERVER_DIR="/valheim_server"                        # полный путь к серверу Valheim без косой черты в конце пути
WORLD_DIR="/root/.config/unity3d/IronGate/Valheim"  # полный путь к папке сохранений миров. Обычно это /<домашняя папка пользователя>/.config/unity3d/IronGate/Valheim
BACKUP_DIR="/root/backup"                           # полный путь к папке хранения резервных копий
LOCK_FILE="/tmp/valheim_update.lock"                # Файл блокировки для предотвращения конфликтов
TIME_FOR_UPDATE="07:00"                             # Время для запуска обновления сервера
LOG_DIR="/root/valheim_updates_log"                 # введите полный путь в папку для хранения логов обновления

export TERM=dumb # необходимо для корректного отображения логов

# Создаёт директорию, если её нет
mkdir -p "$LOG_DIR"
# Задаём имя лог-файлов с учётом директории, указанной выше, и текущей даты
LOG_FILE="$LOG_DIR/valheim_update_$(date +%Y-%m-%d).log"
## Перенаправляем весь вывод (stdout и stderr) в лог-файл с временной меткой
exec > >(while IFS= read -r line; do echo "$(date '+[%Y-%m-%d %H:%M:%S]') $line"; done | tee -a "$LOG_FILE") 2>&1

##### Параметры принудительного обновления
# Параметр "FORCE_UPDATE=1" является триггером для запуска процесса обновления сервера.
# По умолчанию принудительное обновление отключено, то есть 0.
# Если необходимо принудительно запустить процесс обновления сервера Valheim,
# просто укажите FORCE_UPDATE=1 и сохраните файл. В течение 10 секунд после сохранения
# автоматически запустится скрипт обновления, а параметр FORCE_UPDATE=1 автоматически
# изменится на FORCE_UPDATE=0, чтобы функция обновления не попала в цикл.

FORCE_UPDATE=0

# Получаем путь к текущему скрипту и выводим в консоль. Необходимо для проверки FORCE_UPDATE
SCRIPT_PATH="$(realpath "$0")"
echo "Запущен скрипт $SCRIPT_PATH" 

##### Проверка переменных с выводом результатов
echo "=== Начало проверки переменных ==="

[ -d "$STEAM_DIR" ] && echo "[SUCCESS] STEAM_DIR: $STEAM_DIR" || echo "[ERROR] STEAM_DIR: $STEAM_DIR не найден или не доступен"
[ -f "$SERVER_LOG" ] && echo "[SUCCESS] SERVER_LOG: $SERVER_LOG" || echo "[ERROR] SERVER_LOG: $SERVER_LOG не найден или не доступен"
[ -d "$SERVER_DIR" ] && echo "[SUCCESS] SERVER_DIR: $SERVER_DIR" || echo "[ERROR] SERVER_DIR: $SERVER_DIR не найден или не доступен"
[ -d "$WORLD_DIR" ] && echo "[SUCCESS] WORLD_DIR: $WORLD_DIR" || echo "[ERROR] WORLD_DIR: $WORLD_DIR не найден или не доступен"

if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR" && echo "[SUCCESS] BACKUP_DIR создана: $BACKUP_DIR" || echo "[ERROR] Не удалось создать $BACKUP_DIR"
else
    echo "[SUCCESS] BACKUP_DIR: $BACKUP_DIR"
fi

[[ "$TIME_FOR_UPDATE" =~ ^([0-1][0-9]|2[0-3]):[0-5][0-9]$ ]] && echo "[SUCCESS] TIME_FOR_UPDATE: $TIME_FOR_UPDATE" || echo "[ERROR] Неверный формат TIME_FOR_UPDATE, пропускаем."

[[ "$FORCE_UPDATE" =~ ^[01]$ ]] || { echo "[WARNING] значение параметра FORCE_UPDATE некорректно: должно быть 0 или 1. Исправляем на 0"; sed -i 's/^FORCE_UPDATE=.*/FORCE_UPDATE=0/' "$SCRIPT_PATH"; FORCE_UPDATE=0; }

echo "=== Завершение проверки переменных ==="

##### Функция для выполнения обновления сервера
perform_update() {
    DATE=$(date +%Y-%m-%d_%H-%M-%S)
    echo "Получена команда для запуска процесса обновления..."
    touch "$LOCK_FILE" # Создаём файл блокировки

    # Останавливаем сервер Valheim. Проверьте, чтобы название сервиса было valheim.service, либо замените название сервиса на своё.
    echo "Останавливаю службу valheim.service..."
    if ! systemctl stop valheim.service; then
        echo "Не удалось остановить службу. Пытаюсь убить процесс..."
        pkill -f "valheim_server.x86_64" || true
    fi

    # Удаляем резервные копии старше 7 дней
    echo "Удаляю старые бэкапы..."
    find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +6 -exec rm -rf {} +

    # Создаём резервную копию текущего сервера
    echo "Создаю копию папки сервера в папку $BACKUP_DIR ..."
    cp -p -r "$SERVER_DIR" "$BACKUP_DIR/server_$DATE"

    # Создаём резервную копию миров
    echo "Создаю копию папки с мирами в папку $BACKUP_DIR ..."
    cp -r "$WORLD_DIR" "$BACKUP_DIR/world_$DATE"

    # Запускаем обновление через SteamCMD
    echo "Запускаю SteamCMD с командой загрузки последней версии сервера Valheim..."
    "$STEAM_DIR/steamcmd.sh" +force_install_dir "$SERVER_DIR" +login "$STEAM_USER" +app_update 896660 validate +quit

    # Запускаем сервер Valheim
    echo "Запуск valheim.service..."
    systemctl start valheim.service

    rm -f "$LOCK_FILE" # Удаляем файл блокировки
    echo "Процесс обновления завершён."
}

##### Функция проверки принудительного обновления
check_force_update() {
    local force_update_value=$(grep -oP '^FORCE_UPDATE=\K[0-9]+' "$SCRIPT_PATH")
    if [[ "$force_update_value" -eq 1 ]]; then
        echo "Обнаружен параметр "FORCE_UPDATE=1". Запускаю функцию обновления..."
        # Обновляем значение FORCE_UPDATE в самом скрипте
        sed -i 's/^FORCE_UPDATE=.*/FORCE_UPDATE=0/' "$SCRIPT_PATH"
        return 0
    fi
    return 1
}

##### Функция проверки времени
check_time_for_update() {
    [[ "$(date +"%H:%M")" == "$TIME_FOR_UPDATE" ]] && return 0 || return 1
}

##### Функция проверки лога на несовместимость версий
check_log_for_version_mismatch() {
    local log_lines=100  # Количество последних строк лога для анализа
    local mismatch_found=0
    
    # Ищем в последних строках лога сообщения о несовместимости версий
    tail -n $log_lines "$SERVER_LOG" | grep -q "Peer .* has incompatible version" || return 1
    
    # Если нашли сообщение, извлекаем версии
    while read -r line; do
        server_version=$(echo "$line" | grep -oP 'mine:\K[0-9]+\.[0-9]+\.[0-9]+')
        client_version=$(echo "$line" | grep -oP 'remote \K[0-9]+\.[0-9]+\.[0-9]+')
        
        if [[ -n "$server_version" && -n "$client_version" ]]; then
            if [[ "$(printf '%s\n' "$server_version" "$client_version" | sort -V | head -n1)" == "$server_version" ]]; then
                echo "Обнаружено несовпадение версий: Сервер ($server_version) старее клиента ($client_version). Пробую обновиться!"
                mismatch_found=1
                break
            fi
        fi
    done < <(tail -n $log_lines "$SERVER_LOG" | grep "Peer .* has incompatible version")
    
    return $mismatch_found
}

##### Основной цикл мониторинга
while true; do
    # Проверяем, запущено ли уже обновление
    if [[ -f "$LOCK_FILE" ]]; then
        echo "Функция обновления уже запущена. Повторный запуск будет возможен через 60 секунд..."
        sleep 60
        continue
    fi

    # Проверяем условия для запуска функции обновления по очереди
    if check_force_update; then
        perform_update
    elif check_time_for_update; then
        perform_update
    elif check_log_for_version_mismatch; then
        perform_update
    fi

    sleep 10
done
