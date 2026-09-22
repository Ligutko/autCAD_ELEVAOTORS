# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **AutoCAD automation project** for generating parametric grain elevator schematics. The system enables:
- Parametric design of industrial grain storage facilities (silos, conveyors, elevators)
- AutoCAD automation through COM API and MCP (Model Context Protocol) server
- DXF file manipulation using both ezdxf and AutoCAD COM API

**Primary Language:** Python, AutoLISP
**Target Software:** AutoCAD LT 2024+, AutoCAD Plant 3D

## Architecture

### 1. MCP Server Integration (`autocad-mcp/`)

The project uses a custom MCP server (`autocad-industrial`) that bridges Claude with AutoCAD through COM API:

- **Entry point:** `autocad-mcp/server_com_api.py`
- **Configuration:** `.mcp.json` points to this server
- **Key MCP tools available:**
  - `draw_silo()` - draws parametric silos with diameter, height, tag
  - `draw_elevator()` - draws bucket elevators (norії)
  - `draw_conveyor()` - draws conveyors/transporters
  - `draw_pipe_connection()` - draws pipe connections
  - `clear_drawing()` - clears all objects from drawing

**Important:** The MCP server uses `win32com.client` to communicate directly with AutoCAD's COM API. It does NOT use keyboard simulation.

### 2. Configuration-Based Generation

The system is **fully parametric** - equipment layouts are defined in JSON configurations:

- **Equipment catalog:** `Plant3D_Equipment_Catalog.json` - specs from page_08 of source PDF
- **Schema configs:**
  - `grain_system_schema.json` - 2 silos baseline
  - `config_6_silos.json` - 6 silos layout
  - `config_7_silos.json` - 7 silos layout

**Config structure:**
```json
{
  "project_name": "Grain Elevator - 6 Silos",
  "equipment": {
    "silos": [
      {"x": 0, "y": 0, "diameter": 22000, "height": 21422, "tag": "МСВУ-220.13.В12", ...}
    ],
    "elevators": [...],
    "conveyors": [...],
    "pipes": [...]
  },
  "totals": {
    "total_storage_capacity_m3": 38286,
    "total_power_kW": 266.19
  }
}
```

### 3. Generation Workflow

**Primary generator:** `generate_from_config.py`

```bash
python generate_from_config.py config_6_silos.json
```

This reads the JSON config and instructs Claude to call MCP tools to draw the complete schema. The config files are the **single source of truth** - all coordinates, dimensions, and equipment specs come from JSON.

### 4. DXF File Structure

Original schematics are stored as DXF files in `FINAL_DXF_PERFECT_V7/`:
- `page_01.dxf` through `page_12.dxf` (converted from source PDF)
- **Warning:** `page_01.dxf` contains 46,955+ entities - iteration in Python COM API causes timeouts

**Layer organization:**
- Blue objects (`C00-00-FF`): Silos and main equipment
- Red objects (`CFF-00-00` or Color=1): Conveyors and elevators (connections)
- Black hatches (`C00-00-00`): Hatch fills for equipment

### 5. State Management System

Files in root directory use a state tracking system to prevent duplicate operations:

- **`STATE_MANAGER.py`** - manages operation state, preserves originals
- **`processing_state.json`** - tracks which operations have been applied
- **`SAFE_RESIZE_SYSTEM.py`** - applies transformations with state checks

**Directory structure:**
```
ORIGINALS/     - Read-only backups of source files
WORKING/       - Working copies for processing
RESULTS/       - Final outputs with timestamps
```

The state system prevents applying the same transformation twice (e.g., scaling a silo multiple times).

## Common Commands

### Running the MCP Server

The MCP server is configured in `.mcp.json` and runs automatically when Claude Code connects. You can test it manually:

```bash
cd autocad-mcp
venv\Scripts\activate
python server_com_api.py
```

### Generating a Schema

```bash
# Generate from config
python generate_from_config.py config_6_silos.json

# This outputs MCP commands to *_commands.txt
# Claude then executes these commands via the MCP server
```

### AutoCAD Must Be Open

**Critical:** AutoCAD must be running with a drawing open before any COM API operations. The scripts connect via:

```python
acad = win32com.client.Dispatch("AutoCAD.Application")
doc = acad.ActiveDocument
modelSpace = doc.ModelSpace
```

### Analyzing DXF Files

For large DXF files (like `page_01.dxf` with 47K entities), use **ezdxf** instead of COM API to avoid timeouts:

```python
import ezdxf
doc = ezdxf.readfile('FINAL_DXF_PERFECT_V7/page_01.dxf')
msp = doc.modelspace()
# Fast iteration - no timeout issues
```

## Critical Constraints

### DO NOT Iterate Large Files with COM API

Files like `page_01.dxf` have 46,955+ entities. Iterating them with:
```python
for obj in modelSpace:  # WILL TIMEOUT after ~180 seconds
```

**Solution:** Use ezdxf for analysis, COM API only for drawing operations.

### Coordinate System

All coordinates are in **millimeters**:
- Silo diameter: 22000mm (22 meters)
- Silo height: 21422mm (~21.4 meters)
- Spacing between silos: 28000mm (28 meters)

### Equipment Specifications

Equipment specs come from `Plant3D_Equipment_Catalog.json` which was extracted from page_08 of the source PDF:
- **МСВУ 220.13.В12:** D=22m, H=21.422m, V=6381m³
- **Н-100 elevator:** 100 t/h capacity, H=33m
- **Т7/У13-ТЦС-320 conveyor:** 100 t/h, L=30.5m

Do not hardcode specs - reference the catalog file.

## Project-Specific Guidelines

### When Adding New Equipment

1. Add equipment to `Plant3D_Equipment_Catalog.json` if not already present
2. Update a config file (or create new one) with coordinates
3. Use `generate_from_config.py` to generate MCP commands
4. Claude executes the commands via MCP server

### When Modifying Existing Schemas

**NEVER directly edit DXF files.** Instead:
1. Modify the JSON configuration
2. Regenerate the schema via `generate_from_config.py`
3. The MCP server will redraw everything parametrically

### Scaling/Transforming Operations

If you need to scale or transform existing geometry:
1. Use the State Management system (`STATE_MANAGER.py`)
2. Define operations in a config file
3. The system will track which operations have been applied
4. Never scale the same object twice

### File Organization

- **FINAL_DXF_PERFECT_V7/** - Original source files (DO NOT MODIFY)
- **ORIGINALS/** - Backups created by state manager
- **WORKING/** - Temporary files for processing
- **RESULTS/** - Final outputs with timestamps
- **autocad-mcp/** - MCP server code (rarely needs changes)

## Key Technical Details

### COM API Point Creation

AutoCAD COM API requires VARIANT points:

```python
import pythoncom
import win32com.client

def create_variant_point(x, y, z=0):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y, z])

# Usage
modelSpace.AddLine(
    create_variant_point(0, 0, 0),
    create_variant_point(100, 100, 0)
)
```

### MCP Tool Definition

New MCP tools are defined in `autocad-mcp/server_com_api.py`:

```python
@mcp_server.tool()
async def draw_equipment(
    x: float,
    y: float,
    equipment_type: str
) -> str:
    """Tool description for Claude"""
    acad, doc, modelSpace = get_autocad()
    # Drawing logic here
    return "Status message"
```

### Configuration Generation

When creating new schemas, follow the pattern in existing configs:
1. Define all equipment with x,y coordinates
2. Calculate totals (volume, power, etc.)
3. Equipment IDs/tags must be unique
4. Use standard Ukrainian equipment designations (МСВУ, Н, Т7)

## Documentation Files

- **СИСТЕМА_ГОТОВА.md** - Summary of parametric system capabilities (Ukrainian)
- **USAGE_GUIDE.md** - State management system usage
- **FULL_PROJECT_REPORT.md** - Detailed project history and attempts
- **SCRIPTS_REFERENCE.md** - Technical reference for all scripts
- **README_FOR_NEXT_AGENT.md** - Handoff notes between AI sessions

## Important Notes

- This project contains both working and deprecated scripts. Check `SCRIPTS_REFERENCE.md` for current status.
- Many analysis scripts (`ANALYZE_*.py`) have timeout issues on large files - prefer ezdxf for analysis.
- The user prefers copying existing geometry over drawing from scratch when possible.
- All user-facing messages and documentation are in Ukrainian.
- Configuration files use metric units (mm for dimensions, m³ for volume, kW for power).
