# -*- coding: utf-8 -*-
"""
ГЕНЕРАТОР СХЕМ З JSON (STRUCTURED SCHEMA GENERATOR)
Читає structured_schema.json та малює схему в AutoCAD
"""
import win32com.client
import json
from pathlib import Path


def cp(*coords):
    """Create COM-compatible coordinate array"""
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


class SchemaGenerator:
    def __init__(self, schema_path):
        """Initialize generator with schema JSON"""
        self.schema_path = schema_path
        self.schema = None
        self.acad = None
        self.doc = None
        self.ms = None

        self.load_schema()

    def load_schema(self):
        """Load and validate schema JSON"""
        print(f"[1] Zavantazhennia skhemy z {self.schema_path}...")

        with open(self.schema_path, 'r', encoding='utf-8') as f:
            self.schema = json.load(f)

        print(f"    Nazva: {self.schema['schema_info']['name']}")
        print(f"    Sylosiv: {self.schema['schema_info']['total_silos']}")
        print(f"    Layout: {self.schema['schema_info']['layout_type']}")

    def connect_autocad(self):
        """Connect to AutoCAD"""
        print(f"\n[2] Pidkliuchennia do AutoCAD...")

        self.acad = win32com.client.Dispatch("AutoCAD.Application")
        self.doc = self.acad.ActiveDocument
        self.ms = self.doc.ModelSpace

        print(f"    Pidkliucheno do: {self.doc.Name}")

    def clear_drawing(self):
        """Clear current drawing"""
        print(f"\n[3] Ochyshchennia kreslennnia...")

        count = self.ms.Count
        for i in range(count - 1, -1, -1):
            try:
                obj = self.ms.Item(i)
                obj.Delete()
            except:
                pass

        self.doc.Regen(1)
        print(f"    Vydaleno {count} obiektiv")

    def draw_silo_rectangle(self, silo):
        """Draw a single silo as rectangle"""
        center = silo['center']
        dims = silo['dimensions']

        # Calculate corners
        half_w = dims['width'] / 2
        half_h = dims['height'] / 2

        x1 = center['x'] - half_w
        y1 = center['y'] - half_h
        x2 = center['x'] + half_w
        y2 = center['y'] + half_h

        # Draw rectangle (4 lines)
        line1 = self.ms.AddLine(cp(x1, y1, 0), cp(x2, y1, 0))
        line2 = self.ms.AddLine(cp(x2, y1, 0), cp(x2, y2, 0))
        line3 = self.ms.AddLine(cp(x2, y2, 0), cp(x1, y2, 0))
        line4 = self.ms.AddLine(cp(x1, y2, 0), cp(x1, y1, 0))

        # Set color to blue (layer C00-00-FF = color 5)
        for line in [line1, line2, line3, line4]:
            line.Color = 5

        # Add label
        text = self.ms.AddText(
            str(silo['id']),
            cp(center['x'], center['y'] + dims['height']/2 + 5, 0),
            5.0
        )
        text.Color = 5
        text.Alignment = 2  # Center
        text.TextAlignmentPoint = cp(center['x'], center['y'] + dims['height']/2 + 5, 0)

        return [line1, line2, line3, line4, text]

    def draw_all_silos(self):
        """Draw all silos from schema"""
        print(f"\n[4] Maliuvannia {len(self.schema['silos'])} sylosiv...")

        drawn_objects = []

        for silo in self.schema['silos']:
            objects = self.draw_silo_rectangle(silo)
            drawn_objects.extend(objects)

            print(f"    Sylos {silo['id']}: [{silo['center']['x']}, {silo['center']['y']}] "
                  f"{silo['dimensions']['width']}x{silo['dimensions']['height']}")

        return drawn_objects

    def add_frame(self):
        """Add drawing frame"""
        print(f"\n[5] Dodavannia ramky...")

        # Calculate bounds from silos
        all_x = []
        all_y = []

        for silo in self.schema['silos']:
            bounds = silo['bounds']
            all_x.extend([bounds['min_x'], bounds['max_x']])
            all_y.extend([bounds['min_y'], bounds['max_y']])

        margin = 20
        frame_x1 = min(all_x) - margin
        frame_y1 = min(all_y) - margin
        frame_x2 = max(all_x) + margin
        frame_y2 = max(all_y) + margin

        # Draw frame
        f1 = self.ms.AddLine(cp(frame_x1, frame_y1, 0), cp(frame_x2, frame_y1, 0))
        f2 = self.ms.AddLine(cp(frame_x2, frame_y1, 0), cp(frame_x2, frame_y2, 0))
        f3 = self.ms.AddLine(cp(frame_x2, frame_y2, 0), cp(frame_x1, frame_y2, 0))
        f4 = self.ms.AddLine(cp(frame_x1, frame_y2, 0), cp(frame_x1, frame_y1, 0))

        for line in [f1, f2, f3, f4]:
            line.Color = 7  # White/black

        print(f"    Ramka: [{frame_x1:.1f}, {frame_y1:.1f}] do [{frame_x2:.1f}, {frame_y2:.1f}]")

    def zoom_extents(self):
        """Zoom to extents"""
        self.acad.ZoomExtents()

    def generate(self, clear=True):
        """Main generation method"""
        print("="*70)
        print("GENERATSIIA SKHEMY Z JSON")
        print("="*70)

        self.connect_autocad()

        if clear:
            self.clear_drawing()

        self.draw_all_silos()
        self.add_frame()

        print(f"\n[6] Masshtabuvannia...")
        self.zoom_extents()

        print(f"\n{'='*70}")
        print("USPISHNO! Skhema zgenerovana!")
        print(f"{'='*70}")

        print(f"\nSTATYSTYKA:")
        print(f"  Sylosiv namalovano: {len(self.schema['silos'])}")
        print(f"  Layout: {self.schema['schema_info']['layout_type']}")


def main():
    """Main entry point"""
    schema_path = "d:/autocad project/structured_schema.json"

    try:
        generator = SchemaGenerator(schema_path)
        generator.generate(clear=True)

    except Exception as e:
        print(f"\nPOMYLKA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
