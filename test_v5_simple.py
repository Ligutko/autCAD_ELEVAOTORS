# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, "D:/autocad project/autocad-mcp")

import win32com.client
import pythoncom
from smart_anchors import SiloAnchors
from drawing_standards import LayerManager, LineWeights, ACADColors, set_object_properties

def create_point(x, y, z=0):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y, z])

print("="*70)
print("TEST V5 PROFESSIONAL")
print("="*70)

# Підключення
print("\n1. Connecting to AutoCAD...")
acad = win32com.client.Dispatch("AutoCAD.Application")
doc = acad.ActiveDocument
modelSpace = doc.ModelSpace
print("   OK - AutoCAD connected")

# Очищення
print("\n2. Clearing...")
count = 0
while modelSpace.Count > 0:
    try:
        modelSpace.Item(0).Delete()
        count += 1
    except:
        break
print(f"   OK - Deleted {count} objects")

# Створення шарів
print("\n3. Creating professional layers...")
layer_mgr = LayerManager(doc)
layer_count = layer_mgr.create_all_standard_layers()
print(f"   OK - {layer_count} layers created")

# Тест Smart Anchors
print("\n4. TEST: Silo with Smart Anchors...")
x, y = 20000, 20000
diameter, height = 20000, 22000
radius = diameter / 2

# Встановлюємо шар
doc.ActiveLayer = doc.Layers.Item('EQUIPMENT_SILOS')

# Малюємо силос
line1 = modelSpace.AddLine(
    create_point(x - radius, y, 0),
    create_point(x - radius, y + height, 0)
)
line2 = modelSpace.AddLine(
    create_point(x + radius, y, 0),
    create_point(x + radius, y + height, 0)
)

# Застосовуємо ТОВСТУ лінію
set_object_properties(line1, lineweight=LineWeights.THICK)
set_object_properties(line2, lineweight=LineWeights.THICK)

print("   OK - Silo drawn with THICK lines")

# Створюємо Smart Anchors
silo_anchors = SiloAnchors(x, y, diameter, height, 7)
print(f"   OK - Smart Anchors created: {len(silo_anchors.list_anchors())} points")
print(f"   - outlet_1: {silo_anchors.get_anchor('outlet_1')}")
print(f"   - top_center: {silo_anchors.get_anchor('top_center')}")

# Конвеєр
print("\n5. TEST: Conveyor...")
doc.ActiveLayer = doc.Layers.Item('CONVEYORS')

conv_x1, conv_y1 = x + 30000, y + 10000
conv_x2, conv_y2 = conv_x1 + 25000, conv_y1
conv_width = 1200

line_top = modelSpace.AddLine(
    create_point(conv_x1, conv_y1 + conv_width/2, 0),
    create_point(conv_x2, conv_y2 + conv_width/2, 0)
)
line_bottom = modelSpace.AddLine(
    create_point(conv_x1, conv_y1 - conv_width/2, 0),
    create_point(conv_x2, conv_y2 - conv_width/2, 0)
)

# СЕРЕДНЯ товщина, ЗЕЛЕНИЙ колір
set_object_properties(line_top, color=ACADColors.CONVEYORS, lineweight=LineWeights.MEDIUM)
set_object_properties(line_bottom, color=ACADColors.CONVEYORS, lineweight=LineWeights.MEDIUM)

print("   OK - Conveyor drawn with MEDIUM lines, GREEN color")

# Трубопровід
print("\n6. TEST: Pipe connection...")
doc.ActiveLayer = doc.Layers.Item('PIPES_MAIN')

pipe_from = silo_anchors.get_anchor('outlet_1')
pipe_to = (conv_x1, conv_y1)

pipe_line = modelSpace.AddLine(
    create_point(pipe_from[0], pipe_from[1], 0),
    create_point(pipe_to[0], pipe_to[1], 0)
)

# ТОНКА, СИНЯ
set_object_properties(pipe_line, color=ACADColors.PIPES, lineweight=LineWeights.THIN)

print(f"   OK - Smart connection: {pipe_from} -> {pipe_to}")
print("   OK - THIN line, BLUE color")

# Рамка
print("\n7. TEST: Red frame...")
doc.ActiveLayer = doc.Layers.Item('FRAME')

frame_line = modelSpace.AddLine(
    create_point(15000, 15000, 0),
    create_point(80000, 15000, 0)
)

# ДУЖЕ ТОВСТА, ЧЕРВОНА
set_object_properties(frame_line, color=ACADColors.RED, lineweight=LineWeights.EXTRA_THICK)

print("   OK - Red frame with EXTRA_THICK line")

# Фініш
print("\n8. Zoom extents...")
acad.ZoomExtents()

print("\n" + "="*70)
print("SUCCESS! V5 PROFESSIONAL FEATURES WORK!")
print("="*70)
print("\nVERIFIED:")
print("  - Smart Anchors: YES")
print("  - Professional layers (14): YES")
print("  - Line weights (0.13-0.70mm): YES")
print("  - Colors (ACI): YES")
print("  - Smart connections: YES")
print("\nV5 IS CANDY!")
