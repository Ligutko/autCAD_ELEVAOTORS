"""Деталь кіта `silo_msvu_220`: силос МСВУ 220.13.В12 з плоским дном.

Геометрія перенесена без змін чисел із прийнятого зрізу SILO-WAVE
(`blender/silo_msvu_220_wave/build_silo_wave.py`, SILO_PASS 2026-09-23).
Тут вона параметризована лише позицією: деталь будується у своїй колекції
з віссю в (0, 0) і підлогою на Z = 0. Розміри деталі світ змінювати не може.

Звідки числа — у `SPEC["provenance"]`. Статус карток усюди `unverified`.
"""

from __future__ import annotations

import math

from . import common

TYPE = "silo_msvu_220"
COLLECTION = "KIT_silo_msvu_220"

DIAMETER_M = 22.0
RADIUS_M = 11.0
TIER_H = 1.152
RING_COUNT = 13
WALL_TOP = 14.976
SPOUT_Z = 21.422
ROOF_DEG = 30.0
ROOF_RISE = RADIUS_M * math.tan(math.radians(ROOF_DEG))
ROOF_PEAK = WALL_TOP + ROOF_RISE
WAVE_PITCH = 0.064
WAVES_PER_RING = 18
WAVE_HEIGHT = 0.012
WAVE_STEPS = 8
CIRCLE_STEPS = 72
FLANGE_WIDTH_M = 0.35
FLANGE_PROTRUSION_M = 0.12
FLANGE_THICK_M = 0.02
HEAD_D_M = 0.12
HEAD_H_M = 0.04
SHANK_D_M = 0.05
SHANK_H_M = 0.03
ROOF_SECTORS = 8
ROOF_EDGE_STEPS = 16
SPOUT_MAJOR_R = 0.7
SPOUT_TUBE_R = 0.045

SPEC = {
    "type": TYPE,
    "tag": "МСВУ 220.13.В12",
    "footprint_radius_m": RADIUS_M,
    "wall_top_m": WALL_TOP,
    "roof_peak_m": ROOF_PEAK,
    "spout_z_m": SPOUT_Z,
    "provenance": {
        "diameter_m": {"value": DIAMETER_M, "from": "каталог + OCR арк. 8/10/12, rec_020dce78"},
        "spout_z_m": {"value": SPOUT_Z, "from": "каталог + OCR «Н=21,422 м»"},
        "tiers": {"value": RING_COUNT, "from": "розрахунок з таблиці Лубнимаша, inbox/reports/lubnymash_220_tiers.md"},
        "tier_height_m": {"value": TIER_H, "from": "каталог Лубнимаша EN, inbox/reports/lubnymash_sheet_roof.md"},
        "wave_pitch_m": {"value": WAVE_PITCH, "from": "каталоги Лубнимаша"},
        "roof_slope_deg": {"value": ROOF_DEG, "from": "каталоги Лубнимаша"},
        "bottom": {"value": "flat", "from": "rec_7f7031e0"},
        "wave_height_m": {"value": WAVE_HEIGHT, "from": "показ, не з каталогу"},
        "flange_bolts": {"value": "52 болти, фланець 0.35 м", "from": "показ, не з паспорта"},
    },
}


def _wave_radius(phase: float) -> float:
    return RADIUS_M - WAVE_HEIGHT * 0.5 * (1.0 - math.cos(phase))


def _ring(bm, z0: float, z1: float) -> None:
    rows_n = WAVES_PER_RING * WAVE_STEPS
    grid = []
    for row_index in range(rows_n + 1):
        along = row_index / rows_n
        z_value = z0 + (z1 - z0) * along
        radius = _wave_radius(2.0 * math.pi * WAVES_PER_RING * along)
        row = []
        for step in range(CIRCLE_STEPS):
            angle = 2.0 * math.pi * step / CIRCLE_STEPS
            row.append(bm.verts.new((radius * math.cos(angle), radius * math.sin(angle), z_value)))
        grid.append(row)
    for row_index in range(rows_n):
        for step in range(CIRCLE_STEPS):
            nxt = (step + 1) % CIRCLE_STEPS
            bm.faces.new(
                (grid[row_index][step], grid[row_index + 1][step], grid[row_index + 1][nxt], grid[row_index][nxt])
            )


def _sector_angles(index: int) -> tuple[float, float]:
    mid = -math.pi / 2.0 + (index - 1) * (2.0 * math.pi / ROOF_SECTORS)
    half = math.pi / ROOF_SECTORS
    gap = 0.5 * 0.04 / RADIUS_M
    return mid - half + gap, mid + half - gap


def build() -> dict:
    """Будує деталь у колекції COLLECTION. Повертає імена ключових об'єктів."""
    import bpy
    from mathutils import Vector

    existing = bpy.data.collections.get(COLLECTION)
    if existing is not None and existing.objects:
        return {"collection": existing.name}
    kit = common.kit_collection(COLLECTION)
    b = common.Builder(kit)

    wall_a = b.material("SiloWallA", (0.78, 0.80, 0.82), 0.42, metallic=0.55)
    wall_b = b.material("SiloWallB", (0.62, 0.66, 0.70), 0.46, metallic=0.5)
    flange_mat = b.material("SiloFlange", (0.18, 0.20, 0.24), 0.38, metallic=0.4)
    head_mat = b.material("SiloBoltHead", (0.05, 0.05, 0.06), 0.28, metallic=0.85)
    shank_mat = b.material("SiloBoltShank", (0.82, 0.78, 0.68), 0.22, metallic=0.9)
    roof_a = b.material("SiloRoofA", (0.55, 0.30, 0.16), 0.48, metallic=0.25)
    roof_b = b.material("SiloRoofB", (0.28, 0.15, 0.09), 0.52, metallic=0.2)
    spout_mat = b.material("SiloSpoutMark", (0.85, 0.55, 0.18), 0.35, metallic=0.2)
    floor_mat = b.material("SiloFloor", (0.78, 0.66, 0.42), 0.75)

    rings = []
    for index in range(RING_COUNT):
        z0 = index * TIER_H
        z1 = WALL_TOP if index == RING_COUNT - 1 else (index + 1) * TIER_H
        rings.append(
            b.new_mesh(
                f"SILO_RING_{index + 1:02d}",
                lambda bm, z0=z0, z1=z1: _ring(bm, z0, z1),
                wall_a if index % 2 == 0 else wall_b,
                smooth=True,
                outward=True,
            )
        )

    outer = RADIUS_M + FLANGE_PROTRUSION_M
    plate_inner = outer - FLANGE_THICK_M
    half = FLANGE_WIDTH_M * 0.5

    def flange(bm):
        common.add_box(bm, RADIUS_M, plate_inner - 0.001, -0.045, 0.045, 0.0, WALL_TOP)
        common.add_box(bm, plate_inner, outer, -half, half, 0.0, WALL_TOP)

    b.new_mesh("SILO_FLANGE", flange, flange_mat, outward=True)

    bolt = 1
    for index in range(RING_COUNT):
        z0 = index * TIER_H
        z1 = WALL_TOP if index == RING_COUNT - 1 else (index + 1) * TIER_H
        low, high = z0 + 0.18, z1 - 0.18
        for y_value, tilt in ((-0.11, -0.55), (0.11, 0.55)):
            direction = Vector((math.cos(tilt), math.sin(tilt), 0.0))
            for fraction in (0.32, 0.68):
                origin = Vector((outer, y_value, low + fraction * (high - low)))
                b.cylinder(f"SILO_BOLT_{bolt:02d}_BODY", origin, direction, SHANK_H_M, SHANK_D_M * 0.5, shank_mat)
                b.cylinder(
                    f"SILO_BOLT_{bolt:02d}", origin + direction * SHANK_H_M, direction, HEAD_H_M, HEAD_D_M * 0.5, head_mat
                )
                bolt += 1

    def floor(bm):
        verts = [
            bm.verts.new((RADIUS_M * math.cos(2 * math.pi * s / 64), RADIUS_M * math.sin(2 * math.pi * s / 64), 0.0))
            for s in range(64)
        ]
        bm.faces.new(verts)

    b.new_mesh("SILO_FLOOR", floor, floor_mat)

    for index in range(1, ROOF_SECTORS + 1):
        a0, a1 = _sector_angles(index)

        def sector(bm, a0=a0, a1=a1):
            rim = [
                bm.verts.new(
                    (
                        RADIUS_M * math.cos(a0 + (a1 - a0) * s / ROOF_EDGE_STEPS),
                        RADIUS_M * math.sin(a0 + (a1 - a0) * s / ROOF_EDGE_STEPS),
                        WALL_TOP,
                    )
                )
                for s in range(ROOF_EDGE_STEPS + 1)
            ]
            apex = bm.verts.new((0.0, 0.0, ROOF_PEAK))
            for s in range(ROOF_EDGE_STEPS):
                bm.faces.new((rim[s], rim[s + 1], apex))

        b.new_mesh(f"SILO_ROOF_{index:02d}", sector, roof_a if index % 2 else roof_b, outward=True)

    def spout(bm):
        major, minor = 32, 8
        rings_ = []
        for s in range(major):
            angle = 2.0 * math.pi * s / major
            ring = []
            for t in range(minor):
                beta = 2.0 * math.pi * t / minor
                radius = SPOUT_MAJOR_R + SPOUT_TUBE_R * math.cos(beta)
                ring.append(
                    bm.verts.new((radius * math.cos(angle), radius * math.sin(angle), SPOUT_Z + SPOUT_TUBE_R * math.sin(beta)))
                )
            rings_.append(ring)
        for s in range(major):
            nxt = (s + 1) % major
            for t in range(minor):
                tn = (t + 1) % minor
                bm.faces.new((rings_[s][t], rings_[nxt][t], rings_[nxt][tn], rings_[s][tn]))

    b.new_mesh("SILO_SPOUT_MARK", spout, spout_mat, smooth=True)
    return {"collection": kit.name, "rings": [r.name for r in rings]}
