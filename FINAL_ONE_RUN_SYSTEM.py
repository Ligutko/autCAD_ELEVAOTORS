# -*- coding: utf-8 -*-
"""
ФІНАЛЬНА КОМПЛЕКСНА СИСТЕМА - ОДИН ЗАПУСК
Робить ВСЕ за один раз: видаляє червоні, масштабує, переміщує, малює нові з'єднання
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json


def cp(*coords):
    """Create COM-compatible coordinate array"""
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


class FinalOneRunSystem:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = None
        self.acad = None
        self.doc = None
        self.ms = None
        self.silos = []
        self.new_positions = []

    def load_config(self):
        """Load config"""
        print("[1] Завантаження конфігурації...")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        print(f"    Конфігурація завантажена")

    def connect(self):
        """Connect to AutoCAD"""
        print("\n[2] Підключення до AutoCAD...")
        self.acad = win32com.client.Dispatch("AutoCAD.Application")
        self.doc = self.acad.ActiveDocument
        self.ms = self.doc.ModelSpace
        print(f"    Документ: {self.doc.Name}")
        print(f"    Об'єктів: {self.ms.Count}")

    def load_silos(self):
        """Load silos"""
        print("\n[3] Завантаження силосів...")
        with open('d:/autocad project/extracted_silos_AUTO.json', 'r', encoding='utf-8') as f:
            silos_data = json.load(f)
        self.silos = silos_data['silos']
        print(f"    Силосів: {len(self.silos)}")

    def delete_all_red_objects(self):
        """Delete ALL red objects"""
        print("\n[4] Видалення ВСІХ червоних об'єктів...")

        deleted = 0
        indices_to_delete = []

        for i in range(self.ms.Count):
            try:
                obj = self.ms.Item(i)
                if hasattr(obj, 'Layer'):
                    layer = obj.Layer
                    if 'CFF-00-00' in layer:
                        indices_to_delete.append(i)
            except:
                pass

        print(f"    Знайдено червоних: {len(indices_to_delete)}")

        # Delete from end
        for idx in sorted(indices_to_delete, reverse=True):
            try:
                obj = self.ms.Item(idx)
                obj.Delete()
                deleted += 1
            except:
                pass

        print(f"    Видалено: {deleted}")
        return deleted

    def calculate_new_positions(self):
        """Calculate new positions with correct spacing"""
        print("\n[5] Перерахунок позицій...")

        plan = self.config['resize_plan']

        # Scale factors
        scale_factors = {}
        for silo_cfg in plan['silos']:
            scale_factors[silo_cfg['id']] = silo_cfg['scale']

        # Bottom row (3-6)
        bottom_silos = [self.silos[i] for i in range(2, 6)]

        new_positions = []

        # Original spacings (edge to edge)
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
                prev_width = prev_silo['width'] * prev_scale

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

    def transform_silo(self, silo_number, new_pos):
        """Transform single silo"""
        print(f"\n  [6.{silo_number}] Силос #{silo_number}...")

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

        return scaled, moved

    def apply_transformations(self):
        """Apply all transformations"""
        print("\n[6] Трансформації...")

        total_scaled = 0
        total_moved = 0

        for pos_info in self.new_positions:
            scaled, moved = self.transform_silo(pos_info['id'], pos_info)
            total_scaled += scaled
            total_moved += moved

        print(f"\n  ВСЬОГО: Масштабовано={total_scaled}, Переміщено={total_moved}")

    def get_current_silo_positions(self):
        """Get current positions after transformations"""
        print("\n[7] Визначення поточних позицій після трансформацій...")

        current_positions = []

        for pos_info in self.new_positions:
            silo_num = pos_info['id']

            # Find blue objects near expected position
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

                                    expected_x = pos_info['x']
                                    expected_y = pos_info['y']
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

    def draw_connections(self, positions):
        """Draw red connections"""
        print("\n[8] Малювання червоних з'єднань...")

        drawn_lines = 0

        # Find base Y
        base_y = min(p['min_y'] for p in positions)

        print(f"\n  [8.1] Горизонтальні конвеєри (y={base_y - 5:.2f})...")

        # Horizontal conveyors
        for i in range(len(positions) - 1):
            silo1 = positions[i]
            silo2 = positions[i + 1]

            x1 = silo1['x']
            x2 = silo2['x']
            conveyor_y = base_y - 5

            line = self.ms.AddLine(cp(x1, conveyor_y, 0), cp(x2, conveyor_y, 0))
            line.Color = 1  # Red
            drawn_lines += 1

            print(f"    Конвеєр #{silo1['number']}→#{silo2['number']}: x={x1:.2f}→{x2:.2f}, y={conveyor_y:.2f}")

        print(f"\n  [8.2] Вертикальні норії...")

        elevator_height = 50

        # Vertical elevators
        for silo in positions:
            x = silo['x']
            y1 = silo['min_y']
            y2 = y1 + elevator_height

            line = self.ms.AddLine(cp(x, y1, 0), cp(x, y2, 0))
            line.Color = 1  # Red
            drawn_lines += 1

            print(f"    Норія #{silo['number']}: x={x:.2f}, y={y1:.2f}→{y2:.2f}")

        print(f"\n  Всього намальовано: {drawn_lines} ліній")

        return drawn_lines

    def execute(self):
        """Main execution"""
        print("="*70)
        print("ФІНАЛЬНА КОМПЛЕКСНА СИСТЕМА - ОДИН ЗАПУСК")
        print("="*70)

        self.load_config()
        self.connect()
        self.load_silos()

        # Step 1: Delete red
        self.delete_all_red_objects()

        # Step 2: Calculate positions
        self.calculate_new_positions()

        # Step 3: Transform silos
        self.apply_transformations()

        # Step 4: Get current positions
        current_positions = self.get_current_silo_positions()

        # Step 5: Draw connections
        if len(current_positions) >= 2:
            drawn = self.draw_connections(current_positions)

        # Regenerate
        print(f"\n[9] Регенерація...")
        self.doc.Regen(1)

        # Zoom
        print(f"\n[10] Zoom...")
        self.acad.ZoomExtents()

        print(f"\n{'='*70}")
        print("УСПІШНО! СИСТЕМА ЗАВЕРШИЛА РОБОТУ!")
        print(f"{'='*70}")


def main():
    config_path = "d:/autocad project/smart_resize_config.json"

    try:
        system = FinalOneRunSystem(config_path)
        system.execute()

    except Exception as e:
        print(f"\nПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
