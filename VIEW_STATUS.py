# -*- coding: utf-8 -*-
"""
ПЕРЕГЛЯД СТАНУ СИСТЕМИ
Показує які файли оброблені та які операції застосовані
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from STATE_MANAGER import StateManager


def main():
    manager = StateManager("d:/autocad project")

    # Load existing state
    if manager.state_file.exists():
        import json
        with open(manager.state_file, 'r', encoding='utf-8') as f:
            manager.state = json.load(f)
    else:
        print("❌ State файл не знайдено!")
        print("   Запустіть спочатку SAFE_RESIZE_SYSTEM.py")
        return

    # Display full status
    manager.print_status()


if __name__ == "__main__":
    main()
