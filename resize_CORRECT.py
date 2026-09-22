# -*- coding: utf-8 -*-
"""
ПРАВИЛЬНЕ МАСШТАБУВАННЯ - ТІЛЬКИ СИНІ ОБ'ЄКТИ
Масштабує ТІЛЬКИ сині силоси + чорні hatches
НЕ ЧІПАЄ червоні конвеєри
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json


def cp(*coords):
    """Create COM-compatible coordinate array"""
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


class CorrectResizer:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = None
        self.acad = None
        self.doc = None
        self.ms = None
        self.silos = []

    def load_config(self):
        """Load config"""
        print("[1] Zavantazhennia konfihuratsii...")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        plan = self.config['resize_plan']
        print(f"    Sylosiv: {len(plan['silos'])}")

    def connect(self):
        """Connect to AutoCAD"""
        print("\n[2] Pidkliuchennia...")
        self.acad = win32com.client.Dispatch("AutoCAD.Application")
        self.doc = self.acad.ActiveDocument
        self.ms = self.doc.ModelSpace
        print(f"    Dokument: {self.doc.Name}")
        print(f"    Obiektiv: {self.ms.Count}")

    def load_silos(self):
        """Load silos"""
        print("\n[3] Zavantazhennia sylosiv...")
        with open('d:/autocad project/extracted_silos_AUTO.json', 'r', encoding='utf-8') as f:
            silos_data = json.load(f)
        self.silos = silos_data['silos']
        print(f"    Sylosiv: {len(self.silos)}")

    def find_blue_objects_only(self, silo, radius=60):
        """Find ONLY BLUE objects (C00-00-FF layer)"""
        silo_cx = silo['center']['x']
        silo_cy = silo['center']['y']

        blue_objects = []

        for i in range(self.ms.Count):
            try:
                obj = self.ms.Item(i)

                # Perevirka TILKY na syniy layer
                if hasattr(obj, 'Layer'):
                    layer = obj.Layer

                    if 'C00-00-FF' in layer:  # TILKY SYNI!
                        # Perevirka chy poblyzhu
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
            except:
                pass

        return blue_objects

    def find_black_hatches_inside(self, silo):
        """Find black hatches inside silo bounds"""
        bounds = silo['bounds']

        hatches = []

        for i in range(self.ms.Count):
            try:
                obj = self.ms.Item(i)

                if obj.ObjectName == 'AcDbHatch':
                    # Perevirka layer
                    if hasattr(obj, 'Layer'):
                        layer = obj.Layer

                        if 'C00-00-00' in layer:  # TILKY CHORNI!
                            # Perevirka chy vseredyni bounds
                            if hasattr(obj, 'GetBoundingBox'):
                                try:
                                    bbox = obj.GetBoundingBox()
                                    min_p, max_p = bbox[0], bbox[1]

                                    obj_cx = (min_p[0] + max_p[0]) / 2
                                    obj_cy = (min_p[1] + max_p[1]) / 2

                                    # Chy vseredyni silo bounds?
                                    if (bounds['min_x'] <= obj_cx <= bounds['max_x'] and
                                        bounds['min_y'] <= obj_cy <= bounds['max_y']):
                                        hatches.append(obj)
                                except:
                                    pass
            except:
                pass

        return hatches

    def calculate_positions(self):
        """Calculate new positions"""
        print("\n[4] Pererakhunok pozytsiy...")

        plan = self.config['resize_plan']
        min_spacing = plan['min_spacing']

        # Tyly nyzhniy riad
        bottom_silos = [s for s in self.silos if s['number'] >= 3]

        # Scale factors
        scale_factors = {}
        for silo_cfg in plan['silos']:
            scale_factors[silo_cfg['id']] = silo_cfg['scale']

        # Rozrakhunok
        new_positions = []

        for i, silo in enumerate(bottom_silos):
            silo_id = silo['number']
            scale = scale_factors.get(silo_id, 1.0)
            new_width = silo['width'] * scale

            if i == 0:
                new_x = silo['center']['x']
            else:
                prev_pos = new_positions[i-1]
                prev_half_width = (bottom_silos[i-1]['width'] * prev_pos['scale']) / 2
                curr_half_width = new_width / 2

                spacing = prev_half_width + curr_half_width + min_spacing
                new_x = prev_pos['x'] + spacing

            new_positions.append({
                'id': silo_id,
                'x': round(new_x, 2),
                'y': silo['center']['y'],
                'original_x': silo['center']['x'],
                'scale': scale
            })

            print(f"    Sylos #{silo_id}: x={new_x:.2f} (scale={scale})")

        return new_positions

    def transform_silo(self, silo_number, new_pos):
        """Transform single silo (blue + black hatches only)"""
        print(f"\n  [5.{silo_number}] Sylos #{silo_number}...")

        silo = self.silos[silo_number - 1]

        # Znayty TILKY SYNI
        blue_objects = self.find_blue_objects_only(silo, radius=60)
        print(f"      Synikh obiektiv: {len(blue_objects)}")

        # Znayty TILKY CHORNI HATCHES
        black_hatches = self.find_black_hatches_inside(silo)
        print(f"      Chornikh hatches: {len(black_hatches)}")

        all_objects = blue_objects + black_hatches

        base_point = cp(silo['center']['x'], silo['center']['y'], 0)

        scaled = 0
        moved = 0

        # MASSHTABUVANNIA
        if new_pos['scale'] != 1.0:
            for obj in all_objects:
                try:
                    obj.ScaleEntity(base_point, new_pos['scale'])
                    scaled += 1
                except:
                    pass
            print(f"      Masshtabovano: {scaled}")

        # PEREMISHCHENNIA
        dx = new_pos['x'] - new_pos['original_x']

        if abs(dx) > 0.01:
            for obj in all_objects:
                try:
                    obj.Move(cp(0, 0, 0), cp(dx, 0, 0))
                    moved += 1
                except:
                    pass
            print(f"      Peremishcheno: {moved} (dx={dx:.2f})")

        return scaled, moved

    def apply_transformations(self, new_positions):
        """Apply transformations"""
        print("\n[5] Transformatsii...")

        total_scaled = 0
        total_moved = 0

        for pos_info in new_positions:
            scaled, moved = self.transform_silo(pos_info['id'], pos_info)
            total_scaled += scaled
            total_moved += moved

        print(f"\n  VSIOGO:")
        print(f"    Masshtabovano: {total_scaled}")
        print(f"    Peremishcheno: {total_moved}")

    def execute(self):
        """Main execution"""
        print("="*70)
        print("PRAVYLNE MASSHTABUVANNIA (TILKY SYNI)")
        print("="*70)

        self.load_config()
        self.connect()
        self.load_silos()

        new_positions = self.calculate_positions()
        self.apply_transformations(new_positions)

        # Regenerate
        print(f"\n[6] Regeneratsiia...")
        self.doc.Regen(1)

        # Zoom
        print(f"\n[7] Zoom...")
        self.acad.ZoomExtents()

        print(f"\n{'='*70}")
        print("USPISHNO! SYNI OBIEKTY MASSHTABOVANO!")
        print(f"{'='*70}")
        print("\nUVAGA: Chervoni konveyory/noriyi NE zminylysia!")
        print("       Yikh treba peremalyuvaty okremo.")


def main():
    config_path = "d:/autocad project/smart_resize_config.json"

    try:
        resizer = CorrectResizer(config_path)
        resizer.execute()

    except Exception as e:
        print(f"\nPOMYLKA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
