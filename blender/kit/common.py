"""Спільні будівельні функції кіта.

Кожна деталь кіта будується в локальних координатах (вісь деталі в X = 0, Y = 0,
низ на Z = 0) у свою колекцію. Світ ставить її екземплярами колекції.
Шляхи і шрифти не прив'язані до Windows: скрипти запускаються і на
`blender --background` у Windows, і на модулі `bpy` у Linux.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

FONT_CANDIDATES = (
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
)


def clean(value: float) -> float:
    value = round(float(value), 6)
    if abs(value) < 5e-7:
        return 0.0
    return value


class Builder:
    """Кладе нові об'єкти в одну колекцію."""

    def __init__(self, collection: bpy.types.Collection):
        self.collection = collection
        self._materials: dict[str, bpy.types.Material] = {}

    def link(self, obj):
        self.collection.objects.link(obj)
        return obj

    def material(self, name, color, roughness, metallic=0.0):
        existing = bpy.data.materials.get(name)
        if existing is not None:
            return existing
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.use_backface_culling = False
        bsdf = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
        base = bsdf.inputs.get("Base Color") or bsdf.inputs[0]
        base.default_value = (color[0], color[1], color[2], 1.0)
        rough = bsdf.inputs.get("Roughness")
        if rough is not None:
            rough.default_value = roughness
        metal = bsdf.inputs.get("Metallic")
        if metal is not None:
            metal.default_value = metallic
        mat.diffuse_color = (color[0], color[1], color[2], 1.0)
        return mat

    def new_mesh(self, name, build, material, smooth=False, outward=False):
        mesh = bpy.data.meshes.new(name + "_MESH")
        obj = self.link(bpy.data.objects.new(name, mesh))
        bm = bmesh.new()
        build(bm)
        finish_mesh(bm, mesh, smooth, outward=outward)
        mesh.materials.append(material)
        return obj

    def instance_of(self, name, mesh, location=(0.0, 0.0, 0.0), rotation=(0.0, 0.0, 0.0)):
        obj = self.link(bpy.data.objects.new(name, mesh))
        obj.location = location
        obj.rotation_euler = rotation
        return obj

    def cylinder(self, name, origin, direction, length, radius, material, steps=16):
        def build(bm):
            add_cylinder(bm, origin, direction, length, radius, steps)

        return self.new_mesh(name, build, material, smooth=True)


def finish_mesh(bm, mesh, smooth, outward=False):
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    if outward:
        inward = [f for f in bm.faces if f.normal.dot(f.calc_center_median()) < 0.0]
        if inward:
            bmesh.ops.reverse_faces(bm, faces=inward)
            bm.normal_update()
    for face in bm.faces:
        face.smooth = smooth
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()


def add_box(bm, x0, x1, y0, y1, z0, z1, skip=()):
    verts = {}
    for ix, x_value in enumerate((x0, x1)):
        for iy, y_value in enumerate((y0, y1)):
            for iz, z_value in enumerate((z0, z1)):
                verts[(ix, iy, iz)] = bm.verts.new((x_value, y_value, z_value))
    faces = {
        "nx": ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)),
        "px": ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
        "ny": ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)),
        "py": ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
        "nz": ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)),
        "pz": ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
    }
    for key, order in faces.items():
        if key not in skip:
            bm.faces.new(tuple(verts[k] for k in order))


def add_cylinder(bm, origin, direction, length, radius, steps=16):
    origin = Vector(origin)
    direction = Vector(direction).normalized()
    side = direction.cross(Vector((0.0, 0.0, 1.0)))
    if side.length < 1.0e-6:
        side = direction.cross(Vector((1.0, 0.0, 0.0)))
    side.normalize()
    binormal = direction.cross(side).normalized()
    rings = []
    for distance in (0.0, length):
        center = origin + direction * distance
        ring = []
        for step in range(steps):
            angle = 2.0 * math.pi * step / steps
            offset = side * (math.cos(angle) * radius) + binormal * (math.sin(angle) * radius)
            ring.append(bm.verts.new(center + offset))
        rings.append(ring)
    for step in range(steps):
        nxt = (step + 1) % steps
        bm.faces.new((rings[0][step], rings[1][step], rings[1][nxt], rings[0][nxt]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[1])


def load_font():
    extra = os.environ.get("KIT_FONT")
    for path in ((extra,) if extra else ()) + FONT_CANDIDATES:
        if path and Path(path).is_file():
            return bpy.data.fonts.load(path)
    raise RuntimeError("немає шрифту з кирилицею; задайте KIT_FONT")


def kit_collection(name: str) -> bpy.types.Collection:
    """Колекція деталі кіта. Сама в сцені не рендериться, лише через екземпляри."""
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
    return collection
