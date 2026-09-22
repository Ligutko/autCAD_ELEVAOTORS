import ezdxf
import json
from collections import defaultdict
import math

def full_analysis(filepath):
    """Complete analysis of DXF file"""
    print(f"\n{'='*70}")
    print(f"ANALYZING: {filepath.split('\\')[-1]}")
    print(f"{'='*70}")

    doc = ezdxf.readfile(filepath)
    msp = doc.modelspace()

    # Count all entity types
    entity_counts = defaultdict(int)
    for entity in msp:
        entity_counts[entity.dxftype()] += 1

    print("\nAll entity types:")
    for etype in sorted(entity_counts.keys()):
        print(f"  {etype}: {entity_counts[etype]}")

    # Get coordinate extents
    print("\nCoordinate extents:")
    all_x, all_y = [], []

    for entity in msp:
        if entity.dxftype() == 'LINE':
            all_x.extend([entity.dxf.start.x, entity.dxf.end.x])
            all_y.extend([entity.dxf.start.y, entity.dxf.end.y])
        elif entity.dxftype() == 'CIRCLE':
            all_x.append(entity.dxf.center.x)
            all_y.append(entity.dxf.center.y)
        elif entity.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
            try:
                points = list(entity.get_points())
                for p in points:
                    all_x.append(p[0])
                    all_y.append(p[1])
            except:
                pass
        elif entity.dxftype() == 'INSERT':
            all_x.append(entity.dxf.insert.x)
            all_y.append(entity.dxf.insert.y)

    if all_x and all_y:
        print(f"  X range: [{min(all_x):.2f}, {max(all_x):.2f}] = {max(all_x) - min(all_x):.2f} units")
        print(f"  Y range: [{min(all_y):.2f}, {max(all_y):.2f}] = {max(all_y) - min(all_y):.2f} units")

    # Check for CIRCLE and ARC entities
    print("\nCircle/Arc analysis:")
    circles_by_radius = defaultdict(int)
    for entity in msp:
        if entity.dxftype() == 'CIRCLE':
            r = round(entity.dxf.radius, 2)
            circles_by_radius[r] += 1

    if circles_by_radius:
        print("  Circle radii found:")
        for radius in sorted(circles_by_radius.keys(), reverse=True):
            print(f"    R={radius}: {circles_by_radius[radius]} circles")
    else:
        print("  No CIRCLE entities found")

    # Check for INSERT (block references)
    print("\nBlock INSERT analysis:")
    block_names = defaultdict(int)
    for entity in msp:
        if entity.dxftype() == 'INSERT':
            block_names[entity.dxf.name] += 1

    if block_names:
        print("  Blocks used:")
        for name, count in sorted(block_names.items(), key=lambda x: x[1], reverse=True):
            print(f"    {name}: {count} instances")

        # Sample first INSERT
        for entity in msp:
            if entity.dxftype() == 'INSERT':
                print(f"\n  Sample INSERT:")
                print(f"    Block: {entity.dxf.name}")
                print(f"    Position: ({entity.dxf.insert.x:.2f}, {entity.dxf.insert.y:.2f})")
                print(f"    Scale: ({entity.dxf.xscale if hasattr(entity.dxf, 'xscale') else 1}, "
                      f"{entity.dxf.yscale if hasattr(entity.dxf, 'yscale') else 1})")
                break
    else:
        print("  No INSERT entities found")

    # Check blocks definition
    print("\nBlock definitions:")
    for block in doc.blocks:
        if not block.name.startswith('*'):  # Skip anonymous blocks
            entities_in_block = list(block)
            if entities_in_block:
                print(f"  Block '{block.name}': {len(entities_in_block)} entities")

                # Count entity types in block
                block_entities = defaultdict(int)
                for e in entities_in_block:
                    block_entities[e.dxftype()] += 1

                entity_summary = ', '.join([f"{count} {etype}" for etype, count in block_entities.items()])
                print(f"    Contains: {entity_summary}")

    return {
        'entity_counts': dict(entity_counts),
        'bounds': {
            'x_min': min(all_x) if all_x else 0,
            'x_max': max(all_x) if all_x else 0,
            'y_min': min(all_y) if all_y else 0,
            'y_max': max(all_y) if all_y else 0,
        }
    }

# Analyze all pages
all_results = {}
for page_num in range(1, 13):
    filepath = f"d:\\autocad project\\FINAL_DXF_PERFECT_V7\\page_{page_num:02d}.dxf"
    try:
        result = full_analysis(filepath)
        all_results[f'page_{page_num:02d}'] = result
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        import traceback
        traceback.print_exc()

# Summary
print("\n" + "="*70)
print("SUMMARY - ENTITIES WITH POTENTIAL EQUIPMENT")
print("="*70)

has_circles = False
has_inserts = False

for page, result in all_results.items():
    if result['entity_counts'].get('CIRCLE', 0) > 0:
        print(f"{page}: {result['entity_counts']['CIRCLE']} CIRCLE entities")
        has_circles = True
    if result['entity_counts'].get('INSERT', 0) > 0:
        print(f"{page}: {result['entity_counts']['INSERT']} INSERT entities")
        has_inserts = True

if not has_circles and not has_inserts:
    print("\nNo CIRCLE or INSERT entities found in any page.")
    print("Equipment is likely represented by LINE and POLYLINE entities forming patterns.")
