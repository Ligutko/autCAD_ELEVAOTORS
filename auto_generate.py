"""
АВТОМАТИЧНИЙ ГЕНЕРАТОР через MCP
Claude викликає цей скрипт щоб згенерувати повну схему
"""

import json
import sys

# Шлях до конфігурації (передається як аргумент)
config_path = sys.argv[1] if len(sys.argv) > 1 else "d:/autocad project/grain_system_schema.json"

# Завантажити конфігурацію
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

print(f"ГЕНЕРАЦІЯ: {config['project_name']}")
print(f"Силосів: {config['totals']['total_silos']}")
print(f"Об'єм: {config['totals']['total_storage_capacity_m3']} м³\n")

# Вивести інформацію для Claude
print("MCP_COMMANDS_START")

# Силоси
for silo in config['equipment']['silos']:
    print(f"SILO|{silo['x']}|{silo['y']}|{silo['diameter']}|{silo['height']}|{silo['tag']}|{silo['material']}|{silo['capacity']}")

# Норії
if 'elevators' in config['equipment']:
    for elev in config['equipment']['elevators']:
        print(f"ELEVATOR|{elev['x']}|{elev['y']}|{elev['bucket_diameter']}|{elev['lift_height']}|{elev['tag']}|{elev['capacity']}")

# Конвеєри
if 'conveyors' in config['equipment']:
    for conv in config['equipment']['conveyors']:
        print(f"CONVEYOR|{conv['start_x']}|{conv['start_y']}|{conv['end_x']}|{conv['end_y']}|{conv['width']}|{conv['tag']}|{conv['capacity']}")

# Труби
if 'pipes' in config['equipment']:
    for pipe in config['equipment']['pipes']:
        print(f"PIPE|{pipe['from_x']}|{pipe['from_y']}|{pipe['to_x']}|{pipe['to_y']}|{pipe['diameter']}|{pipe['tag']}")

print("MCP_COMMANDS_END")
