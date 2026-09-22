"""
Генерація повної технологічної схеми елеватора через AutoCAD MCP Server
Використовує інструменти: draw_silo, draw_conveyor, draw_elevator, draw_pipe_connection
"""

import json

# Завантажити конфігурацію
with open('d:/autocad project/grain_system_schema.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

print(f"=== Генерація схеми: {config['project_name']} ===\n")

# КРОК 1: Намалювати силоси
print("КРОК 1: Створення силосів...")
for i, silo in enumerate(config['equipment']['silos'], 1):
    print(f"  - Силос {i}: {silo['tag']} (D={silo['diameter']}мм, H={silo['height']}мм)")
    # MCP функція draw_silo буде викликана через Claude
    print(f"    → draw_silo(x={silo['x']}, y={silo['y']}, diameter={silo['diameter']}, "
          f"height={silo['height']}, equipment_tag='{silo['tag']}', "
          f"material='{silo['material']}', capacity={silo['capacity']})")

# КРОК 2: Намалювати норії (elevator)
print("\nКРОК 2: Створення норій...")
for i, elevator in enumerate(config['equipment']['elevators'], 1):
    print(f"  - Норія {i}: {elevator['tag']} (висота={elevator['lift_height']}мм)")
    print(f"    → draw_elevator(x={elevator['x']}, y={elevator['y']}, "
          f"bucket_diameter={elevator['bucket_diameter']}, "
          f"lift_height={elevator['lift_height']}, equipment_tag='{elevator['tag']}', "
          f"capacity={elevator['capacity']})")

# КРОК 3: Намалювати конвеєри
print("\nКРОК 3: Створення конвеєрів...")
for i, conveyor in enumerate(config['equipment']['conveyors'], 1):
    print(f"  - Конвеєр {i}: {conveyor['tag']} (ширина={conveyor['width']}мм)")
    print(f"    → draw_conveyor(start_x={conveyor['start_x']}, start_y={conveyor['start_y']}, "
          f"end_x={conveyor['end_x']}, end_y={conveyor['end_y']}, "
          f"width={conveyor['width']}, equipment_tag='{conveyor['tag']}', "
          f"capacity={conveyor['capacity']})")

# КРОК 4: Намалювати з'єднувальні труби
print("\nКРОК 4: Створення трубопроводів...")
for i, pipe in enumerate(config['equipment']['pipes'], 1):
    print(f"  - Труба {i}: {pipe['tag']} (діаметр={pipe['diameter']}мм)")
    print(f"    → draw_pipe_connection(from_x={pipe['from_x']}, from_y={pipe['from_y']}, "
          f"to_x={pipe['to_x']}, to_y={pipe['to_y']}, "
          f"pipe_diameter={pipe['diameter']}, tag='{pipe['tag']}')")

print("\n=== ПІДСУМОК ===")
print(f"Загальний об'єм зберігання: {config['totals']['total_storage_capacity_m3']} м³")
print(f"Кількість силосів: {config['totals']['total_silos']}")
print(f"Загальна потужність: {config['totals']['total_power_kW']} кВт")
print("\n✅ Конфігурація готова! Тепер Claude виконає MCP команди для малювання.")
