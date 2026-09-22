"""
УНІВЕРСАЛЬНИЙ ГЕНЕРАТОР технологічної схеми елеватора
Читає JSON конфігурацію і генерує схему через AutoCAD MCP Server

ВИКОРИСТАННЯ:
    python generate_from_config.py config_2_silos.json
    python generate_from_config.py config_6_silos.json
    python generate_from_config.py config_7_silos.json
"""

import json
import sys

def load_config(json_path):
    """Завантажити JSON конфігурацію"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_mcp_commands(config):
    """Згенерувати MCP команди для малювання схеми"""

    print(f"\n{'='*80}")
    print(f"ГЕНЕРАЦІЯ СХЕМИ: {config['project_name']}")
    print(f"{'='*80}\n")

    commands = []

    # 1. ОЧИСТИТИ КРЕСЛЕННЯ
    print("🗑️  КРОК 1: Очистка креслення...")
    commands.append("clear_drawing()")

    # 2. СИЛОСИ
    print(f"\n🏗️  КРОК 2: Створення {len(config['equipment']['silos'])} силосів...")
    for i, silo in enumerate(config['equipment']['silos'], 1):
        print(f"   [{i}] {silo['tag']} - D={silo['diameter']}мм, H={silo['height']}мм, V={silo['capacity']}м³")
        cmd = (f"draw_silo(x={silo['x']}, y={silo['y']}, "
               f"diameter={silo['diameter']}, height={silo['height']}, "
               f"equipment_tag='{silo['tag']}', material='{silo['material']}', "
               f"capacity={silo['capacity']})")
        commands.append(cmd)

    # 3. НОРІЇ
    if 'elevators' in config['equipment']:
        print(f"\n⚙️  КРОК 3: Створення {len(config['equipment']['elevators'])} норій...")
        for i, elevator in enumerate(config['equipment']['elevators'], 1):
            print(f"   [{i}] {elevator['tag']} - H={elevator['lift_height']}мм, {elevator['capacity']}т/год")
            cmd = (f"draw_elevator(x={elevator['x']}, y={elevator['y']}, "
                   f"bucket_diameter={elevator['bucket_diameter']}, "
                   f"lift_height={elevator['lift_height']}, "
                   f"equipment_tag='{elevator['tag']}', capacity={elevator['capacity']})")
            commands.append(cmd)

    # 4. КОНВЕЄРИ
    if 'conveyors' in config['equipment']:
        print(f"\n🔄 КРОК 4: Створення {len(config['equipment']['conveyors'])} конвеєрів...")
        for i, conveyor in enumerate(config['equipment']['conveyors'], 1):
            length = abs(conveyor['end_x'] - conveyor['start_x'])
            print(f"   [{i}] {conveyor['tag']} - L={length}мм, {conveyor['capacity']}т/год")
            cmd = (f"draw_conveyor(start_x={conveyor['start_x']}, start_y={conveyor['start_y']}, "
                   f"end_x={conveyor['end_x']}, end_y={conveyor['end_y']}, "
                   f"width={conveyor['width']}, equipment_tag='{conveyor['tag']}', "
                   f"capacity={conveyor['capacity']})")
            commands.append(cmd)

    # 5. ТРУБОПРОВОДИ
    if 'pipes' in config['equipment']:
        print(f"\n🔧 КРОК 5: Створення {len(config['equipment']['pipes'])} трубопроводів...")
        for i, pipe in enumerate(config['equipment']['pipes'], 1):
            print(f"   [{i}] {pipe['tag']} - D={pipe['diameter']}мм")
            cmd = (f"draw_pipe_connection(from_x={pipe['from_x']}, from_y={pipe['from_y']}, "
                   f"to_x={pipe['to_x']}, to_y={pipe['to_y']}, "
                   f"pipe_diameter={pipe['diameter']}, tag='{pipe['tag']}')")
            commands.append(cmd)

    # ПІДСУМОК
    print(f"\n{'='*80}")
    print("📊 ПІДСУМОК:")
    print(f"   Загальний об'єм зберігання: {config['totals']['total_storage_capacity_m3']:,} м³")
    print(f"   Кількість силосів: {config['totals']['total_silos']}")
    print(f"   Загальна потужність: {config['totals']['total_power_kW']:.2f} кВт")
    print(f"{'='*80}\n")

    return commands

def main():
    if len(sys.argv) < 2:
        print("❌ Помилка: Не вказано файл конфігурації!")
        print("\nВикористання:")
        print("    python generate_from_config.py config_6_silos.json")
        sys.exit(1)

    config_file = sys.argv[1]

    try:
        # Завантажити конфігурацію
        config = load_config(config_file)

        # Згенерувати команди
        commands = generate_mcp_commands(config)

        # Зберегти команди у файл
        output_file = config_file.replace('.json', '_commands.txt')
        with open(output_file, 'w', encoding='utf-8') as f:
            for cmd in commands:
                f.write(cmd + '\n')

        print(f"✅ MCP команди збережено у: {output_file}")
        print("\n🚀 Готово! Тепер Claude виконає ці команди для малювання схеми.")

    except FileNotFoundError:
        print(f"❌ Помилка: Файл '{config_file}' не знайдено!")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Помилка: Невалідний JSON файл - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Помилка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
