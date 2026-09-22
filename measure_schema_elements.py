# -*- coding: utf-8 -*-
"""
ВИМІРЮВАННЯ ЕЛЕМЕНТІВ СХЕМИ (web_temp.dxf)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json

print("="*70)
print("ВИМІРЮВАННЯ ЕЛЕМЕНТІВ СХЕМИ")
print("="*70)

try:
    # Підключення до AutoCAD
    print("\n[1] ПІДКЛЮЧЕННЯ ДО AUTOCAD...")
    acad = win32com.client.Dispatch("AutoCAD.Application")
    docs = acad.Documents

    # Відкрити web_temp.dxf
    dxf_path = "D:/autocad project/FINAL_DXF_PERFECT_V7/web_temp_adde8b6cfc43a61f00a8d5a90c2e670a_32945ae7236018cb9c5201d70b32a84c_o.dxf"

    print(f"[2] ВІДКРИВАЮ {dxf_path.split('/')[-1]}...")

    # Перевірити чи вже відкритий
    target_doc = None
    for i in range(docs.Count):
        doc = docs.Item(i)
        if "web_temp" in doc.Name:
            target_doc = doc
            print(f"    ✓ Вже відкритий: {doc.Name}")
            break

    if not target_doc:
        target_doc = docs.Open(dxf_path)
        print(f"    ✓ Відкрито!")

    acad.ActiveDocument = target_doc
    doc = acad.ActiveDocument
    ms = doc.ModelSpace

    print(f"    • Об'єктів: {ms.Count}")

    # Зумування
    print("\n[3] ЗУМУВАННЯ...")
    acad.Application.ZoomExtents()

    print(f"\n{'='*70}")
    print("✅ ФАЙЛ ВІДКРИТИЙ В AUTOCAD!")
    print(f"{'='*70}")

    # Інструкції для користувача
    print("\n📋 ІНСТРУКЦІЇ:")
    print("\n1. Подивись на креслення в AutoCAD")
    print("2. Знайди ПЕРШИЙ СИЛОС (найлівіший зверху)")
    print("3. Виміряй його:")
    print("   • Клік на контур силосу")
    print("   • Подивись Properties → Center або Bounds")
    print("   • Запиши координати центру (X, Y)")
    print("   • Запиши ширину та висоту")
    print("\n4. Повтори для ВСІХ 6 силосів")
    print("\n5. Запиши результати сюди:")

    # Створюю шаблон для заповнення
    template = {
        "source": "web_temp...dxf",
        "scale": "measured_in_autocad",
        "silos": [
            {
                "number": 1,
                "position": "upper_left",
                "center": {"x": 0, "y": 0},  # ← ЗАПОВНИ!
                "width": 0,  # ← ЗАПОВНИ!
                "height": 0,  # ← ЗАПОВНИ!
                "type": "МСВУ_D20_21m"
            },
            {
                "number": 2,
                "position": "upper_right",
                "center": {"x": 0, "y": 0},  # ← ЗАПОВНИ!
                "width": 0,
                "height": 0,
                "type": "МСВУ_D20_21m"
            },
            {
                "number": 3,
                "position": "middle_left",
                "center": {"x": 0, "y": 0},  # ← ЗАПОВНИ!
                "width": 0,
                "height": 0,
                "type": "МСВУ_D22_22m"
            },
            {
                "number": 4,
                "position": "middle_right",
                "center": {"x": 0, "y": 0},  # ← ЗАПОВНИ!
                "width": 0,
                "height": 0,
                "type": "МСВУ_D22_22m"
            },
            {
                "number": 5,
                "position": "lower_left",
                "center": {"x": 0, "y": 0},  # ← ЗАПОВНИ!
                "width": 0,
                "height": 0,
                "type": "МСВУ_D22_22m"
            },
            {
                "number": 6,
                "position": "lower_right",
                "center": {"x": 0, "y": 0},  # ← ЗАПОВНИ!
                "width": 0,
                "height": 0,
                "type": "МСВУ_D22_22m"
            }
        ],
        "noria": [
            {"tag": "H1", "position": {"x": 0, "y": 0}, "height": 0},
            {"tag": "H3", "position": {"x": 0, "y": 0}, "height": 0},
            {"tag": "H4", "position": {"x": 0, "y": 0}, "height": 0},
            {"tag": "H5", "position": {"x": 0, "y": 0}, "height": 0}
        ],
        "conveyors": []
    }

    # Зберегти шаблон
    output_path = "d:/autocad project/schema_measurements_TEMPLATE.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Шаблон збережено: {output_path}")
    print(f"\n⚠️  ЗАПОВНИ координати та розміри в цьому файлі!")

    # АБО - спробую автоматично
    print(f"\n{'='*70}")
    print("⚙️  СПРОБА АВТОМАТИЧНОГО ВИМІРУ...")
    print(f"{'='*70}")

    # Пробую знайти сині полілінії (контури силосів)
    print("\nШукаю сині об'єкти...")

    blue_objects = []

    for i in range(min(ms.Count, 1000)):
        try:
            obj = ms.Item(i)

            # Перевірка кольору (синій = 5)
            if hasattr(obj, 'Color') and obj.Color == 5:
                blue_objects.append({
                    'type': obj.ObjectName,
                    'index': i
                })

            # АБО шар з назвою "blue" / "синій"
            if hasattr(obj.dxf if hasattr(obj, 'dxf') else obj, 'Layer'):
                layer = obj.Layer if hasattr(obj, 'Layer') else None
                if layer and ('blue' in layer.lower() or '00-00-ff' in layer.lower()):
                    blue_objects.append({
                        'type': obj.ObjectName,
                        'index': i
                    })

        except:
            pass

    print(f"Знайдено синіх об'єктів: {len(blue_objects)}")

    if blue_objects:
        for idx, obj_info in enumerate(blue_objects[:10], 1):
            print(f"  {idx}. {obj_info['type']} (index: {obj_info['index']})")

except Exception as e:
    print(f"\n❌ ПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
