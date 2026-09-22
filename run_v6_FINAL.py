# -*- coding: utf-8 -*-
"""
V6 COMPLETE - FULL SCHEMA LIKE ORIGINAL
"""
import sys
sys.path.insert(0, "D:/autocad project/autocad-mcp")

import win32com.client
import pythoncom
from drawing_standards import LayerManager, LineWeights, ACADColors, set_object_properties
import math

def cp(x, y, z=0):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y, z])

def draw_arrow(ms, x1, y1, x2, y2, size=600, color=1):
    line = ms.AddLine(cp(x1, y1), cp(x2, y2))
    set_object_properties(line, color=color, lineweight=LineWeights.MEDIUM)
    dx, dy = x2-x1, y2-y1
    angle = math.atan2(dy, dx)
    aa = 25 * math.pi / 180
    lx = x2 - size * math.cos(angle - aa)
    ly = y2 - size * math.sin(angle - aa)
    rx = x2 - size * math.cos(angle + aa)
    ry = y2 - size * math.sin(angle + aa)
    ms.AddLine(cp(x2, y2), cp(lx, ly))
    ms.AddLine(cp(x2, y2), cp(rx, ry))
    return line

def silo(ms, doc, x, y, d, h, num):
    """Draw silo"""
    r = d/2
    doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_SILOS')

    # Rectangle
    for l in [
        ms.AddLine(cp(x-r, y), cp(x-r, y+h)),
        ms.AddLine(cp(x+r, y), cp(x+r, y+h)),
        ms.AddLine(cp(x-r, y), cp(x+r, y)),
        ms.AddLine(cp(x-r, y+h), cp(x+r, y+h))
    ]:
        set_object_properties(l, lineweight=LineWeights.THICK)

    # Cone
    ch = d * 0.35
    cy = y - ch
    ms.AddLine(cp(x-r, y), cp(x, cy))
    ms.AddLine(cp(x+r, y), cp(x, cy))
    ms.AddArc(cp(x, y+h), r, math.pi, 0)

    # Text
    doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
    t = ms.AddText(str(num), cp(x, y+h+r+500), 2500)
    t.Alignment = 10
    t.TextAlignmentPoint = cp(x, y+h+r+500)

    tt = ms.AddText("МСВУ 220.13.В12", cp(x, y+h/2), 500)
    tt.Alignment = 10
    tt.TextAlignmentPoint = cp(x, y+h/2)

    # 7 arrows
    doc.ActiveLayer = doc.Layers.Item('PIPES_MAIN')
    for i in range(7):
        ox = x - r*0.7 + i*(r*1.4/6)
        draw_arrow(ms, ox, y-300, ox, y-2000, 500, ACADColors.RED if num <= 2 else ACADColors.BLUE)

    return (x, y, r, h)

def noria(ms, doc, x, y, h, tag):
    """Draw noria"""
    w = 800
    doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_NORIA')
    ms.AddLine(cp(x-w/2, y), cp(x-w/2, y+h))
    ms.AddLine(cp(x+w/2, y), cp(x+w/2, y+h))
    ms.AddLine(cp(x-w/2, y), cp(x+w/2, y))
    ms.AddLine(cp(x-w/2, y+h), cp(x+w/2, y+h))

    doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
    ms.AddText(tag, cp(x+1200, y+h/2), 600)
    return (x, y)

def conv(ms, doc, x1, y1, x2, y2, w, tag):
    """Draw conveyor"""
    doc.ActiveLayer = doc.Layers.Item('CONVEYORS')
    ms.AddLine(cp(x1, y1+w/2), cp(x2, y2+w/2))
    ms.AddLine(cp(x1, y1-w/2), cp(x2, y2-w/2))

    doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
    mx = (x1+x2)/2
    my = (y1+y2)/2
    ms.AddText(tag, cp(mx, my+w+300), 500)
    ms.AddText("100 т/год", cp(mx, my+w+700), 300)

    # Arrow
    if x2 > x1:
        draw_arrow(ms, x1+(x2-x1)*0.3, y1, x1+(x2-x1)*0.5, y1, 400, ACADColors.CONVEYORS)
    return (x1, y1, x2, y2)

print("="*70)
print("V6 COMPLETE - RUNNING...")
print("="*70)

acad = win32com.client.Dispatch("AutoCAD.Application")
doc = acad.ActiveDocument
ms = doc.ModelSpace

print("\n1. Clear...")
c = 0
while ms.Count > 0:
    try:
        ms.Item(0).Delete()
        c += 1
    except:
        break
print(f"   {c} objects")

print("\n2. Layers...")
LayerManager(doc).create_all_standard_layers()

bx, by = 5000, 5000

# ВЕРХНІЙ ЛІВИЙ - H1, H3, H4
print("\n=== UPPER LEFT ===")
h4 = noria(ms, doc, bx+2000, by+28000, 8000, "H4")
h1 = noria(ms, doc, bx+1000, by+18000, 7000, "H1")
h3 = noria(ms, doc, bx+3000, by+8000, 7000, "H3")

# RED FRAME
doc.ActiveLayer = doc.Layers.Item('FRAME')
for l in [
    ms.AddLine(cp(bx-500, by+7000), cp(bx+4500, by+7000)),
    ms.AddLine(cp(bx+4500, by+7000), cp(bx+4500, by+37000)),
    ms.AddLine(cp(bx+4500, by+37000), cp(bx-500, by+37000)),
    ms.AddLine(cp(bx-500, by+37000), cp(bx-500, by+7000))
]:
    set_object_properties(l, color=ACADColors.RED, lineweight=LineWeights.EXTRA_THICK)

print("=== CENTER ===")
# T7
t7 = conv(ms, doc, bx+6000, by+33000, bx+25000, by+33000, 600, "T7")

# T8
t8 = conv(ms, doc, bx+6000, by+29000, bx+25000, by+29000, 600, "T8")

# SILOS 1-2
s1 = silo(ms, doc, bx+13000, by+15000, 9000, 11000, 1)
s2 = silo(ms, doc, bx+24000, by+15000, 9000, 11000, 2)

# T9
t9 = conv(ms, doc, bx+8000, by+11000, bx+28000, by+11000, 600, "T9")

# H5 (між силосами)
h5 = noria(ms, doc, bx+18500, by+15000, 10000, "H5")

print("=== LOWER LEFT ===")
# SILOS 3-4
s3 = silo(ms, doc, bx+8000, by+0, 9000, 11000, 3)
s4 = silo(ms, doc, bx+19000, by+0, 9000, 11000, 4)

# T12 (під силосами 3-4)
t12 = conv(ms, doc, bx+3000, by-4000, bx+24000, by-4000, 600, "T12")

print("=== RIGHT ===")
# T10
t10 = conv(ms, doc, bx+32000, by+35000, bx+48000, by+35000, 600, "T10")

# H6
h6 = noria(ms, doc, bx+44000, by+28000, 9000, "H6")

# RED FRAME for H6
doc.ActiveLayer = doc.Layers.Item('FRAME')
for l in [
    ms.AddLine(cp(bx+42000, by+27000), cp(bx+46000, by+27000)),
    ms.AddLine(cp(bx+46000, by+27000), cp(bx+46000, by+38000)),
    ms.AddLine(cp(bx+46000, by+38000), cp(bx+42000, by+38000)),
    ms.AddLine(cp(bx+42000, by+38000), cp(bx+42000, by+27000))
]:
    set_object_properties(l, color=ACADColors.RED, lineweight=LineWeights.EXTRA_THICK)

# T14 (vertical from H5 down)
t14 = conv(ms, doc, bx+26000, by+12000, bx+28000, by-2000, 600, "T14")

print("=== LOWER RIGHT ===")
# SILOS 5-6
s5 = silo(ms, doc, bx+33000, by-8000, 9000, 11000, 5)
s6 = silo(ms, doc, bx+44000, by-8000, 9000, 11000, 6)

# T11
t11 = conv(ms, doc, bx+28000, by-12000, bx+50000, by-12000, 600, "T11")

# T15, T16
t15 = conv(ms, doc, bx+28000, by-5000, bx+50000, by-5000, 600, "T15")
t16 = conv(ms, doc, bx+28000, by-2000, bx+50000, by-2000, 600, "T16")

# CONNECTIONS
print("\n=== CONNECTIONS ===")
doc.ActiveLayer = doc.Layers.Item('PIPES_MAIN')

# H4 -> T7
pts = [(h4[0], h4[1]-500), (h4[0], by+31000), (t7[0]-1000, by+31000), (t7[0]-1000, t7[1])]
for i in range(len(pts)-1):
    l = ms.AddLine(cp(pts[i][0], pts[i][1]), cp(pts[i+1][0], pts[i+1][1]))
    set_object_properties(l, color=ACADColors.RED, lineweight=LineWeights.MEDIUM)
draw_arrow(ms, pts[-2][0], pts[-2][1], pts[-1][0], pts[-1][1], 400, ACADColors.RED)

# H1 -> T8
pts = [(h1[0], h1[1]-500), (h1[0], by+27000), (t8[0]-1000, by+27000), (t8[0]-1000, t8[1])]
for i in range(len(pts)-1):
    l = ms.AddLine(cp(pts[i][0], pts[i][1]), cp(pts[i+1][0], pts[i+1][1]))
    set_object_properties(l, color=ACADColors.RED, lineweight=LineWeights.MEDIUM)

# H3 -> T8
pts = [(h3[0], h3[1]-500), (h3[0], by+27000), (t8[0]+2000, by+27000), (t8[0]+2000, t8[1])]
for i in range(len(pts)-1):
    l = ms.AddLine(cp(pts[i][0], pts[i][1]), cp(pts[i+1][0], pts[i+1][1]))
    set_object_properties(l, color=ACADColors.RED, lineweight=LineWeights.MEDIUM)

print("\n4. Zoom...")
acad.ZoomExtents()

print("\n" + "="*70)
print("V6 COMPLETE!")
print("="*70)
print("\nCREATED:")
print("  - H1, H3, H4 with red frame")
print("  - H5, H6 (H6 with red frame)")
print("  - Silos 1-6 with МСВУ labels")
print("  - Conveyors T7-T16")
print("  - 42 arrows (red/blue)")
print("  - Main connections")

# BUNKERS
print("\n=== BUNKERS ===")
doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_BUNKERS')

b81_x, b81_y, b81_w, b81_h = bx+21000, by+16000, 2000, 3000
out_w = b81_w * 0.4
ms.AddLine(cp(b81_x-b81_w/2, b81_y+b81_h), cp(b81_x+b81_w/2, b81_y+b81_h))
ms.AddLine(cp(b81_x-b81_w/2, b81_y+b81_h), cp(b81_x-out_w/2, b81_y))
ms.AddLine(cp(b81_x+b81_w/2, b81_y+b81_h), cp(b81_x+out_w/2, b81_y))
ms.AddLine(cp(b81_x-out_w/2, b81_y), cp(b81_x+out_w/2, b81_y))

doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
t81 = ms.AddText("8.1", cp(b81_x, b81_y+b81_h/2), 400)
t81.Alignment, t81.TextAlignmentPoint = 10, cp(b81_x, b81_y+b81_h/2)

b82_x, b82_y = bx+2000, by-5000
doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_BUNKERS')
ms.AddLine(cp(b82_x-b81_w/2, b82_y+b81_h), cp(b82_x+b81_w/2, b82_y+b81_h))
ms.AddLine(cp(b82_x-b81_w/2, b82_y+b81_h), cp(b82_x-out_w/2, b82_y))
ms.AddLine(cp(b82_x+b81_w/2, b82_y+b81_h), cp(b82_x+out_w/2, b82_y))
ms.AddLine(cp(b82_x-out_w/2, b82_y), cp(b82_x+out_w/2, b82_y))

doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
t82 = ms.AddText("8.2", cp(b82_x, b82_y+b81_h/2), 400)
t82.Alignment, t82.TextAlignmentPoint = 10, cp(b82_x, b82_y+b81_h/2)

# LEGEND
print("=== LEGEND ===")
doc.ActiveLayer = doc.Layers.Item('LEGEND')
leg_x, leg_y, leg_w, leg_h = bx+52000, by+30000, 8000, 8000

for x1, y1, x2, y2 in [(leg_x,leg_y,leg_x+leg_w,leg_y), (leg_x+leg_w,leg_y,leg_x+leg_w,leg_y+leg_h), (leg_x+leg_w,leg_y+leg_h,leg_x,leg_y+leg_h), (leg_x,leg_y+leg_h,leg_x,leg_y)]:
    ms.AddLine(cp(x1,y1), cp(x2,y2))

doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
title = ms.AddText("Умовні позначення", cp(leg_x+leg_w/2, leg_y+leg_h-600), 350)
title.Alignment, title.TextAlignmentPoint = 10, cp(leg_x+leg_w/2, leg_y+leg_h-600)

for txt, dy in [("Норія",-1500), ("Силос МСВУ",-2500), ("Транспортер",-3500), ("Бункер",-4500), ("Трубопровід",-5500)]:
    ms.AddText(txt, cp(leg_x+300, leg_y+leg_h+dy), 250)

# STAMP
print("=== STAMP ===")
doc.ActiveLayer = doc.Layers.Item('TITLE_BLOCK')
sx, sy, sw, sh = bx+38000, by-15000, 10000, 4000

for x1, y1, x2, y2 in [(sx,sy,sx+sw,sy), (sx+sw,sy,sx+sw,sy+sh), (sx+sw,sy+sh,sx,sy+sh), (sx,sy+sh,sx,sy), (sx+sw*0.7,sy,sx+sw*0.7,sy+sh)]:
    ms.AddLine(cp(x1,y1), cp(x2,y2))

doc.ActiveLayer = doc.Layers.Item('TEXT_LABELS')
name = ms.AddText("Схема технологічного процесу", cp(sx+sw/2, sy+sh-700), 300)
name.Alignment, name.TextAlignmentPoint = 10, cp(sx+sw/2, sy+sh-700)

from datetime import datetime
date = ms.AddText(datetime.now().strftime("%d.%m.%Y"), cp(sx+sw*0.85, sy+sh/2), 250)
date.Alignment, date.TextAlignmentPoint = 10, cp(sx+sw*0.85, sy+sh/2)

print("\nFINAL - BUNKERS, LEGEND, STAMP ADDED!")
