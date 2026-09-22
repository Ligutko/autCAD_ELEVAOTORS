# -*- coding: utf-8 -*-
"""
V6 - ТОЧНА КОПІЯ ОРИГІНАЛУ!
Повне відтворення схеми з PDF
"""
import sys
sys.path.insert(0, "D:/autocad project/autocad-mcp")

import win32com.client
import pythoncom
from drawing_standards import LayerManager, LineWeights, ACADColors, set_object_properties
import math

def create_point(x, y, z=0):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y, z])

def draw_arrow(ms, x1, y1, x2, y2, size=600, color=1):
    """Стрілка"""
    line = ms.AddLine(create_point(x1, y1, 0), create_point(x2, y2, 0))
    set_object_properties(line, color=color, lineweight=LineWeights.MEDIUM)

    dx, dy = x2-x1, y2-y1
    angle = math.atan2(dy, dx)
    arrow_angle = 25 * math.pi / 180

    left_x = x2 - size * math.cos(angle - arrow_angle)
    left_y = y2 - size * math.sin(angle - arrow_angle)
    right_x = x2 - size * math.cos(angle + arrow_angle)
    right_y = y2 - size * math.sin(angle + arrow_angle)

    ms.AddLine(create_point(x2, y2, 0), create_point(left_x, left_y, 0))
    ms.AddLine(create_point(x2, y2, 0), create_point(right_x, right_y, 0))
    return line

def draw_polyline(ms, points, color, lineweight):
    """Polyline для складних ліній"""
    for i in range(len(points)-1):
        line = ms.AddLine(create_point(points[i][0], points[i][1], 0),
                         create_point(points[i+1][0], points[i+1][1], 0))
        set_object_properties(line, color=color, lineweight=lineweight)

print("="*70)
print("V6 - EXACT MATCH ORIGINAL!")
print("="*70)

acad = win32com.client.Dispatch("AutoCAD.Application")
doc = acad.ActiveDocument
ms = doc.ModelSpace

print("\n1. Clear...")
count = 0
while ms.Count > 0:
    try:
        ms.Item(0).Delete()
        count += 1
    except:
        break
print(f"   OK - {count}")

print("\n2. Create layers...")
lm = LayerManager(doc)
lm.create_all_standard_layers()
print("   OK")

# Масштаб: 1 unit = 1mm, база = 5000
base_x = 5000
base_y = 5000
scale = 100  # Масштабний коефіцієнт

# ================================================================
# ВЕРХНІЙ ЛІВИЙ - НОРІЇ H1, H3, H4 в ЧЕРВОНІЙ РАМЦІ
# ================================================================
print("\n=== UPPER LEFT - H1, H3, H4 ===")
doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_NORIA')

# H4 (зверху)
h4_x = base_x + 2000
h4_y = base_y + 28000
h4_h = 8000
h4_w = 800

# H4 - прямокутник
ms.AddLine(create_point(h4_x-h4_w/2, h4_y, 0), create_point(h4_x-h4_w/2, h4_y+h4_h, 0))
ms.AddLine(create_point(h4_x+h4_w/2, h4_y, 0), create_point(h4_x+h4_w/2, h4_y+h4_h, 0))
ms.AddLine(create_point(h4_x-h4_w/2, h4_y, 0), create_point(h4_x+h4_w/2, h4_y, 0))
ms.AddLine(create_point(h4_x-h4_w/2, h4_y+h4_h, 0), create_point(h4_x+h4_w/2, h4_y+h4_h, 0))

doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
text_h4 = ms.AddText("H4", create_point(h4_x+1200, h4_y+h4_h/2, 0), 600)
text_h4_cap = ms.AddText("100 т/год", create_point(h4_x+1200, h4_y+h4_h-1000, 0), 350)

# H1 (середина)
h1_x = base_x + 1000
h1_y = base_y + 18000
h1_h = 7000
h1_w = 800

doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_NORIA')
ms.AddLine(create_point(h1_x-h1_w/2, h1_y, 0), create_point(h1_x-h1_w/2, h1_y+h1_h, 0))
ms.AddLine(create_point(h1_x+h1_w/2, h1_y, 0), create_point(h1_x+h1_w/2, h1_y+h1_h, 0))
ms.AddLine(create_point(h1_x-h1_w/2, h1_y, 0), create_point(h1_x+h1_w/2, h1_y, 0))
ms.AddLine(create_point(h1_x-h1_w/2, h1_y+h1_h, 0), create_point(h1_x+h1_w/2, h1_y+h1_h, 0))

doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
ms.AddText("H1", create_point(h1_x+1200, h1_y+h1_h/2, 0), 600)

# H3 (знизу)
h3_x = base_x + 3000
h3_y = base_y + 8000
h3_h = 7000
h3_w = 800

doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_NORIA')
ms.AddLine(create_point(h3_x-h3_w/2, h3_y, 0), create_point(h3_x-h3_w/2, h3_y+h3_h, 0))
ms.AddLine(create_point(h3_x+h3_w/2, h3_y, 0), create_point(h3_x+h3_w/2, h3_y+h3_h, 0))
ms.AddLine(create_point(h3_x-h3_w/2, h3_y, 0), create_point(h3_x+h3_w/2, h3_y, 0))
ms.AddLine(create_point(h3_x-h3_w/2, h3_y+h3_h, 0), create_point(h3_x+h3_w/2, h3_y+h3_h, 0))

doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
ms.AddText("H3", create_point(h3_x+1200, h3_y+h3_h/2, 0), 600)

# ЧЕРВОНА РАМКА навколо H1, H3, H4
print("4. RED FRAME around H1-H4...")
doc.ActiveLayer = doc.Layers.Item('FRAME')
frame_x1 = base_x - 500
frame_y1 = base_y + 7000
frame_x2 = base_x + 4500
frame_y2 = base_y + 37000

frame_lines = [
    ms.AddLine(create_point(frame_x1, frame_y1, 0), create_point(frame_x2, frame_y1, 0)),
    ms.AddLine(create_point(frame_x2, frame_y1, 0), create_point(frame_x2, frame_y2, 0)),
    ms.AddLine(create_point(frame_x2, frame_y2, 0), create_point(frame_x1, frame_y2, 0)),
    ms.AddLine(create_point(frame_x1, frame_y2, 0), create_point(frame_x1, frame_y1, 0))
]
for line in frame_lines:
    set_object_properties(line, color=ACADColors.RED, lineweight=LineWeights.EXTRA_THICK)

print("   OK - Upper left section")

# ================================================================
# ЦЕНТРАЛЬНИЙ РІВЕНЬ - СИЛОСИ 1, 2 + КОНВЕЄРИ T7, T8, T9
# ================================================================
print("\n=== CENTER LEVEL - SILOS 1-2, T7-T9 ===")

# Конвеєр T7 (верхній горизонтальний)
t7_y = base_y + 33000
t7_x1 = base_x + 6000
t7_x2 = base_x + 25000
t7_w = 600

doc.ActiveLayer = doc.Layers.Item('CONVEYORS')
ms.AddLine(create_point(t7_x1, t7_y+t7_w/2, 0), create_point(t7_x2, t7_y+t7_w/2, 0))
ms.AddLine(create_point(t7_x1, t7_y-t7_w/2, 0), create_point(t7_x2, t7_y-t7_w/2, 0))

doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
ms.AddText("T7", create_point((t7_x1+t7_x2)/2, t7_y+1000, 0), 500)
ms.AddText("100 т/год", create_point((t7_x1+t7_x2)/2, t7_y+1500, 0), 300)

# Стрілка напрямку на T7
draw_arrow(ms, t7_x1+3000, t7_y, t7_x1+5000, t7_y, 400, ACADColors.CONVEYORS)

# Силос 1
silo1_x = base_x + 13000
silo1_y = base_y + 15000
silo1_d = 9000
silo1_h = 11000
silo1_r = silo1_d / 2

doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_SILOS')

# Циліндр
lines_s1 = [
    ms.AddLine(create_point(silo1_x-silo1_r, silo1_y, 0), create_point(silo1_x-silo1_r, silo1_y+silo1_h, 0)),
    ms.AddLine(create_point(silo1_x+silo1_r, silo1_y, 0), create_point(silo1_x+silo1_r, silo1_y+silo1_h, 0)),
    ms.AddLine(create_point(silo1_x-silo1_r, silo1_y, 0), create_point(silo1_x+silo1_r, silo1_y, 0)),
    ms.AddLine(create_point(silo1_x-silo1_r, silo1_y+silo1_h, 0), create_point(silo1_x+silo1_r, silo1_y+silo1_h, 0))
]
for l in lines_s1:
    set_object_properties(l, lineweight=LineWeights.THICK)

# Конус
cone1_h = silo1_d * 0.35
cone1_y = silo1_y - cone1_h
ms.AddLine(create_point(silo1_x-silo1_r, silo1_y, 0), create_point(silo1_x, cone1_y, 0))
ms.AddLine(create_point(silo1_x+silo1_r, silo1_y, 0), create_point(silo1_x, cone1_y, 0))

# Купол
ms.AddArc(create_point(silo1_x, silo1_y+silo1_h, 0), silo1_r, math.pi, 0)

# Текст
doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
text1 = ms.AddText("1", create_point(silo1_x, silo1_y+silo1_h+silo1_r+500, 0), 2500)
text1.Alignment = 10
text1.TextAlignmentPoint = create_point(silo1_x, silo1_y+silo1_h+silo1_r+500, 0)

text1_tag = ms.AddText("МСВУ 220.13.В12", create_point(silo1_x, silo1_y+silo1_h/2, 0), 500)
text1_tag.Alignment = 10
text1_tag.TextAlignmentPoint = create_point(silo1_x, silo1_y+silo1_h/2, 0)

# 7 червоних стрілок вниз
doc.ActiveLayer = doc.Layers.Item('PIPES_MAIN')
for i in range(7):
    outlet_x = silo1_x - silo1_r*0.7 + i*(silo1_r*1.4/6)
    draw_arrow(ms, outlet_x, silo1_y-300, outlet_x, silo1_y-2000, 500, ACADColors.RED)

# Силос 2 (аналогічно)
silo2_x = base_x + 24000
silo2_y = silo1_y

doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_SILOS')

lines_s2 = [
    ms.AddLine(create_point(silo2_x-silo1_r, silo2_y, 0), create_point(silo2_x-silo1_r, silo2_y+silo1_h, 0)),
    ms.AddLine(create_point(silo2_x+silo1_r, silo2_y, 0), create_point(silo2_x+silo1_r, silo2_y+silo1_h, 0)),
    ms.AddLine(create_point(silo2_x-silo1_r, silo2_y, 0), create_point(silo2_x+silo1_r, silo2_y, 0)),
    ms.AddLine(create_point(silo2_x-silo1_r, silo2_y+silo1_h, 0), create_point(silo2_x+silo1_r, silo2_y+silo1_h, 0))
]
for l in lines_s2:
    set_object_properties(l, lineweight=LineWeights.THICK)

ms.AddLine(create_point(silo2_x-silo1_r, silo2_y, 0), create_point(silo2_x, cone1_y, 0))
ms.AddLine(create_point(silo2_x+silo1_r, silo2_y, 0), create_point(silo2_x, cone1_y, 0))
ms.AddArc(create_point(silo2_x, silo2_y+silo1_h, 0), silo1_r, math.pi, 0)

doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
text2 = ms.AddText("2", create_point(silo2_x, silo2_y+silo1_h+silo1_r+500, 0), 2500)
text2.Alignment = 10
text2.TextAlignmentPoint = create_point(silo2_x, silo2_y+silo1_h+silo1_r+500, 0)

text2_tag = ms.AddText("МСВУ 220.13.В12", create_point(silo2_x, silo2_y+silo1_h/2, 0), 500)
text2_tag.Alignment = 10
text2_tag.TextAlignmentPoint = create_point(silo2_x, silo2_y+silo1_h/2, 0)

# 7 червоних стрілок вниз
doc.ActiveLayer = doc.Layers.Item('PIPES_MAIN')
for i in range(7):
    outlet_x = silo2_x - silo1_r*0.7 + i*(silo1_r*1.4/6)
    draw_arrow(ms, outlet_x, silo2_y-300, outlet_x, silo2_y-2000, 500, ACADColors.RED)

print("   OK - Center level")

# З'ЄДНАННЯ H4 -> T7
print("\n=== CONNECTIONS ===")
doc.ActiveLayer = doc.Layers.Item('PIPES_MAIN')

# H4 -> T7 (червона)
h4_out_x = h4_x
h4_out_y = h4_y - 500
t7_in_x = t7_x1 - 1000
t7_in_y = t7_y

points_h4_t7 = [
    (h4_out_x, h4_out_y),
    (h4_out_x, h4_out_y - 1500),
    (t7_in_x, h4_out_y - 1500),
    (t7_in_x, t7_in_y)
]
draw_polyline(ms, points_h4_t7, ACADColors.RED, LineWeights.MEDIUM)
draw_arrow(ms, points_h4_t7[-2][0], points_h4_t7[-2][1], points_h4_t7[-1][0], points_h4_t7[-1][1], 500, ACADColors.RED)

print("   OK - Connections")

print("\n5. Zoom extents...")
acad.ZoomExtents()

print("\n" + "="*70)
print("V6 PART 1 COMPLETE!")
print("="*70)
print("\nCREATED:")
print("  - H1, H3, H4 with RED FRAME")
print("  - Silos 1-2 with labels")
print("  - T7 conveyor")
print("  - 14 red arrows from silos")
print("  - H4 -> T7 connection")
print("\nNEXT: Add remaining elements...")
