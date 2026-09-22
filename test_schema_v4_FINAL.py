# -*- coding: utf-8 -*-
"""
ТЕСТ ФІНАЛЬНОЇ СХЕМИ V4
"""
import sys
import asyncio

sys.path.insert(0, "D:/autocad project/autocad-mcp")
from server_full_schema_v4_FINAL import draw_final_schema_v4, clear_all

print("="*70)
print("ТЕСТ ФІНАЛЬНОЇ СХЕМИ V4 - ПОВНА ВІДПОВІДНІСТЬ ЗРАЗКУ")
print("="*70)

async def main():
    print("\n1. Очищаю креслення...")
    result = await clear_all()
    print(f"   {result}")

    print("\n2. Малюю ФІНАЛЬНУ СХЕМУ V4...")
    print("\n   НОВИНКИ V4:")
    print("   ✓ Конвеєр T10 (правий верхній)")
    print("   ✓ Конвеєр T14 (середній правий)")
    print("   ✓ ЧЕРВОНА РАМКА навколо H1-H4")
    print("   ✓ ВСІ позначки вузлів")
    print("   ✓ Складні міжрівневі трубопроводи")
    print("\n   (це займе 90-120 секунд)")

    result = await draw_final_schema_v4()
    print(f"\n{result}")

    print("\n" + "="*70)
    print("ФІНАЛЬНА СХЕМА V4 ГОТОВА!")
    print("ПЕРЕВІР AUTOCAD!")
    print("="*70)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\nПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()
