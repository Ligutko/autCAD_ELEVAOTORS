# -*- coding: utf-8 -*-
"""
БЕЗПЕЧНА СИСТЕМА МАСШТАБУВАННЯ З STATE MANAGEMENT
Запобігає повторному масштабуванню та зберігає оригінали
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json
from pathlib import Path
from STATE_MANAGER import StateManager


def cp(*coords):
    """Create COM-compatible coordinate array"""
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


class SafeResizeSystem:
    """Безпечна система масштабування з перевірками стану"""

    def __init__(self, config_path, project_dir):
        self.config_path = config_path
        self.project_dir = project_dir
        self.state_manager = StateManager(project_dir)
        self.config = None
        self.acad = None
        self.doc = None
        self.ms = None
        self.silos = []
        self.new_positions = []

    def initialize(self):
        """Initialize system"""
        print("="*70)
        print("БЕЗПЕЧНА СИСТЕМА МАСШТАБУВАННЯ")
        print("="*70)

        # Initialize state manager
        self.state_manager.initialize()

        # Load config
        print("\n[1] Завантаження конфігурації...")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        print("    ✅ Конфігурація завантажена")

        # Load silos data
        print("\n[2] Завантаження даних силосів...")
        with open('d:/autocad project/extracted_silos_REAL_ORIGINAL.json', 'r', encoding='utf-8') as f:
            silos_data = json.load(f)
        self.silos = silos_data['silos']
        print(f"    ✅ Силосів завантажено: {len(self.silos)}")

    def connect_autocad(self, dxf_path):
        """Connect to AutoCAD and open file"""
        print(f"\n[3] Підключення до AutoCAD...")

        self.acad = win32com.client.Dispatch("AutoCAD.Application")
        docs = self.acad.Documents

        # Open the file
        print(f"    Відкриваю: {Path(dxf_path).name}")
        self.doc = docs.Open(str(dxf_path))
        self.acad.ActiveDocument = self.doc
        self.ms = self.doc.ModelSpace

        print(f"    ✅ Документ відкрито: {self.doc.Name}")
        print(f"    Об'єктів: {self.ms.Count}")

    def check_can_process(self, file_key):
        """Check if file can be processed (safety checks)"""
        print(f"\n[4] ПЕРЕВІРКА СТАНУ...")

        # Check if already processed
        if self.state_manager.is_processed(file_key):
            print("    ❌ ФАЙЛ ВЖЕ ОБРОБЛЕНО!")
            print("    Для повторної обробки використайте нову копію оригіналу.")
            return False

        # Check specific operations
        operations_to_apply = [
            "delete_red_lines",
            "scale_silos_3_4",
            "scale_silos_5_6",
            "add_7th_silo",
            "draw_connections"
        ]

        for op in operations_to_apply:
            if not self.state_manager.can_apply_operation(file_key, op):
                print(f"    ⚠ Операція '{op}' вже застосована!")
                return False

        print("    ✅ Файл можна обробляти")
        return True

    def delete_red_lines(self, file_key):
        """Delete all red objects"""
        print("\n[5] Видалення червоних ліній...")

        if not self.state_manager.can_apply_operation(file_key, "delete_red_lines"):
            print("    ⏭ Пропускаю (вже виконано)")
            return 0

        deleted = 0
        to_delete = []

        for i in range(self.ms.Count):
            try:
                obj = self.ms.Item(i)
                if hasattr(obj, 'Layer'):
                    layer = obj.Layer
                    if 'CFF-00-00' in layer:
                        to_delete.append(i)
            except:
                pass

        # Delete from end
        for idx in sorted(to_delete, reverse=True):
            try:
                self.ms.Item(idx).Delete()
                deleted += 1
            except:
                pass

        print(f"    Видалено: {deleted}")

        # Record operation
        self.state_manager.record_operation(file_key, "delete_red_lines", {"deleted": deleted})

        return deleted

    def calculate_new_positions(self):
        """Calculate new positions with correct spacing"""
        print("\n[6] Перерахунок позицій...")

        plan = self.config['resize_plan']

        # Scale factors
        scale_factors = {}
        for silo_cfg in plan['silos']:
            scale_factors[silo_cfg['id']] = silo_cfg['scale']

        # Bottom row (3-6)
        bottom_silos = [self.silos[i] for i in range(2, 6)]

        new_positions = []

        # Original spacings
        original_spacings = {
            '3-4': 47.73,
            '4-5': 88.31,
            '5-6': 47.75
        }

        for i, silo in enumerate(bottom_silos):
            silo_id = silo['number']
            scale = scale_factors.get(silo_id, 1.0)
            new_width = silo['width'] * scale

            if i == 0:
                # First - keep in place
                new_x = silo['center']['x']
            else:
                # Calculate based on spacing
                prev_silo = bottom_silos[i-1]
                prev_scale = scale_factors.get(prev_silo['number'], 1.0)

                # Use original spacing
                if i == 1:  # 3→4
                    base_spacing = original_spacings['3-4']
                elif i == 2:  # 4→5
                    base_spacing = original_spacings['4-5']
                elif i == 3:  # 5→6
                    base_spacing = original_spacings['5-6']

                new_x = new_positions[i-1]['x'] + base_spacing

            new_positions.append({
                'id': silo_id,
                'x': round(new_x, 2),
                'y': silo['center']['y'],
                'original_x': silo['center']['x'],
                'scale': scale,
                'width': new_width
            })

            print(f"    Силос #{silo_id}: x={new_x:.2f}, scale={scale}, width={new_width:.2f}")

        self.new_positions = new_positions
        return new_positions

    def find_blue_and_hatches(self, silo, radius=60):
        """Find blue objects and black hatches"""
        silo_cx = silo['center']['x']
        silo_cy = silo['center']['y']
        bounds = silo['bounds']

        blue_objects = []
        black_hatches = []

        for i in range(self.ms.Count):
            try:
                obj = self.ms.Item(i)

                if hasattr(obj, 'Layer'):
                    layer = obj.Layer

                    # Blue objects
                    if 'C00-00-FF' in layer:
                        if hasattr(obj, 'GetBoundingBox'):
                            try:
                                bbox = obj.GetBoundingBox()
                                min_p, max_p = bbox[0], bbox[1]
                                obj_cx = (min_p[0] + max_p[0]) / 2
                                obj_cy = (min_p[1] + max_p[1]) / 2

                                distance = ((obj_cx - silo_cx)**2 + (obj_cy - silo_cy)**2)**0.5

                                if distance <= radius:
                                    blue_objects.append(obj)
                            except:
                                pass

                    # Black hatches
                    if 'C00-00-00' in layer and obj.ObjectName == 'AcDbHatch':
                        if hasattr(obj, 'GetBoundingBox'):
                            try:
                                bbox = obj.GetBoundingBox()
                                min_p, max_p = bbox[0], bbox[1]
                                obj_cx = (min_p[0] + max_p[0]) / 2
                                obj_cy = (min_p[1] + max_p[1]) / 2

                                if (bounds['min_x'] <= obj_cx <= bounds['max_x'] and
                                    bounds['min_y'] <= obj_cy <= bounds['max_y']):
                                    black_hatches.append(obj)
                            except:
                                pass
            except:
                pass

        return blue_objects, black_hatches

    def transform_silo(self, silo_number, new_pos, file_key, operation_name):
        """Transform single silo"""
        print(f"\n  [{operation_name}] Силос #{silo_number}...")

        # Check if already done
        if not self.state_manager.can_apply_operation(file_key, operation_name):
            print(f"      ⏭ Пропускаю (вже виконано)")
            return 0, 0

        silo = self.silos[silo_number - 1]

        blue_objects, black_hatches = self.find_blue_and_hatches(silo, radius=60)
        all_objects = blue_objects + black_hatches

        print(f"      Синіх: {len(blue_objects)}, Чорних hatches: {len(black_hatches)}")

        base_point = cp(silo['center']['x'], silo['center']['y'], 0)

        scaled = 0
        moved = 0

        # SCALE
        if new_pos['scale'] != 1.0:
            for obj in all_objects:
                try:
                    obj.ScaleEntity(base_point, new_pos['scale'])
                    scaled += 1
                except:
                    pass

        # MOVE
        dx = new_pos['x'] - new_pos['original_x']

        if abs(dx) > 0.01:
            for obj in all_objects:
                try:
                    obj.Move(cp(0, 0, 0), cp(dx, 0, 0))
                    moved += 1
                except:
                    pass
            print(f"      Масштабовано: {scaled}, Переміщено: {moved} (dx={dx:.2f})")

        # Record operation
        self.state_manager.record_operation(file_key, operation_name, {
            "silo_number": silo_number,
            "scale": new_pos['scale'],
            "dx": dx,
            "objects_scaled": scaled,
            "objects_moved": moved
        })

        return scaled, moved

    def apply_transformations(self, file_key):
        """Apply all transformations"""
        print("\n[7] Трансформації...")

        total_scaled = 0
        total_moved = 0

        for pos_info in self.new_positions:
            operation_name = f"scale_silo_{pos_info['id']}"
            scaled, moved = self.transform_silo(pos_info['id'], pos_info, file_key, operation_name)
            total_scaled += scaled
            total_moved += moved

        print(f"\n  ВСЬОГО: Масштабовано={total_scaled}, Переміщено={total_moved}")

    def add_7th_silo(self, file_key):
        """Add 7th silo by copying #6"""
        print("\n[8] Додавання 7-го силосу...")

        if not self.state_manager.can_apply_operation(file_key, "add_7th_silo"):
            print("    ⏭ Пропускаю (вже виконано)")
            return 0

        # Find silo #6 objects
        silo_6 = self.silos[5]  # Index 5 = silo #6
        silo_6_objects = []

        for i in range(self.ms.Count):
            try:
                obj = self.ms.Item(i)
                if hasattr(obj, 'Layer'):
                    layer = obj.Layer
                    if 'C00-00-FF' in layer or (obj.ObjectName == 'AcDbHatch' and 'C00-00-00' in layer):
                        if hasattr(obj, 'GetBoundingBox'):
                            try:
                                bbox = obj.GetBoundingBox()
                                min_p, max_p = bbox[0], bbox[1]
                                cx = (min_p[0] + max_p[0]) / 2
                                cy = (min_p[1] + max_p[1]) / 2

                                # Check if near silo #6
                                distance = ((cx - silo_6['center']['x'])**2 + (cy - silo_6['center']['y'])**2)**0.5

                                if distance < 60:
                                    silo_6_objects.append(obj)
                            except:
                                pass
            except:
                pass

        print(f"    Знайдено об'єктів силосу #6: {len(silo_6_objects)}")

        # Copy all objects
        spacing = 47.75
        dx = spacing

        copied = 0
        for obj in silo_6_objects:
            try:
                new_obj = obj.Copy()
                new_obj.Move(cp(0, 0, 0), cp(dx, 0, 0))
                copied += 1
            except:
                pass

        print(f"    ✅ Скопійовано: {copied} об'єктів")

        # Record operation
        self.state_manager.record_operation(file_key, "add_7th_silo", {"copied": copied})

        return copied

    def get_current_positions(self):
        """Get current positions after transformations"""
        print("\n[9] Визначення поточних позицій...")

        current_positions = []

        # Include all bottom silos (3-7)
        for silo_num in range(3, 8):
            if silo_num <= 6:
                silo = self.silos[silo_num - 1]
                expected_x = silo['center']['x']
                expected_y = silo['center']['y']
            else:
                # Silo #7 position
                silo_6 = self.silos[5]
                expected_x = silo_6['center']['x'] + 47.75
                expected_y = silo_6['center']['y']

            blue_centers = []

            for i in range(self.ms.Count):
                try:
                    obj = self.ms.Item(i)
                    if hasattr(obj, 'Layer'):
                        layer = obj.Layer
                        if 'C00-00-FF' in layer:
                            if hasattr(obj, 'GetBoundingBox'):
                                try:
                                    bbox = obj.GetBoundingBox()
                                    min_p, max_p = bbox[0], bbox[1]
                                    cx = (min_p[0] + max_p[0]) / 2
                                    cy = (min_p[1] + max_p[1]) / 2

                                    distance = ((cx - expected_x)**2 + (cy - expected_y)**2)**0.5

                                    if distance < 80:
                                        blue_centers.append({'x': cx, 'y': cy, 'min_y': min_p[1]})
                                except:
                                    pass
                except:
                    pass

            if blue_centers:
                avg_x = sum(p['x'] for p in blue_centers) / len(blue_centers)
                avg_y = sum(p['y'] for p in blue_centers) / len(blue_centers)
                min_y = min(p['min_y'] for p in blue_centers)

                current_positions.append({
                    'number': silo_num,
                    'x': round(avg_x, 2),
                    'y': round(avg_y, 2),
                    'min_y': round(min_y, 2)
                })

                print(f"    Силос #{silo_num}: x={avg_x:.2f}, y={avg_y:.2f}, min_y={min_y:.2f}")

        return current_positions

    def draw_connections(self, positions, file_key):
        """Draw red connections"""
        print("\n[10] Малювання червоних з'єднань...")

        if not self.state_manager.can_apply_operation(file_key, "draw_connections"):
            print("    ⏭ Пропускаю (вже виконано)")
            return 0

        drawn_lines = 0

        # Find base Y
        base_y = min(p['min_y'] for p in positions)
        conveyor_y = base_y - 5

        print(f"\n  Горизонтальні конвеєри (y={conveyor_y:.2f})...")

        # Horizontal conveyors
        for i in range(len(positions) - 1):
            silo1 = positions[i]
            silo2 = positions[i + 1]

            line = self.ms.AddLine(cp(silo1['x'], conveyor_y, 0), cp(silo2['x'], conveyor_y, 0))
            line.Color = 1
            drawn_lines += 1

            print(f"    Конвеєр #{silo1['number']}→#{silo2['number']}")

        print(f"\n  Вертикальні норії...")

        elevator_height = 50

        # Vertical elevators
        for silo in positions:
            line = self.ms.AddLine(cp(silo['x'], silo['min_y'], 0), cp(silo['x'], silo['min_y'] + elevator_height, 0))
            line.Color = 1
            drawn_lines += 1

            print(f"    Норія #{silo['number']}")

        print(f"\n  Всього намальовано: {drawn_lines} ліній")

        # Record operation
        self.state_manager.record_operation(file_key, "draw_connections", {"lines_drawn": drawn_lines})

        return drawn_lines

    def finalize(self, file_key):
        """Finalize processing"""
        print(f"\n[11] Завершення...")

        # Regenerate
        self.doc.Regen(1)
        print("    ✅ Регенерація")

        # Zoom
        self.acad.ZoomExtents()
        print("    ✅ Zoom")

        # Save
        self.doc.Save()
        print("    ✅ Збережено")

        # Mark as processed
        self.state_manager.mark_processed(file_key)

    def execute(self, source_file):
        """Main execution with state management"""
        self.initialize()

        # Step 1: Preserve original
        file_key = Path(source_file).stem
        print(f"\n[ЕТАП 1] Збереження оригіналу...")
        original_path = self.state_manager.preserve_original(source_file)

        # Step 2: Check if can process
        if not self.check_can_process(file_key):
            print("\n❌ ОБРОБКА НЕМОЖЛИВА - файл вже оброблено або операції застосовано")
            print("   Використайте нову копію оригіналу для повторної обробки.")
            return

        # Step 3: Create working copy
        print(f"\n[ЕТАП 2] Створення робочої копії...")
        working_path = self.state_manager.create_working_copy(file_key)

        # Step 4: Connect to AutoCAD
        print(f"\n[ЕТАП 3] Відкриття файлу...")
        self.connect_autocad(working_path)

        # Step 5: Execute operations
        print(f"\n[ЕТАП 4] ВИКОНАННЯ ОПЕРАЦІЙ...")

        self.delete_red_lines(file_key)
        self.calculate_new_positions()
        self.apply_transformations(file_key)
        self.add_7th_silo(file_key)

        current_positions = self.get_current_positions()

        if len(current_positions) >= 2:
            self.draw_connections(current_positions, file_key)

        # Step 6: Finalize
        self.finalize(file_key)

        # Step 7: Save result
        print(f"\n[ЕТАП 5] Збереження результату...")
        result_path = self.state_manager.save_result(working_path, file_key)

        print("\n" + "="*70)
        print("✅✅✅ УСПІШНО! ВСЕ ВИКОНАНО! ✅✅✅")
        print("="*70)
        print(f"\nОригінал збережено: {original_path.name}")
        print(f"Результат збережено: {result_path.name}")
        print("\nДля повторної обробки використайте нову копію оригіналу.")
        print("="*70)


def main():
    config_path = "d:/autocad project/smart_resize_config.json"
    project_dir = "d:/autocad project"

    # Find current working DXF
    source_file = "d:/autocad project/FRESH_ORIGINAL.dxf"

    try:
        system = SafeResizeSystem(config_path, project_dir)
        system.execute(source_file)

    except Exception as e:
        print(f"\n❌ ПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
