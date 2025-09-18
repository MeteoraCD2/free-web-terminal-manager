#!/bin/bash

# Файл для хранения пользователей
USERS_FILE="users.txt"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Задержка между строками (в секундах) - только для анимации текста
DELAY=0.04

# Функция для вывода текста с задержкой (только для анимации)
print_with_delay() {
    local text="$1"
    echo -e "$text"
    sleep $DELAY
}

# Функция для очистки экрана и отображения заголовка
clear_screen() {
    clear
    print_with_delay "${CYAN}=== Система управления пользователями ===${NC}"
    echo ""
}

# Функция для отображения меню
show_menu() {
    clear_screen
    print_with_delay "${WHITE}1. Создать пользователя${NC}"
    print_with_delay "${WHITE}2. Показать список пользователей${NC}"
    print_with_delay "${WHITE}3. Удалить пользователя${NC}"
    print_with_delay "${WHITE}4. Выйти${NC}"
    echo ""
    echo -n -e "${YELLOW}Выберите действие: ${NC}"
}

# Функция для скрытого ввода пароля с отображением звёздочек
read_password() {
    local password=""
    local char
    while IFS= read -r -s -n1 char 2>/dev/null; do
        if [[ -z $char ]]; then
            break
        elif [[ $char == $'\x7f' ]] || [[ $char == $'\b' ]]; then
            if [[ ${#password} -gt 0 ]]; then
                password="${password%?}"
                echo -ne '\b \b' >&2
            fi
        else
            password+="$char"
            echo -n '*' >&2
        fi
    done
    echo "$password"
}

# Функция проверки пароля по политике
validate_password() {
    local pass="$1"
    local valid=true
    local messages=()

    if [[ ${#pass} -lt 8 ]]; then
        valid=false
        messages+=("- минимум 8 символов")
    fi

    if ! [[ "$pass" =~ [A-Z] ]]; then
        valid=false
        messages+=("- минимум одна заглавная буква")
    fi

    if ! [[ "$pass" =~ [a-z] ]]; then
        valid=false
        messages+=("- минимум одна строчная буква")
    fi

    if ! [[ "$pass" =~ [0-9] ]]; then
        valid=false
        messages+=("- минимум одна цифра")
    fi

    if [[ "$valid" == true ]]; then
        echo "valid"
    else
        for msg in "${messages[@]}"; do
            echo -e "${RED}$msg${NC}"
        done
        echo ""
        echo -e "${YELLOW}Пожалуйста, введите пароль заново:${NC}"
    fi
}

# Функция создания пользователя
create_user() {
    clear_screen
    
    # Ввод логина
    echo -n -e "${BLUE}Введите желаемый логин (пустая строка для отмены): ${NC}"
    read -r username
    
    # Проверка на пустой ввод логина
    if [[ -z "$username" ]]; then
        clear_screen
        echo -e "${YELLOW}Создание пользователя отменено.${NC}"
        echo ""
        echo -n -e "${YELLOW}Нажмите Enter для возврата в меню...${NC}"
        read -r
        return 0
    fi
    
    # Проверка на пробелы в логине
    if [[ "$username" =~ [[:space:]] ]]; then
        clear_screen
        echo -e "${RED}Ошибка: Логин не должен содержать пробелов.${NC}"
        echo ""
        echo -n -e "${YELLOW}Нажмите Enter для возврата в меню...${NC}"
        read -r
        return 1
    fi
    
    # Проверяем, существует ли уже такой пользователь
    if [[ -f "$USERS_FILE" ]] && grep -q "^$username " "$USERS_FILE"; then
        clear_screen
        echo -e "${RED}Ошибка: Пользователь с логином '$username' уже существует.${NC}"
        echo ""
        echo -n -e "${YELLOW}Нажмите Enter для возврата в меню...${NC}"
        read -r
        return 1
    fi

    # Ввод пароля
    while true; do
        echo -n -e "${BLUE}Введите желаемый пароль (пустая строка для отмены): ${NC}"
        password=$(read_password)
        echo ""  # Переход на новую строку после ввода пароля
        
        # Проверка на пустой ввод пароля
        if [[ -z "$password" ]]; then
            clear_screen
            echo -e "${YELLOW}Создание пользователя отменено.${NC}"
            echo ""
            echo -n -e "${YELLOW}Нажмите Enter для возврата в меню...${NC}"
            read -r
            return 0
        fi
        
        validation=$(validate_password "$password")
        if [[ "$validation" == "valid" ]]; then
            break
        else
            echo "$validation"
            echo ""
            echo -n -e "${YELLOW}Нажмите Enter для повторного ввода пароля...${NC}"
            read -r
            clear_screen
            echo -n -e "${BLUE}Введите желаемый логин: ${NC}$username"
            echo ""
        fi
    done

    # Подтверждение пароля
    while true; do
        echo -n -e "${BLUE}Подтвердите пароль (пустая строка для отмены): ${NC}"
        password_confirm=$(read_password)
        echo ""  # Переход на новую строку после ввода подтверждения
        
        # Проверка на пустой ввод подтверждения
        if [[ -z "$password_confirm" ]]; then
            clear_screen
            echo -e "${YELLOW}Создание пользователя отменено.${NC}"
            echo ""
            echo -n -e "${YELLOW}Нажмите Enter для возврата в меню...${NC}"
            read -r
            return 0
        fi
        
        confirm_hash=$(echo -n "$password_confirm" | sha512sum | awk '{print $1}')
        password_hash=$(echo -n "$password" | sha512sum | awk '{print $1}')
        
        if [[ "$password_hash" == "$confirm_hash" ]]; then
            break
        else
            clear_screen
            echo -e "${RED}Пароли не совпадают, создание прервано${NC}"
            echo ""
            echo -n -e "${YELLOW}Нажмите Enter для возврата в меню...${NC}"
            read -r
            return 1
        fi
    done

    # Записываем в файл
    echo "$username $password_hash" >> "$USERS_FILE"
    clear_screen
    echo -e "${GREEN}Пользователь успешно создан!${NC}"
    echo ""
    echo -n -e "${YELLOW}Нажмите Enter для возврата в меню...${NC}"
    read -r
}

# Функция вывода списка пользователей
show_users() {
    clear_screen
    
    if [[ ! -f "$USERS_FILE" ]] || [[ ! -s "$USERS_FILE" ]]; then
        echo -e "${YELLOW}Список пользователей пуст.${NC}"
        echo ""
        echo -n -e "${YELLOW}Нажмите любую клавишу, чтобы вернуться в меню...${NC}"
        read -n1 -s
        return 0
    fi
    
    echo -e "${CYAN}Список пользователей:${NC}"
    echo ""
    
    # Выводим каждый логин (без задержки для мгновенного отображения)
    while IFS= read -r line; do
        if [[ -n "$line" ]]; then
            username=$(echo "$line" | awk '{print $1}')
            echo -e "${WHITE}$username${NC}"
        fi
    done < "$USERS_FILE"
    
    echo ""
    echo -n -e "${YELLOW}Нажмите любую клавишу, чтобы вернуться в меню...${NC}"
    read -n1 -s
}

# Функция удаления пользователя
delete_user() {
    # Проверяем, есть ли пользователи
    if [[ ! -f "$USERS_FILE" ]] || [[ ! -s "$USERS_FILE" ]]; then
        clear_screen
        echo -e "${YELLOW}Список пользователей пуст.${NC}"
        echo ""
        echo -n -e "${YELLOW}Нажмите любую клавишу, чтобы вернуться в меню...${NC}"
        read -n1 -s
        return 0
    fi
    
    # Цикл ввода логина для удаления
    while true; do
        clear_screen
        
        # Выводим список пользователей
        echo -e "${CYAN}Список пользователей:${NC}"
        echo ""
        
        local users=()
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                username=$(echo "$line" | awk '{print $1}')
                users+=("$username")
                echo -e "${WHITE}$username${NC}"
            fi
        done < "$USERS_FILE"
        
        echo ""
        echo -n -e "${BLUE}Введите логин пользователя для удаления (пустая строка для возврата в меню): ${NC}"
        read -r username_to_delete
        
        # Если введена пустая строка, возвращаемся в меню
        if [[ -z "$username_to_delete" ]]; then
            return 0
        fi
        
        # Проверяем, существует ли такой пользователь
        local found=false
        for user in "${users[@]}"; do
            if [[ "$user" == "$username_to_delete" ]]; then
                found=true
                break
            fi
        done
        
        if [[ "$found" == true ]]; then
            # Удаляем пользователя из файла
            # Создаем временный файл без удаляемого пользователя
            > "$USERS_FILE.tmp"  # Создаем пустой временный файл
            while IFS= read -r line || [[ -n "$line" ]]; do
                if [[ -n "$line" ]]; then
                    username=$(echo "$line" | awk '{print $1}')
                    if [[ "$username" != "$username_to_delete" ]]; then
                        echo "$line" >> "$USERS_FILE.tmp"
                    fi
                fi
            done < "$USERS_FILE"
            
            # Заменяем оригинальный файл временным
            mv "$USERS_FILE.tmp" "$USERS_FILE"
            
            clear_screen
            echo -e "${GREEN}Пользователь '$username_to_delete' успешно удален!${NC}"
            echo ""
            echo -n -e "${YELLOW}Нажмите Enter для возврата в меню...${NC}"
            read -r
            return 0
        else
            clear_screen
            echo -e "${RED}Ошибка: Пользователь '$username_to_delete' не существует.${NC}"
            echo ""
            echo -n -e "${YELLOW}Нажмите Enter для повторного ввода...${NC}"
            read -r
            # Продолжаем цикл для повторного ввода
        fi
    done
}

# Основной цикл
while true; do
    show_menu
    read -r choice
    case "$choice" in
        1)
            create_user
            ;;
        2)
            show_users
            ;;
        3)
            delete_user
            ;;
        4)
            clear_screen
            echo -e "${GREEN}Выход...${NC}"
            sleep 1
            clear
            exit 0
            ;;
        *)
            clear_screen
            echo -e "${RED}Неверный выбор. Попробуйте снова.${NC}"
            echo ""
            echo -n -e "${YELLOW}Нажмите Enter для продолжения...${NC}"
            read -r
            ;;
    esac
done