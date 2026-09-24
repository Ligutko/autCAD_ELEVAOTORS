"""Деталь кіта `noria_n100`: норія 100 т/год, труба 33 м, 22 кВт (Н-100 / У13-УН175).

Геометрія перенесена з прийнятого зрізу NORIA-1 (`blender/noria_01/build_noria.py`,
NORIA_PASS 2026-09-23) без зміни чисел. Вісь деталі в (0, 0), низ башмака на Z = 0.
Позицію і відмітку низу задає світ, розміри — ні.
"""

from __future__ import annotations

import math

from . import common

TYPE = "noria_n100"
COLLECTION = "KIT_noria_n100"

TUBE_TOP = 33.0
CLEAR_X = 0.376
CLEAR_Y = 0.256
SHEET_T = 0.012
COURSE_H = 1.0
DRUM_R = 0.12
DRUM_W = 0.16
BELT_X = 0.12
BUCKET_PITCH = 0.18
BUCKET_DEPTH = 0.055
BOLT_GAP = 0.22
HEAD_DZ = 0.20
BOOT_DZ = 0.18

SPEC = {
    "type": TYPE,
    "tag": "Н-100 / У13-УН175",
    "footprint_half_x_m": CLEAR_X * 0.5 + 0.09 + 0.3,
    "footprint_half_y_m": CLEAR_Y * 0.5 + 0.06 + 0.3,
    "tube_height_m": TUBE_TOP,
    "provenance": {
        "tube_height_m": {"value": TUBE_TOP, "from": "каталог + OCR арк. 8 «Нтруб=33000 мм»"},
        "capacity_tph": {"value": 100, "from": "каталог + OCR арк. 8"},
        "power_kw": {"value": 22, "from": "каталог + OCR арк. 8"},
        "bucket_pitch_m": {"value": BUCKET_PITCH, "from": "оголошення bizorg 2017, не паспорт (rec_cdfc5232)"},
        "shaft_clear_m": {"value": [CLEAR_X, CLEAR_Y], "from": "оголошення bizorg 2017, не паспорт (rec_fef4064e)"},
        "head_boot_ladder": {"value": "показ", "from": "не з паспорта"},
    },
}


def build() -> dict:
    import bmesh
    import bpy
    from mathutils import Vector

    existing = bpy.data.collections.get(COLLECTION)
    if existing is not None and existing.objects:
        return {"collection": existing.name}
    kit = common.kit_collection(COLLECTION)
    b = common.Builder(kit)

    sheet_mat = b.material("NoriaSheet", (0.80, 0.82, 0.84), 0.40, metallic=0.55)
    flange_mat = b.material("NoriaFlange", (0.20, 0.22, 0.26), 0.40, metallic=0.4)
    head_mat = b.material("NoriaBoltHead", (0.05, 0.05, 0.06), 0.28, metallic=0.85)
    shank_mat = b.material("NoriaBoltShank", (0.82, 0.78, 0.68), 0.22, metallic=0.9)
    drum_mat = b.material("NoriaDrum", (0.35, 0.36, 0.38), 0.35, metallic=0.7)
    housing_mat = b.material("NoriaHousing", (0.70, 0.72, 0.74), 0.45, metallic=0.5)
    belt_mat = b.material("NoriaBelt", (0.08, 0.08, 0.08), 0.8)
    bucket_mat = b.material("NoriaBucket", (0.85, 0.80, 0.62), 0.5, metallic=0.2)
    ladder_mat = b.material("NoriaLadder", (0.85, 0.62, 0.10), 0.5, metallic=0.3)

    x0, x1 = -CLEAR_X * 0.5, CLEAR_X * 0.5
    y0, y1 = -CLEAR_Y * 0.5, CLEAR_Y * 0.5
    count = int(round(TUBE_TOP / COURSE_H))
    for index in range(count):
        z0 = index * COURSE_H
        z1 = TUBE_TOP if index == count - 1 else (index + 1) * COURSE_H

        def sheet(bm, z0=z0, z1=z1):
            common.add_box(bm, x0 - SHEET_T, x0, y0, y1, z0, z1)
            common.add_box(bm, x1, x1 + SHEET_T, y0, y1, z0, z1)
            common.add_box(bm, x0 - SHEET_T, x1 + SHEET_T, y1, y1 + SHEET_T, z0, z1)

        b.new_mesh(f"NORIA_SHEET_{index + 1:02d}", sheet, sheet_mat)
    b.new_mesh("NORIA_FLANGE", lambda bm: common.add_box(bm, x0 - 0.02, x0, y0 - 0.05, y0, 0.0, TUBE_TOP), flange_mat)

    z_value = 0.28
    number = 1
    direction = Vector((0.0, -1.0, 0.0))
    while z_value < TUBE_TOP - 0.12:
        origin = Vector((x0 - 0.01, y0 - 0.02, z_value))
        b.cylinder(f"NORIA_BOLT_{number:03d}_BODY", origin, direction, 0.012, 0.009, shank_mat)
        b.cylinder(f"NORIA_BOLT_{number:03d}", origin + direction * 0.012, direction, 0.016, 0.022, head_mat)
        number += 1
        z_value += BOLT_GAP

    head_z = TUBE_TOP - HEAD_DZ
    boot_z = BOOT_DZ + DRUM_R
    for name, zc in (("NORIA_HEAD_DRUM", head_z), ("NORIA_BOOT_DRUM", boot_z)):
        b.cylinder(name, Vector((0.0, -DRUM_W * 0.5, zc)), Vector((0.0, 1.0, 0.0)), DRUM_W, DRUM_R, drum_mat)

    hx, hy = CLEAR_X * 0.5 + 0.05, CLEAR_Y * 0.5 + 0.04
    b.new_mesh(
        "NORIA_HEAD",
        lambda bm: common.add_box(bm, -hx, hx, -hy, hy, TUBE_TOP - 0.85, TUBE_TOP + 0.28, skip=("ny",)),
        housing_mat,
    )
    b.new_mesh(
        "NORIA_BOOT",
        lambda bm: common.add_box(bm, -hx - 0.04, hx + 0.04, -hy - 0.02, hy, 0.0, 0.78, skip=("ny",)),
        housing_mat,
    )

    thickness, width = 0.008, 0.14
    for name, xb in (("NORIA_BELT_UP", BELT_X), ("NORIA_BELT_DOWN", -BELT_X)):
        b.new_mesh(
            name,
            lambda bm, xb=xb: common.add_box(
                bm, xb - thickness * 0.5, xb + thickness * 0.5, -width * 0.5, width * 0.5, boot_z, head_z
            ),
            belt_mat,
        )
    for name, zc, sign in (("NORIA_BELT_HEAD", head_z, 1.0), ("NORIA_BELT_BOOT", boot_z, -1.0)):

        def arc(bm, zc=zc, sign=sign):
            steps = 8
            k = (BELT_X + thickness) / BELT_X
            for step in range(steps):
                a0 = math.pi * step / steps + (math.pi if sign < 0.0 else 0.0)
                a1 = math.pi * (step + 1) / steps + (math.pi if sign < 0.0 else 0.0)
                inner = [(BELT_X * math.cos(a), zc + BELT_X * math.sin(a)) for a in (a0, a1)]
                outer = [(px * k, zc + (pz - zc) * k) for px, pz in inner]
                ya, yb = -width * 0.5, width * 0.5
                v = [
                    bm.verts.new((inner[0][0], ya, inner[0][1])),
                    bm.verts.new((inner[1][0], ya, inner[1][1])),
                    bm.verts.new((inner[1][0], yb, inner[1][1])),
                    bm.verts.new((inner[0][0], yb, inner[0][1])),
                    bm.verts.new((outer[0][0], ya, outer[0][1])),
                    bm.verts.new((outer[1][0], ya, outer[1][1])),
                    bm.verts.new((outer[1][0], yb, outer[1][1])),
                    bm.verts.new((outer[0][0], yb, outer[0][1])),
                ]
                bm.faces.new((v[0], v[1], v[2], v[3]))
                bm.faces.new((v[4], v[7], v[6], v[5]))
                bm.faces.new((v[0], v[4], v[5], v[1]))
                bm.faces.new((v[3], v[2], v[6], v[7]))

        b.new_mesh(name, arc, belt_mat)

    bucket_mesh = bpy.data.meshes.new("NORIA_BUCKET_MESH")
    bm = bmesh.new()
    common.add_box(bm, 0.0, BUCKET_DEPTH, -0.07, 0.07, -0.04, 0.04, skip=("px",))
    common.finish_mesh(bm, bucket_mesh, False)
    bucket_mesh.materials.append(bucket_mat)
    z_value = 0.62
    top = TUBE_TOP - HEAD_DZ - DRUM_R - 0.08
    index = 0
    while z_value < top:
        b.instance_of(f"NORIA_BUCKET_UP_{index:03d}", bucket_mesh, (BELT_X, 0.0, z_value))
        b.instance_of(
            f"NORIA_BUCKET_DOWN_{index:03d}", bucket_mesh, (-BELT_X, 0.0, z_value + BUCKET_PITCH * 0.5), (0.0, 0.0, math.pi)
        )
        index += 1
        z_value += BUCKET_PITCH

    x_rail = CLEAR_X * 0.5 + 0.28
    for offset, tag in ((-0.16, "A"), (0.16, "B")):
        b.new_mesh(
            f"NORIA_LADDER_RAIL_{tag}",
            lambda bm, offset=offset: common.add_box(
                bm, x_rail - 0.015, x_rail + 0.015, offset - 0.012, offset + 0.012, 0.15, 31.85
            ),
            ladder_mat,
        )
    rung_mesh = bpy.data.meshes.new("NORIA_RUNG_MESH")
    bm = bmesh.new()
    common.add_box(bm, x_rail - 0.012, x_rail + 0.012, -0.16, 0.16, -0.01, 0.01)
    common.finish_mesh(bm, rung_mesh, False)
    rung_mesh.materials.append(ladder_mat)
    z_value = 0.35
    while z_value < 31.7:
        b.instance_of(f"NORIA_RUNG_{int(z_value * 100):04d}", rung_mesh, (0.0, 0.0, z_value))
        z_value += 0.30
    deck_z = 31.55

    def deck(bm):
        common.add_box(bm, 0.22, 1.15, -0.42, 0.42, deck_z, deck_z + 0.03)
        common.add_box(bm, 0.22, 1.15, -0.42, -0.39, deck_z + 0.03, deck_z + 0.85)
        common.add_box(bm, 0.22, 1.15, 0.39, 0.42, deck_z + 0.03, deck_z + 0.85)
        common.add_box(bm, 1.12, 1.15, -0.42, 0.42, deck_z + 0.03, deck_z + 0.85)

    b.new_mesh("NORIA_PLATFORM", deck, ladder_mat)
    return {"collection": kit.name}
