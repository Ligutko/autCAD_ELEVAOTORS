import ezdxf
import json
from collections import defaultdict
import math

def analyze_line_statistics(filepath):
    """Analyze line statistics to understand the structure"""
    print(f"\nDetailed analysis: {filepath}")

    try:
        doc = ezdxf.readfile(filepath)
        msp = doc.modelspace()

        # Statistics
        line_lengths = defaultdict(int)
        vertical_lines = []
        horizontal_lines = []
        diagonal_lines = []

        for entity in msp:
            if entity.dxftype() == 'LINE':
                dx = entity.dxf.end.x - entity.dxf.start.x
                dy = entity.dxf.end.y - entity.dxf.start.y
                length = math.sqrt(dx**2 + dy**2)

                # Round length to nearest 100mm
                rounded_length = round(length / 100) * 100
                line_lengths[rounded_length] += 1

                # Classify by direction
                if abs(dx) < 100:  # Vertical
                    vertical_lines.append({
                        'x': entity.dxf.start.x,
                        'y_start': min(entity.dxf.start.y, entity.dxf.end.y),
                        'y_end': max(entity.dxf.start.y, entity.dxf.end.y),
                        'length': abs(dy)
                    })
                elif abs(dy) < 100:  # Horizontal
                    horizontal_lines.append({
                        'y': entity.dxf.start.y,
                        'x_start': min(entity.dxf.start.x, entity.dxf.end.x),
                        'x_end': max(entity.dxf.start.x, entity.dxf.end.x),
                        'length': abs(dx)
                    })
                else:
                    diagonal_lines.append({
                        'start': (entity.dxf.start.x, entity.dxf.start.y),
                        'end': (entity.dxf.end.x, entity.dxf.end.y),
                        'length': length
                    })

        # Top 10 most common line lengths
        top_lengths = sorted(line_lengths.items(), key=lambda x: x[1], reverse=True)[:10]

        print(f"  Total lines: {len(vertical_lines) + len(horizontal_lines) + len(diagonal_lines)}")
        print(f"    Vertical: {len(vertical_lines)}")
        print(f"    Horizontal: {len(horizontal_lines)}")
        print(f"    Diagonal: {len(diagonal_lines)}")
        print(f"  Top 10 line lengths:")
        for length, count in top_lengths:
            print(f"    {length}mm: {count} times")

        # Find tall vertical structures (potential elevators)
        tall_verticals = [v for v in vertical_lines if v['length'] > 15000]
        if tall_verticals:
            print(f"  Tall vertical structures (>15m): {len(tall_verticals)}")
            # Show a few examples
            for v in tall_verticals[:3]:
                print(f"    Height: {v['length']:.0f}mm at X={v['x']:.0f}")

        # Find long horizontal structures (potential conveyors)
        long_horizontals = [h for h in horizontal_lines if h['length'] > 5000]
        if long_horizontals:
            print(f"  Long horizontal structures (>5m): {len(long_horizontals)}")
            for h in long_horizontals[:3]:
                print(f"    Length: {h['length']:.0f}mm at Y={h['y']:.0f}")

        return {
            'vertical': vertical_lines,
            'horizontal': horizontal_lines,
            'diagonal': diagonal_lines
        }

    except Exception as e:
        print(f"  Error: {e}")
        return None

def detect_circular_structures(vertical_lines, horizontal_lines):
    """Detect circular structures by finding rectangular bounding boxes"""
    # Look for sets of 4 lines forming rectangles with similar width/height (squares)
    # These could be bounding boxes for circles

    potential_silos = []

    # Group horizontal lines by Y coordinate
    h_by_y = defaultdict(list)
    for h in horizontal_lines:
        y_key = round(h['y'] / 1000) * 1000
        h_by_y[y_key].append(h)

    # Group vertical lines by X coordinate
    v_by_x = defaultdict(list)
    for v in vertical_lines:
        x_key = round(v['x'] / 1000) * 1000
        v_by_x[x_key].append(v)

    # Look for pairs of horizontal lines at different Y with similar length
    h_pairs = []
    y_coords = sorted(h_by_y.keys())
    for i, y1 in enumerate(y_coords):
        for y2 in y_coords[i+1:]:
            for h1 in h_by_y[y1]:
                for h2 in h_by_y[y2]:
                    # Check if they have similar length and X position
                    if abs(h1['length'] - h2['length']) < 1000:
                        if abs(h1['x_start'] - h2['x_start']) < 1000:
                            height = abs(y2 - y1)
                            width = (h1['length'] + h2['length']) / 2

                            # Check if it's roughly square (circle bounding box)
                            if abs(height - width) < width * 0.1:
                                # This could be a silo
                                diameter = (height + width) / 2

                                # Check if diameter matches expected sizes
                                if 20000 < diameter < 30000:
                                    potential_silos.append({
                                        'diameter': diameter,
                                        'center_x': (h1['x_start'] + h1['x_end']) / 2,
                                        'center_y': (y1 + y2) / 2
                                    })

    return potential_silos

# Analyze first page in detail
filepath = r"d:\autocad project\FINAL_DXF_PERFECT_V7\page_01.dxf"
result = analyze_line_statistics(filepath)

if result:
    silos = detect_circular_structures(result['vertical'], result['horizontal'])
    print(f"\nPotential silos detected: {len(silos)}")
    for silo in silos[:5]:
        print(f"  Diameter: {silo['diameter']:.0f}mm at ({silo['center_x']:.0f}, {silo['center_y']:.0f})")

# Quick analysis of all pages
print("\n" + "="*60)
print("QUICK ANALYSIS OF ALL PAGES")
print("="*60)

for page_num in range(1, 13):
    filepath = f"d:\\autocad project\\FINAL_DXF_PERFECT_V7\\page_{page_num:02d}.dxf"
    result = analyze_line_statistics(filepath)
