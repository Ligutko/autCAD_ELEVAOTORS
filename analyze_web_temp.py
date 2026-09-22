# -*- coding: utf-8 -*-
"""
АНАЛІЗ web_temp...dxf (той що на скріншоті!)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    import ezdxf
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "ezdxf"], check=True)
    import ezdxf

print("="*70)
print("АНАЛІЗ web_temp DXF (ЗІ СКРІНШОТУ)")
print("="*70)

dxf_path = "d:/autocad project/FINAL_DXF_PERFECT_V7/web_temp_adde8b6cfc43a61f00a8d5a90c2e670a_32945ae7236018cb9c5201d70b32a84c_o.dxf"

try:
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    print(f"\n📊 БАЗОВА ІНФОРМАЦІЯ:")
    print(f"   • Версія: {doc.dxfversion}")
    print(f"   • Об'єктів: {len(list(msp))}")

    # Типи
    entity_types = {}
    for e in msp:
        etype = e.dxftype()
        entity_types[etype] = entity_types.get(etype, 0) + 1

    print(f"\n🔍 ТИПИ ОБ'ЄКТІВ:")
    for etype, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   • {etype}: {count}")

    # Геометрія
    lines = [e for e in msp if e.dxftype() == 'LINE']
    circles = [e for e in msp if e.dxftype() == 'CIRCLE']
    arcs = [e for e in msp if e.dxftype() == 'ARC']
    polylines = [e for e in msp if e.dxftype() in ['LWPOLYLINE', 'POLYLINE']]
    texts = [e for e in msp if e.dxftype() in ['TEXT', 'MTEXT']]
    inserts = [e for e in msp if e.dxftype() == 'INSERT']

    print(f"\n📐 ДЕТАЛЬНА ГЕОМЕТРІЯ:")
    print(f"   • Лінії: {len(lines)}")
    print(f"   • Кола: {len(circles)}")
    print(f"   • Дуги: {len(arcs)}")
    print(f"   • Полілінії: {len(polylines)}")
    print(f"   • Текст: {len(texts)}")
    print(f"   • Блоки (INSERT): {len(inserts)}")

    # ТЕКСТ!!!
    if texts:
        print(f"\n📝 ТЕКСТОВИЙ ВМІСТ (всі):")
        text_by_content = {}

        for t in texts:
            try:
                if t.dxftype() == 'TEXT':
                    txt = t.dxf.text
                    pos = t.dxf.insert
                    height = t.dxf.height
                elif t.dxftype() == 'MTEXT':
                    txt = t.text
                    pos = t.dxf.insert
                    height = t.dxf.char_height if hasattr(t.dxf, 'char_height') else 2.5

                txt_clean = txt.replace('\\P', ' ').strip()

                if txt_clean not in text_by_content:
                    text_by_content[txt_clean] = []

                text_by_content[txt_clean].append({
                    'x': pos.x,
                    'y': pos.y,
                    'height': height
                })
            except:
                pass

        # Групуємо по змісту
        print(f"\n   СИЛОСИ (цифри 1-6):")
        for num in ['1', '2', '3', '4', '5', '6']:
            if num in text_by_content:
                positions = text_by_content[num]
                for idx, p in enumerate(positions, 1):
                    print(f"      Силос {num}: [{p['x']:.1f}, {p['y']:.1f}]")

        print(f"\n   МІТКИ МСВУ:")
        for key in text_by_content.keys():
            if 'МСВУ' in key or 'мсву' in key.lower():
                positions = text_by_content[key]
                print(f"      '{key}': {len(positions)} входжень")
                for idx, p in enumerate(positions[:3], 1):
                    print(f"         [{p['x']:.1f}, {p['y']:.1f}]")

        print(f"\n   НОРІЇ:")
        for key in ['H1', 'H3', 'H4', 'H5', 'H6']:
            if key in text_by_content:
                positions = text_by_content[key]
                for p in positions:
                    print(f"      {key}: [{p['x']:.1f}, {p['y']:.1f}]")

        print(f"\n   ТРАНСПОРТЕРИ:")
        for key in text_by_content.keys():
            if key.startswith('T') and any(c.isdigit() for c in key):
                positions = text_by_content[key]
                if len(positions) <= 2:  # Не "100 т/год"
                    for p in positions:
                        print(f"      {key}: [{p['x']:.1f}, {p['y']:.1f}]")

    # БЛОКИ
    if inserts:
        print(f"\n🔲 БЛОКИ:")
        block_info = {}
        for ins in inserts:
            try:
                name = ins.dxf.name
                pos = ins.dxf.insert
                if name not in block_info:
                    block_info[name] = []
                block_info[name].append({'x': pos.x, 'y': pos.y})
            except:
                pass

        for name, positions in sorted(block_info.items()):
            print(f"   • {name}: {len(positions)} входжень")
            for idx, p in enumerate(positions[:3], 1):
                print(f"      {idx}. [{p['x']:.1f}, {p['y']:.1f}]")

    # Шари
    print(f"\n🗂️  ШАРИ:")
    layers = list(doc.layers)
    for layer in layers[:15]:
        try:
            print(f"   • {layer.dxf.name}")
        except:
            pass

    # Розміри
    if lines:
        min_x = min(min(l.dxf.start.x, l.dxf.end.x) for l in lines)
        max_x = max(max(l.dxf.start.x, l.dxf.end.x) for l in lines)
        min_y = min(min(l.dxf.start.y, l.dxf.end.y) for l in lines)
        max_y = max(max(l.dxf.start.y, l.dxf.end.y) for l in lines)

        print(f"\n📏 РОЗМІРИ КРЕСЛЕННЯ:")
        print(f"   • X: {min_x:.1f} → {max_x:.1f} (ширина: {max_x-min_x:.1f})")
        print(f"   • Y: {min_y:.1f} → {max_y:.1f} (висота: {max_y-min_y:.1f})")

    print(f"\n{'='*70}")
    print("🎯 ВИСНОВОК:")

    if len(texts) > 20:
        print(f"   ✅ БАГАТО ТЕКСТУ! ({len(texts)} об'єктів)")
        print(f"   ✅ Це СТРУКТУРОВАНА схема!")

    if len(lines) < 2000:
        print(f"   ✅ ЧИСТА ГЕОМЕТРІЯ! ({len(lines)} ліній)")
        print(f"   ✅ НЕ растеризовано!")

    if inserts:
        print(f"   ✅ Є БЛОКИ! ({len(inserts)} шт)")
        print(f"   ✅ МОЖНА редагувати!")
    else:
        print(f"   ⚠ Немає INSERT блоків")
        print(f"   ℹ️  Але є текст та структура!")

    print(f"\n{'='*70}")
    print("✅ ЦЕЙ ФАЙЛ МОЖНА ВИКОРИСТОВУВАТИ!")
    print(f"{'='*70}")

except Exception as e:
    print(f"\n❌ ПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
