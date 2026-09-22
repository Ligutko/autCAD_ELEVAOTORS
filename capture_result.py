# -*- coding: utf-8 -*-
"""
АНАЛІЗ ТА СКРІНШОТ РЕЗУЛЬТАТУ V7
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import time

print("="*70)
print("АНАЛІЗ РЕЗУЛЬТАТУ V7 + СКРІНШОТ")
print("="*70)

try:
    acad = win32com.client.Dispatch("AutoCAD.Application")
    doc = acad.ActiveDocument
    ms = doc.ModelSpace

    print(f"\n📄 Активний документ: {doc.Name}")
    print(f"📊 Всього об'єктів: {ms.Count}")

    # Аналіз типів об'єктів
    print("\n🔍 АНАЛІЗ ОБ'ЄКТІВ:")

    lines = circles = arcs = texts = 0

    for i in range(min(ms.Count, 500)):
        try:
            obj = ms.Item(i)
            otype = obj.ObjectName

            if otype == "AcDbLine":
                lines += 1
            elif otype == "AcDbCircle":
                circles += 1
            elif otype == "AcDbArc":
                arcs += 1
            elif otype in ["AcDbText", "AcDbMText"]:
                texts += 1
        except:
            pass

    print(f"   • Лінії: {lines}")
    print(f"   • Кола: {circles}")
    print(f"   • Дуги: {arcs}")
    print(f"   • Текст: {texts}")

    # Зум на всі об'єкти
    print("\n🔍 ЗУМУВАННЯ НА ВСІ ОБ'ЄКТИ...")
    try:
        acad.Application.ZoomExtents()
        time.sleep(0.5)
    except Exception as e:
        print(f"   ⚠ Помилка зуму: {e}")

    # Створення скріншоту
    print("\n📸 СТВОРЕННЯ СКРІНШОТУ...")

    try:
        # Спробувати через PIL
        from PIL import ImageGrab
        import datetime

        time.sleep(1)  # Чекаємо щоб AutoCAD оновився

        screenshot = ImageGrab.grab()

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"d:/autocad project/v7_result_{timestamp}.png"

        screenshot.save(screenshot_path)

        print(f"   ✅ Скріншот збережено: {screenshot_path}")

    except ImportError:
        print("   ⚠ PIL не встановлено, встановлюю...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "pillow"], check=True)

        from PIL import ImageGrab
        import datetime

        time.sleep(1)
        screenshot = ImageGrab.grab()

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"d:/autocad project/v7_result_{timestamp}.png"

        screenshot.save(screenshot_path)

        print(f"   ✅ Скріншот збережено: {screenshot_path}")

    except Exception as e:
        print(f"   ❌ Помилка скріншоту: {e}")

    # Детальна інформація про креслення
    print("\n📐 РОЗМІРИ КРЕСЛЕННЯ:")

    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')

    for i in range(min(ms.Count, 500)):
        try:
            obj = ms.Item(i)

            if obj.ObjectName == "AcDbLine":
                sp = obj.StartPoint
                ep = obj.EndPoint
                min_x = min(min_x, sp[0], ep[0])
                max_x = max(max_x, sp[0], ep[0])
                min_y = min(min_y, sp[1], ep[1])
                max_y = max(max_y, sp[1], ep[1])
        except:
            pass

    if min_x != float('inf'):
        width = max_x - min_x
        height = max_y - min_y

        print(f"   • X: {min_x:.0f} → {max_x:.0f}")
        print(f"   • Y: {min_y:.0f} → {max_y:.0f}")
        print(f"   • Ширина: {width:.0f} мм ({width/1000:.1f} м)")
        print(f"   • Висота: {height:.0f} мм ({height/1000:.1f} м)")

    # Перевірка наявності ключових елементів
    print("\n✅ ПЕРЕВІРКА КЛЮЧОВИХ ЕЛЕМЕНТІВ:")

    found_silos = 0
    found_conveyors = 0

    for i in range(ms.Count):
        try:
            obj = ms.Item(i)

            if obj.ObjectName in ["AcDbText", "AcDbMText"]:
                text = obj.TextString

                if "МСВУ" in text:
                    found_silos += 1
                elif text.startswith("T") and any(c.isdigit() for c in text):
                    found_conveyors += 1
        except:
            pass

    print(f"   • Знайдено міток МСВУ: {found_silos}")
    print(f"   • Знайдено міток конвеєрів: {found_conveyors}")

    print(f"\n{'='*70}")
    print("✅ АНАЛІЗ ЗАВЕРШЕНО!")
    print(f"{'='*70}")

except Exception as e:
    print(f"\n❌ ПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
