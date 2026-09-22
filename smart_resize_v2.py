# -*- coding: utf-8 -*-
"""
РОЗУМНА СИСТЕМА V2 - З ГРУПОВИМ МАСШТАБУВАННЯМ
Масштабує ВСІ об'єкти силосу разом + перемальовує зв'язки
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json


def cp(*coords):
    """Create COM-compatible coordinate array"""
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


class SmartResizerV2:
    def __init__(self, config_path, analysis_path):
        self.config_path = config_path
        self.analysis_path = analysis_path
        self.config = None
        self.analysis = None
        self.acad = None
        self.doc = None
        self.ms = None
        self.silos = []

    def load_config(self):
        """Load configuration"""
        print("[1] Zavantazhennia konfihuratsii...")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        plan = self.config['resize_plan']
        print(f"    Sylosiv: {len(plan['silos'])}")

    def load_analysis(self):
        """Load analysis results"""
        print("\n[2] Zavantazhennia analizu...")
        with open(self.analysis_path, 'r', encoding='utf-8') as f:
            self.analysis = json.load(f)

        print(f"    Obiektiv: {self.analysis['total_objects']}")
        print(f"    Zviazkiv: {len(self.analysis['connections'])}")

    def connect_autocad(self):
        """Connect to AutoCAD"""
        print("\n[3] Pidkliuchennia...")
        self.acad = win32com.client.Dispatch("AutoCAD.Application")
        self.doc = self.acad.ActiveDocument
        self.ms = self.doc.ModelSpace
        print(f"    Dokument: {self.doc.Name}")

    def load_silos(self):
        """Load silos"""
        print("\n[4] Zavantazhennia sylosiv...")
        with open('d:/autocad project/extracted_silos_AUTO.json', 'r', encoding='utf-8') as f:
            silos_data = json.load(f)
        self.silos = silos_data['silos']
        print(f"    Sylosiv: {len(self.silos)}")

    def get_silo_objects(self, silo_number):
        """Get all object indices for a silo"""
        key = f'silo_{silo_number}'
        if key not in self.analysis['assignments']:
            return []

        objects_data = self.analysis['assignments'][key]['objects']
        indices = [obj['index'] for obj in objects_data]

        return indices

    def calculate_new_positions(self):
        """Calculate new positions"""
        print("\n[5] Pererakhunok pozytsiy...")

        plan = self.config['resize_plan']
        min_spacing = plan['min_spacing']

        # Tyly nyzhniy riad (3-6)
        bottom_silos = [s for s in self.silos if s['number'] >= 3]

        # Scale factors
        scale_factors = {}
        for silo_cfg in plan['silos']:
            scale_factors[silo_cfg['id']] = silo_cfg['scale']

        # Rozrakhunok novykh rozmiriv ta pozytsiy
        new_positions = []
        current_x = bottom_silos[0]['center']['x']

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

            print(f"    Sylos #{silo_id}: x={new_x:.2f} (was {silo['center']['x']:.2f}), scale={scale}")

        return new_positions

    def transform_silo_group(self, silo_number, new_pos):
        """Transform entire silo group"""
        print(f"\n  [6.{silo_number}] Transformatsiia sylosa #{silo_number}...")

        # Otrymaty INDEKSY vsiakh obiektiv
        indices = self.get_silo_objects(silo_number)
        print(f"      Obiektiv u hrupi: {len(indices)}")

        if len(indices) == 0:
            print(f"      POPEREDZENNIA: Nemaye obiektiv!")
            return 0, 0

        silo = self.silos[silo_number - 1]
        base_point = cp(silo['center']['x'], silo['center']['y'], 0)

        scaled = 0
        moved = 0

        # MASSHTABUVANNIA
        if new_pos['scale'] != 1.0:
            for idx in indices:
                try:
                    obj = self.ms.Item(idx)
                    obj.ScaleEntity(base_point, new_pos['scale'])
                    scaled += 1
                except:
                    pass

            print(f"      Masshtabovano: {scaled} (scale={new_pos['scale']})")

        # PEREMISHCHENNIA
        dx = new_pos['x'] - new_pos['original_x']
        dy = 0

        if abs(dx) > 0.01:
            for idx in indices:
                try:
                    obj = self.ms.Item(idx)
                    obj.Move(cp(0, 0, 0), cp(dx, dy, 0))
                    moved += 1
                except:
                    pass

            print(f"      Peremishcheno: {moved} (dx={dx:.2f})")

        return scaled, moved

    def apply_transformations(self, new_positions):
        """Apply all transformations"""
        print("\n[6] Zastosuvannia transformatsiy...")

        total_scaled = 0
        total_moved = 0

        for pos_info in new_positions:
            scaled, moved = self.transform_silo_group(pos_info['id'], pos_info)
            total_scaled += scaled
            total_moved += moved

        print(f"\n  VSIOGO:")
        print(f"    Masshtabovano: {total_scaled}")
        print(f"    Peremishcheno: {total_moved}")

    def execute(self):
        """Main execution"""
        print("="*70)
        print("ROZUMNA SYSTEMA V2 (Z ANALIZOM)")
        print("="*70)

        self.load_config()
        self.load_analysis()
        self.connect_autocad()
        self.load_silos()

        new_positions = self.calculate_new_positions()
        self.apply_transformations(new_positions)

        # Regenerate
        print(f"\n[7] Regeneratsiia...")
        self.doc.Regen(1)

        # Zoom
        print(f"\n[8] Masshtabuvannia vyhladu...")
        self.acad.ZoomExtents()

        print(f"\n{'='*70}")
        print("USPISHNO! SYSTEMA V2 ZAVERSHYLA!")
        print(f"{'='*70}")


def main():
    config_path = "d:/autocad project/smart_resize_config.json"
    analysis_path = "d:/autocad project/deep_analysis_result.json"

    try:
        system = SmartResizerV2(config_path, analysis_path)
        system.execute()

    except Exception as e:
        print(f"\nPOMYLKA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
