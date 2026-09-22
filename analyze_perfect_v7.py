# -*- coding: utf-8 -*-
"""
ДЕТАЛЬНИЙ АНАЛІЗ page_01.dxf (PERFECT V7)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    import ezdxf
except ImportError:
    print("Встановлюю ezdxf...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "ezdxf"], check=True)
    import ezdxf

print("="*70)
print("АНАЛІЗ page_01.dxf (PERFECT V7)")
print("="*70)

dxf_path = "d:/autocad project/FINAL_DXF_PERFECT_V7/page_01.dxf"

try:
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # Статистика
    print(f"\n📊 БАЗОВА ІНФОРМАЦІЯ:")
    print(f"   • Версія DXF: {doc.dxfversion}")
    print(f"   • Всього об'єктів: {len(list(msp))}")

    # Типи об'єктів
    print(f"\n🔍 ТИПИ ОБ'ЄКТІВ:")
    entity_types = {}
    for e in msp:
        etype = e.dxftype()
        entity_types[etype] = entity_types.get(etype, 0) + 1

    for etype, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
        print(f"   • {etype}: {count}")

    # Детальний аналіз
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

    # ТЕКСТ - КЛЮЧОВЕ!
    if texts:
        print(f"\n📝 ТЕКСТОВИЙ ВМІСТ (перші 30):")
        for idx, t in enumerate(texts[:30], 1):
            try:
                if t.dxftype() == 'TEXT':
                    txt = t.dxf.text
                    pos = t.dxf.insert
                elif t.dxftype() == 'MTEXT':
                    txt = t.text
                    pos = t.dxf.insert

                txt_clean = txt.replace('\\P', ' ').strip()[:60]
                print(f"   {idx}. [{pos.x:.1f}, {pos.y:.1f}]: {txt_clean}")
            except:
                pass

    # КОЛА (якщо є - це силоси!)
    if circles:
        print(f"\n⭕ КОЛА (можливо силоси):")
        for idx, c in enumerate(circles[:20], 1):
            center = c.dxf.center
            radius = c.dxf.radius
            diameter = radius * 2
            print(f"   {idx}. Центр: [{center.x:.1f}, {center.y:.1f}], D={diameter:.1f}")

    # БЛОКИ
    if inserts:
        print(f"\n🔲 БЛОКИ:")
        block_names = {}
        for ins in inserts[:50]:
            try:
                name = ins.dxf.name
                pos = ins.dxf.insert
                block_names[name] = block_names.get(name, 0) + 1
                if block_names[name] <= 3:  # Перші 3 входження
                    print(f"   • {name} на [{pos.x:.1f}, {pos.y:.1f}]")
            except:
                pass

        print(f"\n   Всього унікальних блоків: {len(block_names)}")
        for name, count in sorted(block_names.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   • {name}: {count}x")

    # Шари
    print(f"\n🗂️  ШАРИ:")
    layers = list(doc.layers)
    print(f"   • Всього шарів: {len(layers)}")
    for layer in layers[:20]:
        try:
            print(f"   • {layer.dxf.name} (колір: {layer.dxf.color})")
        except:
            pass

    # Розміри креслення
    print(f"\n📏 РОЗМІРИ:")
    if lines:
        min_x = min(min(l.dxf.start.x, l.dxf.end.x) for l in lines)
        max_x = max(max(l.dxf.start.x, l.dxf.end.x) for l in lines)
        min_y = min(min(l.dxf.start.y, l.dxf.end.y) for l in lines)
        max_y = max(max(l.dxf.start.y, l.dxf.end.y) for l in lines)

        width = max_x - min_x
        height = max_y - min_y

        print(f"   • X: {min_x:.1f} → {max_x:.1f} (ширина: {width:.1f})")
        print(f"   • Y: {min_y:.1f} → {max_y:.1f} (висота: {height:.1f})")

    print(f"\n{'='*70}")
    print("✅ АНАЛІЗ ЗАВЕРШЕНО!")
    print(f"{'='*70}")

    # ВИСНОВОК
    print(f"\n🎯 ВИСНОВОК:")

    if inserts and len(inserts) > 0:
        print(f"   ✅ Є БЛОКИ! ({len(inserts)} шт)")
        print(f"   ✅ ЦЕ МОЖНА РЕДАГУВАТИ!")
        print(f"   ✅ Можна копіювати/масштабувати блоки!")
    else:
        print(f"   ⚠ Немає блоків")

    if texts and len(texts) > 10:
        print(f"   ✅ Є ТЕКСТ! ({len(texts)} об'єктів)")
        print(f"   ✅ Мітки збережені!")
    else:
        print(f"   ⚠ Мало тексту")

    if circles and len(circles) > 3:
        print(f"   ✅ Є КОЛА! ({len(circles)} шт)")
        print(f"   ✅ Структуровані об'єкти!")
    else:
        print(f"   ⚠ Немає кіл")

    if len(lines) < 1000:
        print(f"   ✅ ЧИСТА ГЕОМЕТРІЯ! (тільки {len(lines)} ліній)")
        print(f"   ✅ НЕ РАСТЕРИЗОВАНО!")
    else:
        print(f"   ⚠ Багато ліній ({len(lines)})")
        print(f"   ⚠ Можливо растеризовано")

except Exception as e:
    print(f"\n❌ ПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
