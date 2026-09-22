# -*- coding: utf-8 -*-
"""
СИСТЕМА КОПІЮВАННЯ СИЛОСУ З УСІМА ЗВ'ЯЗКАМИ
Копіює існуючий силос + його норії + конвеєри
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json


def cp(*coords):
    """Create COM-compatible coordinate array"""
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


class SiloCopySystem:
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

    def find_objects_near_silo(self, silo, radius=50):
        """Find all objects near a silo (within radius)"""
        print(f"\n[3] Poshuk obiektiv navkolo sylosa #{silo['number']}...")

        silo_cx = silo['center']['x']
        silo_cy = silo['center']['y']

        nearby_objects = {
            'blue_polylines': [],    # Sylos sam
            'red_polylines': [],     # Noriyi/konveyory
            'brown_polylines': [],   # Inshe obladnannia
            'hatches': []            # Zalivky
        }

        for i in range(self.ms.Count):
            try:
                obj = self.ms.Item(i)

                # Perevirka chy obiekt poblyzhu
                is_nearby = False
                obj_cx, obj_cy = None, None

                if hasattr(obj, 'GetBoundingBox'):
                    try:
                        bbox = obj.GetBoundingBox()
                        min_p, max_p = bbox[0], bbox[1]
                        obj_cx = (min_p[0] + max_p[0]) / 2
                        obj_cy = (min_p[1] + max_p[1]) / 2

                        distance = ((obj_cx - silo_cx)**2 + (obj_cy - silo_cy)**2)**0.5

                        if distance <= radius:
                            is_nearby = True
                    except:
                        pass

                if is_nearby and hasattr(obj, 'Layer'):
                    layer = obj.Layer
                    obj_type = obj.ObjectName

                    obj_info = {
                        'index': i,
                        'object': obj,
                        'type': obj_type,
                        'layer': layer,
                        'center': {'x': round(obj_cx, 2), 'y': round(obj_cy, 2)}
                    }

                    # Klasyfikatsiia po layerakh
                    if 'C00-00-FF' in layer:  # Syniy
                        nearby_objects['blue_polylines'].append(obj_info)
                    elif 'CFF-00-00' in layer:  # Chervoniy
                        nearby_objects['red_polylines'].append(obj_info)
                    elif 'C00-95-25' in layer:  # Korichneviy
                        nearby_objects['brown_polylines'].append(obj_info)
                    elif obj_type == 'AcDbHatch':
                        nearby_objects['hatches'].append(obj_info)

            except:
                pass

        total = sum(len(v) for v in nearby_objects.values())
        print(f"    Znaideno poblyzhu (radius={radius}):")
        print(f"      - Synikh (sylos): {len(nearby_objects['blue_polylines'])}")
        print(f"      - Chervonykh (noriyi/konveyory): {len(nearby_objects['red_polylines'])}")
        print(f"      - Korychnevykh: {len(nearby_objects['brown_polylines'])}")
        print(f"      - Zalivok: {len(nearby_objects['hatches'])}")
        print(f"      VSIOGO: {total}")

        return nearby_objects

    def copy_objects(self, objects_to_copy, offset_x, offset_y):
        """Copy objects with offset"""
        print(f"\n[4] Kopiuvannia obiektiv (offset: dx={offset_x}, dy={offset_y})...")

        copied_count = 0

        for category, objects in objects_to_copy.items():
            for obj_info in objects:
                try:
                    original = obj_info['object']

                    # Kopiuvaty obiekt
                    copied = original.Copy()

                    # Peremistyty
                    displacement = cp(offset_x, offset_y, 0)
                    copied.Move(cp(0, 0, 0), displacement)

                    copied_count += 1

                except Exception as e:
                    pass

        print(f"    Skopiiovano obiektiv: {copied_count}")
        return copied_count

    def add_7th_silo(self):
        """Main method: add 7th silo by copying 6th"""
        print("="*70)
        print("DODAVANNIA 7-GO SYLOSA (KOPIUVANNIA)")
        print("="*70)

        self.connect_autocad()
        self.load_silos()

        # Vybraty 6-y sylos iak shablon
        template_silo = self.silos[5]  # Sylos #6
        print(f"\n[INFO] Shablon: Sylos #{template_silo['number']}")
        print(f"        Tsentr: [{template_silo['center']['x']}, {template_silo['center']['y']}]")

        # Znayty vsi obiekty navkolo 6-go sylosa
        nearby = self.find_objects_near_silo(template_silo, radius=60)

        # Rozrakhuvaty ofset dlia 7-go sylosa
        # Vidstan mizh 5-m ta 6-m sylosom
        silo5_x = self.silos[4]['center']['x']  # Sylos #5
        silo6_x = self.silos[5]['center']['x']  # Sylos #6
        spacing = silo6_x - silo5_x

        offset_x = spacing
        offset_y = 0

        print(f"\n[INFO] Rozrakhovanyi ofset:")
        print(f"        dx = {offset_x:.2f}")
        print(f"        dy = {offset_y:.2f}")
        print(f"        Nova pozytsiia 7-go sylosa: x = {template_silo['center']['x'] + offset_x:.2f}")

        # Kopiuvaty
        copied = self.copy_objects(nearby, offset_x, offset_y)

        # Masshtabuvaty
        print(f"\n[5] Masshtabuvannia...")
        self.acad.ZoomExtents()

        print(f"\n{'='*70}")
        print("USPISHNO! 7-Y SYLOS DODANO!")
        print(f"{'='*70}")
        print(f"\nSTATYSTYKA:")
        print(f"  Shablon: Sylos #{template_silo['number']}")
        print(f"  Skopiiovano obiektiv: {copied}")
        print(f"  Nova pozytsiia: x={template_silo['center']['x'] + offset_x:.2f}, y={template_silo['center']['y']:.2f}")


def main():
    try:
        system = SiloCopySystem()
        system.add_7th_silo()

    except Exception as e:
        print(f"\nPOMYLKA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
