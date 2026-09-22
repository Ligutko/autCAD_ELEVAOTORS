# -*- coding: utf-8 -*-
"""
ПРОСТИЙ ТЕСТ - МАЛЮЄМО БАЗОВУ ФІГУРУ БЕЗ СКЛАДНИХ LISP
"""
import sys
import io
import time
import win32gui
import keyboard

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def find_autocad_window():
    windows = []
    def enum_callback(hwnd, result):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            if "autocad" in window_text.lower() and ("drawing" in window_text.lower() or ".dwg" in window_text.lower()):
                result.append((hwnd, window_text))
        return True
    win32gui.EnumWindows(enum_callback, windows)
    return windows[0] if windows else (None, None)

def execute_command(hwnd, command, wait_time=0.5):
    try:
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.3)

        keyboard.press_and_release('esc')
        time.sleep(0.2)

        keyboard.write(command)
        time.sleep(0.1)
        keyboard.press_and_release('enter')
        time.sleep(wait_time)

        return True
    except Exception as e:
        print(f"ПОМИЛКА: {e}")
        return False

print("="*70)
print("ПРОСТИЙ ТЕСТ - МАЛЮЄМО КВАДРАТ ТА КОЛО")
print("="*70)

hwnd, title = find_autocad_window()
if not hwnd:
    print("ПОМИЛКА: AutoCAD не знайдено!")
    sys.exit(1)

print(f"\nПідключено до: {title}")

# Очищаємо екран
print("\n1. Очищаю командний рядок...")
execute_command(hwnd, '', wait_time=0.3)

# ТЕСТ 1: Малюємо квадрат через RECTANG
print("\n2. Малюю КВАДРАТ через команду RECTANG...")
execute_command(hwnd, '_RECTANG', wait_time=0.3)
execute_command(hwnd, '0,0', wait_time=0.2)
execute_command(hwnd, '5000,5000', wait_time=0.5)

print("   OK: Квадрат 5000x5000 намальовано")

# ТЕСТ 2: Малюємо коло
print("\n3. Малюю КОЛО через команду CIRCLE...")
execute_command(hwnd, '_CIRCLE', wait_time=0.3)
execute_command(hwnd, '2500,2500', wait_time=0.2)
execute_command(hwnd, '1500', wait_time=0.5)

print("   OK: Коло радіусом 1500 намальовано")

# ТЕСТ 3: Додаємо текст
print("\n4. Додаю ТЕКСТ...")
execute_command(hwnd, '_TEXT', wait_time=0.3)
execute_command(hwnd, '2500,2500', wait_time=0.2)
execute_command(hwnd, '500', wait_time=0.2)
execute_command(hwnd, '0', wait_time=0.2)
execute_command(hwnd, 'TEST OK', wait_time=0.5)

print("   OK: Текст додано")

# ZOOM EXTENTS
print("\n5. ZOOM EXTENTS для перегляду...")
execute_command(hwnd, '_ZOOM', wait_time=0.2)
execute_command(hwnd, 'E', wait_time=0.5)

print("\n" + "="*70)
print("ГОТОВО! ПЕРЕВІР AUTOCAD!")
print("="*70)
print("\nМає бути:")
print("  - Квадрат 5000x5000")
print("  - Коло в центрі")
print("  - Текст 'TEST OK'")
print("\nЯкщо бачиш - базові команди працюють!")
print("Якщо ні - скажи що бачиш!")
