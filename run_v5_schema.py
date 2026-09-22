# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, "D:/autocad project/autocad-mcp")

import win32com.client
import pythoncom
from smart_anchors import SiloAnchors, ConveyorAnchors, NoriaAnchors, BunkerAnchors, create_connection_path
from drawing_standards import LayerManager, DrawingContext, LineWeights, ACADColors, set_object_properties
import math

def create_point(x, y, z=0):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y, z])

def draw_arrow_simple(modelSpace, from_x, from_y, to_x, to_y, size=300):
    line = modelSpace.AddLine(create_point(from_x, from_y, 0), create_point(to_x, to_y, 0))
    dx = to_x - from_x
    dy = to_y - from_y
    angle = math.atan2(dy, dx)
    arrow_angle = 30 * math.pi / 180
    left_x = to_x - size * math.cos(angle - arrow_angle)
    left_y = to_y - size * math.sin(angle - arrow_angle)
    right_x = to_x - size * math.cos(angle + arrow_angle)
    right_y = to_y - size * math.sin(angle + arrow_angle)
    modelSpace.AddLine(create_point(to_x, to_y, 0), create_point(left_x, left_y, 0))
    modelSpace.AddLine(create_point(to_x, to_y, 0), create_point(right_x, right_y, 0))
    return line

print("="*70)
print("POVNACOMPLETA V5 SCHEMA")
print("="*70)

# Pidklyuchennya
print("\n1. Pidklyuchennya AutoCAD...")
acad = win32com.client.Dispatch("AutoCAD.Application")
doc = acad.ActiveDocument
modelSpace = doc.ModelSpace
print("   OK")

# Ochyshchennya
print("\n2. Ochyshchennya...")
count = 0
while modelSpace.Count > 0:
    try:
        modelSpace.Item(0).Delete()
        count += 1
    except:
        break
print(f"   OK - {count} ob'yektiv")

# Shary
print("\n3. Stvorennya shariv...")
layer_mgr = LayerManager(doc)
layer_mgr.create_all_standard_layers()
print("   OK - 14 shariv")

base = 10000
anchors_dict = {}

# VERHNIJ RIVEN - Noriyi
print("\n=== VERHNIJ RIVEN ===")
print("4. Noriyi H1, H3, H4...")

for i, (x_pos, h) in enumerate([(7000, 35000), (15000, 38000), (23000, 38000)], start=1):
    doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_NORIA')
    x = base + x_pos
    y = base + 8000
    height = h
    width = 2000

    # Shahta
    modelSpace.AddLine(create_point(x-width/2, y, 0), create_point(x-width/2, y+height, 0))
    modelSpace.AddLine(create_point(x+width/2, y, 0), create_point(x+width/2, y+height, 0))
    modelSpace.AddLine(create_point(x-width/2, y, 0), create_point(x+width/2, y, 0))
    modelSpace.AddLine(create_point(x-width/2, y+height, 0), create_point(x+width/2, y+height, 0))

    # Tekst
    doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
    tag = f"H{i}" if i in [1,3,4] else f"H{i}"
    if i == 1:
        anchors_dict['H1'] = NoriaAnchors(x, y, width, height)
        text = modelSpace.AddText("H1", create_point(x+1500, y+height/2, 0), 600)
    elif i == 2:
        anchors_dict['H3'] = NoriaAnchors(x, y, width, height)
        text = modelSpace.AddText("H3", create_point(x+1500, y+height/2, 0), 600)
    else:
        anchors_dict['H4'] = NoriaAnchors(x, y, width, height)
        text = modelSpace.AddText("H4", create_point(x+1500, y+height/2, 0), 600)

print("   OK - H1, H3, H4")

# Chervona ramka
print("5. CHERVONA RAMKA...")
doc.ActiveLayer = doc.Layers.Item('FRAME')
frame_lines = [
    modelSpace.AddLine(create_point(base+4000, base+1000, 0), create_point(base+35000, base+1000, 0)),
    modelSpace.AddLine(create_point(base+35000, base+1000, 0), create_point(base+35000, base+48000, 0)),
    modelSpace.AddLine(create_point(base+35000, base+48000, 0), create_point(base+4000, base+48000, 0)),
    modelSpace.AddLine(create_point(base+4000, base+48000, 0), create_point(base+4000, base+1000, 0))
]
for line in frame_lines:
    set_object_properties(line, color=ACADColors.RED, lineweight=LineWeights.EXTRA_THICK)
print("   OK")

# SEREDNIJ RIVEN - Sylosy
print("\n=== SEREDNIJ RIVEN ===")
print("6. Sylosy 1-2...")

for i, x_pos in enumerate([55000, 84000], start=1):
    doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_SILOS')
    x = base + x_pos
    y = base + 10000
    diameter = 22000
    height = 21400
    radius = diameter / 2

    # Cylindr
    lines = [
        modelSpace.AddLine(create_point(x-radius, y, 0), create_point(x-radius, y+height, 0)),
        modelSpace.AddLine(create_point(x+radius, y, 0), create_point(x+radius, y+height, 0)),
        modelSpace.AddLine(create_point(x-radius, y, 0), create_point(x+radius, y, 0)),
        modelSpace.AddLine(create_point(x-radius, y+height, 0), create_point(x+radius, y+height, 0))
    ]
    for line in lines:
        set_object_properties(line, lineweight=LineWeights.THICK)

    # Konus
    cone_h = diameter * 0.35
    cone_y = y - cone_h
    modelSpace.AddLine(create_point(x-radius, y, 0), create_point(x, cone_y, 0))
    modelSpace.AddLine(create_point(x+radius, y, 0), create_point(x, cone_y, 0))

    # Kupol
    modelSpace.AddArc(create_point(x, y+height, 0), radius, math.pi, 0)

    # Tekst
    doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
    text = modelSpace.AddText(str(i), create_point(x, y+height+radius*1.3, 0), 3000)
    text.Alignment = 10
    text.TextAlignmentPoint = create_point(x, y+height+radius*1.3, 0)

    anchors_dict[f'SILO{i}'] = SiloAnchors(x, y, diameter, height, 7)

print("   OK - Sylosy 1-2")

# Konveyery serednogo rivnya
print("7. Konveyery T7-T10...")
doc.ActiveLayer = doc.Layers.Item('CONVEYORS')

conveyors = [
    (30000, 45000, 85000, 45000, 1400, "T7"),
    (38000, 38000, 85000, 38000, 1200, "T8"),
    (38000, 20000, 80000, 20000, 900, "T9"),
    (90000, 45000, 140000, 45000, 900, "T10")
]

for x1, y1, x2, y2, w, tag in conveyors:
    line1 = modelSpace.AddLine(create_point(base+x1, base+y1+w/2, 0), create_point(base+x2, base+y2+w/2, 0))
    line2 = modelSpace.AddLine(create_point(base+x1, base+y1-w/2, 0), create_point(base+x2, base+y2-w/2, 0))
    set_object_properties(line1, color=ACADColors.CONVEYORS, lineweight=LineWeights.MEDIUM)
    set_object_properties(line2, color=ACADColors.CONVEYORS, lineweight=LineWeights.MEDIUM)

    doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
    mid_x = (base+x1 + base+x2) / 2
    text = modelSpace.AddText(tag, create_point(mid_x, base+y1+w, 0), 500)
    text.Alignment = 10
    text.TextAlignmentPoint = create_point(mid_x, base+y1+w, 0)

print("   OK - T7-T10")

# NYZHNIJ RIVEN - Sylosy 3-6
print("\n=== NYZHNIJ RIVEN ===")
print("8. Sylosy 3-6...")

for i, x_pos in enumerate([42000, 68000, 100000, 126000], start=3):
    doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_SILOS')
    x = base + x_pos
    y = base - 35000
    diameter = 20000
    height = 22000
    radius = diameter / 2

    # Cylindr
    lines = [
        modelSpace.AddLine(create_point(x-radius, y, 0), create_point(x-radius, y+height, 0)),
        modelSpace.AddLine(create_point(x+radius, y, 0), create_point(x+radius, y+height, 0)),
        modelSpace.AddLine(create_point(x-radius, y, 0), create_point(x+radius, y, 0)),
        modelSpace.AddLine(create_point(x-radius, y+height, 0), create_point(x+radius, y+height, 0))
    ]
    for line in lines:
        set_object_properties(line, lineweight=LineWeights.THICK)

    # Konus
    cone_h = diameter * 0.35
    cone_y = y - cone_h
    modelSpace.AddLine(create_point(x-radius, y, 0), create_point(x, cone_y, 0))
    modelSpace.AddLine(create_point(x+radius, y, 0), create_point(x, cone_y, 0))

    # Kupol
    modelSpace.AddArc(create_point(x, y+height, 0), radius, math.pi, 0)

    # Tekst
    doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
    text = modelSpace.AddText(str(i), create_point(x, y+height+radius*1.3, 0), 3000)
    text.Alignment = 10
    text.TextAlignmentPoint = create_point(x, y+height+radius*1.3, 0)

    anchors_dict[f'SILO{i}'] = SiloAnchors(x, y, diameter, height, 7)

print("   OK - Sylosy 3-6")

# Konveyery nyzhnogo rivnya
print("9. Konveyery T11-T16...")
doc.ActiveLayer = doc.Layers.Item('CONVEYORS')

conveyors_low = [
    (30000, -45000, 145000, -45000, 1400, "T11"),
    (30000, -8000, 80000, -8000, 900, "T12"),
    (30000, -38000, 80000, -38000, 1200, "T13"),
    (88000, 12000, 95000, -5000, 900, "T14"),
    (88000, -15000, 145000, -15000, 900, "T15"),
    (88000, -25000, 145000, -25000, 900, "T16")
]

for x1, y1, x2, y2, w, tag in conveyors_low:
    line1 = modelSpace.AddLine(create_point(base+x1, base+y1+w/2, 0), create_point(base+x2, base+y2+w/2, 0))
    line2 = modelSpace.AddLine(create_point(base+x1, base+y1-w/2, 0), create_point(base+x2, base+y2-w/2, 0))
    set_object_properties(line1, color=ACADColors.CONVEYORS, lineweight=LineWeights.MEDIUM)
    set_object_properties(line2, color=ACADColors.CONVEYORS, lineweight=LineWeights.MEDIUM)

print("   OK - T11-T16")

# 42 STRILKY
print("\n10. 42 strilky vid sylosiv...")
doc.ActiveLayer = doc.Layers.Item('PIPES_MAIN')

for silo_num in range(1, 7):
    silo = anchors_dict[f'SILO{silo_num}']
    for outlet_num in range(1, 8):
        outlet = silo.get_anchor(f'outlet_{outlet_num}')
        arrow = draw_arrow_simple(modelSpace, outlet[0], outlet[1], outlet[0], outlet[1]-1500, 200)
        set_object_properties(arrow, color=ACADColors.PIPES, lineweight=LineWeights.THIN)

print("   OK - 42 strilky")

# POZNACHKY
print("11. Poznachky vuzliv...")
doc.ActiveLayer = doc.Layers.Item('TEXT_NODES')

nodes = [
    (105000, 48000, "6.9"),
    (115000, 48000, "6.10"),
    (125000, 48000, "7"),
    (90000, -8000, "6.11"),
    (90000, -15000, "6.12"),
    (90000, -25000, "9")
]

for x, y, label in nodes:
    circle = modelSpace.AddCircle(create_point(base+x, base+y, 0), 300)
    set_object_properties(circle, color=ACADColors.RED, lineweight=LineWeights.THIN)
    text = modelSpace.AddText(label, create_point(base+x, base+y-100, 0), 250)
    text.Alignment = 10
    text.TextAlignmentPoint = create_point(base+x, base+y-100, 0)

print("   OK - Poznachky")

print("\n12. Zoom extents...")
acad.ZoomExtents()

print("\n" + "="*70)
print("V5 SCHEMA GOTOVA - CUKERKA!")
print("="*70)
print("\nSTVORENO:")
print("  - 6 sylosiv z Smart Anchors")
print("  - 10 konveyeriv")
print("  - 3 noriyi")
print("  - 42 strilky vid vyhodiv")
print("  - 14 profesijnyh shariv")
print("  - Chervona ramka")
print("  - Vsі poznachky")
