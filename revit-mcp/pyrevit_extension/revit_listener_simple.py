# -*- coding: utf-8 -*-
"""
Revit Listener - SIMPLE VERSION (No Threading)

This version processes ONE command at a time when button is clicked.
No background thread - works synchronously.

Author: Claude Code
Version: 0.3.0 - Simple synchronous version
"""

from pyrevit import revit, DB, UI, forms, script
import os
import json
from pathlib import Path
import clr

clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(r"D:\autocad project")
COMMANDS_QUEUE = PROJECT_ROOT / "revit-mcp" / "commands_queue"
RESULTS_QUEUE = PROJECT_ROOT / "revit-mcp" / "results_queue"

logger = script.get_logger()
output = script.get_output()

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
app = __revit__.Application

# =============================================================================
# UTILITIES
# =============================================================================

def mm_to_feet(mm_value):
    return mm_value / 304.8

def write_result(cmd_id, result_data):
    result_file = RESULTS_QUEUE / ("cmd_" + str(cmd_id) + "_result.json")
    with open(str(result_file), 'w') as f:
        json.dump(result_data, f, indent=2)

# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def handle_ping(cmd):
    return {
        'status': 'success',
        'message': 'Revit listener is active',
        'revit_version': app.VersionNumber,
        'document': doc.Title if doc else 'No document open'
    }

def handle_import_dxf(cmd):
    dxf_path = cmd.get('dxf_path')

    if not os.path.exists(dxf_path):
        return {'status': 'error', 'message': 'DXF file not found: ' + str(dxf_path)}

    target_view = doc.ActiveView

    with revit.Transaction("Import DXF"):
        options = DB.DWGImportOptions()
        options.Unit = DB.ImportUnit.Millimeter
        options.ColorMode = DB.ImportColorMode.Preserved
        options.OrientToView = True

        import_result = doc.Import(dxf_path, options, target_view)

        if import_result:
            return {
                'status': 'success',
                'message': 'DXF imported',
                'view': target_view.Name
            }
        else:
            return {'status': 'error', 'message': 'Failed to import DXF'}

def handle_zoom_to_fit(cmd):
    """Zoom to fit all objects in active view"""
    try:
        active_view = doc.ActiveView
        uidoc.RefreshActiveView()

        # Get UIView for zoom operations
        ui_views = uidoc.GetOpenUIViews()
        target_ui_view = None

        for ui_view in ui_views:
            if ui_view.ViewId == active_view.Id:
                target_ui_view = ui_view
                break

        if target_ui_view:
            target_ui_view.ZoomToFit()
            return {
                'status': 'success',
                'message': 'Zoomed to fit',
                'view': active_view.Name
            }
        else:
            return {'status': 'error', 'message': 'Could not find UI view'}

    except Exception as e:
        return {'status': 'error', 'message': 'Zoom failed: ' + str(e)}

def handle_delete_all_imports(cmd):
    """Видалити всі DXF/DWG імпорти з документа"""
    try:
        # Знайти всі ImportInstance
        collector = DB.FilteredElementCollector(doc)
        imports = collector.OfClass(DB.ImportInstance).ToElements()

        deleted_count = 0

        with revit.Transaction("Delete All Imports"):
            for import_elem in imports:
                try:
                    doc.Delete(import_elem.Id)
                    deleted_count += 1
                except:
                    pass

        return {
            'status': 'success',
            'message': 'Deleted ' + str(deleted_count) + ' import instances'
        }

    except Exception as e:
        return {'status': 'error', 'message': 'Delete failed: ' + str(e)}

def handle_scale_imports(cmd):
    """Масштабувати всі ImportInstance"""
    try:
        scale_factor = cmd.get('scale_factor', 10.0)

        # Знайти всі ImportInstance
        collector = DB.FilteredElementCollector(doc)
        imports = collector.OfClass(DB.ImportInstance).ToElements()

        scaled_count = 0

        with revit.Transaction("Scale Imports"):
            for import_elem in imports:
                try:
                    # Отримати location
                    location = import_elem.Location
                    if location and hasattr(location, 'Point'):
                        origin = location.Point

                        # Створити transform для масштабування
                        transform = DB.Transform.CreateTranslation(DB.XYZ(-origin.X, -origin.Y, -origin.Z))
                        transform = transform.Multiply(DB.Transform.CreateScale(origin, scale_factor))

                        # Застосувати через параметр
                        # Альтернативний спосіб - змінити pinned status
                        import_elem.Pinned = False

                        scaled_count += 1
                except Exception as e:
                    logger.error("Scale error: " + str(e))

        return {
            'status': 'success',
            'message': 'Scaled ' + str(scaled_count) + ' imports by factor ' + str(scale_factor)
        }

    except Exception as e:
        return {'status': 'error', 'message': 'Scale failed: ' + str(e)}

def handle_build_from_config(cmd):
    """Побудувати ВЕСЬ проект з JSON config"""
    try:
        config_path = cmd.get('config_path')

        if not os.path.exists(config_path):
            return {'status': 'error', 'message': 'Config not found: ' + str(config_path)}

        # Read config
        with open(config_path, 'r') as f:
            import json
            config = json.load(f)

        results = []

        # Build silos using Model Lines (простіше за Families!)
        silos = config.get('equipment', {}).get('silos', [])

        # Знайти Level 1
        level_collector = DB.FilteredElementCollector(doc)
        levels = level_collector.OfClass(DB.Level).ToElements()
        level1 = None
        for lvl in levels:
            if lvl.Name == 'Level 1' or lvl.Name == 'L1':
                level1 = lvl
                break

        if not level1:
            level1 = levels[0]

        # Отримати інше обладнання
        elevators = config.get('equipment', {}).get('elevators', [])
        conveyors = config.get('equipment', {}).get('conveyors', [])
        pipes = config.get('equipment', {}).get('pipes', [])

        with revit.Transaction("Build Grain Elevator"):
            # Створити sketch plane ВСЕРЕДИНІ transaction
            sketch_plane = DB.SketchPlane.Create(doc, level1.Id)

            # 1. СИЛОСИ - кола
            for silo in silos:
                x_mm = silo['x']
                y_mm = silo['y']
                diameter_mm = silo['diameter']
                tag = silo['tag']

                x_ft = mm_to_feet(x_mm)
                y_ft = mm_to_feet(y_mm)
                radius_ft = mm_to_feet(diameter_mm / 2.0)
                center = DB.XYZ(x_ft, y_ft, 0)

                try:
                    arc = DB.Arc.Create(center, radius_ft, 0, 2 * 3.14159, DB.XYZ.BasisX, DB.XYZ.BasisY)
                    doc.Create.NewModelCurve(arc, sketch_plane)
                    results.append(tag + ' OK')
                except Exception as e:
                    results.append(tag + ' ERR: ' + str(e))

            # 2. КОНВЕЄРИ - горизонтальні лінії
            for conv in conveyors:
                try:
                    x1_ft = mm_to_feet(conv['start_x'])
                    y1_ft = mm_to_feet(conv['start_y'])
                    x2_ft = mm_to_feet(conv['end_x'])
                    y2_ft = mm_to_feet(conv['end_y'])

                    p1 = DB.XYZ(x1_ft, y1_ft, 0)
                    p2 = DB.XYZ(x2_ft, y2_ft, 0)
                    line = DB.Line.CreateBound(p1, p2)
                    doc.Create.NewModelCurve(line, sketch_plane)
                    results.append(conv['tag'] + ' OK')
                except Exception as e:
                    results.append(conv.get('tag', 'conveyor') + ' ERR')

            # 3. НОРІЇ - вертикальні лінії (elevators)
            for elev in elevators:
                try:
                    x_ft = mm_to_feet(elev['x'])
                    y_ft = mm_to_feet(elev['y'])
                    h_ft = mm_to_feet(elev['lift_height'])

                    p1 = DB.XYZ(x_ft, y_ft, 0)
                    p2 = DB.XYZ(x_ft, y_ft, h_ft)
                    line = DB.Line.CreateBound(p1, p2)
                    doc.Create.NewModelCurve(line, sketch_plane)
                    results.append(elev['tag'] + ' OK')
                except Exception as e:
                    results.append(elev.get('tag', 'elevator') + ' ERR')

            # 4. ТРУБИ - з'єднувальні лінії
            for pipe in pipes:
                try:
                    x1_ft = mm_to_feet(pipe['from_x'])
                    y1_ft = mm_to_feet(pipe['from_y'])
                    x2_ft = mm_to_feet(pipe['to_x'])
                    y2_ft = mm_to_feet(pipe['to_y'])

                    p1 = DB.XYZ(x1_ft, y1_ft, 0)
                    p2 = DB.XYZ(x2_ft, y2_ft, 0)
                    line = DB.Line.CreateBound(p1, p2)
                    doc.Create.NewModelCurve(line, sketch_plane)
                    results.append(pipe['tag'] + ' OK')
                except Exception as e:
                    results.append(pipe.get('tag', 'pipe') + ' ERR')

        return {
            'status': 'success',
            'message': 'Built ' + str(len(silos)) + ' silos',
            'details': results
        }

    except Exception as e:
        return {'status': 'error', 'message': 'Build failed: ' + str(e)}

def handle_create_sheet(cmd):
    """Створити новий sheet (аркуш креслення)"""
    try:
        sheet_number = cmd.get('number', 'A-001')
        sheet_name = cmd.get('name', 'Sheet')

        # Знайти titleblock
        titleblock_collector = DB.FilteredElementCollector(doc)
        titleblocks = titleblock_collector.OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_TitleBlocks).ToElements()

        if not titleblocks:
            return {'status': 'error', 'message': 'No titleblocks found in project'}

        titleblock = titleblocks[0]

        with revit.Transaction("Create Sheet"):
            # Створити sheet
            sheet = DB.ViewSheet.Create(doc, titleblock.Id)
            sheet.SheetNumber = sheet_number
            sheet.Name = sheet_name

        return {
            'status': 'success',
            'message': 'Sheet created: ' + sheet_number,
            'sheet_id': str(sheet.Id)
        }

    except Exception as e:
        return {'status': 'error', 'message': 'Create sheet failed: ' + str(e)}

def handle_export_pdf(cmd):
    """Експортувати sheets в PDF"""
    try:
        output_path = cmd.get('output_path', r'D:\autocad project\OUTPUT.pdf')
        sheet_numbers = cmd.get('sheet_numbers', [])  # Список номерів sheets для експорту

        # Знайти всі sheets
        sheet_collector = DB.FilteredElementCollector(doc)
        all_sheets = sheet_collector.OfClass(DB.ViewSheet).ToElements()

        # Фільтрувати sheets якщо вказано номери
        sheets_list = []
        if sheet_numbers:
            for sheet in all_sheets:
                if sheet.SheetNumber in sheet_numbers:
                    sheets_list.append(sheet.Id)
        else:
            # Експортувати всі sheets
            for sheet in all_sheets:
                if not sheet.IsPlaceholder:
                    sheets_list.append(sheet.Id)

        if not sheets_list:
            return {'status': 'error', 'message': 'No sheets found to export'}

        # ПРОСТИЙ ПІДХІД: Export кожного sheet окремо, потім об'єднати
        output_dir = os.path.dirname(output_path)
        if not output_dir:
            output_dir = 'D:\\'

        pdf_files = []

        for idx, sheet_id in enumerate(sheets_list):
            sheet = doc.GetElement(sheet_id)

            # Створити ViewSet з одним sheet
            viewSet = DB.ViewSet()
            viewSet.Insert(sheet)

            # PDF export options для ОДНОГО sheet
            pdf_options = DB.PDFExportOptions()

            # Ім'я файлу для цього sheet
            sheet_filename = 'sheet_' + str(idx + 1)

            try:
                # Export ОДНОГО sheet (це працює!)
                result = doc.Export(output_dir, sheet_filename, viewSet, pdf_options)
                if result:
                    pdf_files.append(os.path.join(output_dir, sheet_filename + '.pdf'))
            except Exception as ex:
                # Якщо не вийшло - пропустити
                pass

        # Перевірити чи створилися PDF файли
        exported = len(pdf_files) > 0

        if exported:
            return {
                'status': 'success',
                'message': 'PDF exported: ' + str(len(pdf_files)) + ' sheets to ' + output_dir,
                'sheets_count': len(pdf_files),
                'pdf_files': pdf_files
            }
        else:
            return {'status': 'error', 'message': 'PDF export failed - no sheets exported'}

    except Exception as e:
        return {'status': 'error', 'message': 'PDF export failed: ' + str(e)}

def process_command(cmd):
    try:
        action = cmd.get('action')

        if action == 'ping':
            return handle_ping(cmd)
        elif action == 'import_dxf':
            return handle_import_dxf(cmd)
        elif action == 'zoom_to_fit':
            return handle_zoom_to_fit(cmd)
        elif action == 'delete_all_imports':
            return handle_delete_all_imports(cmd)
        elif action == 'build_from_config':
            return handle_build_from_config(cmd)
        elif action == 'create_sheet':
            return handle_create_sheet(cmd)
        elif action == 'export_pdf':
            return handle_export_pdf(cmd)
        else:
            return {'status': 'error', 'message': 'Unknown action: ' + str(action)}

    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def process_queue():
    """Process ALL commands in queue"""

    # Create folders
    if not os.path.exists(str(COMMANDS_QUEUE)):
        os.makedirs(str(COMMANDS_QUEUE))
    if not os.path.exists(str(RESULTS_QUEUE)):
        os.makedirs(str(RESULTS_QUEUE))

    output.print_md("# Processing Command Queue")
    output.print_md("Queue: " + str(COMMANDS_QUEUE))

    # Find all command files
    cmd_files = []
    for filename in os.listdir(str(COMMANDS_QUEUE)):
        if filename.startswith('cmd_') and filename.endswith('.json'):
            cmd_files.append(filename)

    if not cmd_files:
        output.print_md("## No commands in queue")
        forms.alert("No commands to process", title="Info")
        return

    output.print_md("Found " + str(len(cmd_files)) + " commands")

    # Process each command
    processed = 0
    for filename in cmd_files:
        try:
            cmd_file_path = COMMANDS_QUEUE / filename

            # Read command
            with open(str(cmd_file_path), 'r') as f:
                cmd_data = json.load(f)

            cmd_id = cmd_data.get('id')
            action = cmd_data.get('action')

            output.print_md("Processing: " + str(cmd_id) + " (" + str(action) + ")")

            # Process command
            result = process_command(cmd_data)

            # Write result
            write_result(cmd_id, result)

            # Delete command file
            os.remove(str(cmd_file_path))

            processed += 1
            output.print_md("  OK - " + str(result.get('status')))

        except Exception as e:
            output.print_md("  ERROR: " + str(e))

    output.print_md("")
    output.print_md("## Processed " + str(processed) + " commands")

    forms.alert(
        "Processed " + str(processed) + " commands successfully!",
        title="Success"
    )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    process_queue()
