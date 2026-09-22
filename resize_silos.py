# -*- coding: utf-8 -*-
"""
СИСТЕМА МАСШТАБУВАННЯ СИЛОСІВ
Змінює розміри існуючих силосів (зі всіма норіями/конвеєрами)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json


def cp(*coords):
    """Create COM-compatible coordinate array"""
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


class SiloResizer:
    def __init__(self):
        self.acad = None
        self.doc = None
        self.ms = None
        self.silos = []

    def connect_autocad(self):
        """Connect to AutoCAD"""
        print("[1] Pidkliuchennia do AutoCAD...")
        self.acad = win32com.client.Dispatch("AutoCAD.Application")
        self.doc = self.acad.ActiveDocument
        self.ms = self.doc.ModelSpace
        print(f"    Dokument: {self.doc.Name}")
        print(f"    Obiektiv: {self.ms.Count}")

    def load_silos(self):
        """Load silos data"""
        print("\n[2] Zavantazhennia danykh sylosiv...")
        with open('d:/autocad project/extracted_silos_AUTO.json', 'r', encoding='utf-8') as f:
            silos_data = json.load(f)

        self.silos = silos_data['silos']
        print(f"    Zavantazheno: {len(self.silos)} sylosiv")

    def find_silo_objects(self, silo, radius=60):
        """Find all objects belonging to a silo"""
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
                            objects.append({
                                'object': obj,
                                'type': obj.ObjectName,
                                'distance': distance
                            })
                    except:
                        pass
            except:
                pass

        return objects

    def scale_objects(self, objects, base_point, scale_factor):
        """Scale objects around base point"""
        scaled_count = 0

        for obj_info in objects:
            try:
                obj = obj_info['object']

                # Masshtabuvannia
                obj.ScaleEntity(
                    cp(base_point['x'], base_point['y'], 0),
                    scale_factor
                )

                scaled_count += 1
            except Exception as e:
                pass

        return scaled_count

    def resize_silo(self, silo_number, scale_factor, radius=60):
        """Resize specific silo"""
        print(f"\n[3.{silo_number}] Masshtabuvannia sylosa #{silo_number}...")

        silo = self.silos[silo_number - 1]

        print(f"    Tsentr: [{silo['center']['x']}, {silo['center']['y']}]")
        print(f"    Scale factor: {scale_factor}")

        # Znayty vsi obiekty
        objects = self.find_silo_objects(silo, radius)
        print(f"    Znaideno obiektiv: {len(objects)}")

        # Masshtabuvaty
        base_point = silo['center']
        scaled = self.scale_objects(objects, base_point, scale_factor)

        print(f"    Masshtabovano: {scaled} obiektiv")

        return scaled

    def apply_resize_plan(self):
        """Apply complete resize plan"""
        print("="*70)
        print("MASSHTABUVANNIA SYLOSIV")
        print("="*70)

        self.connect_autocad()
        self.load_silos()

        # PLAN MASSHTABUVANNIA
        resize_plan = {
            'keep': [1, 2],           # Zalyshyty iak ye (riady 1)
            'bigger': [3, 4],         # Zbilshyty (pershi 2 v riadu 2)
            'smaller': [5, 6, 7]      # Zmenshyty (ostanni 3 v riadu 2)
        }

        scale_bigger = 1.15   # +15%
        scale_smaller = 0.85  # -15%

        print(f"\n[PLAN]:")
        print(f"  Zalyshyty bez zmin: {resize_plan['keep']}")
        print(f"  Zbilshyty (x{scale_bigger}): {resize_plan['bigger']}")
        print(f"  Zmenshyty (x{scale_smaller}): {resize_plan['smaller']}")

        total_scaled = 0

        # Zalyshyty bez zmin
        print(f"\n[3] Zalyshaiemo bez zmin...")
        for silo_num in resize_plan['keep']:
            print(f"    Sylos #{silo_num}: BEZ ZMIN")

        # Zbilshyty
        print(f"\n[4] Zbilshuiemo...")
        for silo_num in resize_plan['bigger']:
            if silo_num <= len(self.silos):
                scaled = self.resize_silo(silo_num, scale_bigger, radius=60)
                total_scaled += scaled

        # Zmenshyty
        print(f"\n[5] Zmenshuiemo...")
        for silo_num in resize_plan['smaller']:
            if silo_num <= len(self.silos):
                scaled = self.resize_silo(silo_num, scale_smaller, radius=60)
                total_scaled += scaled

        # Regenerate
        print(f"\n[6] Regeneratsiia kreslennnia...")
        self.doc.Regen(1)

        # Zoom
        print(f"\n[7] Masshtabuvannia vyhladu...")
        self.acad.ZoomExtents()

        print(f"\n{'='*70}")
        print("USPISHNO! SYLOSY MASSHTABOVANO!")
        print(f"{'='*70}")
        print(f"\nSTATYSTYKA:")
        print(f"  Zalysheno bez zmin: {len(resize_plan['keep'])} sylosiv")
        print(f"  Zbilsheno (x{scale_bigger}): {len(resize_plan['bigger'])} sylosiv")
        print(f"  Zmensheno (x{scale_smaller}): {len(resize_plan['smaller'])} sylosiv")
        print(f"  Vsiogo masshtabovano obiektiv: {total_scaled}")


def main():
    try:
        resizer = SiloResizer()
        resizer.apply_resize_plan()

    except Exception as e:
        print(f"\nPOMYLKA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
