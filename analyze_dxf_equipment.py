import ezdxf
import json
from collections import defaultdict
import math
import os

def analyze_dxf_file(filepath):
    """Analyze a single DXF file and extract equipment geometry"""
    print(f"\nAnalyzing: {filepath}")

    try:
        doc = ezdxf.readfile(filepath)
        msp = doc.modelspace()

        # Collect geometry elements
        circles = []
        arcs = []
        lines = []
        polylines = []

        for entity in msp:
            if entity.dxftype() == 'CIRCLE':
                circles.append({
                    'center': (entity.dxf.center.x, entity.dxf.center.y),
                    'radius': entity.dxf.radius,
                    'diameter': entity.dxf.radius * 2
                })
            elif entity.dxftype() == 'ARC':
                arcs.append({
                    'center': (entity.dxf.center.x, entity.dxf.center.y),
                    'radius': entity.dxf.radius,
                    'diameter': entity.dxf.radius * 2,
                    'start_angle': entity.dxf.start_angle,
                    'end_angle': entity.dxf.end_angle
                })
            elif entity.dxftype() == 'LINE':
                lines.append({
                    'start': (entity.dxf.start.x, entity.dxf.start.y),
                    'end': (entity.dxf.end.x, entity.dxf.end.y),
                    'length': math.sqrt(
                        (entity.dxf.end.x - entity.dxf.start.x)**2 +
                        (entity.dxf.end.y - entity.dxf.start.y)**2
                    )
                })
            elif entity.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                points = list(entity.get_points())
                polylines.append({
                    'points': points,
                    'closed': entity.is_closed if hasattr(entity, 'is_closed') else False
                })

        print(f"  Found: {len(circles)} circles, {len(arcs)} arcs, {len(lines)} lines, {len(polylines)} polylines")

        return {
            'circles': circles,
            'arcs': arcs,
            'lines': lines,
            'polylines': polylines
        }

    except Exception as e:
        print(f"  Error reading file: {e}")
        return None

def detect_circular_patterns_from_lines(lines, tolerance=500):
    """Detect circular patterns from line segments"""
    circles_found = []

    # Group lines by approximate center
    # Look for lines that form circular patterns
    centers = {}

    for line in lines:
        # Calculate midpoint and direction
        mid_x = (line['start'][0] + line['end'][0]) / 2
        mid_y = (line['start'][1] + line['end'][1]) / 2

        # Round to grid
        grid_size = 1000
        grid_x = round(mid_x / grid_size) * grid_size
        grid_y = round(mid_y / grid_size) * grid_size

        key = (grid_x, grid_y)

        if key not in centers:
            centers[key] = []
        centers[key].append(line)

    # Analyze each potential center
    for center, line_group in centers.items():
        if len(line_group) < 8:  # Need enough segments for a circle
            continue

        # Calculate average distance from center to line midpoints
        distances = []
        for line in line_group:
            mid_x = (line['start'][0] + line['end'][0]) / 2
            mid_y = (line['start'][1] + line['end'][1]) / 2

            dist = math.sqrt((mid_x - center[0])**2 + (mid_y - center[1])**2)
            distances.append(dist)

        if not distances:
            continue

        avg_radius = sum(distances) / len(distances)
        diameter = avg_radius * 2

        # Check if this looks like a circle (consistent distances)
        variance = sum((d - avg_radius)**2 for d in distances) / len(distances)
        std_dev = math.sqrt(variance)

        if std_dev < avg_radius * 0.2:  # Less than 20% variation
            circles_found.append({
                'center': center,
                'radius': avg_radius,
                'diameter': diameter,
                'segment_count': len(line_group)
            })

    return circles_found

def identify_silos(circles, arcs, lines):
    """Identify silos from circles/arcs (diameter ~22000mm or ~28000mm)"""
    silos = []

    # Tolerance for diameter matching
    diameter_tolerance = 2000  # 2000mm tolerance

    # Expected silo diameters
    silo_220_diameter = 22000
    silo_280_diameter = 28000

    # Check actual circles
    for circle in circles:
        diameter = circle['diameter']

        if abs(diameter - silo_220_diameter) < diameter_tolerance:
            silos.append({
                'type': 'МСВУ-220.13',
                'diameter': round(diameter),
                'center': circle['center']
            })
        elif abs(diameter - silo_280_diameter) < diameter_tolerance:
            silos.append({
                'type': 'МСВУ-280.17',
                'diameter': round(diameter),
                'center': circle['center']
            })

    # Check arcs
    for arc in arcs:
        diameter = arc['diameter']

        if abs(diameter - silo_220_diameter) < diameter_tolerance:
            silos.append({
                'type': 'МСВУ-220.13',
                'diameter': round(diameter),
                'center': arc['center']
            })
        elif abs(diameter - silo_280_diameter) < diameter_tolerance:
            silos.append({
                'type': 'МСВУ-280.17',
                'diameter': round(diameter),
                'center': arc['center']
            })

    # Detect circular patterns from lines
    detected_circles = detect_circular_patterns_from_lines(lines)

    for circle in detected_circles:
        diameter = circle['diameter']

        if abs(diameter - silo_220_diameter) < diameter_tolerance:
            silos.append({
                'type': 'МСВУ-220.13',
                'diameter': round(diameter),
                'center': circle['center']
            })
        elif abs(diameter - silo_280_diameter) < diameter_tolerance:
            silos.append({
                'type': 'МСВУ-280.17',
                'diameter': round(diameter),
                'center': circle['center']
            })

    return silos

def identify_elevators(lines):
    """Identify elevators (vertical structures)"""
    elevators = []

    # Look for vertical lines (height > 20000mm)
    min_height = 15000

    for line in lines:
        dx = abs(line['end'][0] - line['start'][0])
        dy = abs(line['end'][1] - line['start'][1])

        # Vertical line
        if dx < 1000 and dy > min_height:
            elevators.append({
                'height': round(dy),
                'position': line['start']
            })

    return elevators

def identify_conveyors(lines):
    """Identify conveyors (horizontal/inclined long lines)"""
    conveyors = []

    # Look for long horizontal or inclined lines
    min_length = 5000

    for line in lines:
        if line['length'] > min_length:
            dx = abs(line['end'][0] - line['start'][0])
            dy = abs(line['end'][1] - line['start'][1])

            # Horizontal or inclined
            if dx > min_length:
                conveyors.append({
                    'length': round(line['length']),
                    'start': line['start'],
                    'end': line['end']
                })

    return conveyors

def merge_similar_equipment(equipment_list, tolerance=500):
    """Merge equipment that are very close to each other (probably same object)"""
    if not equipment_list:
        return []

    merged = []
    used = set()

    for i, eq1 in enumerate(equipment_list):
        if i in used:
            continue

        # Get position from equipment
        pos1 = eq1.get('center') or eq1.get('position') or eq1.get('start')
        if not pos1:
            continue

        similar_count = 1
        used.add(i)

        for j, eq2 in enumerate(equipment_list[i+1:], start=i+1):
            pos2 = eq2.get('center') or eq2.get('position') or eq2.get('start')
            if not pos2:
                continue

            distance = math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

            if distance < tolerance:
                similar_count += 1
                used.add(j)

        if similar_count == 1:
            merged.append(eq1)

    return merged

def main():
    dxf_folder = r"d:\autocad project\FINAL_DXF_PERFECT_V7"

    all_silos = []
    all_elevators = []
    all_conveyors = []

    # Analyze all 12 pages
    for page_num in range(1, 13):
        filename = f"page_{page_num:02d}.dxf"
        filepath = os.path.join(dxf_folder, filename)

        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue

        geometry = analyze_dxf_file(filepath)

        if geometry:
            # Identify equipment
            silos = identify_silos(geometry['circles'], geometry['arcs'], geometry['lines'])
            elevators = identify_elevators(geometry['lines'])
            conveyors = identify_conveyors(geometry['lines'])

            print(f"  Identified: {len(silos)} silos, {len(elevators)} elevators, {len(conveyors)} conveyors")

            all_silos.extend(silos)
            all_elevators.extend(elevators)
            all_conveyors.extend(conveyors)

    # Merge similar equipment
    all_silos = merge_similar_equipment(all_silos, tolerance=2000)
    all_elevators = merge_similar_equipment(all_elevators, tolerance=1000)
    all_conveyors = merge_similar_equipment(all_conveyors, tolerance=2000)

    # Group by type
    silo_groups = defaultdict(list)
    for silo in all_silos:
        key = (silo['type'], silo['diameter'])
        silo_groups[key].append(silo)

    # Create catalog
    catalog = {
        "silos": [],
        "elevators": [],
        "conveyors": []
    }

    # Add silos
    for (silo_type, diameter), silos_list in silo_groups.items():
        # Estimate height based on typical proportions
        if "220" in silo_type:
            height = 24000
        elif "280" in silo_type:
            height = 30000
        else:
            height = 25000

        catalog["silos"].append({
            "type": silo_type,
            "diameter": diameter,
            "height": height,
            "count": len(silos_list)
        })

    # Add elevators
    if all_elevators:
        avg_height = sum(e['height'] for e in all_elevators) / len(all_elevators)
        catalog["elevators"].append({
            "type": "Норія",
            "capacity": 100,
            "height": round(avg_height),
            "count": len(all_elevators)
        })

    # Add conveyors
    if all_conveyors:
        catalog["conveyors"].append({
            "type": "Транспортер",
            "width": 800,
            "capacity": 100,
            "count": len(all_conveyors)
        })

    # Save to JSON
    output_file = r"d:\autocad project\equipment_catalog.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print("EQUIPMENT CATALOG")
    print(f"{'='*60}")
    print(json.dumps(catalog, ensure_ascii=False, indent=2))
    print(f"\nCatalog saved to: {output_file}")
    print(f"\nTotal equipment found:")
    print(f"  Silos: {sum(s['count'] for s in catalog['silos'])}")
    print(f"  Elevators: {sum(e['count'] for e in catalog['elevators'])}")
    print(f"  Conveyors: {sum(c['count'] for c in catalog['conveyors'])}")

if __name__ == "__main__":
    main()
