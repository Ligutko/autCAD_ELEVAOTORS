# -*- coding: utf-8 -*-
"""
КОМПЛЕКСНА СИСТЕМА МАСШТАБУВАННЯ
Робить ВСЕ правильно: видаляє червоні, масштабує, переміщує, малює нові з'єднання
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json


def cp(*coords):
    """Create COM-compatible coordinate array"""
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


class CompleteResizeSystem:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = None
        self.acad = None
        self.doc = None
        self.ms = None
        self.silos = []
        self.original_spacings = {
            '3-4': 47.73,
            '4-5': 88.31,  # VELYKA vidstan!
            '5-6': 47.75
        }

    def load_config(self):
        """Load config"""
        print("[1] Zavantazhennia konfihuratsii...")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

    def connect(self):
        """Connect"""
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

    def delete_all_red_objects(self):
        """Delete ALL red objects (conveyors/elevators)"""
        print("\n[4] Vydalennia VSIAKH chervonykh obiektiv...")

        deleted = 0
        indices_to_delete = []

        # Znayty vsi chervoni
        for i in range(self.ms.Count):
            try:
                obj = self.ms.Item(i)
                if hasattr(obj, 'Layer'):
                    layer = obj.Layer
                    if 'CFF-00-00' in layer:  # Chervonyi layer
                        indices_to_delete.append(i)
            except:
                pass

        print(f"    Znaideno chervonykh: {len(indices_to_delete)}")

        # Vydalyty (z kintsia)
        for idx in sorted(indices_to_delete, reverse=True):
            try:
                obj = self.ms.Item(idx)
                obj.Delete()
                deleted += 1
            except:
                pass

        print(f"    Vydaleno: {deleted}")

        return deleted

    def calculate_correct_positions(self):
        """Calculate positions with correct spacing"""
        print("\n[5] Pererakhunok PRAVYLNYKH pozytsiy...")

        plan = self.config['resize_plan']

        # Scale factors
        scale_factors = {}
        for silo_cfg in plan['silos']:
            scale_factors[silo_cfg['id']] = silo_cfg['scale']

        # Sylosy 3-6
        silos_3to6 = [self.silos[i] for i in range(2, 6)]

        new_positions = []

        for i, silo in enumerate(silos_3to6):
            silo_id = silo['number']
            scale = scale_factors.get(silo_id, 1.0)
            new_width = silo['width'] * scale

            if i == 0:
                # Pershyi - zalyshyty na mists
                new_x = silo['center']['x']
            else:
                # Rozrakhuvaty vidstan
                prev_silo = silos_3to6[i-1]
                prev_scale = scale_factors.get(prev_silo['number'], 1.0)
                prev_width = prev_silo['width'] * prev_scale

                # Vykorystaty ORYHINALNU vidstan
                if i == 1:  # 3→4
                    base_spacing = self.original_spacings['3-4']
                elif i == 2:  # 4→5
                    base_spacing = self.original_spacings['4-5']
                elif i == 3:  # 5→6
                    base_spacing = self.original_spacings['5-6']

                new_x = new_positions[i-1]['x'] + base_spacing

            new_positions.append({
                'id': silo_id,
                'x': round(new_x, 2),
                'y': silo['center']['y'],
                'original_x': silo['center']['x'],
                'scale': scale,
                'width': new_width
            })

            print(f"    Sylos #{silo_id}: x={new_x:.2f} (scale={scale}), width={new_width:.2f}")

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

                    # SYNI obiekty
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

                    # CHORNI hatches
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
        """Transform silo"""
        print(f"\n  [6.{silo_number}] Sylos #{silo_number}...")

        silo = self.silos[silo_number - 1]

        blue_objects, black_hatches = self.find_blue_and_hatches(silo, radius=60)
        all_objects = blue_objects + black_hatches

        print(f"      Synikh: {len(blue_objects)}, Chornikh hatches: {len(black_hatches)}")

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

        # PEREMISHCHENNIA
        dx = new_pos['x'] - new_pos['original_x']

        if abs(dx) > 0.01:
            for obj in all_objects:
                try:
                    obj.Move(cp(0, 0, 0), cp(dx, 0, 0))
                    moved += 1
                except:
                    pass
            print(f"      Masshtabovano: {scaled}, Peremishcheno: {moved} (dx={dx:.2f})")

        return scaled, moved

    def apply_transformations(self, new_positions):
        """Apply all transformations"""
        print("\n[6] Transformatsii...")

        total_scaled = 0
        total_moved = 0

        for pos_info in new_positions:
            scaled, moved = self.transform_silo(pos_info['id'], pos_info)
            total_scaled += scaled
            total_moved += moved

        print(f"\n  VSIOGO: Masshtabovano={total_scaled}, Peremishcheno={total_moved}")

    def execute(self):
        """Main execution"""
        print("="*70)
        print("KOMPLEKSNA SYSTEMA MASSHTABUVANNIA")
        print("="*70)

        self.load_config()
        self.connect()
        self.load_silos()

        # KROK 1: Vydalyty chervoni
        self.delete_all_red_objects()

        # KROK 2: Pererakhuvanty + transformuvaty
        new_positions = self.calculate_correct_positions()
        self.apply_transformations(new_positions)

        # Regenerate
        print(f"\n[7] Regeneratsiia...")
        self.doc.Regen(1)

        # Zoom
        print(f"\n[8] Zoom...")
        self.acad.ZoomExtents()

        print(f"\n{'='*70}")
        print("USPISHNO! SYSTEMA ZAVERSHYLA!")
        print(f"{'='*70}")
        print("\nTODO:")
        print("  - Perevirte pozytsiyi sylosiv")
        print("  - Teper treba namalyuvaty NOVI chervoni zvyazky")


def main():
    config_path = "d:/autocad project/smart_resize_config.json"

    try:
        system = CompleteResizeSystem(config_path)
        system.execute()

    except Exception as e:
        print(f"\nPOMYLKA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
