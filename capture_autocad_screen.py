# -*- coding: utf-8 -*-
"""
ЗРОБИТИ СКРІНШОТ ВІКНА AUTOCAD
"""
import sys
import io
import time
import win32gui
import win32ui
import win32con
from PIL import Image

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

def capture_window(hwnd, output_path):
    """Зробити скріншот вікна"""
    try:
        # Отримуємо розміри вікна
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        # Створюємо DC
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        # Створюємо bitmap
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)

        # Копіюємо вміст вікна
        saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

        # Зберігаємо як зображення
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)

        img = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1
        )

        img.save(output_path)

        # Очищаємо
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)

        return True, f"Скріншот збережено: {output_path}"

    except Exception as e:
        return False, f"Помилка: {str(e)}"

print("="*60)
print("РОБЮ СКРІНШОТ AUTOCAD")
print("="*60)

hwnd, title = find_autocad_window()
if not hwnd:
    print("ПОМИЛКА: AutoCAD не знайдено!")
    sys.exit(1)

print(f"\nЗнайдено: {title}")

# Активуємо вікно
win32gui.SetForegroundWindow(hwnd)
time.sleep(0.5)

output_path = "d:/autocad project/autocad_screenshot.png"
print(f"\nРоблю скріншот...")

success, message = capture_window(hwnd, output_path)

if success:
    print(f"\nУСПІХ! {message}")
    print("\nТепер Claude може подивитись на скріншот!")
else:
    print(f"\nПОМИЛКА! {message}")
