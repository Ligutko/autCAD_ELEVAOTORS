# -*- coding: utf-8 -*-
"""
ШВИДКА ПЕРЕВІРКА page_02.dxf
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client

print("ПЕРЕМИКАННЯ НА page_02.dxf...")

acad = win32com.client.Dispatch("AutoCAD.Application")
docs = acad.Documents

# Шукаємо page_02
for i in range(docs.Count):
    doc = docs.Item(i)
    if "page_02" in doc.Name or "page_04" in doc.Name:
        print(f"✓ Перемикаюсь на: {doc.Name}")
        acad.ActiveDocument = doc
        ms = acad.ActiveDocument.ModelSpace

        print(f"Об'єктів: {ms.Count}")

        # Швидка перевірка перших 100
        has_text = False
        has_circles = False

        for j in range(min(100, ms.Count)):
            try:
                obj = ms.Item(j)
                if obj.ObjectName in ["AcDbText", "AcDbMText"]:
                    has_text = True
                    print(f"✓ ТЕКСТ: {obj.TextString[:50]}")
                if obj.ObjectName == "AcDbCircle":
                    has_circles = True
                    print(f"✓ КОЛО: D={obj.Radius*2:.0f}")
            except:
                pass

        print(f"Має текст: {has_text}")
        print(f"Має кола: {has_circles}")
        print()
