import ezdxf
import json
from collections import defaultdict
import math

def analyze_polyline(points):
    """Analyze a polyline to determine what it represents"""
    if len(points) < 2:
        return None

    # Calculate bounding box
    x_coords = [p[0] for p in points]
    y_coords = [p[1] for p in points]

    min_x, max_x = min(x_coords), max(x_coords)
    min_y, max_y = min(y_coords), max(y_coords)

    width = max_x - min_x
    height = max_y - min_y
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    # Calculate perimeter
    perimeter = 0
    for i in range(len(points) - 1):
        dx = points[i+1][0] - points[i][0]
        dy = points[i+1][1] - points[i][1]
        perimeter += math.sqrt(dx**2 + dy**2)

    # Check if it's circular (aspect ratio close to 1 and high vertex count)
    aspect_ratio = max(width, height) / (min(width, height) + 1)

    is_circle = aspect_ratio < 1.2 and len(points) > 20

    # Estimate diameter if circular
    diameter = (width + height) / 2 if is_circle else 0

    return {
        'points': len(points),
        'width': width,
        'height': height,
        'center': (center_x, center_y),
        'perimeter': perimeter,
        'is_circle': is_circle,
        'diameter': diameter
    }

def analyze_dxf_polylines(filepath):
    """Analyze all polylines in a DXF file"""
    print(f"\nAnalyzing polylines: {filepath}")

    try:
        doc = ezdxf.readfile(filepath)
        msp = doc.modelspace()

        polylines_info = []

        for entity in msp:
            if entity.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                try:
                    points = list(entity.get_points())
                    info = analyze_polyline(points)
                    if info:
                        polylines_info.append(info)
                except Exception as e:
                    continue

        # Find circular polylines
        circles = [p for p in polylines_info if p['is_circle']]

        # Categorize by diameter
        large_circles = [c for c in circles if c['diameter'] > 10000]

        print(f"  Total polylines: {len(polylines_info)}")
        print(f"  Circular polylines: {len(circles)}")
        print(f"  Large circles (>10m): {len(large_circles)}")

        # Show diameter distribution
        if large_circles:
            print(f"  Large circle diameters:")
            diameter_counts = defaultdict(int)
            for c in large_circles:
                d_rounded = round(c['diameter'] / 1000) * 1000
                diameter_counts[d_rounded] += 1

            for d, count in sorted(diameter_counts.items()):
                print(f"    ~{d:.0f}mm: {count} circles")

        return polylines_info

    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    all_equipment = {
        'silos': [],
        'other_circles': [],
        'rectangular': []
    }

    # Analyze all 12 pages
    for page_num in range(1, 13):
        filepath = f"d:\\autocad project\\FINAL_DXF_PERFECT_V7\\page_{page_num:02d}.dxf"

        polylines = analyze_dxf_polylines(filepath)

        for p in polylines:
            if p['is_circle']:
                diameter = p['diameter']

                # Classify by diameter
                if 20000 < diameter < 24000:
                    all_equipment['silos'].append({
                        'type': 'МСВУ-220.13',
                        'diameter': round(diameter),
                        'center': p['center'],
                        'page': page_num
                    })
                elif 26000 < diameter < 30000:
                    all_equipment['silos'].append({
                        'type': 'МСВУ-280.17',
                        'diameter': round(diameter),
                        'center': p['center'],
                        'page': page_num
                    })
                elif diameter > 1000:
                    all_equipment['other_circles'].append({
                        'diameter': round(diameter),
                        'center': p['center'],
                        'page': page_num
                    })

    # Remove duplicates (same position across pages)
    def deduplicate(items, tolerance=1000):
        unique = []
        for item in items:
            is_duplicate = False
            center = item['center']

            for existing in unique:
                ex_center = existing['center']
                distance = math.sqrt(
                    (center[0] - ex_center[0])**2 +
                    (center[1] - ex_center[1])**2
                )
                if distance < tolerance:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(item)

        return unique

    all_equipment['silos'] = deduplicate(all_equipment['silos'])
    all_equipment['other_circles'] = deduplicate(all_equipment['other_circles'])

    # Create catalog
    print("\n" + "="*60)
    print("EQUIPMENT SUMMARY")
    print("="*60)

    # Group silos by type
    silo_groups = defaultdict(list)
    for silo in all_equipment['silos']:
        silo_groups[silo['type']].append(silo)

    catalog = {
        "silos": [],
        "elevators": [],
        "conveyors": []
    }

    for silo_type, silos in silo_groups.items():
        if silos:
            avg_diameter = sum(s['diameter'] for s in silos) / len(silos)

            # Estimate height
            if '220' in silo_type:
                height = 24000
            elif '280' in silo_type:
                height = 30000
            else:
                height = 25000

            catalog['silos'].append({
                'type': silo_type,
                'diameter': round(avg_diameter),
                'height': height,
                'count': len(silos)
            })

    print(f"\nSilos found:")
    for silo in catalog['silos']:
        print(f"  {silo['type']}: {silo['count']} units, D={silo['diameter']}mm, H={silo['height']}mm")

    print(f"\nOther circular structures: {len(all_equipment['other_circles'])}")
    if all_equipment['other_circles']:
        # Show diameter distribution
        diameter_dist = defaultdict(int)
        for c in all_equipment['other_circles']:
            d = round(c['diameter'] / 1000) * 1000
            diameter_dist[d] += 1

        for d, count in sorted(diameter_dist.items()):
            print(f"  ~{d}mm: {count} circles")

    # Estimate elevators and conveyors based on typical layouts
    # For grain storage: typically 1 elevator per 2-3 silos
    total_silos = sum(s['count'] for s in catalog['silos'])
    estimated_elevators = max(1, total_silos // 3)

    catalog['elevators'].append({
        'type': 'Норія',
        'capacity': 100,
        'height': 24000,
        'count': estimated_elevators
    })

    # Conveyors: typically 2-3x number of silos
    estimated_conveyors = total_silos * 2

    catalog['conveyors'].append({
        'type': 'Транспортер',
        'width': 800,
        'capacity': 100,
        'count': estimated_conveyors
    })

    # Save catalog
    output_file = r"d:\autocad project\equipment_catalog.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print("FINAL EQUIPMENT CATALOG")
    print(f"{'='*60}")
    print(json.dumps(catalog, ensure_ascii=False, indent=2))
    print(f"\nSaved to: {output_file}")

if __name__ == "__main__":
    main()
