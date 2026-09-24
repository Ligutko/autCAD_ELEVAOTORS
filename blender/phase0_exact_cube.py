"""Phase 0 proof: a cube of exact metric dimensions, rendered headless.

Target box: 3.500 m x 2.000 m x 1.250 m, sitting on Z = 0.
Run:
    blender --background --factory-startup --python phase0_exact_cube.py
"""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

TARGET_M = (3.5, 2.0, 1.25)
TOLERANCE_M = 1e-4
OUT = Path(r"d:\autocad project\blender\proof")
OUT.mkdir(parents=True, exist_ok=True)


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_material(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.45
    return mat


def main():
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
    cube = bpy.context.active_object
    cube.name = "PHASE0_CUBE"
    cube.dimensions = TARGET_M
    bpy.context.view_layer.update()
    cube.location.z = cube.dimensions.z / 2.0
    cube.data.materials.append(make_material("CubeOrange", (0.82, 0.38, 0.08)))

    bpy.ops.mesh.primitive_plane_add(size=14.0, location=(0.0, 0.0, 0.0))
    ground = bpy.context.active_object
    ground.name = "GROUND"
    ground.data.materials.append(make_material("GroundGrey", (0.45, 0.47, 0.50)))

    label = f"{TARGET_M[0]:.3f} x {TARGET_M[1]:.3f} x {TARGET_M[2]:.3f} m"
    bpy.ops.object.text_add(location=(0.0, -2.4, 0.02))
    text = bpy.context.active_object
    text.name = "PHASE0_LABEL"
    text.data.body = label
    text.data.size = 0.28
    text.data.align_x = "CENTER"
    text.data.extrude = 0.01
    text.rotation_euler = (1.5708, 0.0, 0.0)
    text.data.materials.append(make_material("LabelWhite", (0.95, 0.95, 0.95)))

    bpy.ops.object.camera_add(location=(7.2, -6.4, 4.2))
    camera = bpy.context.active_object
    camera.name = "PHASE0_CAMERA"
    look_at(camera, (0.0, 0.0, TARGET_M[2] / 2.0))
    camera.data.lens = 35
    scene.camera = camera

    bpy.ops.object.light_add(type="SUN", location=(4.0, -2.0, 10.0))
    sun = bpy.context.active_object
    sun.data.energy = 4.0
    look_at(sun, (0.0, 0.0, 0.5))

    bpy.ops.object.light_add(type="AREA", location=(-3.0, 3.0, 4.0))
    fill = bpy.context.active_object
    fill.data.energy = 250.0
    fill.data.size = 4.0
    look_at(fill, (0.0, 0.0, 0.6))

    world = bpy.data.worlds.new("PHASE0_WORLD")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs[0].default_value = (0.55, 0.60, 0.66, 1.0)
        background.inputs[1].default_value = 1.0

    engines = [item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items]
    if "BLENDER_EEVEE_NEXT" in engines:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in engines:
        scene.render.engine = "BLENDER_EEVEE"
    else:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 32
        scene.cycles.device = "CPU"

    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.image_settings.file_format = "PNG"
    image_path = OUT / "phase0_cube.png"
    scene.render.filepath = str(image_path)

    bpy.context.view_layer.update()
    measured = tuple(float(v) for v in cube.dimensions)
    ok = all(abs(measured[i] - TARGET_M[i]) < TOLERANCE_M for i in range(3))

    bpy.ops.render.render(write_still=True)
    blend_path = OUT / "phase0_cube.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "pass": ok,
        "name": cube.name,
        "target_m": {"x": TARGET_M[0], "y": TARGET_M[1], "z": TARGET_M[2]},
        "measured_m": {
            "x": round(measured[0], 6),
            "y": round(measured[1], 6),
            "z": round(measured[2], 6),
        },
        "tolerance_m": TOLERANCE_M,
        "location_m": [round(float(v), 6) for v in cube.location],
        "unit_system": scene.unit_settings.system,
        "length_unit": scene.unit_settings.length_unit,
        "scale_length": scene.unit_settings.scale_length,
        "render_engine": scene.render.engine,
        "image": str(image_path),
        "blend": str(blend_path),
    }
    (OUT / "phase0_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print("PHASE0_REPORT " + json.dumps(report))
    print("PHASE0_PASS" if ok else "PHASE0_FAIL")
    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
