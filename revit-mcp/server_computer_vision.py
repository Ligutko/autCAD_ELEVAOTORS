"""
Revit Computer Vision MCP Server

Дозволяє Claude бачити та керувати Revit UI через screenshots та автоматизацію.
Аналог Playwright але для desktop застосунків.

Author: Claude Code
Version: 1.0.0
"""

from mcp.server.fastmcp import FastMCP
import pyautogui
import pygetwindow as gw
from PIL import Image
import base64
import io
from pathlib import Path
from typing import Optional, Tuple
import json
import time

# Initialize MCP server
mcp = FastMCP("revit-computer-vision")

# Configuration
SCREENSHOT_DIR = Path(r"D:\autocad project\revit-mcp\screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


def find_revit_window() -> Optional[gw.Window]:
    """Знайти вікно Revit"""
    windows = gw.getAllWindows()

    for window in windows:
        if 'Autodesk Revit' in window.title:
            return window

    return None


def capture_revit_screenshot(region: Optional[Tuple[int, int, int, int]] = None) -> str:
    """
    Зробити screenshot Revit вікна

    Args:
        region: (x, y, width, height) для crop, None = весь екран

    Returns:
        Base64 encoded PNG image
    """
    revit_window = find_revit_window()

    if revit_window:
        # Activate window
        try:
            revit_window.activate()
            time.sleep(0.2)  # Wait for activation
        except:
            pass

        # Screenshot region або весь екран
        if region:
            screenshot = pyautogui.screenshot(region=region)
        else:
            # Screenshot всього вікна Revit
            screenshot = pyautogui.screenshot(region=(
                revit_window.left,
                revit_window.top,
                revit_window.width,
                revit_window.height
            ))
    else:
        # Якщо Revit не знайдено - весь екран
        screenshot = pyautogui.screenshot(region=region)

    # Convert to base64
    buffered = io.BytesIO()
    screenshot.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    return img_str


@mcp.tool()
def take_screenshot(
    save_file: bool = True,
    region: Optional[str] = None
) -> str:
    """
    Зробити screenshot Revit вікна

    Args:
        save_file: Зберегти файл на диск
        region: JSON string "(x, y, width, height)" для crop

    Returns:
        Шлях до збереженого файлу або base64
    """
    # Parse region if provided
    region_tuple = None
    if region:
        try:
            region_tuple = tuple(json.loads(region))
        except:
            pass

    # Take screenshot
    img_base64 = capture_revit_screenshot(region=region_tuple)

    if save_file:
        # Save to file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = SCREENSHOT_DIR / f"revit_{timestamp}.png"

        # Decode and save
        img_data = base64.b64decode(img_base64)
        with open(filename, 'wb') as f:
            f.write(img_data)

        return str(filename)
    else:
        return f"data:image/png;base64,{img_base64}"


@mcp.tool()
def get_revit_info() -> dict:
    """
    Отримати інформацію про вікно Revit

    Returns:
        Позиція, розмір, статус вікна
    """
    revit_window = find_revit_window()

    if revit_window:
        return {
            'found': True,
            'title': revit_window.title,
            'position': {
                'left': revit_window.left,
                'top': revit_window.top,
                'width': revit_window.width,
                'height': revit_window.height
            },
            'is_active': revit_window.isActive,
            'is_maximized': revit_window.isMaximized
        }
    else:
        return {
            'found': False,
            'message': 'Revit window not found'
        }


@mcp.tool()
def click_at(x: int, y: int, clicks: int = 1, button: str = 'left') -> str:
    """
    Клікнути мишкою в координатах

    Args:
        x, y: Координати екрану
        clicks: Кількість кліків (1 або 2)
        button: 'left', 'right', 'middle'

    Returns:
        Статус
    """
    try:
        pyautogui.click(x, y, clicks=clicks, button=button)
        return f"Clicked at ({x}, {y}) with {button} button, {clicks} times"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def type_text(text: str, interval: float = 0.05) -> str:
    """
    Ввести текст

    Args:
        text: Текст для введення
        interval: Затримка між символами (секунди)

    Returns:
        Статус
    """
    try:
        pyautogui.write(text, interval=interval)
        return f"Typed: {text}"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def press_key(key: str, presses: int = 1) -> str:
    """
    Натиснути клавішу

    Args:
        key: Назва клавіші ('enter', 'esc', 'tab', 'delete', 'f1', etc.)
        presses: Кількість натискань

    Returns:
        Статус
    """
    try:
        pyautogui.press(key, presses=presses)
        return f"Pressed key: {key} ({presses} times)"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def hotkey(*keys: str) -> str:
    """
    Натиснути комбінацію клавіш

    Args:
        keys: Клавіші для одночасного натискання (наприклад 'ctrl', 'c')

    Returns:
        Статус
    """
    try:
        pyautogui.hotkey(*keys)
        return f"Pressed hotkey: {' + '.join(keys)}"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def move_mouse(x: int, y: int, duration: float = 0.5) -> str:
    """
    Перемістити курсор миші

    Args:
        x, y: Координати
        duration: Тривалість руху (секунди)

    Returns:
        Статус
    """
    try:
        pyautogui.moveTo(x, y, duration=duration)
        return f"Moved mouse to ({x}, {y})"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_screen_size() -> dict:
    """
    Отримати розмір екрану

    Returns:
        Ширина та висота
    """
    size = pyautogui.size()
    return {
        'width': size.width,
        'height': size.height
    }


@mcp.tool()
def activate_revit() -> str:
    """
    Активувати вікно Revit (вивести на передній план)

    Returns:
        Статус
    """
    revit_window = find_revit_window()

    if revit_window:
        try:
            revit_window.activate()
            time.sleep(0.3)
            return f"Activated Revit window: {revit_window.title}"
        except Exception as e:
            return f"Error activating window: {str(e)}"
    else:
        return "Error: Revit window not found"


if __name__ == "__main__":
    # Run MCP server
    mcp.run()
