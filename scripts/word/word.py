#!/usr/bin/env python3
import time
import random

# Пример словаря слов для генерации
words = [
    "автомобиль", "книга", "солнце", "океан", "компьютер",
    "программирование", "кофе", "музыка", "природа", "звезда",
    "облако", "птица", "город", "дорога", "время"
]

def generate_text(word_count=5):
    """Генерирует случайный текст из заданного количества слов."""
    return ' '.join(random.choices(words, k=word_count))

try:
    while True:
        # Генерируем и выводим текст
        print(generate_text())
        # Ждём 1 секунду
        time.sleep(5)
except KeyboardInterrupt:
    print("\nОстановлено пользователем.")