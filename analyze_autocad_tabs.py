# -*- coding: utf-8 -*-
"""
АНАЛІЗ ВКЛАДОК AUTOCAD - КОНВЕРТОВАНІ PDF→DXF
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import pythoncom

print("="*70)
print("АНАЛІЗ КОНВЕРТОВАНИХ DXF ФАЙЛІВ В AUTOCAD")
print("="*70)

try:
    acad = win32com.client.Dispatch("AutoCAD.Application")
    docs = acad.Documents

    print(f"\n📂 Всього відкритих документів: {docs.Count}")
    print("\n" + "="*70)

    # Аналіз кожної вкладки
    for i in range(docs.Count):
        try:
            doc = docs.Item(i)
            print(f"\n{'='*70}")
            print(f"📄 ДОКУМЕНТ #{i+1}: {doc.Name}")
            print(f"{'='*70}")

            # Перемикаємось на цей документ
            acad.ActiveDocument = doc

            # Отримуємо ModelSpace після активації
            ms = acad.ActiveDocument.ModelSpace
        except Exception as e:
            print(f"❌ Помилка доступу: {e}")
            continue

        # Базова статистика
        print(f"\n📊 БАЗОВА СТАТИСТИКА:")
        print(f"   • Всього об'єктів: {ms.Count}")

        # Аналіз шарів
        print(f"\n🗂️  ШАРИ (Layers):")
        layers_info = {}
        for j in range(doc.Layers.Count):
            layer = doc.Layers.Item(j)
            layers_info[layer.Name] = {
                'color': layer.Color,
                'lineweight': layer.Lineweight,
                'on': layer.LayerOn
            }
            print(f"   • {layer.Name}")
            print(f"     - Колір: {layer.Color}")
            print(f"     - Товщина ліній: {layer.Lineweight}")
            print(f"     - Увімкнений: {layer.LayerOn}")

        # Аналіз типів об'єктів
        print(f"\n🔍 ТИПИ ОБ'ЄКТІВ:")
        object_types = {}

        for k in range(min(ms.Count, 100)):  # Перші 100 об'єктів
            try:
                obj = ms.Item(k)
                obj_type = obj.ObjectName
                if obj_type not in object_types:
                    object_types[obj_type] = 0
                object_types[obj_type] += 1
            except:
                pass

        for obj_type, count in sorted(object_types.items()):
            print(f"   • {obj_type}: {count}")

        # Детальний аналіз геометрії
        print(f"\n📐 ДЕТАЛЬНИЙ АНАЛІЗ ГЕОМЕТРІЇ:")

        lines_count = 0
        circles_count = 0
        arcs_count = 0
        polylines_count = 0
        text_count = 0
        blocks_count = 0

        min_x, max_x = float('inf'), float('-inf')
        min_y, max_y = float('inf'), float('-inf')

        for k in range(min(ms.Count, 500)):  # Перші 500 об'єктів
            try:
                obj = ms.Item(k)
                obj_type = obj.ObjectName

                if obj_type == "AcDbLine":
                    lines_count += 1
                    # Координати початку/кінця
                    sp = obj.StartPoint
                    ep = obj.EndPoint
                    min_x = min(min_x, sp[0], ep[0])
                    max_x = max(max_x, sp[0], ep[0])
                    min_y = min(min_y, sp[1], ep[1])
                    max_y = max(max_y, sp[1], ep[1])

                elif obj_type == "AcDbCircle":
                    circles_count += 1
                    center = obj.Center
                    radius = obj.Radius
                    min_x = min(min_x, center[0] - radius)
                    max_x = max(max_x, center[0] + radius)
                    min_y = min(min_y, center[1] - radius)
                    max_y = max(max_y, center[1] + radius)

                elif obj_type == "AcDbArc":
                    arcs_count += 1

                elif obj_type == "AcDbPolyline":
                    polylines_count += 1

                elif obj_type == "AcDbText" or obj_type == "AcDbMText":
                    text_count += 1

                elif obj_type == "AcDbBlockReference":
                    blocks_count += 1

            except:
                pass

        print(f"   • Лінії (Lines): {lines_count}")
        print(f"   • Кола (Circles): {circles_count}")
        print(f"   • Дуги (Arcs): {arcs_count}")
        print(f"   • Полілінії (Polylines): {polylines_count}")
        print(f"   • Текст (Text): {text_count}")
        print(f"   • Блоки (Blocks): {blocks_count}")

        if min_x != float('inf'):
            print(f"\n📏 РОЗМІРИ КРЕСЛЕННЯ:")
            print(f"   • X: від {min_x:.0f} до {max_x:.0f} (ширина: {max_x-min_x:.0f})")
            print(f"   • Y: від {min_y:.0f} до {max_y:.0f} (висота: {max_y-min_y:.0f})")

        # Аналіз текстових елементів
        print(f"\n📝 ПРИКЛАДИ ТЕКСТУ (перші 10):")
        text_samples = []
        for k in range(min(ms.Count, 500)):
            try:
                obj = ms.Item(k)
                if obj.ObjectName == "AcDbText":
                    text_samples.append(obj.TextString)
                elif obj.ObjectName == "AcDbMText":
                    text_samples.append(obj.TextString)
                if len(text_samples) >= 10:
                    break
            except:
                pass

        for idx, txt in enumerate(text_samples, 1):
            print(f"   {idx}. {txt[:50]}...")

        print(f"\n{'='*70}\n")

    print("\n" + "="*70)
    print("✅ АНАЛІЗ ЗАВЕРШЕНО!")
    print("="*70)

except Exception as e:
    print(f"\n❌ ПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
