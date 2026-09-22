# -*- coding: utf-8 -*-
"""
ПЕРЕМИКАННЯ НА page_02.dxf ТА ДЕТАЛЬНИЙ АНАЛІЗ
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client

print("="*70)
print("ПЕРЕМИКАННЯ НА page_02.dxf")
print("="*70)

try:
    acad = win32com.client.Dispatch("AutoCAD.Application")
    docs = acad.Documents

    # Знаходимо page_02.dxf
    target_doc = None
    for i in range(docs.Count):
        doc = docs.Item(i)
        if "page_02" in doc.Name:
            target_doc = doc
            break

    if not target_doc:
        print("❌ page_02.dxf не знайдено!")
        print("\nДоступні документи:")
        for i in range(docs.Count):
            print(f"  • {docs.Item(i).Name}")
        sys.exit(1)

    # ПЕРЕМИКАЄМОСЬ
    print(f"\n✓ Знайдено: {target_doc.Name}")
    print(f"✓ Перемикаюсь...")
    acad.ActiveDocument = target_doc
    doc = acad.ActiveDocument
    ms = doc.ModelSpace

    print(f"\n{'='*70}")
    print(f"📄 АКТИВНИЙ ДОКУМЕНТ: {doc.Name}")
    print(f"{'='*70}")

    print(f"\n📊 БАЗОВА СТАТИСТИКА:")
    print(f"   • Всього об'єктів: {ms.Count}")

    # Детальний аналіз
    print(f"\n🔍 АНАЛІЗ ОБ'ЄКТІВ (перші 2000):")

    lines = circles = arcs = polylines = texts = mtexts = blocks = splines = 0
    object_types = {}

    for i in range(min(ms.Count, 2000)):
        try:
            obj = ms.Item(i)
            otype = obj.ObjectName
            object_types[otype] = object_types.get(otype, 0) + 1

            if otype == "AcDbLine": lines += 1
            elif otype == "AcDbCircle": circles += 1
            elif otype == "AcDbArc": arcs += 1
            elif "Polyline" in otype: polylines += 1
            elif otype == "AcDbText": texts += 1
            elif otype == "AcDbMText": mtexts += 1
            elif otype == "AcDbBlockReference": blocks += 1
            elif otype == "AcDbSpline": splines += 1
        except:
            pass

    print(f"   • Лінії: {lines}")
    print(f"   • Кола: {circles}")
    print(f"   • Дуги: {arcs}")
    print(f"   • Полілінії: {polylines}")
    print(f"   • Сплайни: {splines}")
    print(f"   • Текст: {texts}")
    print(f"   • MText: {mtexts}")
    print(f"   • Блоки: {blocks}")

    print(f"\n📋 ВСІ ТИПИ:")
    for otype, count in sorted(object_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   • {otype}: {count}")

    # ТЕКСТ - КЛЮЧОВЕ!
    print(f"\n📝 ВЕСЬ ТЕКСТОВИЙ ВМІСТ:")
    text_data = []

    for i in range(ms.Count):
        try:
            obj = ms.Item(i)

            if obj.ObjectName == "AcDbText":
                text_data.append({
                    'type': 'TEXT',
                    'text': obj.TextString,
                    'x': obj.InsertionPoint[0],
                    'y': obj.InsertionPoint[1],
                    'height': obj.Height,
                    'layer': obj.Layer
                })
            elif obj.ObjectName == "AcDbMText":
                text_data.append({
                    'type': 'MTEXT',
                    'text': obj.TextString,
                    'x': obj.InsertionPoint[0],
                    'y': obj.InsertionPoint[1],
                    'height': obj.Height,
                    'layer': obj.Layer
                })
        except:
            pass

    print(f"\n   ЗНАЙДЕНО ТЕКСТІВ: {len(text_data)}")
    for idx, t in enumerate(text_data, 1):
        txt = t['text'].replace('\\P', ' ').replace('\n', ' ').strip()
        print(f"   {idx}. [{t['x']:.0f}, {t['y']:.0f}] h={t['height']:.1f} ({t['layer']}): {txt[:80]}")

    # КОЛА (силоси!)
    if circles > 0:
        print(f"\n⭕ КОЛА (СИЛОСИ):")
        circle_data = []

        for i in range(ms.Count):
            try:
                obj = ms.Item(i)
                if obj.ObjectName == "AcDbCircle":
                    circle_data.append({
                        'x': obj.Center[0],
                        'y': obj.Center[1],
                        'radius': obj.Radius,
                        'diameter': obj.Radius * 2,
                        'layer': obj.Layer
                    })
            except:
                pass

        print(f"   ЗНАЙДЕНО КІЛ: {len(circle_data)}")
        for idx, c in enumerate(circle_data, 1):
            print(f"   {idx}. Центр: [{c['x']:.0f}, {c['y']:.0f}] D={c['diameter']:.0f} ({c['layer']})")

    # Блоки
    if blocks > 0:
        print(f"\n🔲 БЛОКИ:")
        block_info = {}

        for i in range(ms.Count):
            try:
                obj = ms.Item(i)
                if obj.ObjectName == "AcDbBlockReference":
                    name = obj.Name
                    x, y = obj.InsertionPoint[0], obj.InsertionPoint[1]
                    if name not in block_info:
                        block_info[name] = []
                    block_info[name].append((x, y))
            except:
                pass

        for name, positions in sorted(block_info.items()):
            print(f"   • {name}: {len(positions)} входжень")
            for idx, (x, y) in enumerate(positions[:5], 1):
                print(f"     {idx}. [{x:.0f}, {y:.0f}]")

    # Шари з об'єктами
    print(f"\n🗂️  РОЗПОДІЛ ПО ШАРАХ:")
    layer_count = {}

    for i in range(min(ms.Count, 2000)):
        try:
            obj = ms.Item(i)
            layer = obj.Layer
            layer_count[layer] = layer_count.get(layer, 0) + 1
        except:
            pass

    for layer, count in sorted(layer_count.items(), key=lambda x: x[1], reverse=True):
        print(f"   • {layer}: {count}")

    print(f"\n{'='*70}")
    print("✅ ДЕТАЛЬНИЙ АНАЛІЗ ЗАВЕРШЕНО!")
    print(f"{'='*70}")

except Exception as e:
    print(f"\n❌ ПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
