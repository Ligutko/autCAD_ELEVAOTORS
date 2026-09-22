# -*- coding: utf-8 -*-
"""
АНАЛІЗ АКТИВНОГО ДОКУМЕНТА В AUTOCAD
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client

print("="*70)
print("АНАЛІЗ АКТИВНОГО ДОКУМЕНТА (page_02.dxf)")
print("="*70)

try:
    acad = win32com.client.Dispatch("AutoCAD.Application")
    doc = acad.ActiveDocument
    ms = doc.ModelSpace

    print(f"\n📄 Активний документ: {doc.Name}")
    print(f"\n📊 БАЗОВА СТАТИСТИКА:")
    print(f"   • Всього об'єктів: {ms.Count}")

    # Аналіз типів об'єктів
    print(f"\n🔍 ДЕТАЛЬНИЙ АНАЛІЗ ОБ'ЄКТІВ:")

    lines_count = 0
    circles_count = 0
    arcs_count = 0
    polylines_count = 0
    text_count = 0
    mtext_count = 0
    blocks_count = 0
    splines_count = 0

    object_types = {}

    # Аналіз перших 1000 об'єктів
    for i in range(min(ms.Count, 1000)):
        try:
            obj = ms.Item(i)
            obj_type = obj.ObjectName

            if obj_type not in object_types:
                object_types[obj_type] = 0
            object_types[obj_type] += 1

            if obj_type == "AcDbLine":
                lines_count += 1
            elif obj_type == "AcDbCircle":
                circles_count += 1
            elif obj_type == "AcDbArc":
                arcs_count += 1
            elif obj_type == "AcDbPolyline" or obj_type == "AcDbPolyline2d":
                polylines_count += 1
            elif obj_type == "AcDbText":
                text_count += 1
            elif obj_type == "AcDbMText":
                mtext_count += 1
            elif obj_type == "AcDbBlockReference":
                blocks_count += 1
            elif obj_type == "AcDbSpline":
                splines_count += 1
        except:
            pass

    print(f"   • Лінії (AcDbLine): {lines_count}")
    print(f"   • Кола (AcDbCircle): {circles_count}")
    print(f"   • Дуги (AcDbArc): {arcs_count}")
    print(f"   • Полілінії: {polylines_count}")
    print(f"   • Сплайни: {splines_count}")
    print(f"   • Текст (AcDbText): {text_count}")
    print(f"   • Багаторядковий текст (AcDbMText): {mtext_count}")
    print(f"   • Блоки: {blocks_count}")

    print(f"\n📋 ВСІ ТИПИ ОБ'ЄКТІВ:")
    for obj_type, count in sorted(object_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   • {obj_type}: {count}")

    # НАЙВАЖЛИВІШЕ - ТЕКСТ!
    print(f"\n📝 ТЕКСТОВИЙ ВМІСТ (перші 50):")
    text_samples = []

    for i in range(min(ms.Count, 2000)):
        try:
            obj = ms.Item(i)

            if obj.ObjectName == "AcDbText":
                text_samples.append({
                    'text': obj.TextString,
                    'x': obj.InsertionPoint[0],
                    'y': obj.InsertionPoint[1],
                    'height': obj.Height
                })
            elif obj.ObjectName == "AcDbMText":
                text_samples.append({
                    'text': obj.TextString,
                    'x': obj.InsertionPoint[0],
                    'y': obj.InsertionPoint[1],
                    'height': obj.Height
                })

            if len(text_samples) >= 50:
                break
        except:
            pass

    for idx, t in enumerate(text_samples, 1):
        txt_clean = t['text'].replace('\n', ' ').strip()[:60]
        print(f"   {idx}. [{t['x']:.0f}, {t['y']:.0f}] h={t['height']:.1f}: {txt_clean}")

    # Аналіз кіл (СИЛОСИ!)
    if circles_count > 0:
        print(f"\n⭕ ДЕТАЛЬНИЙ АНАЛІЗ КІЛ (силоси):")
        circle_info = []

        for i in range(min(ms.Count, 2000)):
            try:
                obj = ms.Item(i)
                if obj.ObjectName == "AcDbCircle":
                    circle_info.append({
                        'x': obj.Center[0],
                        'y': obj.Center[1],
                        'radius': obj.Radius,
                        'diameter': obj.Radius * 2
                    })

                if len(circle_info) >= 20:
                    break
            except:
                pass

        for idx, c in enumerate(circle_info, 1):
            print(f"   {idx}. Центр: [{c['x']:.0f}, {c['y']:.0f}] Діаметр: {c['diameter']:.0f}")

    # Шари
    print(f"\n🗂️  ШАРИ:")
    layer_objects = {}

    for i in range(min(ms.Count, 1000)):
        try:
            obj = ms.Item(i)
            layer = obj.Layer
            layer_objects[layer] = layer_objects.get(layer, 0) + 1
        except:
            pass

    for layer, count in sorted(layer_objects.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"   • {layer}: {count} об'єктів")

    # Блоки
    if blocks_count > 0:
        print(f"\n🔲 БЛОКИ:")
        block_names = {}

        for i in range(min(ms.Count, 1000)):
            try:
                obj = ms.Item(i)
                if obj.ObjectName == "AcDbBlockReference":
                    name = obj.Name
                    block_names[name] = block_names.get(name, 0) + 1
            except:
                pass

        for name, count in sorted(block_names.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {name}: {count}x")

    print(f"\n{'='*70}")
    print("✅ АНАЛІЗ ЗАВЕРШЕНО!")
    print(f"{'='*70}")

except Exception as e:
    print(f"\n❌ ПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
