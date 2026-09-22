# -*- coding: utf-8 -*-
"""
СПРОЩЕНЕ МАЛЮВАННЯ ЧЕРВОНИХ З'ЄДНАНЬ
Малює конвеєри та норії ТІЛЬКИ між 4 нижніми силосами (3-6)
Використовує ВІДОМІ позиції з JSON
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json


def cp(*coords):
    """Create COM-compatible coordinate array"""
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


class SimpleRedConnectionsDrawer:
    def __init__(self):
        self.acad = None
        self.doc = None
        self.ms = None
        self.silos = []

    def connect(self):
        """Connect to AutoCAD"""
        print("[1] Pidkliuchennia do AutoCAD...")
        self.acad = win32com.client.Dispatch("AutoCAD.Application")
        self.doc = self.acad.ActiveDocument
        self.ms = self.doc.ModelSpace
        print(f"    Dokument: {self.doc.Name}")
        print(f"    Obiektiv: {self.ms.Count}")

    def load_silos(self):
        """Load silos from JSON"""
        print("\n[2] Zavantazhennia sylosiv z JSON...")
        with open('d:/autocad project/extracted_silos_AUTO.json', 'r', encoding='utf-8') as f:
            silos_data = json.load(f)
        self.silos = silos_data['silos']
        print(f"    Sylosiv: {len(self.silos)}")

        # Show bottom silos
        print("\n    Nyzhniy riad (3-6):")
        for silo in self.silos[2:6]:
            print(f"      Sylos #{silo['number']}: [{silo['center']['x']:.2f}, {silo['center']['y']:.2f}]")

    def get_current_positions(self):
        """Get current positions after scaling"""
        print("\n[3] Vyznachennia POTOCHNYKH pozytsiy (pislia masshtabuvannia)...")

        # Find actual blue object positions
        current_positions = []

        for silo in self.silos[2:6]:  # Only bottom row (3-6)
            # Find blue objects near this silo
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

                                    # Check if near expected position
                                    expected_x = silo['center']['x']
                                    expected_y = silo['center']['y']
                                    distance = ((cx - expected_x)**2 + (cy - expected_y)**2)**0.5

                                    if distance < 80:  # Within 80mm
                                        blue_centers.append({'x': cx, 'y': cy, 'min_y': min_p[1]})
                                except:
                                    pass
                except:
                    pass

            if blue_centers:
                # Average position
                avg_x = sum(p['x'] for p in blue_centers) / len(blue_centers)
                avg_y = sum(p['y'] for p in blue_centers) / len(blue_centers)
                min_y = min(p['min_y'] for p in blue_centers)

                current_positions.append({
                    'number': silo['number'],
                    'x': round(avg_x, 2),
                    'y': round(avg_y, 2),
                    'min_y': round(min_y, 2)
                })

                print(f"    Sylos #{silo['number']}: x={avg_x:.2f}, y={avg_y:.2f}, min_y={min_y:.2f}")

        return current_positions

    def draw_horizontal_conveyor(self, x1, y, x2):
        """Draw horizontal conveyor line (RED)"""
        line = self.ms.AddLine(cp(x1, y, 0), cp(x2, y, 0))
        line.Color = 1  # Red (ACI color 1)
        return line

    def draw_vertical_elevator(self, x, y1, y2):
        """Draw vertical elevator line (RED)"""
        line = self.ms.AddLine(cp(x, y1, 0), cp(x, y2, 0))
        line.Color = 1  # Red
        return line

    def draw_all_connections(self, positions):
        """Draw all red connections"""
        print("\n[4] Maliuvannia chervonykh zviazkiv...")

        drawn_lines = 0

        # Find base Y (bottom of lowest silo)
        base_y = min(p['min_y'] for p in positions)

        print(f"\n  [4.1] Horyzontalni konveyory (y={base_y - 5:.2f})...")

        # Draw horizontal conveyors between adjacent silos
        for i in range(len(positions) - 1):
            silo1 = positions[i]
            silo2 = positions[i + 1]

            x1 = silo1['x']
            x2 = silo2['x']
            conveyor_y = base_y - 5  # 5mm below base

            line = self.draw_horizontal_conveyor(x1, conveyor_y, x2)
            drawn_lines += 1

            print(f"    Konveyor #{silo1['number']}→#{silo2['number']}: "
                  f"x={x1:.2f}→{x2:.2f}, y={conveyor_y:.2f}")

        print(f"\n  [4.2] Vertykalni noriyi...")

        elevator_height = 50  # Height of elevator

        # Draw vertical elevators from each silo
        for silo in positions:
            x = silo['x']
            y1 = silo['min_y']
            y2 = y1 + elevator_height

            line = self.draw_vertical_elevator(x, y1, y2)
            drawn_lines += 1

            print(f"    Noriya #{silo['number']}: x={x:.2f}, y={y1:.2f}→{y2:.2f}")

        print(f"\n  Vsiogo namalovano: {drawn_lines} liniy")

        return drawn_lines

    def execute(self):
        """Main execution"""
        print("="*70)
        print("SPROSHCHENE MALIUVANNIA CHERVONYKH ZVIAZKIV")
        print("="*70)

        self.connect()
        self.load_silos()

        # Get current positions after scaling
        current_positions = self.get_current_positions()

        if len(current_positions) < 2:
            print("\nPOMYLKA: Nedostatno sylosiv dlia zviazkiv!")
            return

        # Draw connections
        drawn = self.draw_all_connections(current_positions)

        # Regenerate
        print(f"\n[5] Regeneratsiia...")
        self.doc.Regen(1)

        # Zoom
        print(f"\n[6] Zoom...")
        self.acad.ZoomExtents()

        print(f"\n{'='*70}")
        print(f"USPISHNO! Namalovano {drawn} chervonykh liniy!")
        print(f"{'='*70}")


def main():
    try:
        drawer = SimpleRedConnectionsDrawer()
        drawer.execute()

    except Exception as e:
        print(f"\nPOMYLKA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
