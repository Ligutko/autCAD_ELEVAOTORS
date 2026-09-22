"""
Test DXF Import in Revit

Імпортує page_01.dxf з PDF як reference underlay в Revit.
"""

from auto_mcp_wrapper import send_command_to_revit
import json
from pathlib import Path

# Шлях до DXF файлу
DXF_FILE = Path(r"D:\autocad project\FINAL_DXF_PERFECT_V7\page_01.dxf")

print("="*70)
print("TEST: IMPORT DXF TO REVIT")
print("="*70)
print()
print(f"DXF file: {DXF_FILE}")
print(f"File exists: {DXF_FILE.exists()}")
print()

if not DXF_FILE.exists():
    print("ERROR: DXF file not found!")
    exit(1)

print("ВАЖЛИВО:")
print("  1. Відкрий Revit з новим проектом")
print("  2. Відкрий Floor Plan view (Level 1)")
print("  3. Натисни StartListener")
print()
input("Press Enter коли готово...")
print()

# Відправляємо команду на імпорт
print("[IMPORT] Sending import_dxf command...")
result = send_command_to_revit(
    action='import_dxf',
    dxf_path=str(DXF_FILE),
    view_name=None  # Active view
)

print("[RESULT]")
print(json.dumps(result, indent=2, ensure_ascii=False))
print()

if result.get('status') == 'success':
    print("✅ SUCCESS! DXF imported to Revit!")
    print(f"Import ID: {result.get('import_id')}")
    print(f"View: {result.get('view')}")
    print()
    print("Тепер в Revit маєш побачити креслення з PDF як підкладку!")
else:
    print(f"❌ FAILED: {result.get('message')}")
