# -*- coding: utf-8 -*-
"""
Revit Listener - pyRevit Script (IronPython 2.7 Compatible)

This script runs INSIDE Revit as a pyRevit plugin.
Monitors command queue from MCP Server and executes via Revit API.

Author: Claude Code
Version: 0.2.0 - IronPython 2.7 compatible (no f-strings)
"""

from pyrevit import revit, DB, UI, forms, script
import os
import json
import time
import threading
import traceback
from pathlib import Path
import clr

clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

# =============================================================================
# CONFIGURATION
# =============================================================================

# Queue paths (must match MCP Server!)
PROJECT_ROOT = Path(r"D:\autocad project")
COMMANDS_QUEUE = PROJECT_ROOT / "revit-mcp" / "commands_queue"
RESULTS_QUEUE = PROJECT_ROOT / "revit-mcp" / "results_queue"

# Poll interval (seconds)
POLL_INTERVAL = 0.5

# Listener state
_listener_running = False
_listener_thread = None

# Logger
logger = script.get_logger()
output = script.get_output()

# Current document
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
app = __revit__.Application

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def mm_to_feet(mm_value):
    """Convert millimeters to feet (Revit internal units)"""
    return mm_value / 304.8


def feet_to_mm(feet_value):
    """Convert feet to millimeters"""
    return feet_value * 304.8


def write_result(cmd_id, result_data):
    """Write command execution result"""
    result_file = RESULTS_QUEUE / ("cmd_" + str(cmd_id) + "_result.json")
    with open(str(result_file), 'w') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)


def get_active_view():
    """Get active view"""
    return doc.ActiveView


def find_level_by_name(level_name):
    """Find Level by name"""
    collector = DB.FilteredElementCollector(doc)
    levels = collector.OfClass(DB.Level).ToElements()

    for level in levels:
        if level.Name == level_name:
            return level

    # If not found, return first
    return levels[0] if levels else None


def find_family_symbol(family_name, symbol_name):
    """Find FamilySymbol by family and type name"""
    collector = DB.FilteredElementCollector(doc)
    symbols = collector.OfClass(DB.FamilySymbol).ToElements()

    for symbol in symbols:
        if (symbol.FamilyName == family_name and
            symbol.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() == symbol_name):
            return symbol

    return None


# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def handle_ping(cmd):
    """Handle ping command"""
    return {
        'status': 'success',
        'message': 'Revit listener is active',
        'revit_version': app.VersionNumber,
        'document': doc.Title if doc else 'No document open'
    }


def handle_place_family(cmd):
    """Handle place_family_instance command"""
    family_name = cmd.get('family_name')
    symbol_name = cmd.get('symbol_name', 'Default')
    x = cmd.get('x', 0)
    y = cmd.get('y', 0)
    z = cmd.get('z', 0)
    level_name = cmd.get('level_name')
    parameters = cmd.get('parameters', {})

    # Find family symbol
    symbol = find_family_symbol(family_name, symbol_name)
    if not symbol:
        return {
            'status': 'error',
            'message': 'Family symbol not found: ' + str(family_name) + ' / ' + str(symbol_name)
        }

    # Find level
    if level_name:
        level = find_level_by_name(level_name)
    else:
        level = find_level_by_name('Level 1')

    if not level:
        return {'status': 'error', 'message': 'Level not found: ' + str(level_name)}

    # Create instance
    with revit.Transaction("Place Family Instance"):
        # Activate symbol if needed
        if not symbol.IsActive:
            symbol.Activate()

        # Create insertion point (convert mm to feet)
        point = DB.XYZ(mm_to_feet(x), mm_to_feet(y), mm_to_feet(z))

        # Place instance
        instance = doc.Create.NewFamilyInstance(
            point,
            symbol,
            level,
            DB.Structure.StructuralType.NonStructural
        )

        # Set parameters
        for param_name, param_value in parameters.items():
            param = instance.LookupParameter(param_name)
            if param and not param.IsReadOnly:
                if param.StorageType == DB.StorageType.Double:
                    # If parameter is Length type, convert mm to feet
                    param.Set(mm_to_feet(float(param_value)))
                elif param.StorageType == DB.StorageType.Integer:
                    param.Set(int(param_value))
                elif param.StorageType == DB.StorageType.String:
                    param.Set(str(param_value))

    return {
        'status': 'success',
        'message': 'Family instance placed',
        'instance_id': str(instance.Id.IntegerValue)
    }


def handle_load_family(cmd):
    """Handle load_family command"""
    family_path = cmd.get('family_path')

    if not os.path.exists(family_path):
        return {'status': 'error', 'message': 'Family file not found: ' + str(family_path)}

    with revit.Transaction("Load Family"):
        family = None
        success = doc.LoadFamily(family_path, family)

        if success:
            return {
                'status': 'success',
                'message': 'Family loaded successfully',
                'family_name': os.path.basename(family_path)
            }
        else:
            return {'status': 'error', 'message': 'Failed to load family'}


def handle_import_dxf(cmd):
    """Handle import_dxf command"""
    dxf_path = cmd.get('dxf_path')
    view_name = cmd.get('view_name')

    if not os.path.exists(dxf_path):
        return {'status': 'error', 'message': 'DXF file not found: ' + str(dxf_path)}

    # Get target view
    if view_name:
        target_view = None
        collector = DB.FilteredElementCollector(doc)
        views = collector.OfClass(DB.View).ToElements()
        for v in views:
            if v.Name == view_name:
                target_view = v
                break
        if not target_view:
            return {'status': 'error', 'message': 'View not found: ' + str(view_name)}
    else:
        target_view = doc.ActiveView

    # Import DXF
    with revit.Transaction("Import DXF"):
        options = DB.DWGImportOptions()
        options.Unit = DB.ImportUnit.Millimeter
        options.ColorMode = DB.ImportColorMode.Preserved
        options.OrientToView = True

        import_id = clr.Reference[DB.ElementId]()
        result = doc.Import(dxf_path, options, target_view, import_id)

        if result:
            return {
                'status': 'success',
                'message': 'DXF imported',
                'import_id': str(import_id.Value.IntegerValue),
                'view': target_view.Name
            }
        else:
            return {'status': 'error', 'message': 'Failed to import DXF'}


def handle_create_sheet(cmd):
    """Handle create_sheet command"""
    number = cmd.get('number')
    name = cmd.get('name')

    with revit.Transaction("Create Sheet"):
        # Get default titleblock
        collector = DB.FilteredElementCollector(doc)
        titleblocks = collector.OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_TitleBlocks).ToElements()

        if not titleblocks:
            return {'status': 'error', 'message': 'No titleblocks found'}

        titleblock = titleblocks[0]

        # Create sheet
        sheet = DB.ViewSheet.Create(doc, titleblock.Id)
        sheet.SheetNumber = number
        sheet.Name = name

    return {
        'status': 'success',
        'message': 'Sheet created',
        'sheet_id': str(sheet.Id.IntegerValue),
        'sheet_number': number
    }


# =============================================================================
# COMMAND PROCESSOR
# =============================================================================

def process_command(cmd):
    """Process single command"""
    try:
        action = cmd.get('action')

        # Command handlers map
        handlers = {
            'ping': handle_ping,
            'import_dxf': handle_import_dxf,
            'load_family': handle_load_family,
            'place_family_instance': handle_place_family,
            'create_sheet': handle_create_sheet
        }

        if action in handlers:
            result = handlers[action](cmd)
            logger.info("Command processed: " + str(action))
            return result
        else:
            return {
                'status': 'error',
                'message': 'Unknown action: ' + str(action)
            }

    except Exception as e:
        logger.error("Error processing command: " + str(e))
        logger.error(traceback.format_exc())
        return {
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }


# =============================================================================
# LISTENER LOOP
# =============================================================================

def listener_loop():
    """Main listener loop (runs in separate thread)"""
    global _listener_running

    logger.info("Listener loop started")
    # output.print_md("## Listener ACTIVE - monitoring queue...")

    while _listener_running:
        try:
            # Check for commands
            if not os.path.exists(str(COMMANDS_QUEUE)):
                os.makedirs(str(COMMANDS_QUEUE))

            # Find command files (IronPython compatible)
            cmd_files = []
            for filename in os.listdir(str(COMMANDS_QUEUE)):
                if filename.startswith('cmd_') and filename.endswith('.json'):
                    cmd_files.append(Path(str(COMMANDS_QUEUE)) / filename)

            for cmd_file in cmd_files:
                # Read command
                with open(str(cmd_file), 'r') as f:
                    cmd_data = json.load(f)

                cmd_id = cmd_data.get('id')
                logger.info("Processing command: " + str(cmd_id))

                # Process command
                result = process_command(cmd_data)

                # Write result
                write_result(cmd_id, result)

                # Delete command file
                cmd_file.unlink()

                logger.info("Command " + str(cmd_id) + " processed successfully")

        except Exception as e:
            logger.error("Error in listener loop: " + str(e))

        time.sleep(POLL_INTERVAL)

    logger.info("Listener loop stopped")
    # output.print_md("## Listener STOPPED")


# =============================================================================
# PUBLIC FUNCTIONS (called from pyRevit buttons)
# =============================================================================

def start_listener():
    """Start listener"""
    global _listener_running, _listener_thread

    if _listener_running:
        forms.alert("Listener already running!", title="Info", warn_icon=False)
        return

    # Create folders if not exist
    if not os.path.exists(str(COMMANDS_QUEUE)):
        os.makedirs(str(COMMANDS_QUEUE))
    if not os.path.exists(str(RESULTS_QUEUE)):
        os.makedirs(str(RESULTS_QUEUE))

    # Start listener thread
    _listener_running = True
    _listener_thread = threading.Thread(target=listener_loop)
    _listener_thread.daemon = True
    _listener_thread.start()

    logger.info("Revit Listener Started")
    logger.info("Commands Queue: " + str(COMMANDS_QUEUE))
    logger.info("Results Queue: " + str(RESULTS_QUEUE))
    logger.info("Waiting for commands...")

    forms.alert(
        "Listener started successfully!\n\nMonitoring: " + str(COMMANDS_QUEUE),
        title="Success",
        warn_icon=False
    )


def stop_listener():
    """Stop listener"""
    global _listener_running

    if not _listener_running:
        forms.alert("Listener not running!", title="Info", warn_icon=False)
        return

    _listener_running = False
    logger.info("Stopping listener...")

    forms.alert("Listener stopped!", title="Info", warn_icon=False)


# =============================================================================
# MAIN ENTRY POINT (called when button clicked)
# =============================================================================

if __name__ == '__main__':
    start_listener()
