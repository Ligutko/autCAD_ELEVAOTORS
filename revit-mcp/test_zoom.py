"""
Test Zoom to Fit in Revit

Відправляє команду zoom_to_fit щоб побачити всі імпортовані об'єкти
"""

from auto_mcp_wrapper import send_command_to_revit
import json

print("="*70)
print("TEST: ZOOM TO FIT")
print("="*70)
print()

print("ВАЖЛИВО:")
print("  1. Переконайся що Revit відкритий")
print("  2. Натисни StartListener")
print()
input("Press Enter коли готово...")
print()

# Відправляємо команду zoom
print("[ZOOM] Sending zoom_to_fit command...")
result = send_command_to_revit(action='zoom_to_fit')

print("[RESULT]")
print(json.dumps(result, indent=2, ensure_ascii=False))
print()

if result.get('status') == 'success':
    print("✅ SUCCESS! View zoomed to fit!")
    print(f"View: {result.get('view')}")
    print()
    print("Тепер має бути видно всі об'єкти!")
else:
    print(f"❌ FAILED: {result.get('message')}")
