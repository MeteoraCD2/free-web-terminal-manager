#!/bin/bash

pwd
while true; do
    # Выводим приглашение ко вводу
    echo -n "Введите команду (или 'exit' для выхода): "
    
    # Считываем введённую команду
    read command

    # Проверяем, не хочет ли пользователь выйти
    if [[ "$command" == "exit" ]]; then
        echo "Выход..."
        break
    fi

    # Выполняем команду
    if [[ -n "$command" ]]; then
        echo "Выполняется: $command"
        eval "$command"
    else
        echo "Пустая команда, попробуйте снова."
    fi
done