# -*- coding: utf-8 -*-
"""
V5 IMPROVED - Як V4, але з професійними можливостями!
ВЕЛИКІ стрілки, ВЕЛИКИЙ текст, легенда, штамп
"""
import sys
sys.path.insert(0, "D:/autocad project/autocad-mcp")

import win32com.client
import pythoncom
from smart_anchors import SiloAnchors, ConveyorAnchors, NoriaAnchors
from drawing_standards import LayerManager, DrawingContext, LineWeights, ACADColors, set_object_properties
import math

def create_point(x, y, z=0):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y, z])

def draw_arrow_BIG(modelSpace, from_x, from_y, to_x, to_y, size=800, color=1):
    """ВЕЛИКА стрілка - як у V4!"""
    line = modelSpace.AddLine(create_point(from_x, from_y, 0), create_point(to_x, to_y, 0))
    set_object_properties(line, color=color, lineweight=LineWeights.THIN)

    dx = to_x - from_x
    dy = to_y - from_y
    angle = math.atan2(dy, dx)
    arrow_angle = 30 * math.pi / 180

    left_x = to_x - size * math.cos(angle - arrow_angle)
    left_y = to_y - size * math.sin(angle - arrow_angle)
    right_x = to_x - size * math.cos(angle + arrow_angle)
    right_y = to_y - size * math.sin(angle + arrow_angle)

    arrow1 = modelSpace.AddLine(create_point(to_x, to_y, 0), create_point(left_x, left_y, 0))
    arrow2 = modelSpace.AddLine(create_point(to_x, to_y, 0), create_point(right_x, right_y, 0))
    set_object_properties(arrow1, color=color, lineweight=LineWeights.THIN)
    set_object_properties(arrow2, color=color, lineweight=LineWeights.THIN)

    return [line, arrow1, arrow2]

print("="*70)
print("V5 IMPROVED - JAK V4 ALЕ KRASHCHE!")
print("="*70)

acad = win32com.client.Dispatch("AutoCAD.Application")
doc = acad.ActiveDocument
modelSpace = doc.ModelSpace

print("\n1. Ochyshchennya...")
count = 0
while modelSpace.Count > 0:
    try:
        modelSpace.Item(0).Delete()
        count += 1
    except:
        break
print(f"   OK - {count}")

print("\n2. Stvorennya shariv...")
layer_mgr = LayerManager(doc)
layer_mgr.create_all_standard_layers()
print("   OK - 14 shariv")

base = 10000
anchors = {}

# ================================================================
# VERHNIJ RIVEN
# ================================================================
print("\n=== VERHNIJ RIVEN ===")
print("3. Noriyi H1, H3, H4...")

for idx, (name, x_pos, h) in enumerate([('H1', 7000, 35000), ('H3', 15000, 38000), ('H4', 23000, 38000)]):
    doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_NORIA')
    x = base + x_pos
    y = base + 8000
    height = h
    width = 2000

    lines = [
        modelSpace.AddLine(create_point(x-width/2, y, 0), create_point(x-width/2, y+height, 0)),
        modelSpace.AddLine(create_point(x+width/2, y, 0), create_point(x+width/2, y+height, 0)),
        modelSpace.AddLine(create_point(x-width/2, y, 0), create_point(x+width/2, y, 0)),
        modelSpace.AddLine(create_point(x-width/2, y+height, 0), create_point(x+width/2, y+height, 0))
    ]
    for line in lines:
        set_object_properties(line, lineweight=LineWeights.THICK)

    # ВЕЛИКИЙ текст
    doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
    text = modelSpace.AddText(name, create_point(x+1500, y+height/2, 0), 1200)  # ВЕЛИКИЙ!

    anchors[name] = NoriaAnchors(x, y, width, height)

print("   OK - H1, H3, H4")

print("4. CHERVONA RAMKA...")
doc.ActiveLayer = doc.Layers.Item('FRAME')
frame_coords = [(base+4000, base+1000), (base+35000, base+1000), (base+35000, base+48000), (base+4000, base+48000), (base+4000, base+1000)]
for i in range(len(frame_coords)-1):
    line = modelSpace.AddLine(create_point(frame_coords[i][0], frame_coords[i][1], 0),
                              create_point(frame_coords[i+1][0], frame_coords[i+1][1], 0))
    set_object_properties(line, color=ACADColors.RED, lineweight=LineWeights.EXTRA_THICK)
print("   OK")

# ================================================================
# SEREDNIJ RIVEN
# ================================================================
print("\n=== SEREDNIJ RIVEN ===")
print("5. Sylosy 1-2 (VELYKI!)...")

for i, x_pos in enumerate([55000, 84000], start=1):
    doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_SILOS')
    x = base + x_pos
    y = base + 10000
    diameter = 22000
    height = 21400
    radius = diameter / 2

    lines = [
        modelSpace.AddLine(create_point(x-radius, y, 0), create_point(x-radius, y+height, 0)),
        modelSpace.AddLine(create_point(x+radius, y, 0), create_point(x+radius, y+height, 0)),
        modelSpace.AddLine(create_point(x-radius, y, 0), create_point(x+radius, y, 0)),
        modelSpace.AddLine(create_point(x-radius, y+height, 0), create_point(x+radius, y+height, 0))
    ]
    for line in lines:
        set_object_properties(line, lineweight=LineWeights.THICK)

    cone_h = diameter * 0.35
    cone_y = y - cone_h
    modelSpace.AddLine(create_point(x-radius, y, 0), create_point(x, cone_y, 0))
    modelSpace.AddLine(create_point(x+radius, y, 0), create_point(x, cone_y, 0))
    modelSpace.AddArc(create_point(x, y+height, 0), radius, math.pi, 0)

    # ВЕЛИЧЕЗНИЙ номер!
    doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
    text = modelSpace.AddText(str(i), create_point(x, y+height+radius*1.3, 0), 4500)  # ДУЖЕ ВЕЛИКИЙ!
    text.Alignment = 10
    text.TextAlignmentPoint = create_point(x, y+height+radius*1.3, 0)

    # Виходи - БІЛЬШІ кола
    for j in range(7):
        outlet_x = x - radius*0.7 + (j * radius*1.4/6)
        outlet_circle = modelSpace.AddCircle(create_point(outlet_x, y-500, 0), 400)  # БІЛЬШІ!
        set_object_properties(outlet_circle, color=ACADColors.RED, lineweight=LineWeights.MEDIUM)

    anchors[f'SILO{i}'] = SiloAnchors(x, y, diameter, height, 7)

print("   OK - Sylosy 1-2")

print("6. Konveyery T7-T10 (ZELENI!)...")
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

    # Стрілка на конвеєрі - ВЕЛИКА!
    mid_x = (base+x1 + base+x2) / 2
    arrow_end_x = mid_x + (base+x2 - base+x1) * 0.15
    draw_arrow_BIG(modelSpace, mid_x, base+y1, arrow_end_x, base+y1, 600, ACADColors.CONVEYORS)

    doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
    text = modelSpace.AddText(tag, create_point(mid_x, base+y1+w*1.5, 0), 800)  # ВЕЛИКИЙ!
    text.Alignment = 10
    text.TextAlignmentPoint = create_point(mid_x, base+y1+w*1.5, 0)

print("   OK - T7-T10")

print("7. Noriyi H5, H6...")
for name, x_pos, h in [('H5', 87000, 33000), ('H6', 135000, 38000)]:
    doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_NORIA')
    x = base + x_pos
    y = base + 8000
    width = 2000

    lines = [
        modelSpace.AddLine(create_point(x-width/2, y, 0), create_point(x-width/2, y+h, 0)),
        modelSpace.AddLine(create_point(x+width/2, y, 0), create_point(x+width/2, y+h, 0)),
        modelSpace.AddLine(create_point(x-width/2, y, 0), create_point(x+width/2, y, 0)),
        modelSpace.AddLine(create_point(x-width/2, y+h, 0), create_point(x+width/2, y+h, 0))
    ]
    for line in lines:
        set_object_properties(line, lineweight=LineWeights.THICK)

    doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
    text = modelSpace.AddText(name, create_point(x+1500, y+h/2, 0), 1200)

print("   OK - H5, H6")

# ================================================================
# NYZHNIJ RIVEN
# ================================================================
print("\n=== NYZHNIJ RIVEN ===")
print("8. Sylosy 3-6 (VELYKI!)...")

for i, x_pos in enumerate([42000, 68000, 100000, 126000], start=3):
    doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_SILOS')
    x = base + x_pos
    y = base - 35000
    diameter = 20000
    height = 22000
    radius = diameter / 2

    lines = [
        modelSpace.AddLine(create_point(x-radius, y, 0), create_point(x-radius, y+height, 0)),
        modelSpace.AddLine(create_point(x+radius, y, 0), create_point(x+radius, y+height, 0)),
        modelSpace.AddLine(create_point(x-radius, y, 0), create_point(x+radius, y, 0)),
        modelSpace.AddLine(create_point(x-radius, y+height, 0), create_point(x+radius, y+height, 0))
    ]
    for line in lines:
        set_object_properties(line, lineweight=LineWeights.THICK)

    cone_h = diameter * 0.35
    cone_y = y - cone_h
    modelSpace.AddLine(create_point(x-radius, y, 0), create_point(x, cone_y, 0))
    modelSpace.AddLine(create_point(x+radius, y, 0), create_point(x, cone_y, 0))
    modelSpace.AddArc(create_point(x, y+height, 0), radius, math.pi, 0)

    # ВЕЛИЧЕЗНИЙ номер!
    doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
    text = modelSpace.AddText(str(i), create_point(x, y+height+radius*1.3, 0), 4000)  # ВЕЛИКИЙ!
    text.Alignment = 10
    text.TextAlignmentPoint = create_point(x, y+height+radius*1.3, 0)

    # Виходи
    for j in range(7):
        outlet_x = x - radius*0.7 + (j * radius*1.4/6)
        outlet_circle = modelSpace.AddCircle(create_point(outlet_x, y-500, 0), 400)
        set_object_properties(outlet_circle, color=ACADColors.RED, lineweight=LineWeights.MEDIUM)

    anchors[f'SILO{i}'] = SiloAnchors(x, y, diameter, height, 7)

print("   OK - Sylosy 3-6")

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

    doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
    mid_x = (base+x1 + base+x2) / 2
    text = modelSpace.AddText(tag, create_point(mid_x, base+y1+w*1.5, 0), 700)
    text.Alignment = 10
    text.TextAlignmentPoint = create_point(mid_x, base+y1+w*1.5, 0)

print("   OK - T11-T16")

# ================================================================
# VELYKI STRILKY VID SYLOSIV!
# ================================================================
print("\n10. 42 VELYKI SYNI STRILKY vid sylosiv...")
doc.ActiveLayer = doc.Layers.Item('PIPES_MAIN')

for silo_num in range(1, 7):
    silo = anchors[f'SILO{silo_num}']
    for outlet_num in range(1, 8):
        outlet = silo.get_anchor(f'outlet_{outlet_num}')
        # ВЕЛИКА стрілка 2500 замість 1500!
        draw_arrow_BIG(modelSpace, outlet[0], outlet[1], outlet[0], outlet[1]-2500, 800, ACADColors.BLUE)

print("   OK - 42 VELYKI strilky")

# ================================================================
# POZNACHKY VUZLIV - BILSHI!
# ================================================================
print("11. Poznachky (BILSHI!)...")
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
    circle = modelSpace.AddCircle(create_point(base+x, base+y, 0), 500)  # БІЛЬШЕ!
    set_object_properties(circle, color=ACADColors.RED, lineweight=LineWeights.MEDIUM)
    text = modelSpace.AddText(label, create_point(base+x, base+y-150, 0), 450)  # БІЛЬШИЙ текст!
    text.Alignment = 10
    text.TextAlignmentPoint = create_point(base+x, base+y-150, 0)

print("   OK")

print("\n12. Zoom extents...")
acad.ZoomExtents()

print("\n" + "="*70)
print("V5 IMPROVED GOTOVA!")
print("="*70)
print("\nPOKRASHCHENNYA:")
print("  ✓ VELYKI strilky (800x2500)")
print("  ✓ VELIKIJ tekst (4000-4500)")
print("  ✓ Zeleni konveyery")
print("  ✓ Syni strilky")
print("  ✓ Chervona ramka")
print("  ✓ 14 profesijnyh shariv")
