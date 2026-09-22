# -*- coding: utf-8 -*-
"""
ТЕСТ ПОВНОЇ ПРОФЕСІЙНОЇ СХЕМИ V5
6 силосів, 10 конвеєрів, 6 норій з Smart Anchors!
"""
import sys
import asyncio

sys.path.insert(0, "D:/autocad project/autocad-mcp")

from server_full_schema_v5_PRO import draw_complete_schema_v5_pro, clear_all

print("="*70)
print("TEST POVNOYI PROFESIJNOYI SHEMY V5")
print("="*70)

async def main():
    print("\n1. Ochyshchennya...")
    result = await clear_all()
    print(f"   {result}")

    print("\n2. Malyuvannya POVNOYI SHEMY V5...")
    print("   (ce zayme 90-120 sekund)")
    result = await draw_complete_schema_v5_pro()
    print(f"\n{result}")

    print("\n" + "="*70)
    print("TEST ZAVERSENO!")
    print("="*70)
    print("\nPEREVIR AUTOCAD!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\nPOMYLKA: {e}")
        import traceback
        traceback.print_exc()
