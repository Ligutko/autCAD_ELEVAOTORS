# -*- coding: utf-8 -*-
"""
МАЛЮВАННЯ ЧЕРВОНИХ З'ЄДНАНЬ
Малює спрощені конвеєри та норії для масштабованих силосів
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json


def cp(*coords):
    """Create COM-compatible coordinate array"""
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


class RedConnectionsDrawer:
    def __init__(self):
        self.acad = None
        self.doc = None
        self.ms = None
        self.silos_current = []  # Potochni pozytsiyi

    def connect(self):
        """Connect"""
        print("[1] Pidkliuchennia...")
        self.acad = win32com.client.Dispatch("AutoCAD.Application")
        self.doc = self.acad.ActiveDocument
        self.ms = self.doc.ModelSpace
        print(f"    Dokument: {self.doc.Name}")

    def get_current_silo_positions(self):
        """Get current silo positions (after scaling)"""
        print("\n[2] Vyznachennia POTOCHNYKH pozytsiy sylosiv...")

        # Znayty vsi SYNI obiekty ta yikh bounds
        blue_groups = {}

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

                                cx = round((min_p[0] + max_p[0]) / 2, 2)
                                cy = round((min_p[1] + max_p[1]) / 2, 2)

                                key = (cx, cy)
                                if key not in blue_groups:
                                    blue_groups[key] = {
                                        'center': {'x': cx, 'y': cy},
                                        'min_x': min_p[0],
                                        'max_x': max_p[0],
                                        'min_y': min_p[1],
                                        'max_y': max_p[1],
                                        'count': 0
                                    }

                                # Rozshyryty bounds
                                blue_groups[key]['min_x'] = min(blue_groups[key]['min_x'], min_p[0])
                                blue_groups[key]['max_x'] = max(blue_groups[key]['max_x'], max_p[0])
                                blue_groups[key]['min_y'] = min(blue_groups[key]['min_y'], min_p[1])
                                blue_groups[key]['max_y'] = max(blue_groups[key]['max_y'], max_p[1])
                                blue_groups[key]['count'] += 1

                            except:
                                pass
            except:
                pass

        # Sortuvannia po Y, potim po X
        silos_sorted = sorted(blue_groups.values(), key=lambda s: (-s['center']['y'], s['center']['x']))

        # Prysvoyity nomera
        for idx, silo in enumerate(silos_sorted, 1):
            silo['number'] = idx
            silo['width'] = round(silo['max_x'] - silo['min_x'], 2)
            silo['height'] = round(silo['max_y'] - silo['min_y'], 2)

            self.silos_current.append(silo)

            print(f"    Sylos #{idx}: [{silo['center']['x']}, {silo['center']['y']}], "
                  f"{silo['width']}x{silo['height']}")

        return self.silos_current

    def draw_horizontal_conveyor(self, x1, y, x2, width=1):
        """Draw horizontal conveyor line"""
        # Prosta horyzontalna liniia
        line = self.ms.AddLine(cp(x1, y, 0), cp(x2, y, 0))
        line.Color = 1  # Chervonyi (ACI color 1)
        return line

    def draw_vertical_elevator(self, x, y1, y2, width=1):
        """Draw vertical elevator line"""
        # Prosta vertykalna liniia
        line = self.ms.AddLine(cp(x, y1, 0), cp(x, y2, 0))
        line.Color = 1  # Chervonyi
        return line

    def draw_all_connections(self):
        """Draw all red connections"""
        print("\n[3] Maliuvannia chervonykh zviazkiv...")

        drawn_lines = 0

        # Nyzhniy riad (sylosy 3-6)
        bottom_silos = [s for s in self.silos_current if s['number'] >= 3]

        if len(bottom_silos) < 2:
            print("    POPEREDZENNIA: Malo sylosiv dlia zviazkiv!")
            return 0

        # Vyznachyty bazovu visotu dlia konveyoriv (nyz sylosa)
        base_y = min(s['min_y'] for s in bottom_silos)

        print(f"\n  [3.1] Horyzontalni konveyory (y={base_y:.2f})...")

        # Namalyuvaty horyzontalni konveyory mizh sylosamy
        for i in range(len(bottom_silos) - 1):
            silo1 = bottom_silos[i]
            silo2 = bottom_silos[i + 1]

            x1 = silo1['center']['x']
            x2 = silo2['center']['x']

            line = self.draw_horizontal_conveyor(x1, base_y - 5, x2, width=1)
            drawn_lines += 1

            print(f"    Konveyor #{silo1['number']}→#{silo2['number']}: "
                  f"x={x1:.2f}→{x2:.2f}, y={base_y-5:.2f}")

        # Namalyuvaty vertykalni noriyi vid kozhn oho sylosa
        print(f"\n  [3.2] Vertykalni noriyi...")

        elevator_height = 50  # Vysota noriyi

        for silo in bottom_silos:
            x = silo['center']['x']
            y1 = silo['min_y']
            y2 = y1 + elevator_height

            line = self.draw_vertical_elevator(x, y1, y2, width=1)
            drawn_lines += 1

            print(f"    Noriya #{silo['number']}: x={x:.2f}, y={y1:.2f}→{y2:.2f}")

        print(f"\n  Vsiogo namalovano: {drawn_lines} liniy")

        return drawn_lines

    def execute(self):
        """Main execution"""
        print("="*70)
        print("MALIUVANNIA CHERVONYKH ZVIAZKIV")
        print("="*70)

        self.connect()
        self.get_current_silo_positions()

        drawn = self.draw_all_connections()

        # Regenerate
        print(f"\n[4] Regeneratsiia...")
        self.doc.Regen(1)

        # Zoom
        print(f"\n[5] Zoom...")
        self.acad.ZoomExtents()

        print(f"\n{'='*70}")
        print(f"USPISHNO! Namalovano {drawn} chervonykh liniy!")
        print(f"{'='*70}")


def main():
    try:
        drawer = RedConnectionsDrawer()
        drawer.execute()

    except Exception as e:
        print(f"\nPOMYLKA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
