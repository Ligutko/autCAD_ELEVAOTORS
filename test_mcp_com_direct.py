# -*- coding: utf-8 -*-
"""
ТЕСТУЄМО НОВИЙ MCP СЕРВЕР НА COM API - ПРЯМИЙ ВИКЛИК
"""
import sys
import asyncio

# Імпортуємо функції з нашого сервера
sys.path.insert(0, "D:/autocad project/autocad-mcp")
from server_com_api import draw_silo, draw_conveyor, draw_elevator, clear_drawing

print("="*70)
print("ТЕСТ НОВОГО MCP СЕРВЕРА (COM API) - ПРЯМИЙ ВИКЛИК")
print("="*70)

async def run_tests():
    """Запустити тести"""

    # Тест 1: Очистити креслення
    print("\n1. Очищаю креслення...")
    result = await clear_drawing()
    print(f"   {result}")

    # Тест 2: Намалювати силос
    print("\n2. Малюю силос МСВУ-220.13...")
    result = await draw_silo(
        x=0,
        y=0,
        diameter=22000,
        height=21422,
        equipment_tag="МСВУ-220.13.В12",
        material="carbon_steel",
        capacity=6381
    )
    print(f"   {result}")

    # Пауза щоб побачити
    await asyncio.sleep(1)

    # Тест 3: Намалювати норію
    print("\n3. Малюю норію H5...")
    result = await draw_elevator(
        x=30000,
        y=0,
        bucket_diameter=800,
        lift_height=33000,
        equipment_tag="H5",
        capacity=100
    )
    print(f"   {result}")

    await asyncio.sleep(1)

    # Тест 4: Намалювати конвеєр
    print("\n4. Малюю конвеєр T7...")
    result = await draw_conveyor(
        start_x=0,
        start_y=25000,
        end_x=30000,
        end_y=25000,
        width=800,
        equipment_tag="T7",
        capacity=100
    )
    print(f"   {result}")

    print("\n" + "="*70)
    print("✓ ВСІ ТЕСТИ ВИКОНАНО!")
    print("="*70)
    print("\nПеревір AutoCAD - має бути:")
    print("  ✓ Силос МСВУ-220.13.В12 (D=22m, H=21.4m, V=6381m³)")
    print("  ✓ Норія H5 (висота 33m, 100 т/год)")
    print("  ✓ Конвеєр T7 (довжина 30m, 100 т/год)")

# Запускаємо тести
if __name__ == "__main__":
    try:
        asyncio.run(run_tests())
        print("\n✓✓✓ УСПІХ! Новий MCP сервер працює через COM API!")
    except Exception as e:
        print(f"\n✗ ПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()
