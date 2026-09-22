# -*- coding: utf-8 -*-
"""
РОЗУМНА СИСТЕМА МАСШТАБУВАННЯ СИЛОСІВ
Масштабує + переміщує + перераховує відстані
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json


def cp(*coords):
    """Create COM-compatible coordinate array"""
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


class SmartResizerSystem:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = None
        self.acad = None
        self.doc = None
        self.ms = None
        self.silos = []
        self.silo_objects = {}  # {silo_id: [objects]}

    def load_config(self):
        """Load resize configuration"""
        print("[1] Zavantazhennia konfihuratsii...")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        plan = self.config['resize_plan']
        print(f"    Sylosiv u plani: {len(plan['silos'])}")

        for silo_cfg in plan['silos']:
            action = silo_cfg['action']
            scale = silo_cfg['scale']
            print(f"      Sylos #{silo_cfg['id']}: {action} (scale={scale})")

    def connect_autocad(self):
        """Connect to AutoCAD"""
        print("\n[2] Pidkliuchennia do AutoCAD...")
        self.acad = win32com.client.Dispatch("AutoCAD.Application")
        self.doc = self.acad.ActiveDocument
        self.ms = self.doc.ModelSpace
        print(f"    Dokument: {self.doc.Name}")
        print(f"    Obiektiv: {self.ms.Count}")

    def load_silos(self):
        """Load silos data"""
        print("\n[3] Zavantazhennia danykh sylosiv...")
        with open('d:/autocad project/extracted_silos_AUTO.json', 'r', encoding='utf-8') as f:
            silos_data = json.load(f)

        self.silos = silos_data['silos']
        print(f"    Zavantazheno: {len(self.silos)} sylosiv")

    def find_silo_objects(self, silo, radius=60):
        """Find all objects for a silo"""
        silo_cx = silo['center']['x']
        silo_cy = silo['center']['y']

        objects = []

        for i in range(self.ms.Count):
            try:
                obj = self.ms.Item(i)

                if hasattr(obj, 'GetBoundingBox'):
                    try:
                        bbox = obj.GetBoundingBox()
                        min_p, max_p = bbox[0], bbox[1]
                        obj_cx = (min_p[0] + max_p[0]) / 2
                        obj_cy = (min_p[1] + max_p[1]) / 2

                        distance = ((obj_cx - silo_cx)**2 + (obj_cy - silo_cy)**2)**0.5

                        if distance <= radius:
                            objects.append(obj)
                    except:
                        pass
            except:
                pass

        return objects

    def calculate_new_positions(self):
        """Calculate new positions after scaling"""
        print("\n[4] Pererakhunok novykh pozytsiy...")

        plan = self.config['resize_plan']
        min_spacing = plan['min_spacing']

        # Vziaty tyly nyzhniy riad (sylosy 3-6)
        bottom_row_silos = [s for s in self.silos if s['number'] >= 3]

        print(f"    Nyzhniy riad: {len(bottom_row_silos)} sylosiv")

        # Otrimaty scale factors
        scale_factors = {}
        for silo_cfg in plan['silos']:
            scale_factors[silo_cfg['id']] = silo_cfg['scale']

        # Rozrakhuvaty novi rozmiry
        new_sizes = []
        for silo in bottom_row_silos:
            silo_id = silo['number']
            scale = scale_factors.get(silo_id, 1.0)

            new_width = silo['width'] * scale
            new_height = silo['height'] * scale

            new_sizes.append({
                'id': silo_id,
                'original_x': silo['center']['x'],
                'y': silo['center']['y'],
                'width': new_width,
                'height': new_height,
                'scale': scale
            })

        # Rozrakhuvaty novi X pozytsiyi (zliva napravo)
        new_positions = []

        # Pochaty z pershogo (sylos #3)
        current_x = new_sizes[0]['original_x']

        for i, size_info in enumerate(new_sizes):
            if i == 0:
                # Pershyy zalyshaiemo na mists
                new_x = size_info['original_x']
            else:
                # Rozrakhuvaty vidstan vid poperedniogo
                prev_half_width = new_sizes[i-1]['width'] / 2
                curr_half_width = size_info['width'] / 2

                # Vidstan = polovyny obokh + min spacing
                spacing = prev_half_width + curr_half_width + min_spacing

                new_x = new_positions[i-1]['x'] + spacing

            new_positions.append({
                'id': size_info['id'],
                'x': round(new_x, 2),
                'y': size_info['y'],
                'width': size_info['width'],
                'height': size_info['height'],
                'scale': size_info['scale'],
                'original_x': size_info['original_x']
            })

        for pos in new_positions:
            print(f"      Sylos #{pos['id']}: x={pos['x']} (was {pos['original_x']}), scale={pos['scale']}")

        return new_positions

    def apply_transformations(self, new_positions):
        """Apply scaling and repositioning"""
        print("\n[5] Zastosuvannia transformatsiy...")

        total_scaled = 0
        total_moved = 0

        for pos_info in new_positions:
            silo_id = pos_info['id']
            silo = self.silos[silo_id - 1]

            print(f"\n  [5.{silo_id}] Sylos #{silo_id}...")

            # Znayty obiekty
            objects = self.find_silo_objects(silo, radius=60)
            print(f"      Znaideno obiektiv: {len(objects)}")

            if pos_info['scale'] != 1.0:
                # Masshtabuvaty
                base_point = cp(silo['center']['x'], silo['center']['y'], 0)

                scaled = 0
                for obj in objects:
                    try:
                        obj.ScaleEntity(base_point, pos_info['scale'])
                        scaled += 1
                    except:
                        pass

                print(f"      Masshtabovano: {scaled} obiektiv (scale={pos_info['scale']})")
                total_scaled += scaled

            # Peremistyty (yakshcho nova pozytsiia)
            dx = pos_info['x'] - pos_info['original_x']
            dy = 0  # Y zalyshaiemo

            if abs(dx) > 0.01:
                moved = 0
                for obj in objects:
                    try:
                        obj.Move(cp(0, 0, 0), cp(dx, dy, 0))
                        moved += 1
                    except:
                        pass

                print(f"      Peremishcheno: {moved} obiektiv (dx={dx:.2f})")
                total_moved += moved

        print(f"\n  VSIOGO:")
        print(f"    Masshtabovano: {total_scaled} obiektiv")
        print(f"    Peremishcheno: {total_moved} obiektiv")

    def execute(self):
        """Main execution"""
        print("="*70)
        print("ROZUMNA SYSTEMA MASSHTABUVANNIA")
        print("="*70)

        self.load_config()
        self.connect_autocad()
        self.load_silos()

        new_positions = self.calculate_new_positions()
        self.apply_transformations(new_positions)

        # Regenerate
        print(f"\n[6] Regeneratsiia...")
        self.doc.Regen(1)

        # Zoom
        print(f"\n[7] Masshtabuvannia vyhladu...")
        self.acad.ZoomExtents()

        print(f"\n{'='*70}")
        print("USPISHNO! SYLOSY ZMASHSTABOVANO TA PEREROZPODILENО!")
        print(f"{'='*70}")


def main():
    config_path = "d:/autocad project/smart_resize_config.json"

    try:
        system = SmartResizerSystem(config_path)
        system.execute()

    except Exception as e:
        print(f"\nPOMYLKA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
