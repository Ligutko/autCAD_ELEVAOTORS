# -*- coding: utf-8 -*-
"""
ОТРИМАТИ ШЛЯХИ ДО ВІДКРИТИХ ФАЙЛІВ В AUTOCAD
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import time

print("="*70)
print("СПИСОК ВІДКРИТИХ ДОКУМЕНТІВ В AUTOCAD")
print("="*70)

try:
    acad = win32com.client.Dispatch("AutoCAD.Application")
    docs = acad.Documents

    print(f"\n📂 Всього відкритих документів: {docs.Count}\n")

    for i in range(docs.Count):
        doc = docs.Item(i)
        print(f"{'='*70}")
        print(f"ДОКУМЕНТ #{i+1}:")
        print(f"  • Ім'я: {doc.Name}")
        try:
            print(f"  • Повний шлях: {doc.FullName}")
        except:
            print(f"  • Повний шлях: (не збережено)")
        try:
            print(f"  • Папка: {doc.Path}")
        except:
            print(f"  • Папка: (не збережено)")
        print(f"{'='*70}\n")

except Exception as e:
    print(f"\n❌ ПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
