# -*- coding: utf-8 -*-
"""
ТЕСТ ПОВНОЇ ТЕХНОЛОГІЧНОЇ СХЕМИ
"""
import sys
import asyncio

sys.path.insert(0, "D:/autocad project/autocad-mcp")
from server_full_schema import draw_complete_technological_schema, clear_all

print("="*70)
print("ТЕСТ ПОВНОЇ ТЕХНОЛОГІЧНОЇ СХЕМИ")
print("="*70)

async def main():
    # Очищаємо креслення
    print("\n1. Очищаю креслення...")
    result = await clear_all()
    print(f"   {result}")

    # Малюємо повну схему
    print("\n2. Малюю ПОВНУ ТЕХНОЛОГІЧНУ СХЕМУ...")
    print("   (це може зайняти 30-60 секунд)")
    result = await draw_complete_technological_schema()
    print(f"\n{result}")

    print("\n" + "="*70)
    print("ТЕСТ ЗАВЕРШЕНО!")
    print("="*70)
    print("\nПЕРЕВІР AUTOCAD!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\nПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()
