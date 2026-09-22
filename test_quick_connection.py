# -*- coding: utf-8 -*-
"""
ШВИДКИЙ ТЕСТ ПІДКЛЮЧЕННЯ ДО AUTOCAD
"""
import sys
import io
import time
import win32gui
import keyboard

# Виправлення кодування для Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def find_autocad_window():
    """Знайти вікно AutoCAD"""
    windows = []

    def enum_callback(hwnd, result):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            text_lower = window_text.lower()
            if "autocad" in text_lower and ("drawing" in text_lower or ".dwg" in text_lower):
                result.append((hwnd, window_text))
        return True

    win32gui.EnumWindows(enum_callback, windows)
    return windows

print("="*60)
print("ШУКАЮ ВІКНО AUTOCAD...")
print("="*60)

windows = find_autocad_window()

if not windows:
    print("ПОМИЛКА: Вікно AutoCAD не знайдено!")
    print("\nПереконайся що:")
    print("1. AutoCAD запущений")
    print("2. Відкритий малюнок (Drawing1.dwg)")
    print("3. Вікно не згорнуте")
    sys.exit(1)

print(f"\nЗНАЙДЕНО {len(windows)} ВІКОН AUTOCAD:\n")
for i, (hwnd, title) in enumerate(windows, 1):
    print(f"{i}. HWND: {hwnd}")
    print(f"   Назва: {title}\n")

# Використовуємо перше вікно
hwnd, title = windows[0]
print(f"Використовую вікно: {title}")
print("="*60)

# Тест фокусу
print("\nТЕСТУЮ ФОКУС ВІКНА...")
try:
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    print("OK: Фокус встановлено!")
except Exception as e:
    print(f"ПОМИЛКА встановлення фокусу: {e}")
    sys.exit(1)

# Тест введення команди
print("\nТЕСТУЮ ВВЕДЕННЯ КОМАНДИ...")
print("Зараз в AutoCAD з'явиться команда LINE")
print("Дивись в командний рядок AutoCAD!")
time.sleep(2)

try:
    # Очищуємо командний рядок
    keyboard.press_and_release('esc')
    time.sleep(0.3)

    # Вводимо команду LINE для тесту
    keyboard.write('LINE')
    time.sleep(0.1)
    keyboard.press_and_release('enter')
    time.sleep(0.3)

    print("OK: Команда LINE відправлена!")
    print("\nТепер натисни ESC в AutoCAD щоб скасувати команду LINE")

except Exception as e:
    print(f"ПОМИЛКА введення: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("ВСІ БАЗОВІ ТЕСТИ ПРОЙДЕНО!")
print("="*60)
print("\nAutoCAD готовий до роботи!")
print("Тепер можна тестувати LISP та MCP сервер!")
