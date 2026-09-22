#!/usr/bin/env python
"""
ELEVATOR SCHEMA GENERATOR - CLI Interface

Використання:
    python generate.py --config configs/my_project.json --output result.dxf

Приклади:
    # AUTO режим (автоматичні розрахунки)
    python generate.py --config configs/example_7silos_auto.json

    # MANUAL режим (професійне ТЗ)
    python generate.py --config configs/example_7silos_manual.json --output PROJECT_012.dxf
"""

import argparse
import sys
import json
from pathlib import Path

# Додати engine до path
sys.path.insert(0, str(Path(__file__).parent / 'engine'))

from generator import SchemaGenerator
from calculator import ElevatorCalculator


def main():
    parser = argparse.ArgumentParser(
        description='Elevator Schema Generator - Генерація креслень елеваторів',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Приклади використання:

  # Згенерувати з config (AUTO режим)
  python generate.py --config configs/example_7silos_auto.json

  # Вказати вихідний файл
  python generate.py --config my_project.json --output PROJECT_001.dxf

  # Тільки розрахунки (без генерації DXF)
  python generate.py --config my_project.json --calc-only

Режими роботи:
  AUTO   - Автоматичні розрахунки (мінімум параметрів в config)
  MANUAL - Всі параметри задані вручну (професійне ТЗ)

Докладніше: GENERATORS_COMPARISON.md
        """
    )

    parser.add_argument(
        '--config', '-c',
        required=True,
        help='Шлях до JSON config файлу'
    )

    parser.add_argument(
        '--output', '-o',
        default=None,
        help='Вихідний DXF файл (за замовчуванням: OUTPUT/elevator_generated.dxf)'
    )

    parser.add_argument(
        '--calc-only',
        action='store_true',
        help='Тільки розрахунки, без генерації DXF'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Детальний вивід'
    )

    args = parser.parse_args()

    # Перевірити config файл
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: Config file not found: {args.config}")
        return 1

    # Завантажити config
    print(f"Loading config: {args.config}")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"ERROR loading config: {e}")
        return 1

    # Визначити режим
    mode = config.get('project', {}).get('mode', 'AUTO')
    project_name = config.get('project', {}).get('name', 'Elevator Project')

    print(f"\nProject: {project_name}")
    print(f"Mode: {mode}")

    # Якщо тільки розрахунки
    if args.calc_only:
        if mode != 'AUTO':
            print("WARNING: calc-only works only in AUTO mode")
            return 1

        print("\nCalculating parameters...")
        calc = ElevatorCalculator()
        result = calc.calculate_all(config)

        print("\n" + "="*80)
        print("CALCULATION RESULTS")
        print("="*80)

        print("\nGEOMETRY:")
        for key, value in result['geometry'].items():
            print(f"  {key}: {value}")

        print("\nEQUIPMENT:")
        print(f"  Elevators: {result['equipment']['elevators']['count']} x {result['equipment']['elevators']['power_kw']} kW")
        print(f"  Conveyors: {result['equipment']['conveyors']['type']}")
        print(f"  Gates: {result['equipment']['gates']['count']} pcs")

        print("\nBOM (SPECIFICATION):")
        bom = result['bom']
        print(f"  Total capacity: {bom['summary']['total_capacity_m3']:.0f} m3 ({bom['summary']['total_capacity_tons']:.0f} tons)")
        print(f"  Throughput: {bom['summary']['throughput_tph']} t/h")

        print("\nVALIDATION:")
        print(f"  Valid: {result['validation']['valid']}")
        if result['validation']['warnings']:
            for w in result['validation']['warnings']:
                print(f"  WARNING: {w}")
        if result['validation']['errors']:
            for e in result['validation']['errors']:
                print(f"  ERROR: {e}")

        return 0

    # Визначити вихідний файл
    if args.output:
        output_file = args.output
    else:
        # За замовчуванням
        output_dir = Path('OUTPUT')
        output_dir.mkdir(exist_ok=True)

        # Ім'я з config
        safe_name = project_name.replace(' ', '_').replace('/', '_')
        output_file = str(output_dir / f"{safe_name}.dxf")

    print(f"Output: {output_file}")

    # Створити output директорію якщо потрібно
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    # Згенерувати схему
    print(f"\n{'='*80}")
    print("GENERATING SCHEMA...")
    print(f"{'='*80}\n")

    generator = SchemaGenerator()

    try:
        success = generator.generate(config, output_file)

        if success:
            print(f"\n{'='*80}")
            print("SUCCESS!")
            print(f"{'='*80}")
            print(f"\nGenerated: {output_file}")
            print(f"\nOpen in AutoCAD:")
            print(f"  {Path(output_file).absolute()}")
            return 0
        else:
            print("\nFAILED to generate schema")
            return 1

    except Exception as e:
        print(f"\nERROR: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
