import ezdxf
import math

def inspect_entities(filepath, max_samples=20):
    """Inspect sample entities to understand structure"""
    print(f"\n{'='*70}")
    print(f"INSPECTING: {filepath}")
    print(f"{'='*70}")

    doc = ezdxf.readfile(filepath)
    msp = doc.modelspace()

    # Count entity types
    entity_types = {}
    for entity in msp:
        etype = entity.dxftype()
        entity_types[etype] = entity_types.get(etype, 0) + 1

    print("\nEntity type counts:")
    for etype, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {etype}: {count}")

    # Sample polylines
    print("\nSample POLYLINES:")
    polyline_count = 0
    for entity in msp:
        if entity.dxftype() in ('LWPOLYLINE', 'POLYLINE') and polyline_count < 5:
            print(f"\n  Polyline {polyline_count + 1}:")
            try:
                points = list(entity.get_points())
                print(f"    Points: {len(points)}")
                print(f"    Closed: {entity.is_closed if hasattr(entity, 'is_closed') else 'N/A'}")

                if points:
                    # Calculate bounding box
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    width = max(xs) - min(xs)
                    height = max(ys) - min(ys)

                    print(f"    Bounding box: {width:.2f} x {height:.2f}")
                    print(f"    First 3 points: {points[:3]}")
                    print(f"    Last 3 points: {points[-3:]}")

                polyline_count += 1
            except Exception as e:
                print(f"    Error: {e}")

    # Sample lines (non-zero length)
    print("\nSample LINES (non-zero length):")
    line_count = 0
    for entity in msp:
        if entity.dxftype() == 'LINE' and line_count < 10:
            dx = entity.dxf.end.x - entity.dxf.start.x
            dy = entity.dxf.end.y - entity.dxf.start.y
            length = math.sqrt(dx**2 + dy**2)

            if length > 1:  # Only show lines with length > 1mm
                print(f"  Line {line_count + 1}:")
                print(f"    Start: ({entity.dxf.start.x:.2f}, {entity.dxf.start.y:.2f})")
                print(f"    End: ({entity.dxf.end.x:.2f}, {entity.dxf.end.y:.2f})")
                print(f"    Length: {length:.2f}mm")
                line_count += 1

# Inspect multiple pages to understand patterns
files_to_inspect = [
    r"d:\autocad project\FINAL_DXF_PERFECT_V7\page_01.dxf",
    r"d:\autocad project\FINAL_DXF_PERFECT_V7\page_08.dxf",  # Has most polylines
]

for filepath in files_to_inspect:
    inspect_entities(filepath)
