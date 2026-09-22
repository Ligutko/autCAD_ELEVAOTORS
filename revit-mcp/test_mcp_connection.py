#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test MCP Connection - Перевірка з'єднання з Revit

Цей скрипт перевіряє, чи MCP Server може комунікувати з pyRevit Listener.

Запуск:
    python test_mcp_connection.py
"""

import sys
from pathlib import Path

# Додаємо шлях до MCP Server
sys.path.insert(0, str(Path(__file__).parent))

from revit_mcp_server import (
    ping_revit,
    get_revit_info,
    list_families,
    list_sheets,
    COMMANDS_QUEUE,
    RESULTS_QUEUE
)

def print_header(text):
    """Друкує заголовок"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def test_ping():
    """Тест 1: Ping Revit"""
    print_header("TEST 1: Ping Revit")

    print("Sending ping command to Revit...")
    print(f"Commands Queue: {COMMANDS_QUEUE}")
    print(f"Results Queue: {RESULTS_QUEUE}\n")

    try:
        result = ping_revit()
        print("✅ SUCCESS!")
        print(result)
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_get_info():
    """Тест 2: Отримати інформацію про проект"""
    print_header("TEST 2: Get Revit Project Info")

    try:
        info = get_revit_info()
        print("✅ SUCCESS!")
        print(f"\nProject Info:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_list_families():
    """Тест 3: Список сімей"""
    print_header("TEST 3: List Families")

    try:
        families = list_families()
        print(f"✅ SUCCESS! Found {len(families)} families\n")

        if families:
            print("First 5 families:")
            for family in families[:5]:
                print(f"  - {family['name']} ({family['category']})")
                print(f"    Types: {', '.join([s['name'] for s in family['symbols']])}")
        else:
            print("  (No families loaded)")

        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_list_sheets():
    """Тест 4: Список аркушів"""
    print_header("TEST 4: List Sheets")

    try:
        sheets = list_sheets()
        print(f"✅ SUCCESS! Found {len(sheets)} sheets\n")

        if sheets:
            print("Sheets:")
            for sheet in sheets:
                print(f"  - {sheet['number']}: {sheet['name']}")
        else:
            print("  (No sheets in project)")

        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def main():
    """Головна функція"""
    print_header("REVIT MCP SERVER - CONNECTION TEST")

    print("This script tests the connection between MCP Server and pyRevit Listener.")
    print("\nBEFORE RUNNING THIS TEST:")
    print("  1. Start Autodesk Revit")
    print("  2. Open a project (or create new)")
    print("  3. Start pyRevit Listener (click 'Start Listener' button)")
    print("\nPress Enter to continue...")
    input()

    # Запустити тести
    results = []

    results.append(("Ping Revit", test_ping()))

    if results[-1][1]:  # Якщо ping успішний
        results.append(("Get Project Info", test_get_info()))
        results.append(("List Families", test_list_families()))
        results.append(("List Sheets", test_list_sheets()))

    # Підсумок
    print_header("TEST SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"Tests passed: {passed}/{total}\n")

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {test_name}")

    print()

    if passed == total:
        print("🎉 ALL TESTS PASSED! MCP Server is working correctly!")
        print("\nNext steps:")
        print("  1. Import a DXF file: import_dxf(page_number=1)")
        print("  2. Load a Family: load_family('path/to/family.rfa')")
        print("  3. Create a sheet: create_sheet('A-01', 'Test Sheet')")
    else:
        print("⚠️ SOME TESTS FAILED!")
        print("\nTroubleshooting:")
        print("  1. Check if Revit is running")
        print("  2. Check if pyRevit Listener is started")
        print("  3. Check folder paths in revit_mcp_server.py")


if __name__ == "__main__":
    main()
