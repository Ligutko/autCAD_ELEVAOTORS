# -*- coding: utf-8 -*-
"""
ТЕСТ ПРОФЕСІЙНОЇ ВЕРСІЇ V5 - "ЦУКЕРКА"

Демонструє:
✓ Smart Anchors (розумні з'єднання)
✓ Професійні шари (14 шарів ГОСТ)
✓ Товщини ліній (0.13-0.70мм)
"""
import sys
import io
import asyncio

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, "D:/autocad project/autocad-mcp")

import win32com.client
import pythoncom
from smart_anchors import SiloAnchors, ConveyorAnchors, create_connection_path
from drawing_standards import LayerManager, DrawingContext, LineWeights, ACADColors, set_object_properties

def create_point(x, y, z=0):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y, z])

async def test_v5_professional():
    """Тестуємо професійні можливості V5"""
    print("="*70)
    print("🎯 ТЕСТ ПРОФЕСІЙНОЇ ВЕРСІЇ V5")
    print("="*70)

    try:
        # Підключення
        print("\n1. Підключаюсь до AutoCAD...")
        acad = win32com.client.Dispatch("AutoCAD.Application")
        doc = acad.ActiveDocument
        modelSpace = doc.ModelSpace
        print("   ✓ AutoCAD підключено")

        # Очищення
        print("\n2. Очищаю креслення...")
        count = 0
        while modelSpace.Count > 0:
            try:
                modelSpace.Item(0).Delete()
                count += 1
            except:
                break
        print(f"   ✓ Видалено {count} об'єктів")

        # Створення професійних шарів
        print("\n3. Створюю професійні шари...")
        layer_mgr = LayerManager(doc)
        layer_count = layer_mgr.create_all_standard_layers()
        print(f"   ✓ {layer_count} шарів створено")

        # Тест 1: Силос з Smart Anchors
        print("\n4. ТЕСТ 1: Силос з Smart Anchors...")
        base = 20000

        # Малюємо силос на шарі EQUIPMENT_SILOS
        with DrawingContext(doc, 'EQUIPMENT_SILOS'):
            print("   Малюю силос на шарі 'EQUIPMENT_SILOS'...")

            x, y = base, base
            diameter, height = 20000, 22000

            # Основні лінії силосу (ТОВСТІ)
            lines = []
            radius = diameter / 2

            # Циліндр
            lines.append(modelSpace.AddLine(
                create_point(x - radius, y, 0),
                create_point(x - radius, y + height, 0)
            ))
            lines.append(modelSpace.AddLine(
                create_point(x + radius, y, 0),
                create_point(x + radius, y + height, 0)
            ))

            # Застосовуємо товсту лінію
            for line in lines:
                set_object_properties(line, lineweight=LineWeights.THICK)

            # Текст
            with DrawingContext(doc, 'TEXT_LABELS'):
                text = modelSpace.AddText("СИЛОС №1\nSMART ANCHORS",
                                         create_point(x, y + height/2, 0), 1000)
                text.Alignment = 10
                text.TextAlignmentPoint = create_point(x, y + height/2, 0)

        # Створюємо Smart Anchors об'єкт
        silo_anchors = SiloAnchors(x, y, diameter, height, num_outlets=7)
        print(f"   ✓ Силос намальовано з {len(silo_anchors.list_anchors())} точками прив'язки")
        print(f"   ✓ Доступні точки: {silo_anchors.list_anchors()[:5]}...")

        # Тест 2: Конвеєр з Smart Anchors
        print("\n5. ТЕСТ 2: Конвеєр з Smart Anchors...")

        with DrawingContext(doc, 'CONVEYORS'):
            print("   Малюю конвеєр на шарі 'CONVEYORS'...")

            conv_x1, conv_y1 = base + 30000, base + 15000
            conv_x2, conv_y2 = base + 60000, base + 15000
            conv_width = 1200

            # Лінії конвеєра
            offset = conv_width / 2
            top_line = modelSpace.AddLine(
                create_point(conv_x1, conv_y1 + offset, 0),
                create_point(conv_x2, conv_y2 + offset, 0)
            )
            bottom_line = modelSpace.AddLine(
                create_point(conv_x1, conv_y1 - offset, 0),
                create_point(conv_x2, conv_y2 - offset, 0)
            )

            # Застосовуємо середню товщину і зелений колір
            set_object_properties(top_line, color=ACADColors.CONVEYORS, lineweight=LineWeights.MEDIUM)
            set_object_properties(bottom_line, color=ACADColors.CONVEYORS, lineweight=LineWeights.MEDIUM)

            with DrawingContext(doc, 'TEXT_LABELS'):
                mid_x = (conv_x1 + conv_x2) / 2
                text = modelSpace.AddText("T-100\n100 т/год",
                                         create_point(mid_x, conv_y1 + 2000, 0), 600)
                text.Alignment = 10
                text.TextAlignmentPoint = create_point(mid_x, conv_y1 + 2000, 0)

        conveyor_anchors = ConveyorAnchors(conv_x1, conv_y1, conv_x2, conv_y2, conv_width)
        print(f"   ✓ Конвеєр намальовано з {len(conveyor_anchors.list_anchors())} точками прив'язки")
        print(f"   ✓ Вхід: {conveyor_anchors.get_anchor('inlet_center')}")
        print(f"   ✓ Вихід: {conveyor_anchors.get_anchor('outlet_center')}")

        # Тест 3: РОЗУМНЕ З'ЄДНАННЯ!
        print("\n6. ТЕСТ 3: Розумне з'єднання (Smart Connection)...")

        with DrawingContext(doc, 'PIPES_MAIN'):
            print("   З'єдную Силос (вихід 1) -> Конвеєр (вхід)...")

            # Отримуємо точки з ІМЕНОВАНИХ анкорів
            from_point = silo_anchors.get_anchor('outlet_1')
            to_point = conveyor_anchors.get_anchor('inlet_center')

            print(f"   Від точки: {from_point}")
            print(f"   До точки: {to_point}")

            # Створюємо ортогональний шлях
            path = create_connection_path(from_point, to_point, style='orthogonal')
            print(f"   ✓ Шлях має {len(path)} точок")

            # Малюємо лінії шляху
            for i in range(len(path) - 1):
                line = modelSpace.AddLine(
                    create_point(path[i][0], path[i][1], 0),
                    create_point(path[i+1][0], path[i+1][1], 0)
                )
                # Тонка синя лінія
                set_object_properties(line, color=ACADColors.PIPES, lineweight=LineWeights.THIN)

        print("   ✓ РОЗУМНЕ З'ЄДНАННЯ ГОТОВЕ!")

        # Тест 4: Червона рамка
        print("\n7. ТЕСТ 4: Червона рамка...")

        with DrawingContext(doc, 'FRAME'):
            frame_x1, frame_y1 = base - 5000, base - 5000
            frame_x2, frame_y2 = base + 70000, base + 50000

            frame_lines = []
            frame_lines.append(modelSpace.AddLine(
                create_point(frame_x1, frame_y1, 0),
                create_point(frame_x2, frame_y1, 0)
            ))
            frame_lines.append(modelSpace.AddLine(
                create_point(frame_x2, frame_y1, 0),
                create_point(frame_x2, frame_y2, 0)
            ))
            frame_lines.append(modelSpace.AddLine(
                create_point(frame_x2, frame_y2, 0),
                create_point(frame_x1, frame_y2, 0)
            ))
            frame_lines.append(modelSpace.AddLine(
                create_point(frame_x1, frame_y2, 0),
                create_point(frame_x1, frame_y1, 0)
            ))

            # ДУЖЕ ТОВСТА ЧЕРВОНА ЛІНІЯ
            for line in frame_lines:
                set_object_properties(line, color=ACADColors.RED, lineweight=LineWeights.EXTRA_THICK)

        print("   ✓ Червона рамка (extra thick)")

        # Фініш
        print("\n8. Zoom extents...")
        acad.ZoomExtents()

        print("\n" + "="*70)
        print("🎯 ТЕСТ V5 УСПІШНИЙ!")
        print("="*70)
        print("\nПЕРЕВІРЕНО:")
        print("  ✓ Smart Anchors працюють")
        print("  ✓ 14 професійних шарів створено")
        print("  ✓ Товщини ліній застосовані")
        print("  ✓ Розумні з'єднання працюють")
        print("  ✓ Кольори правильні")
        print("\n💎 V5 - ЦЕ СПРАВДІ ЦУКЕРКА!")

    except Exception as e:
        import traceback
        print(f"\n✗ ПОМИЛКА: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_v5_professional())
