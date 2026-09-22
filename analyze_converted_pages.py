# -*- coding: utf-8 -*-
"""
ДЕТАЛЬНИЙ АНАЛІЗ КОНВЕРТОВАНИХ СТОРІНОК PDF→DXF
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os

try:
    import ezdxf
except ImportError:
    print("Встановлюю ezdxf...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "ezdxf"], check=True)
    import ezdxf

print("="*70)
print("ДЕТАЛЬНИЙ АНАЛІЗ КОНВЕРТОВАНИХ СТОРІНОК")
print("="*70)

dxf_folder = "D:/autocad project/FINAL_DXF_OUTPUT"
pages = ["page_01.dxf", "page_02.dxf", "page_04.dxf"]

for page_name in pages:
    dxf_path = os.path.join(dxf_folder, page_name)

    print(f"\n{'='*70}")
    print(f"📄 {page_name}")
    print(f"{'='*70}")

    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        # Розмір файлу
        file_size = os.path.getsize(dxf_path)
        print(f"\n📊 БАЗОВА ІНФОРМАЦІЯ:")
        print(f"   • Розмір: {file_size / 1024:.1f} KB")
        print(f"   • Версія DXF: {doc.dxfversion}")

        # Типи об'єктів
        print(f"\n🔍 ОБ'ЄКТИ:")
        entity_types = {}
        for entity in msp:
            etype = entity.dxftype()
            entity_types[etype] = entity_types.get(etype, 0) + 1

        total = sum(entity_types.values())
        print(f"   • ВСЬОГО: {total}")
        for etype, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True)[:15]:
            print(f"   • {etype}: {count}")

        # Детальна геометрія
        lines = [e for e in msp if e.dxftype() == 'LINE']
        circles = [e for e in msp if e.dxftype() == 'CIRCLE']
        arcs = [e for e in msp if e.dxftype() == 'ARC']
        polylines = [e for e in msp if e.dxftype() in ['LWPOLYLINE', 'POLYLINE']]
        texts = [e for e in msp if e.dxftype() in ['TEXT', 'MTEXT']]
        inserts = [e for e in msp if e.dxftype() == 'INSERT']
        splines = [e for e in msp if e.dxftype() == 'SPLINE']
        ellipses = [e for e in msp if e.dxftype() == 'ELLIPSE']

        print(f"\n📐 ГЕОМЕТРІЯ:")
        print(f"   • Лінії: {len(lines)}")
        print(f"   • Кола: {len(circles)}")
        print(f"   • Дуги: {len(arcs)}")
        print(f"   • Полілінії: {len(polylines)}")
        print(f"   • Сплайни: {len(splines)}")
        print(f"   • Еліпси: {len(ellipses)}")
        print(f"   • Текст: {len(texts)}")
        print(f"   • Блоки: {len(inserts)}")

        # Розміри креслення
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')

        for e in list(lines)[:500] + list(circles)[:500]:
            try:
                if e.dxftype() == 'LINE':
                    min_x = min(min_x, e.dxf.start.x, e.dxf.end.x)
                    max_x = max(max_x, e.dxf.start.x, e.dxf.end.x)
                    min_y = min(min_y, e.dxf.start.y, e.dxf.end.y)
                    max_y = max(max_y, e.dxf.start.y, e.dxf.end.y)
                elif e.dxftype() == 'CIRCLE':
                    r = e.dxf.radius
                    min_x = min(min_x, e.dxf.center.x - r)
                    max_x = max(max_x, e.dxf.center.x + r)
                    min_y = min(min_y, e.dxf.center.y - r)
                    max_y = max(max_y, e.dxf.center.y + r)
            except:
                pass

        if min_x != float('inf'):
            print(f"\n📏 РОЗМІРИ:")
            print(f"   • X: {min_x:.0f} → {max_x:.0f} (ширина: {max_x-min_x:.0f})")
            print(f"   • Y: {min_y:.0f} → {max_y:.0f} (висота: {max_y-min_y:.0f})")

        # Шари
        print(f"\n🗂️  ШАРИ:")
        layer_usage = {}
        for e in msp:
            try:
                layer = e.dxf.layer
                layer_usage[layer] = layer_usage.get(layer, 0) + 1
            except:
                pass

        for layer, count in sorted(layer_usage.items(), key=lambda x: x[1], reverse=True)[:15]:
            print(f"   • {layer}: {count} об'єктів")

        # Текст - НАЙВАЖЛИВІШЕ!
        print(f"\n📝 ТЕКСТОВИЙ ВМІСТ (перші 30):")
        text_samples = []
        for t in texts[:30]:
            try:
                if t.dxftype() == 'TEXT':
                    text_samples.append(t.dxf.text)
                elif t.dxftype() == 'MTEXT':
                    text_samples.append(t.text)
            except:
                pass

        for idx, txt in enumerate(text_samples, 1):
            txt_clean = txt.replace('\n', ' ').replace('\P', ' ').strip()
            if txt_clean:
                print(f"   {idx}. {txt_clean[:70]}")

        # Аналіз кіл (СИЛОСИ!)
        if circles:
            print(f"\n⭕ АНАЛІЗ КІЛ (потенційні силоси):")
            circle_radii = {}
            for c in circles:
                try:
                    r = int(c.dxf.radius)
                    circle_radii[r] = circle_radii.get(r, 0) + 1
                except:
                    pass

            for r, count in sorted(circle_radii.items(), key=lambda x: x[1], reverse=True)[:10]:
                diameter = r * 2
                print(f"   • Радіус {r} (діаметр {diameter}): {count} кіл")

        # Блоки
        if inserts:
            print(f"\n🔲 БЛОКИ:")
            block_names = {}
            for ins in inserts[:100]:
                try:
                    name = ins.dxf.name
                    block_names[name] = block_names.get(name, 0) + 1
                except:
                    pass

            for name, count in sorted(block_names.items(), key=lambda x: x[1], reverse=True)[:15]:
                print(f"   • {name}: {count}x")

    except Exception as e:
        print(f"❌ ПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*70}")
print("✅ АНАЛІЗ ЗАВЕРШЕНО!")
print(f"{'='*70}")
