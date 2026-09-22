# -*- coding: utf-8 -*-
"""
ДЕТАЛЬНИЙ АНАЛІЗ DXF ФАЙЛІВ - КОНВЕРТОВАНИХ З PDF
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import glob

print("="*70)
print("ДЕТАЛЬНИЙ АНАЛІЗ КОНВЕРТОВАНИХ DXF ФАЙЛІВ")
print("="*70)

# Знаходимо всі DXF файли
dxf_files = glob.glob("d:/autocad project/*.dxf")

print(f"\n📂 Знайдено DXF файлів: {len(dxf_files)}")

try:
    import ezdxf
    print("✓ ezdxf встановлено")
except ImportError:
    print("❌ ezdxf не встановлено. Встановлюю...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "ezdxf"], check=True)
    import ezdxf
    print("✓ ezdxf встановлено успішно")

print("\n" + "="*70)

for dxf_path in dxf_files:
    print(f"\n{'='*70}")
    print(f"📄 ФАЙЛ: {os.path.basename(dxf_path)}")
    print(f"{'='*70}")

    try:
        # Читаємо DXF
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        # Розмір файлу
        file_size = os.path.getsize(dxf_path)
        print(f"\n📊 БАЗОВА ІНФОРМАЦІЯ:")
        print(f"   • Розмір файлу: {file_size / 1024:.1f} KB")
        print(f"   • Версія DXF: {doc.dxfversion}")
        print(f"   • Кодування: {doc.encoding}")

        # Шари
        print(f"\n🗂️  ШАРИ (Layers):")
        layers = list(doc.layers)
        print(f"   • Всього шарів: {len(layers)}")
        for layer in layers[:20]:  # Перші 20 шарів
            print(f"   • {layer.dxf.name}")
            if hasattr(layer.dxf, 'color'):
                print(f"     - Колір: {layer.dxf.color}")
            if hasattr(layer.dxf, 'lineweight'):
                print(f"     - Товщина: {layer.dxf.lineweight}")

        # Типи об'єктів
        print(f"\n🔍 ТИПИ ОБ'ЄКТІВ В MODELSPACE:")
        entity_types = {}
        total_entities = 0

        for entity in msp:
            etype = entity.dxftype()
            entity_types[etype] = entity_types.get(etype, 0) + 1
            total_entities += 1

        print(f"   • ВСЬОГО ОБ'ЄКТІВ: {total_entities}")
        for etype, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {etype}: {count}")

        # Аналіз геометрії
        print(f"\n📐 ДЕТАЛЬНА ГЕОМЕТРІЯ:")

        lines = [e for e in msp if e.dxftype() == 'LINE']
        circles = [e for e in msp if e.dxftype() == 'CIRCLE']
        arcs = [e for e in msp if e.dxftype() == 'ARC']
        polylines = [e for e in msp if e.dxftype() == 'LWPOLYLINE' or e.dxftype() == 'POLYLINE']
        texts = [e for e in msp if e.dxftype() == 'TEXT' or e.dxftype() == 'MTEXT']
        inserts = [e for e in msp if e.dxftype() == 'INSERT']

        print(f"   • Лінії (LINE): {len(lines)}")
        print(f"   • Кола (CIRCLE): {len(circles)}")
        print(f"   • Дуги (ARC): {len(arcs)}")
        print(f"   • Полілінії (POLYLINE): {len(polylines)}")
        print(f"   • Текст (TEXT/MTEXT): {len(texts)}")
        print(f"   • Блоки (INSERT): {len(inserts)}")

        # Розміри креслення
        if total_entities > 0:
            try:
                extents = msp.query('*')
                if extents:
                    # Обчислюємо bounding box
                    min_x = min_y = float('inf')
                    max_x = max_y = float('-inf')

                    for e in extents[:1000]:  # Перші 1000 для швидкості
                        try:
                            if e.dxftype() == 'LINE':
                                min_x = min(min_x, e.dxf.start.x, e.dxf.end.x)
                                max_x = max(max_x, e.dxf.start.x, e.dxf.end.x)
                                min_y = min(min_y, e.dxf.start.y, e.dxf.end.y)
                                max_y = max(max_y, e.dxf.start.y, e.dxf.end.y)
                            elif e.dxftype() == 'CIRCLE':
                                min_x = min(min_x, e.dxf.center.x - e.dxf.radius)
                                max_x = max(max_x, e.dxf.center.x + e.dxf.radius)
                                min_y = min(min_y, e.dxf.center.y - e.dxf.radius)
                                max_y = max(max_y, e.dxf.center.y + e.dxf.radius)
                        except:
                            pass

                    if min_x != float('inf'):
                        print(f"\n📏 РОЗМІРИ КРЕСЛЕННЯ:")
                        print(f"   • X: від {min_x:.0f} до {max_x:.0f} (ширина: {max_x-min_x:.0f})")
                        print(f"   • Y: від {min_y:.0f} до {max_y:.0f} (висота: {max_y-min_y:.0f})")
            except:
                pass

        # Приклади тексту
        print(f"\n📝 ПРИКЛАДИ ТЕКСТУ (перші 20):")
        text_samples = []
        for t in texts[:20]:
            try:
                if t.dxftype() == 'TEXT':
                    text_samples.append(t.dxf.text)
                elif t.dxftype() == 'MTEXT':
                    text_samples.append(t.text)
            except:
                pass

        for idx, txt in enumerate(text_samples, 1):
            txt_clean = txt.replace('\n', ' ').strip()
            print(f"   {idx}. {txt_clean[:60]}")

        # Аналіз блоків
        if inserts:
            print(f"\n🔲 БЛОКИ:")
            block_names = {}
            for ins in inserts[:50]:
                try:
                    name = ins.dxf.name
                    block_names[name] = block_names.get(name, 0) + 1
                except:
                    pass

            for name, count in sorted(block_names.items(), key=lambda x: x[1], reverse=True):
                print(f"   • {name}: {count} використань")

        print(f"\n{'='*70}\n")

    except Exception as e:
        print(f"❌ Помилка читання: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*70)
print("✅ АНАЛІЗ ЗАВЕРШЕНО!")
print("="*70)
