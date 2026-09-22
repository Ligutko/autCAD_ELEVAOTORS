#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Revit MCP Server - Model Context Protocol Server for Revit Automation

Цей сервер дозволяє Claude Code керувати Autodesk Revit через pyRevit listener.
Використовується file-based queue для комунікації (простіший підхід для прототипу).

Автор: Claude Code (Sonnet 4.5)
Дата: 2026-01-01
Версія: 0.1.0 (Prototype)
"""

import os
import sys
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional

# Додаємо FastMCP (якщо встановлено)
try:
    from mcp.server import FastMCP
except ImportError:
    print("ERROR: FastMCP not installed. Run: pip install mcp")
    sys.exit(1)

# =============================================================================
# КОНФІГУРАЦІЯ
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
COMMANDS_QUEUE = PROJECT_ROOT / "revit-mcp" / "commands_queue"
RESULTS_QUEUE = PROJECT_ROOT / "revit-mcp" / "results_queue"
DXF_SOURCE = PROJECT_ROOT / "FINAL_DXF_PERFECT_V7"

# Створити папки якщо не існують
COMMANDS_QUEUE.mkdir(parents=True, exist_ok=True)
RESULTS_QUEUE.mkdir(parents=True, exist_ok=True)

# Timeout для очікування результату від Revit (секунди)
COMMAND_TIMEOUT = 30

# =============================================================================
# УТИЛІТАРНІ ФУНКЦІЇ
# =============================================================================

def generate_command_id() -> str:
    """Генерує унікальний ID для команди"""
    return str(uuid.uuid4())[:8]


def write_command(cmd_id: str, command_data: Dict[str, Any]) -> None:
    """
    Записує команду в чергу для pyRevit listener

    Args:
        cmd_id: Унікальний ID команди
        command_data: Дані команди (action, parameters)
    """
    command_data['cmd_id'] = cmd_id
    command_data['timestamp'] = time.time()

    cmd_file = COMMANDS_QUEUE / f"cmd_{cmd_id}.json"
    with open(cmd_file, 'w', encoding='utf-8') as f:
        json.dump(command_data, f, ensure_ascii=False, indent=2)


def wait_for_result(cmd_id: str, timeout: int = COMMAND_TIMEOUT) -> Dict[str, Any]:
    """
    Очікує результат від pyRevit listener

    Args:
        cmd_id: ID команди
        timeout: Максимальний час очікування (секунди)

    Returns:
        Результат виконання команди

    Raises:
        TimeoutError: Якщо результат не отримано вчасно
    """
    result_file = RESULTS_QUEUE / f"cmd_{cmd_id}_result.json"
    start_time = time.time()

    while time.time() - start_time < timeout:
        if result_file.exists():
            with open(result_file, 'r', encoding='utf-8') as f:
                result = json.load(f)

            # Видалити файл результату
            result_file.unlink()

            # Видалити команду з черги (якщо ще там)
            cmd_file = COMMANDS_QUEUE / f"cmd_{cmd_id}.json"
            if cmd_file.exists():
                cmd_file.unlink()

            return result

        time.sleep(0.1)  # Перевірка кожні 100ms

    raise TimeoutError(
        f"Timeout waiting for Revit response (cmd_id: {cmd_id}). "
        f"Is pyRevit listener running?"
    )


def cleanup_old_files(max_age_hours: int = 24) -> None:
    """Очищує старі файли з черг"""
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600

    for queue_dir in [COMMANDS_QUEUE, RESULTS_QUEUE]:
        for file_path in queue_dir.glob("*.json"):
            file_age = current_time - file_path.stat().st_mtime
            if file_age > max_age_seconds:
                file_path.unlink()


# =============================================================================
# MCP SERVER
# =============================================================================

mcp = FastMCP("Revit Automation Server")


# =============================================================================
# СИСТЕМНІ ІНСТРУМЕНТИ
# =============================================================================

@mcp.tool()
def ping_revit() -> str:
    """
    Перевірити, чи Revit listener активний та відповідає

    Returns:
        Повідомлення зі статусом Revit
    """
    cmd_id = generate_command_id()

    write_command(cmd_id, {
        'action': 'ping'
    })

    try:
        result = wait_for_result(cmd_id, timeout=5)

        if result.get('status') == 'ok':
            return (
                f"✅ Revit listener is ACTIVE!\n"
                f"Version: {result.get('revit_version', 'Unknown')}\n"
                f"Document: {result.get('document_name', 'No document open')}\n"
                f"Response time: {result.get('response_time', 0):.2f}s"
            )
        else:
            return f"⚠️ Revit responded with error: {result.get('message', 'Unknown error')}"

    except TimeoutError:
        return (
            "❌ Revit listener NOT RESPONDING!\n"
            "Please ensure:\n"
            "1. Revit is running\n"
            "2. pyRevit is installed\n"
            "3. revit_listener.py is started in Revit"
        )


@mcp.tool()
def get_revit_info() -> dict:
    """
    Отримати детальну інформацію про поточний стан Revit

    Returns:
        Словник з інформацією про Revit проект
    """
    cmd_id = generate_command_id()

    write_command(cmd_id, {
        'action': 'get_info'
    })

    result = wait_for_result(cmd_id)

    if result.get('status') == 'ok':
        return result.get('data', {})
    else:
        raise Exception(f"Error getting Revit info: {result.get('message')}")


# =============================================================================
# РОБОТА З DXF/CAD ФАЙЛАМИ
# =============================================================================

@mcp.tool()
def import_dxf(
    page_number: int,
    as_link: bool = False,
    preserve_colors: bool = True,
    view_name: Optional[str] = None
) -> str:
    """
    Імпортувати DXF файл в Revit

    Args:
        page_number: Номер сторінки (1-12) з FINAL_DXF_PERFECT_V7
        as_link: True = link (посилання), False = import (вставка)
        preserve_colors: Зберегти кольори з DXF (RGB шари)
        view_name: Назва виду для імпорту (None = активний вигляд)

    Returns:
        Повідомлення про результат імпорту
    """
    if not 1 <= page_number <= 12:
        return f"❌ Error: page_number must be 1-12, got {page_number}"

    dxf_file = DXF_SOURCE / f"page_{page_number:02d}.dxf"

    if not dxf_file.exists():
        return f"❌ Error: DXF file not found: {dxf_file}"

    cmd_id = generate_command_id()

    write_command(cmd_id, {
        'action': 'import_dxf',
        'file_path': str(dxf_file),
        'page_number': page_number,
        'as_link': as_link,
        'preserve_colors': preserve_colors,
        'view_name': view_name
    })

    result = wait_for_result(cmd_id, timeout=60)  # DXF import може бути довгим

    if result.get('status') == 'ok':
        data = result.get('data', {})
        return (
            f"✅ Successfully imported Page {page_number:02d}\n"
            f"Import ID: {data.get('import_id')}\n"
            f"Type: {'Link' if as_link else 'Embedded'}\n"
            f"View: {data.get('view_name', 'Unknown')}"
        )
    else:
        return f"❌ Import failed: {result.get('message', 'Unknown error')}"


@mcp.tool()
def analyze_imported_geometry(import_id: str) -> dict:
    """
    Проаналізувати імпортовану геометрію (LIDAR-підхід)

    Виконує кластеризацію ліній по шарах та кольорах,
    знаходить потенційні об'єкти (силоси, конвеєри тощо)

    Args:
        import_id: ID ImportInstance з Revit

    Returns:
        Словник з результатами аналізу:
        {
            'layers': {layer_name: entity_count},
            'clusters': [{center, line_count, type}, ...],
            'bounding_box': {min, max}
        }
    """
    cmd_id = generate_command_id()

    write_command(cmd_id, {
        'action': 'analyze_geometry',
        'import_id': import_id
    })

    result = wait_for_result(cmd_id, timeout=120)  # Аналіз може бути довгим

    if result.get('status') == 'ok':
        return result.get('data', {})
    else:
        raise Exception(f"Analysis failed: {result.get('message')}")


@mcp.tool()
def list_import_instances() -> list:
    """
    Отримати список всіх імпортованих CAD файлів в проекті

    Returns:
        Список словників з інформацією про ImportInstance
    """
    cmd_id = generate_command_id()

    write_command(cmd_id, {
        'action': 'list_imports'
    })

    result = wait_for_result(cmd_id)

    if result.get('status') == 'ok':
        return result.get('data', [])
    else:
        raise Exception(f"Error listing imports: {result.get('message')}")


# =============================================================================
# РОБОТА З FAMILIES (ПАРАМЕТРИЧНІ ОБ'ЄКТИ)
# =============================================================================

@mcp.tool()
def load_family(family_path: str) -> dict:
    """
    Завантажити Family (.rfa файл) в поточний проект

    Args:
        family_path: Шлях до .rfa файлу

    Returns:
        Інформація про завантажену сім'ю
    """
    cmd_id = generate_command_id()

    write_command(cmd_id, {
        'action': 'load_family',
        'family_path': family_path
    })

    result = wait_for_result(cmd_id)

    if result.get('status') == 'ok':
        data = result.get('data', {})
        return {
            'family_name': data.get('family_name'),
            'family_id': data.get('family_id'),
            'symbols': data.get('symbols', [])
        }
    else:
        raise Exception(f"Error loading family: {result.get('message')}")


@mcp.tool()
def place_family_instance(
    family_name: str,
    symbol_name: str,
    x: float,
    y: float,
    z: float = 0.0,
    level_name: Optional[str] = None,
    parameters: Optional[dict] = None
) -> dict:
    """
    Розмістити екземпляр Family в проекті

    Args:
        family_name: Ім'я сім'ї (напр. "Silo_MSVU_220")
        symbol_name: Ім'я типу (напр. "Default", "Type 1")
        x, y, z: Координати в МІЛІМЕТРАХ (конвертуються в фути автоматично)
        level_name: Назва рівня (None = Level 1)
        parameters: Словник параметрів для встановлення
                   Приклад: {"Diameter": 22000, "Height": 21422, "Tag": "МСВУ-1"}

    Returns:
        Інформація про створений екземпляр
    """
    cmd_id = generate_command_id()

    write_command(cmd_id, {
        'action': 'place_family',
        'family_name': family_name,
        'symbol_name': symbol_name,
        'x': x,
        'y': y,
        'z': z,
        'level_name': level_name,
        'parameters': parameters or {}
    })

    result = wait_for_result(cmd_id)

    if result.get('status') == 'ok':
        data = result.get('data', {})
        return {
            'instance_id': data.get('instance_id'),
            'location': data.get('location'),
            'parameters_set': data.get('parameters_set', [])
        }
    else:
        raise Exception(f"Error placing family: {result.get('message')}")


@mcp.tool()
def list_families() -> list:
    """
    Отримати список всіх завантажених сімей в проекті

    Returns:
        Список сімей з типами та параметрами
    """
    cmd_id = generate_command_id()

    write_command(cmd_id, {
        'action': 'list_families'
    })

    result = wait_for_result(cmd_id)

    if result.get('status') == 'ok':
        return result.get('data', [])
    else:
        raise Exception(f"Error listing families: {result.get('message')}")


# =============================================================================
# РОБОТА З SHEETS (АРКУШІ КРЕСЛЕНЬ)
# =============================================================================

@mcp.tool()
def create_sheet(
    number: str,
    name: str,
    titleblock_name: str = "A0 metric"
) -> dict:
    """
    Створити новий аркуш креслення

    Args:
        number: Номер аркуша (напр. "А-01", "T-001")
        name: Назва аркуша (напр. "Схема технологічного процесу")
        titleblock_name: Назва рамки (A0, A1, A2, ...)

    Returns:
        Інформація про створений аркуш
    """
    cmd_id = generate_command_id()

    write_command(cmd_id, {
        'action': 'create_sheet',
        'number': number,
        'name': name,
        'titleblock_name': titleblock_name
    })

    result = wait_for_result(cmd_id)

    if result.get('status') == 'ok':
        return result.get('data', {})
    else:
        raise Exception(f"Error creating sheet: {result.get('message')}")


@mcp.tool()
def place_view_on_sheet(
    sheet_number: str,
    view_name: str,
    x: float,
    y: float
) -> str:
    """
    Розмістити вигляд на аркуші

    Args:
        sheet_number: Номер аркуша (напр. "А-01")
        view_name: Назва виду для розміщення
        x, y: Координати на аркуші (мм)

    Returns:
        Повідомлення про результат
    """
    cmd_id = generate_command_id()

    write_command(cmd_id, {
        'action': 'place_view',
        'sheet_number': sheet_number,
        'view_name': view_name,
        'x': x,
        'y': y
    })

    result = wait_for_result(cmd_id)

    if result.get('status') == 'ok':
        return f"✅ View '{view_name}' placed on sheet {sheet_number}"
    else:
        return f"❌ Error: {result.get('message')}"


@mcp.tool()
def list_sheets() -> list:
    """
    Отримати список всіх аркушів в проекті

    Returns:
        Список аркушів з номерами та назвами
    """
    cmd_id = generate_command_id()

    write_command(cmd_id, {
        'action': 'list_sheets'
    })

    result = wait_for_result(cmd_id)

    if result.get('status') == 'ok':
        return result.get('data', [])
    else:
        raise Exception(f"Error listing sheets: {result.get('message')}")


# =============================================================================
# ЕКСПОРТ
# =============================================================================

@mcp.tool()
def export_sheets_to_pdf(
    sheet_numbers: list,
    output_path: str,
    combined: bool = True
) -> str:
    """
    Експортувати аркуші в PDF

    Args:
        sheet_numbers: Список номерів аркушів (напр. ["А-01", "А-02"])
        output_path: Шлях для збереження PDF
        combined: True = один PDF файл, False = окремі файли

    Returns:
        Шлях до створеного PDF
    """
    cmd_id = generate_command_id()

    write_command(cmd_id, {
        'action': 'export_pdf',
        'sheet_numbers': sheet_numbers,
        'output_path': output_path,
        'combined': combined
    })

    result = wait_for_result(cmd_id, timeout=120)

    if result.get('status') == 'ok':
        return result.get('data', {}).get('pdf_path', output_path)
    else:
        raise Exception(f"Export failed: {result.get('message')}")


# =============================================================================
# РОБОТА З JSON КОНФІГУРАЦІЄЮ
# =============================================================================

@mcp.tool()
def build_from_config(config_path: str) -> dict:
    """
    Побудувати проект з JSON конфігурації (як config_6_silos.json)

    Читає конфігурацію та автоматично:
    1. Завантажує необхідні Families
    2. Розміщує обладнання (силоси, конвеєри, норії)
    3. Створює з'єднання (труби)
    4. Генерує аркуші

    Args:
        config_path: Шлях до JSON конфігурації

    Returns:
        Звіт про виконання
    """
    cmd_id = generate_command_id()

    write_command(cmd_id, {
        'action': 'build_from_config',
        'config_path': config_path
    })

    result = wait_for_result(cmd_id, timeout=300)  # 5 хвилин для великих проектів

    if result.get('status') == 'ok':
        return result.get('data', {})
    else:
        raise Exception(f"Build failed: {result.get('message')}")


# =============================================================================
# ГОЛОВНА ФУНКЦІЯ
# =============================================================================

def main():
    """Запуск MCP сервера"""
    print("=" * 70)
    print("  REVIT MCP SERVER v0.1.0")
    print("  Model Context Protocol Server for Autodesk Revit")
    print("=" * 70)
    print()
    print(f"Commands Queue: {COMMANDS_QUEUE}")
    print(f"Results Queue:  {RESULTS_QUEUE}")
    print()
    print("Waiting for Claude Code to connect...")
    print()

    # Очистити старі файли
    cleanup_old_files(max_age_hours=1)

    # Запустити MCP сервер
    mcp.run()


if __name__ == "__main__":
    main()
