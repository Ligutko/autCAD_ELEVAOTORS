"""
Create Silo Family Automatically via Revit API

Створює параметричну Family силосу МСВУ програмно через Revit API.
"""

from auto_mcp_wrapper import send_command_to_revit
import json


def create_silo_family_via_api():
    """
    Створює Silo Family через спеціальну команду

    Family параметри:
    - Diameter (мм) - діаметр силосу
    - Height (мм) - висота циліндричної частини
    - Tag (текст) - позначка обладнання
    - Volume (м3) - об'єм (обчислюється автоматично)
    """

    print("="*70)
    print("CREATING SILO FAMILY PROGRAMMATICALLY")
    print("="*70)
    print()

    # Відправляємо команду на створення Family
    result = send_command_to_revit(
        action='create_silo_family',
        family_name='Silo_MSVU_220',
        template='Metric Generic Model'
    )

    print("[RESULT]", json.dumps(result, indent=2, ensure_ascii=False))

    if result.get('status') == 'success':
        print("\n✅ SUCCESS! Silo Family created!")
        print(f"Family file: {result.get('family_path')}")
        return True
    else:
        print(f"\n❌ FAILED: {result.get('message')}")
        return False


if __name__ == '__main__':
    print("ВАЖЛИВО: Перед запуском:")
    print("  1. Відкрий Revit 2026")
    print("  2. Створи НОВИЙ Family файл:")
    print("     File → New → Family")
    print("     Template: Metric Generic Model.rft")
    print("  3. Натисни StartListener в Revit")
    print("  4. Запусти цей скрипт")
    print()
    input("Press Enter коли готово...")
    print()

    create_silo_family_via_api()
