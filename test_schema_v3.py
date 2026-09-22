# -*- coding: utf-8 -*-
"""
ТЕСТ ПОВНОЇ СХЕМИ V3 (6 СИЛОСІВ)
"""
import sys
import asyncio

sys.path.insert(0, "D:/autocad project/autocad-mcp")
from server_full_schema_v3 import draw_complete_schema_v3, clear_all

print("="*70)
print("ТЕСТ ПОВНОЇ СХЕМИ V3 - 6 СИЛОСІВ + ЛЕГЕНДА + ШТАМП")
print("="*70)

async def main():
    print("\n1. Очищаю креслення...")
    result = await clear_all()
    print(f"   {result}")

    print("\n2. Малюю ПОВНУ СХЕМУ V3...")
    print("   НОВИНКИ:")
    print("   - 6 силосів (було 2)")
    print("   - 8 конвеєрів (було 3)")
    print("   - Легенда")
    print("   - Штамп креслення")
    print("\n   (це займе 60-90 секунд)")

    result = await draw_complete_schema_v3()
    print(f"\n{result}")

    print("\n" + "="*70)
    print("ГОТОВО! ПЕРЕВІР AUTOCAD!")
    print("="*70)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\nПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()
