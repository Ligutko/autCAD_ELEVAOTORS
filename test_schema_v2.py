# -*- coding: utf-8 -*-
"""
ТЕСТ ВИПРАВЛЕНОЇ СХЕМИ V2
"""
import sys
import asyncio

sys.path.insert(0, "D:/autocad project/autocad-mcp")
from server_full_schema_v2 import draw_complete_schema_v2, clear_all

print("="*70)
print("ТЕСТ ВИПРАВЛЕНОЇ СХЕМИ V2")
print("="*70)

async def main():
    print("\n1. Очищаю креслення...")
    result = await clear_all()
    print(f"   {result}")

    print("\n2. Малюю ВИПРАВЛЕНУ СХЕМУ...")
    print("   ГОЛОВНЕ ВИПРАВЛЕННЯ: Силоси тепер ВИД ЗБОКУ!")
    result = await draw_complete_schema_v2()
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
