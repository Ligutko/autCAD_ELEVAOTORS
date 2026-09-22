# -*- coding: utf-8 -*-
"""
Revit Listener - AUTO BACKGROUND VERSION

Uses System.Windows.Threading.DispatcherTimer for automatic background processing.
No manual button clicks needed - processes commands automatically every 0.5 seconds.

Author: Claude Code
Version: 0.4.0 - Auto background with DispatcherTimer
"""

from pyrevit import revit, DB, UI, forms, script
import os
import json
from pathlib import Path
import clr

clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('WindowsBase')
clr.AddReference('PresentationCore')

from System.Windows.Threading import DispatcherTimer, DispatcherPriority
from System import TimeSpan

# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(r"D:\autocad project")
COMMANDS_QUEUE = PROJECT_ROOT / "revit-mcp" / "commands_queue"
RESULTS_QUEUE = PROJECT_ROOT / "revit-mcp" / "results_queue"

POLL_INTERVAL_MS = 500  # 0.5 seconds

logger = script.get_logger()
output = script.get_output()

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
app = __revit__.Application

# Global timer
_timer = None
_listener_active = False

# =============================================================================
# UTILITIES
# =============================================================================

def mm_to_feet(mm_value):
    return mm_value / 304.8

def write_result(cmd_id, result_data):
    result_file = RESULTS_QUEUE / ("cmd_" + str(cmd_id) + "_result.json")
    with open(str(result_file), 'w') as f:
        json.dump(result_data, f, indent=2)

def find_level_by_name(level_name):
    collector = DB.FilteredElementCollector(doc)
    levels = collector.OfClass(DB.Level).ToElements()
    for level in levels:
        if level.Name == level_name:
            return level
    return levels[0] if levels else None

def find_family_symbol(family_name, symbol_name):
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
    return {
        'status': 'success',
        'message': 'Revit listener is active',
        'revit_version': app.VersionNumber,
        'document': doc.Title if doc else 'No document'
    }

def handle_load_family(cmd):
    family_path = cmd.get('family_path')

    if not os.path.exists(family_path):
        return {'status': 'error', 'message': 'Family file not found: ' + str(family_path)}

    with revit.Transaction("Load Family"):
        family = None
        success = doc.LoadFamily(family_path, family)

        if success:
            return {
                'status': 'success',
                'message': 'Family loaded',
                'family_name': os.path.basename(family_path)
            }
        else:
            return {'status': 'error', 'message': 'Failed to load family'}

def handle_place_family(cmd):
    family_name = cmd.get('family_name')
    symbol_name = cmd.get('symbol_name', 'Default')
    x = cmd.get('x', 0)
    y = cmd.get('y', 0)
    z = cmd.get('z', 0)
    level_name = cmd.get('level_name', 'Level 1')
    parameters = cmd.get('parameters', {})

    symbol = find_family_symbol(family_name, symbol_name)
    if not symbol:
        return {'status': 'error', 'message': 'Family not found: ' + str(family_name)}

    level = find_level_by_name(level_name)
    if not level:
        return {'status': 'error', 'message': 'Level not found: ' + str(level_name)}

    with revit.Transaction("Place Family"):
        if not symbol.IsActive:
            symbol.Activate()

        point = DB.XYZ(mm_to_feet(x), mm_to_feet(y), mm_to_feet(z))
        instance = doc.Create.NewFamilyInstance(
            point, symbol, level,
            DB.Structure.StructuralType.NonStructural
        )

        # Set parameters
        for param_name, param_value in parameters.items():
            param = instance.LookupParameter(param_name)
            if param and not param.IsReadOnly:
                if param.StorageType == DB.StorageType.Double:
                    param.Set(mm_to_feet(float(param_value)))
                elif param.StorageType == DB.StorageType.Integer:
                    param.Set(int(param_value))
                elif param.StorageType == DB.StorageType.String:
                    param.Set(str(param_value))

    return {
        'status': 'success',
        'message': 'Family placed',
        'instance_id': str(instance.Id.IntegerValue)
    }

def handle_create_sheet(cmd):
    number = cmd.get('number')
    name = cmd.get('name')

    with revit.Transaction("Create Sheet"):
        collector = DB.FilteredElementCollector(doc)
        titleblocks = collector.OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_TitleBlocks).ToElements()

        if not titleblocks:
            return {'status': 'error', 'message': 'No titleblocks found'}

        titleblock = titleblocks[0]
        sheet = DB.ViewSheet.Create(doc, titleblock.Id)
        sheet.SheetNumber = number
        sheet.Name = name

    return {
        'status': 'success',
        'message': 'Sheet created',
        'sheet_id': str(sheet.Id.IntegerValue)
    }

def process_command(cmd):
    try:
        action = cmd.get('action')

        handlers = {
            'ping': handle_ping,
            'load_family': handle_load_family,
            'place_family_instance': handle_place_family,
            'create_sheet': handle_create_sheet
        }

        if action in handlers:
            result = handlers[action](cmd)
            logger.info("Processed: " + str(action))
            return result
        else:
            return {'status': 'error', 'message': 'Unknown action: ' + str(action)}

    except Exception as e:
        logger.error("Error: " + str(e))
        return {'status': 'error', 'message': str(e)}

# =============================================================================
# TIMER CALLBACK
# =============================================================================

def on_timer_tick(sender, event_args):
    """Called every 0.5 seconds by DispatcherTimer"""
    try:
        # Create folders if needed
        if not os.path.exists(str(COMMANDS_QUEUE)):
            os.makedirs(str(COMMANDS_QUEUE))
        if not os.path.exists(str(RESULTS_QUEUE)):
            os.makedirs(str(RESULTS_QUEUE))

        # Find command files
        cmd_files = []
        for filename in os.listdir(str(COMMANDS_QUEUE)):
            if filename.startswith('cmd_') and filename.endswith('.json'):
                cmd_files.append(filename)

        # Process commands
        for filename in cmd_files:
            try:
                cmd_file_path = COMMANDS_QUEUE / filename

                with open(str(cmd_file_path), 'r') as f:
                    cmd_data = json.load(f)

                cmd_id = cmd_data.get('id')

                # Process
                result = process_command(cmd_data)

                # Write result
                write_result(cmd_id, result)

                # Delete command
                os.remove(str(cmd_file_path))

                logger.info("Command " + str(cmd_id) + " processed")

            except Exception as e:
                logger.error("Error processing command: " + str(e))

    except Exception as e:
        logger.error("Timer error: " + str(e))

# =============================================================================
# START/STOP FUNCTIONS
# =============================================================================

def start_auto_listener():
    """Start automatic background listener"""
    global _timer, _listener_active

    if _listener_active:
        forms.alert("Listener already running!", title="Info")
        return

    # Create folders
    if not os.path.exists(str(COMMANDS_QUEUE)):
        os.makedirs(str(COMMANDS_QUEUE))
    if not os.path.exists(str(RESULTS_QUEUE)):
        os.makedirs(str(RESULTS_QUEUE))

    # Create timer
    _timer = DispatcherTimer()
    _timer.Interval = TimeSpan.FromMilliseconds(POLL_INTERVAL_MS)
    _timer.Tick += on_timer_tick
    _timer.Start()

    _listener_active = True

    output.print_md("# AUTO LISTENER STARTED")
    output.print_md("Queue: " + str(COMMANDS_QUEUE))
    output.print_md("Monitoring every 0.5 seconds...")
    output.print_md("")
    output.print_md("**Listener runs in background automatically!**")

    forms.alert(
        "Auto Listener Started!\n\nMonitoring: " + str(COMMANDS_QUEUE) + "\n\nProcesses commands automatically every 0.5s",
        title="Success"
    )

def stop_auto_listener():
    """Stop automatic listener"""
    global _timer, _listener_active

    if not _listener_active:
        forms.alert("Listener not running!", title="Info")
        return

    if _timer:
        _timer.Stop()
        _timer = None

    _listener_active = False

    output.print_md("## Listener STOPPED")
    forms.alert("Listener stopped!", title="Info")

# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    start_auto_listener()
