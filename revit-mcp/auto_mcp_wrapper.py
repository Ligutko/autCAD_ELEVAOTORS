"""
Auto MCP Wrapper - Автоматична обробка команд

Цей wrapper автоматично:
1. Приймає команди від Claude через MCP
2. Записує в commands_queue
3. Чекає результату від Revit listener
4. Повертає результат назад в MCP

Revit listener просто обробляє команди коли його викликають.
Цей wrapper автоматизує весь процес.
"""

import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

# Шляхи
PROJECT_ROOT = Path(r"D:\autocad project")
COMMANDS_QUEUE = PROJECT_ROOT / "revit-mcp" / "commands_queue"
RESULTS_QUEUE = PROJECT_ROOT / "revit-mcp" / "results_queue"

# Timeout для очікування результату
COMMAND_TIMEOUT = 30  # seconds
POLL_INTERVAL = 0.2   # seconds


def send_command_to_revit(action: str, **params) -> Dict[str, Any]:
    """
    Відправляє команду в Revit та чекає результату

    Args:
        action: Тип команди (ping, load_family, place_family_instance, etc.)
        **params: Параметри команди

    Returns:
        Результат виконання команди
    """

    # Створити ID команди
    cmd_id = str(uuid.uuid4())

    # Створити команду
    cmd = {
        'id': cmd_id,
        'action': action,
        **params
    }

    # Записати команду в чергу
    COMMANDS_QUEUE.mkdir(parents=True, exist_ok=True)
    cmd_file = COMMANDS_QUEUE / f"cmd_{cmd_id}.json"

    with open(cmd_file, 'w', encoding='utf-8') as f:
        json.dump(cmd, f, ensure_ascii=False, indent=2)

    print(f"[AUTO] Command sent: {action} (ID: {cmd_id})")

    # Чекати результату
    result_file = RESULTS_QUEUE / f"cmd_{cmd_id}_result.json"

    start_time = time.time()
    while (time.time() - start_time) < COMMAND_TIMEOUT:

        # Перевірити чи є результат
        if result_file.exists():
            with open(result_file, 'r', encoding='utf-8') as f:
                result = json.load(f)

            # Видалити файл результату
            result_file.unlink()

            print(f"[AUTO] Result received: {result.get('status')}")
            return result

        time.sleep(POLL_INTERVAL)

    # Timeout
    # Видалити команду якщо вона не оброблена
    if cmd_file.exists():
        cmd_file.unlink()

    return {
        'status': 'error',
        'message': f'Timeout waiting for Revit listener ({COMMAND_TIMEOUT}s)'
    }


def auto_ping() -> Dict[str, Any]:
    """Ping Revit listener"""
    return send_command_to_revit('ping')


def auto_load_family(family_path: str) -> Dict[str, Any]:
    """Load Family file"""
    return send_command_to_revit('load_family', family_path=family_path)


def auto_place_family(
    family_name: str,
    symbol_name: str,
    x: float,
    y: float,
    z: float = 0,
    level_name: Optional[str] = None,
    parameters: Optional[Dict] = None
) -> Dict[str, Any]:
    """Place Family instance"""
    return send_command_to_revit(
        'place_family_instance',
        family_name=family_name,
        symbol_name=symbol_name,
        x=x, y=y, z=z,
        level_name=level_name,
        parameters=parameters or {}
    )


def auto_create_sheet(number: str, name: str) -> Dict[str, Any]:
    """Create drawing sheet"""
    return send_command_to_revit(
        'create_sheet',
        number=number,
        name=name
    )


# =============================================================================
# ТЕСТУВАННЯ
# =============================================================================

if __name__ == '__main__':
    print("="*60)
    print("AUTO MCP WRAPPER - TEST")
    print("="*60)
    print()
    print("IMPORTANT: Start Revit listener FIRST!")
    print("  1. Open Revit")
    print("  2. Click StartListener button")
    print("  3. Then run this script")
    print()
    input("Press Enter when Revit listener is ready...")
    print()

    # Test ping
    print("[TEST] Sending ping...")
    result = auto_ping()
    print(f"[TEST] Result: {json.dumps(result, indent=2)}")
    print()

    if result.get('status') == 'success':
        print("✅ SUCCESS! Auto wrapper works!")
    else:
        print("❌ FAILED! Check if Revit listener is running")
