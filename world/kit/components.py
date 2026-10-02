"""Parametric IEC foot-mounted motor (IM B3, 4-pole).

Geometry is metres, shaft axis +X, drive end toward +X, feet on z=0, x=0 on the
fan-side housing face. Frame size comes from data/iec_motor_frames.json.
Numbers marked EST in that file (fan-cover length, terminal-box envelope,
nameplate, endshield thickness, fin section) are called out below.
"""

import json
from pathlib import Path

import numpy as np

from . import common as c
from . import steel as st

DATA = Path(__file__).resolve().parent / "data" / "iec_motor_frames.json"

# Estimates. Fan cover and terminal box are not lettered on WEG p.57; see motor_iec.md.
COWL_OF_H = 0.55
BOX_LENGTH_OF_H = 0.55
BOX_WIDTH_OF_H = 0.70
BOX_HEIGHT_OF_H = 0.45
BOX_EMBED = 0.003
ENDSHIELD_OF_H = 0.08
NAMEPLATE_T = 0.0016
# EST standoff of the nameplate off the shell, inside the 3–4 mm brief.
NAMEPLATE_STANDOFF = 0.0035
# Locknut across-flats in gland radii. M20 nut is about 30 mm across 20 mm thread.
GLAND_NUT = 2.5
# EST: fin root/tip and pitch are not lettered. Tip is narrower than the root.
FIN_ROOT_MIN = 0.0022
FIN_TIP_MIN = 0.0014

PARTS = ("body", "fins", "feet", "terminal_box", "fan_cover", "shaft", "endshield_de", "nameplate")


def _table(frames):
    if frames is None:
        frames = json.loads(DATA.read_text(encoding="utf-8"))
    return frames


def _num(row, key):
    return float(row[key]["v"]) / 1000.0


def _std_key(kw, mapping):
    keys = [(float(k), k) for k in mapping]
    return min(keys, key=lambda item: (abs(item[0] - float(kw)), item[0]))[1]


def _snap(a):
    a = np.asarray(a, float)
    a[np.abs(a) < 1e-12] = 0.0
    return a


def _circle(radius, steps):
    ang = np.linspace(0.0, 2.0 * np.pi, steps, endpoint=False)
    return _snap(np.column_stack([radius * np.cos(ang), radius * np.sin(ang)]))


def _as_member(yz):
    """(y, z) offsets to the (u, v) profile steel.member expects along +X."""
    return np.column_stack([-yz[:, 0], yz[:, 1]])


def _shaft_yz(radius, width, g_dim, steps):
    """Shaft section. Keyway on +Z. G is the WEG distance from the keyway bottom to the far side."""
    z_flat = -radius + g_dim
    half = min(width / 2.0, radius * 0.85)
    z_side = float(np.sqrt(max(radius * radius - half * half, 0.0)))
    a0 = float(np.arctan2(z_side, half))
    a1 = float(np.arctan2(z_side, -half))
    ang = list(np.linspace(a0, a1 - 2.0 * np.pi, steps, endpoint=False))
    for extra in (0.0, -np.pi / 2.0, -np.pi):
        if a1 - 2.0 * np.pi < extra < a0:
            ang.append(extra)
    ang = sorted(set(np.round(ang, 8)), reverse=True)
    yz = [[radius * np.cos(a), radius * np.sin(a)] for a in ang]
    yz.append([-half, z_flat])
    yz.append([half, z_flat])
    return _snap(np.array(yz, float))


def _along_x(x0, x1, yz, origin_z):
    prof = _as_member(yz)
    return st.member((x0, 0.0, origin_z), (x1, 0.0, origin_z), prof)


def _tube(x0, x1, radius, origin_z, steps):
    yz = _circle(radius, steps)
    verts, faces = _along_x(x0, x1, yz, origin_z)
    return verts, faces[0]


def _quad(p00, p10, p11, p01):
    return np.array([p00, p10, p11, p01], float), np.array([[0, 1, 2, 3]], np.int32)


def _annulus(x, radius, z, r0, r1, steps):
    a = np.linspace(0.0, 2.0 * np.pi, steps, endpoint=False)
    outer = np.column_stack([np.full(steps, x), radius * 0 + r1 * np.cos(a), z + r1 * np.sin(a)])
    inner = np.column_stack([np.full(steps, x), r0 * np.cos(a), z + r0 * np.sin(a)])
    # y was wrong above: outer used `radius * 0`. Keep a clean pair.
    outer = np.column_stack([np.full(steps, x), r1 * np.cos(a), z + r1 * np.sin(a)])
    verts = np.concatenate([outer, inner])
    return verts, c.grid_faces(2, steps, wrap_cols=True)


def _foot_pad(x0, x1, y0, y1, z0, z1, holes, hole_r, steps):
    """One longitudinal foot. Sole corners and the hole rings sit on z=z0; the holes stay inside the pad."""
    parts = []
    for xa, xb, ya, yb in (
        (x0, x1, y0, y1),
    ):
        parts.append(_quad((xa, ya, z0), (xb, ya, z0), (xb, ya, z1), (xa, ya, z1)))
        parts.append(_quad((xb, yb, z0), (xa, yb, z0), (xa, yb, z1), (xb, yb, z1)))
        parts.append(_quad((xa, yb, z0), (xa, ya, z0), (xa, ya, z1), (xa, yb, z1)))
        parts.append(_quad((xb, ya, z0), (xb, yb, z0), (xb, yb, z1), (xb, ya, z1)))
    margin = 0.004
    spans = [x0]
    for hx, hy in holes:
        spans += [hx - hole_r - margin, hx + hole_r + margin]
    spans.append(x1)
    for xa, xb in zip(spans[0::2], spans[1::2]):
        if xb - xa > 1e-4:
            parts.append(_quad((xa, y0, z1), (xb, y0, z1), (xb, y1, z1), (xa, y1, z1)))
    for hx, hy in holes:
        parts.append(_quad((hx - hole_r - margin, y0, z1), (hx + hole_r + margin, y0, z1),
                           (hx + hole_r + margin, hy - hole_r - margin, z1), (hx - hole_r - margin, hy - hole_r - margin, z1)))
        parts.append(_quad((hx - hole_r - margin, hy + hole_r + margin, z1), (hx + hole_r + margin, hy + hole_r + margin, z1),
                           (hx + hole_r + margin, y1, z1), (hx - hole_r - margin, y1, z1)))
        depth = min(0.0025, (z1 - z0) * 0.34)
        parts.append(_countersink(hx, hy, z1, hole_r, hole_r + margin, depth, steps))
        wall, wall_f = c.cylinder(hole_r, z0, z1 - depth, steps=steps, center=(hx, hy), capped=False)
        parts.append((wall, wall_f))
    return c.merge_parts(parts)


def _countersink(hx, hy, z_top, r_hole, r_face, depth, steps):
    """Spotface: the sole ring of the hole stays on z of the pad, this cone is the top."""
    a = np.linspace(0.0, 2.0 * np.pi, steps, endpoint=False)
    outer = np.column_stack([hx + r_face * np.cos(a), hy + r_face * np.sin(a), np.full(steps, z_top)])
    inner = np.column_stack([hx + r_hole * np.cos(a), hy + r_hole * np.sin(a), np.full(steps, z_top - depth)])
    return np.concatenate([outer, inner]), c.grid_faces(2, steps, wrap_cols=True)


def _gusset(x0, x1, y0, y1, z_base, z_peak):
    xm = (x0 + x1) * 0.5
    v = np.array([
        [x0, y0, z_base], [x1, y0, z_base], [xm, y0, z_peak],
        [x0, y1, z_base], [x1, y1, z_base], [xm, y1, z_peak],
    ], float)
    tri = np.array([[0, 2, 1], [3, 4, 5]], np.int32)
    quad = np.array([[0, 1, 4, 3], [1, 2, 5, 4], [2, 0, 3, 5]], np.int32)
    return v, [tri, quad]


def _hex(across):
    radius = across / np.sqrt(3.0)
    ang = np.linspace(0.0, 2.0 * np.pi, 6, endpoint=False)
    return _snap(np.column_stack([radius * np.cos(ang), radius * np.sin(ang)]))


def _frame_no(frame):
    digits = "".join(ch for ch in str(frame) if ch.isdigit())
    return int(digits or "0")


def _nameplate_size(frame):
    # EST: not lettered on WEG p.57. 63–90: 0.040×0.030 m; 160–225: 0.100×0.060 m.
    # 112 and 132 are the same estimate, linearly between those two.
    n = _frame_no(frame)
    if n <= 90:
        return 0.040, 0.030
    if n >= 160:
        return 0.100, 0.060
    t = (n - 90.0) / 70.0
    return 0.040 + 0.060 * t, 0.030 + 0.030 * t


def _gland_reach(radius):
    return max(0.012, float(radius) * 1.6)


def _fin_count(radius, lod):
    pitch = 0.034 if lod else 0.009
    n = int(round(2.0 * np.pi * radius / pitch))
    n = min(16 if lod else 72, max(8, n))
    n -= n % 4
    return max(8, n)


def _open_x(x0, x1, yz, origin_z):
    verts, faces = _along_x(x0, x1, yz, origin_z)
    return verts, faces[0]


def _frustum_x(x0, x1, r0, r1, origin_z, steps):
    ang = np.linspace(0.0, 2.0 * np.pi, steps, endpoint=False)
    c0 = np.column_stack([np.full(steps, x0), r0 * np.cos(ang), origin_z + r0 * np.sin(ang)])
    c1 = np.column_stack([np.full(steps, x1), r1 * np.cos(ang), origin_z + r1 * np.sin(ang)])
    return np.concatenate([c0, c1]), c.grid_faces(2, steps, wrap_cols=True)


def _disk_x(x, origin_z, radius, steps):
    ang = np.linspace(0.0, 2.0 * np.pi, steps, endpoint=False)
    verts = np.column_stack([np.full(steps, x), radius * np.cos(ang), origin_z + radius * np.sin(ang)])
    return verts, np.arange(steps)[None, :]


def _overlap_box(a, b):
    return not (a[1] <= b[0] or b[1] <= a[0] or a[3] <= b[2] or b[3] <= a[2] or a[5] <= b[4] or b[5] <= a[4])


def _cut_x(x0, x1, cuts):
    segs = [(x0, x1)]
    for a, b in cuts:
        nxt = []
        for s0, s1 in segs:
            if b <= s0 or a >= s1:
                nxt.append((s0, s1))
                continue
            if s0 < a:
                nxt.append((s0, min(s1, a)))
            if s1 > b:
                nxt.append((max(s0, b), s1))
        segs = nxt
    return [(s0, s1) for s0, s1 in segs if s1 - s0 > 0.008]


def _bolt(p0, p1, across, up):
    if np.linalg.norm(np.subtract(p1, p0)) < 0.001 or across < 0.001:
        return None
    return st.member(p0, p1, _hex(across), up=up)


def _rod(p0, p1, radius, steps):
    if np.linalg.norm(np.subtract(p1, p0)) < 0.001 or radius < 0.0004:
        return None
    return st.rod(p0, p1, radius, steps)


def _bbox(verts):
    v = np.asarray(verts, float).reshape(-1, 3)
    return v.min(axis=0), v.max(axis=0)


def _count_faces(faces):
    blocks = faces if isinstance(faces, list) else [faces]
    return int(sum(len(np.asarray(b)) for b in blocks if len(np.asarray(b))))


def iec_motor(kw, poles=4, mount="B3", detail="full", *, frame=None, frames=None, faults=None):
    """IEC squirrel-cage motor. `frame`, `frames` and `faults` inject the check's broken cases.

    Local frame: shaft +X, feet on z=0, x=0 at the non-drive housing face.
    """
    if poles != 4:
        raise ValueError("only 4-pole frames are tabulated")
    if mount != "B3":
        raise ValueError("only IM B3 feet are tabulated")
    if detail not in ("full", "lod"):
        raise ValueError("detail must be full or lod")
    faults = faults or {}
    data = _table(frames)
    key = _std_key(kw, data["kw_to_frame"])
    frame = frame or data["kw_to_frame"][key]["frame"]
    row = data["frames"][frame]

    H, A, B = _num(row, "H"), _num(row, "A"), _num(row, "B")
    C, K, D, E = _num(row, "C"), _num(row, "K"), _num(row, "D"), _num(row, "E")
    L, AC = _num(row, "L"), _num(row, "AC")
    AA, AB, HA = _num(row, "AA"), _num(row, "AB"), _num(row, "HA")
    F, G = _num(row, "F"), _num(row, "G")
    es = _num(row, "ES")
    gland_r = _num(row, "gland_od") / 2.0

    if faults.get("swap_ab"):
        A, B = B, A
    e_len = E * float(faults.get("shaft_scale", 1.0))
    feet_z = float(faults.get("feet_z", 0.0))
    box_dy = float(faults.get("box_dy", 0.0))

    cowl = COWL_OF_H * H
    end_th = min(0.025, max(0.008, ENDSHIELD_OF_H * H))
    shoulder = L - cowl
    body_end = shoulder - end_th
    radius = H - HA
    if radius < 0.02 or body_end < 0.04 or shoulder <= cowl:
        raise ValueError("frame %s does not leave room for a body" % frame)
    fin_r = AC / 2.0
    hole_y = A / 2.0
    de_x = shoulder - C
    nde_x = de_x - B

    lod = detail == "lod"
    # Housing from 48, DE shield / flange / NDE cowl from 32. Shaft was faceted at 20.
    n_body = 12 if lod else 96
    n_cowl = 12 if lod else 64
    n_shaft = 12 if lod else 48
    n_shield = 12 if lod else 64
    n_hole = 8 if lod else 12
    n_bolt = 4 if lod else 6
    n_fin = _fin_count(radius, lod)
    n_gland = 8 if lod else 24
    n_rivet = 8 if lod else 12

    length = BOX_LENGTH_OF_H * H
    width = BOX_WIDTH_OF_H * H
    box_h = BOX_HEIGHT_OF_H * H
    crown = H + radius
    box_z0 = crown - BOX_EMBED
    box_x0 = max(0.01, body_end * 0.42 - length / 2.0)
    box_x1 = box_x0 + length
    box_y0, box_y1 = -width / 2.0 + box_dy, width / 2.0 + box_dy
    plate_len, plate_h = _nameplate_size(frame)
    plate_x = body_end * 0.48
    plate_z = H - plate_h / 2.0
    gland_reach = _gland_reach(gland_r)
    gland_x = box_x0 + (box_x1 - box_x0) * 0.55
    gland_z = box_z0 + box_h * 0.42
    nut_r = gland_r * GLAND_NUT / np.sqrt(3.0)

    obstacles = [
        (nde_x - K / 2.0 - 0.008, de_x + K / 2.0 + 0.008, AB / 2.0 - AA, AB / 2.0, feet_z, feet_z + HA),
        (nde_x - K / 2.0 - 0.008, de_x + K / 2.0 + 0.008, -AB / 2.0, -(AB / 2.0 - AA), feet_z, feet_z + HA),
        (box_x0 - 0.004, box_x1 + 0.004, box_y0 - 0.004, box_y1 + 0.004, box_z0, box_z0 + box_h + 0.006),
        (plate_x - plate_len / 2.0 - 0.004, plate_x + plate_len / 2.0 + 0.004,
         radius - 0.002, radius + 0.012, plate_z - 0.003, plate_z + plate_h + 0.003),
        (gland_x - nut_r - 0.002, gland_x + nut_r + 0.002,
         box_y1 - 0.002, box_y1 + gland_reach + 0.003,
         gland_z - nut_r - 0.002, gland_z + nut_r + 0.002),
    ]
    eye = None
    if _frame_no(frame) >= 132:
        scale = H / 0.132
        eye_r = 0.013 * scale + 0.0022 * scale
        eye_x = min(max(0.03, box_x0 * 0.45), box_x0 - eye_r - 0.008)
        if eye_x > eye_r + 0.012:
            eye = (eye_x, scale, crown)
            obstacles.append((eye_x - eye_r - 0.003, eye_x + eye_r + 0.003, -0.008, 0.008, crown - 0.01, crown + 0.06 * scale))

    body = _along_x(0.0, body_end, _circle(radius, n_body), H)
    if eye is not None:
        body = c.merge_parts([body, _eyebolt(eye[0], eye[2], eye[1], 6 if lod else 8)])

    fins = _fins(radius, fin_r, H, 0.012, body_end - 0.012, n_fin, obstacles)
    feet = _feet(nde_x, de_x, hole_y, K, AA, AB, HA, feet_z, n_hole)
    box = _terminal_box_h(radius, H, box_x0, box_x1, box_y0, box_y1, box_z0, box_h, gland_r, n_gland)
    cover = _fan_cover(-cowl, radius, fin_r, H, n_cowl, lod)
    shaft = _shaft(shoulder, e_len, D / 2.0, F, G, es, H, n_shaft)
    shield = _endshield(body_end, shoulder, radius, H, D / 2.0, K, n_shield, n_bolt)
    plate = _nameplate(radius, H, plate_x, plate_len, plate_h, plate_z, fin_r, n_rivet)

    built = {
        "body": body,
        "fins": fins,
        "feet": feet,
        "terminal_box": box,
        "fan_cover": cover,
        "shaft": shaft,
        "endshield_de": shield,
        "nameplate": plate,
    }
    all_v = np.concatenate([np.asarray(v, float).reshape(-1, 3) for v, _ in built.values()])
    lo, hi = _bbox(all_v)
    part_dims = {}
    n_verts = 0
    n_faces = 0
    for name, (verts, faces) in built.items():
        p0, p1 = _bbox(verts)
        faces_n = _count_faces(faces)
        part_dims[name] = {
            "min": [float(x) for x in p0],
            "max": [float(x) for x in p1],
            "verts": int(len(verts)),
            "faces": faces_n,
        }
        n_verts += int(len(verts))
        n_faces += faces_n
    # reported letters are the frame row, in metres, before a check fault moves the mesh
    catalog = data["frames"][frame]
    dims = {
        "frame": frame,
        "kw": float(kw),
        "std_kw": float(key),
        "H": _num(catalog, "H"),
        "A": _num(catalog, "A"),
        "B": _num(catalog, "B"),
        "C": _num(catalog, "C"),
        "K": _num(catalog, "K"),
        "D": _num(catalog, "D"),
        "E": _num(catalog, "E"),
        "L": _num(catalog, "L"),
        "bbox": {"min": [float(x) for x in lo], "max": [float(x) for x in hi]},
        "verts": n_verts,
        "faces": n_faces,
        "parts": part_dims,
    }
    return {"parts": built, "dims": dims}


def _fin_profile(radius):
    root_t = min(0.0055, max(FIN_ROOT_MIN, 0.020 * radius))
    tip_t = max(FIN_TIP_MIN, root_t * 0.38)
    return root_t, tip_t


def _fin_aabb(ang, x0, x1, axis_z, r_in, r_out, half_t):
    radial = np.array([np.cos(ang), np.sin(ang)])
    tang = np.array([-np.sin(ang), np.cos(ang)])
    pts = [radial * r + tang * s for r in (r_in, r_out) for s in (-half_t, half_t)]
    pts = np.array(pts)
    return (x0, x1, float(pts[:, 0].min()), float(pts[:, 0].max()),
            axis_z + float(pts[:, 1].min()), axis_z + float(pts[:, 1].max()))


def _fins(radius, fin_r, axis_z, x0, x1, count, obstacles):
    if fin_r <= radius + 0.002:
        return _tube(x0, x1, radius, axis_z, 8)
    height = fin_r - radius + 0.002
    r_in = radius - 0.001
    r_out = r_in + height
    root_t, tip_t = _fin_profile(radius)
    prof = np.array([[-root_t / 2.0, -height / 2.0], [root_t / 2.0, -height / 2.0],
                     [tip_t / 2.0, height / 2.0], [-tip_t / 2.0, height / 2.0]])
    mid = (r_in + r_out) / 2.0
    raw = np.linspace(0.0, 2.0 * np.pi, count, endpoint=False)
    angles = sorted(set(np.round(np.concatenate([raw, [0.0, np.pi / 2.0, np.pi]]), 8)))
    parts = []
    for ang in angles:
        box = _fin_aabb(ang, x0, x1, axis_z, r_in, r_out, root_t / 2.0)
        if box[4] < 0.001:
            continue
        cuts = []
        for obs in obstacles:
            if _overlap_box(box, obs):
                cuts.append((obs[0] - 0.003, obs[1] + 0.003))
        radial = np.array([0.0, np.cos(ang), np.sin(ang)])
        centre = np.array([0.0, 0.0, axis_z]) + radial * mid
        for s0, s1 in _cut_x(x0, x1, cuts):
            verts, faces = st.member(centre + np.array([s0, 0.0, 0.0]), centre + np.array([s1, 0.0, 0.0]), prof, up=radial)
            if len(verts) == 0 or float(verts[:, 2].min()) < 0.001:
                continue
            parts.append((verts, faces))
    if not parts:
        raise ValueError("no cooling fin survived the foot clearance")
    return c.merge_parts(parts)


def _feet(nde_x, de_x, hole_y, k_diam, aa, ab, ha, z0, steps):
    hole_r = k_diam / 2.0
    overhang = hole_r + 0.008
    x0, x1 = nde_x - overhang, de_x + overhang
    outer, inner = ab / 2.0, ab / 2.0 - aa
    z1 = z0 + ha
    holes_r = ((nde_x, hole_y), (de_x, hole_y))
    holes_l = ((nde_x, -hole_y), (de_x, -hole_y))
    right = _foot_pad(x0, x1, inner, outer, z0, z1, holes_r, hole_r, steps)
    left = _foot_pad(x0, x1, -outer, -inner, z0, z1, holes_l, hole_r, steps)
    parts = [right, left]
    # Rib on the pad, inboard of the K holes, rising toward the shell. Sole stays the pad bottom.
    thick = max(0.0035, min(0.006, hole_r * 0.7))
    rise = max(0.012, min(0.055, ha * 2.2))
    y_face = hole_y - hole_r - 0.004
    if de_x - nde_x > 0.02 and y_face - thick > 0.006:
        parts.append(_gusset(nde_x, de_x, y_face - thick, y_face, z1, z1 + rise))
        parts.append(_gusset(nde_x, de_x, -y_face, -y_face + thick, z1, z1 + rise))
    return c.merge_parts(parts)


def _terminal_box(radius, axis_z, body_end, dy, gland_r, steps):
    # axis_z is the shaft-centre height H. The box scales with H, not with the body radius.
    length = BOX_LENGTH_OF_H * axis_z
    width = BOX_WIDTH_OF_H * axis_z
    height = BOX_HEIGHT_OF_H * axis_z
    crown = axis_z + radius
    z0 = crown - BOX_EMBED
    x0 = max(0.01, body_end * 0.42 - length / 2.0)
    x1 = x0 + length
    y0, y1 = -width / 2.0 + dy, width / 2.0 + dy
    return _terminal_box_h(radius, axis_z, x0, x1, y0, y1, z0, height, gland_r, steps)


def _gland(x, y_face, z, radius, steps):
    """Cable gland: cylinder, hex locknut, short sleeve. Outer end stays at y_face + reach.

    The sleeve is capped, so with no cable it reads as a blanking plug.
    """
    reach = _gland_reach(radius)
    nut_l = max(0.003, 0.22 * reach)
    across = radius * GLAND_NUT
    barrel_r = radius * 0.78
    sleeve_r = radius * 0.46
    y_nut1 = y_face + nut_l
    y_sleeve0 = y_face + reach * 0.62
    y_end = y_face + reach
    parts = []
    nut = _bolt((x, y_face, z), (x, y_nut1, z), across, (0.0, 0.0, 1.0))
    barrel = _rod((x, y_face, z), (x, y_sleeve0 + reach * 0.08, z), barrel_r, steps)
    sleeve = _rod((x, y_sleeve0, z), (x, y_end, z), sleeve_r, steps)
    for piece in (nut, barrel, sleeve):
        if piece is not None:
            parts.append(piece)
    return parts


def _terminal_box_h(radius, axis_z, x0, x1, y0, y1, z0, height, gland_r, steps):
    # Skirt is the adapter flange. Lid overhang and four corner bolts stay inside the old top.
    flange_h = min(height * 0.22, max(0.004, 0.035 * axis_z))
    top = z0 + height + 0.003
    head_h = min(0.008, max(0.0045, 0.045 * axis_z))
    parts = [
        c.box((x0 - 0.002, y0 - 0.002, z0), (x1 + 0.002, y1 + 0.002, z0 + flange_h)),
        c.box((x0, y0, z0), (x1, y1, z0 + height)),
        c.box((x0 - 0.002, y0 - 0.002, z0 + height), (x1 + 0.002, y1 + 0.002, top)),
    ]
    inset = max(0.004, head_h)
    across = head_h * 1.85
    for cx, cy in ((x0 + inset, y0 + inset), (x0 + inset, y1 - inset), (x1 - inset, y0 + inset), (x1 - inset, y1 - inset)):
        bolt = _bolt((cx, cy, top - head_h), (cx, cy, top), across, (1.0, 0.0, 0.0))
        if bolt is not None:
            parts.append(bolt)
    zg = z0 + height * 0.42
    xg = x0 + (x1 - x0) * 0.55
    parts.extend(_gland(xg, y1, zg, gland_r, steps))
    return c.merge_parts(parts)


def _ring(x0, x1, origin_z, r0, r1, steps):
    return [
        _tube(x0, x1, r1, origin_z, steps),
        _tube(x0, x1, r0, origin_z, steps),
        _annulus(x0, 0.0, origin_z, r0, r1, steps),
        _annulus(x1, 0.0, origin_z, r0, r1, steps),
    ]


def _fan_cover(x_outer, radius, fin_r, axis_z, steps, lod=False):
    """NDE cowl. Grille is radial slots plus a stiffening ring; four bolts sit on that face."""
    cowl_r = min(radius + 0.006, fin_r - 0.002)
    depth = 0.004
    r_outer = cowl_r * 0.96
    r_slot_o = cowl_r * 0.78
    r_slot_i = cowl_r * 0.36
    r_hub = cowl_r * 0.18
    parts = [_tube(x_outer, 0.0, cowl_r, axis_z, steps)]
    parts.extend(_ring(x_outer, x_outer + depth, axis_z, r_slot_o, r_outer, steps))
    parts.extend(_ring(x_outer, x_outer + depth, axis_z, r_hub, r_slot_i, steps))
    n_rib = 6 if lod else 12
    rib_w = max(0.0022, cowl_r * 0.035)
    half_w, half_d = rib_w / 2.0, depth / 2.0
    prof = np.array([[-half_w, -half_d], [half_w, -half_d], [half_w, half_d], [-half_w, half_d]])
    x_mid = x_outer + half_d
    for i in range(n_rib):
        ang = 2.0 * np.pi * i / n_rib
        d0, d1 = r_slot_i - 0.001, r_slot_o + 0.001
        p0 = np.array([x_mid, d0 * np.cos(ang), axis_z + d0 * np.sin(ang)])
        p1 = np.array([x_mid, d1 * np.cos(ang), axis_z + d1 * np.sin(ang)])
        parts.append(st.member(p0, p1, prof, up=(1.0, 0.0, 0.0)))
    across = max(0.005, min(0.012, cowl_r * 0.14))
    vertex_r = across / np.sqrt(3.0)
    center_r = min(cowl_r * 0.80, cowl_r - vertex_r - 0.001)
    head = 0.004
    for i in range(4):
        ang = np.pi / 4.0 + i * np.pi / 2.0
        centre = np.array([0.0, center_r * np.cos(ang), axis_z + center_r * np.sin(ang)])
        if centre[2] - vertex_r < 0.004:
            continue
        bolt = _bolt(centre + np.array([x_outer, 0.0, 0.0]), centre + np.array([x_outer + head, 0.0, 0.0]), across, (0.0, 0.0, 1.0))
        if bolt is not None:
            parts.append(bolt)
    return c.merge_parts(parts)


def _shaft(shoulder, e_len, radius, width, g_dim, es, axis_z, steps):
    """Key is the square bar of side F sitting on the G flat. Centre hole is EST (not on WEG p.57)."""
    steps = steps - steps % 4
    inserted = 0.15 * e_len
    key_len = min(es, 0.85 * e_len)
    round_yz = _circle(radius, steps)
    keyed = _shaft_yz(radius, width, g_dim, max(8, steps - 4))
    x_key1 = shoulder + key_len
    x_tip = shoulder + e_len
    tail = x_tip - x_key1
    chamfer = min(0.008, max(0.001, 0.16 * radius), 0.35 * max(tail, 0.0))
    chamfer = min(chamfer, max(0.0, tail - 0.0015))
    parts = [
        _along_x(shoulder - inserted, shoulder, round_yz, axis_z),
        _along_x(shoulder, x_key1, keyed, axis_z),
    ]
    if chamfer > 0.0005 and tail - chamfer > 0.001:
        x_chamfer = x_tip - chamfer
        parts.append(_along_x(x_key1, x_chamfer, round_yz, axis_z))
        r_tip = radius * 0.70
        parts.append(_frustum_x(x_chamfer, x_tip, radius, r_tip, axis_z, steps))
        # EST centre hole, about 0.16 of the shaft radius, drilled in the chamfer face.
        hole_r = min(radius * 0.16, r_tip * 0.45)
        depth = min(0.005, max(0.0008, chamfer * 0.85), x_tip - x_key1 - 0.001)
        if hole_r > 0.0004 and depth > 0.0005 and r_tip - hole_r > 0.0004:
            parts.append(_frustum_x(x_tip - depth, x_tip, hole_r, hole_r, axis_z, max(8, steps // 2)))
            parts.append(_annulus(x_tip, 0.0, axis_z, hole_r, r_tip, steps))
            parts.append(_disk_x(x_tip - depth, axis_z, hole_r, max(8, steps // 2)))
    else:
        parts.append(_along_x(x_key1, x_tip, round_yz, axis_z))
    inset = min(0.001, key_len * 0.08)
    if key_len - 2.0 * inset > 0.002 and width > 0.0008:
        z_flat = axis_z - radius + g_dim
        parts.append(c.box((shoulder + inset, -width / 2.0, z_flat), (x_key1 - inset, width / 2.0, z_flat + width)))
    return c.merge_parts(parts)


def _endshield(body_end, shoulder, radius, axis_z, shaft_r, k_diam, steps, n_bolt):
    """DE flange: rim, bolt circle, shaft-seal collar. Nothing passes x = shoulder (letter E)."""
    flange_r = radius + 0.006
    thick = max(0.004, shoulder - body_end)
    head_len = min(0.007, max(0.004, thick * 0.34))
    face = shoulder - head_len
    seal_r = max(shaft_r * 1.65, 0.008)
    hub = max(seal_r * 1.35, flange_r * 0.34)
    lip = min(0.0035, head_len * 0.6)
    n_seal = steps
    parts = [
        _tube(body_end, face, flange_r, axis_z, steps),
        _annulus(face - lip, 0.0, axis_z, hub, flange_r - 0.004, steps),
        _annulus(face, 0.0, axis_z, flange_r - 0.004, flange_r, steps),
        _tube(face - lip, face, flange_r - 0.004, axis_z, steps),
        _annulus(body_end, 0.0, axis_z, shaft_r * 1.15, flange_r, steps),
        _tube(face, shoulder, seal_r, axis_z, n_seal),
        _annulus(shoulder, 0.0, axis_z, shaft_r * 1.12, seal_r, n_seal),
    ]
    across = max(0.005, min(0.012, 0.55 * k_diam))
    bolt_r = (hub + flange_r) * 0.5
    for i in range(n_bolt):
        ang = 2.0 * np.pi * i / n_bolt + np.pi / n_bolt
        centre = np.array([0.0, bolt_r * np.cos(ang), axis_z + bolt_r * np.sin(ang)])
        if centre[2] < 0.006:
            continue
        bolt = _bolt(centre + np.array([face, 0.0, 0.0]), centre + np.array([shoulder, 0.0, 0.0]), across, (0.0, 0.0, 1.0))
        if bolt is not None:
            parts.append(bolt)
    return c.merge_parts(parts)


def _nameplate(radius, axis_z, x, length, height, z, fin_r, steps):
    """Blank plate on the +Y shell, stood off the surface, four corner rivets, no legend."""
    y0 = radius + NAMEPLATE_STANDOFF
    y1 = y0 + NAMEPLATE_T
    x0, x1 = x - length / 2.0, x + length / 2.0
    z0, z1 = z, z + height
    parts = [c.box((x0, y0, z0), (x1, y1, z1))]
    inset = min(0.007, 0.16 * min(length, height))
    rivet_r = min(0.0024, max(0.0012, 0.35 * inset))
    head_r = rivet_r * 1.65
    # Longer than the rod's 1 mm reject, so the four heads survive.
    head_h = 0.0012
    proud = y1 + head_h <= fin_r - 0.00015
    for cx, cz in (
        (x0 + inset, z0 + inset),
        (x0 + inset, z1 - inset),
        (x1 - inset, z0 + inset),
        (x1 - inset, z1 - inset),
    ):
        dz = cz - axis_z
        shell = float(np.sqrt(max(radius * radius - dz * dz, 0.0)))
        y_shell = min(shell + 0.0003, y0 - 0.0004)
        shank = _rod((cx, y_shell, cz), (cx, y0, cz), rivet_r, steps)
        if shank is not None:
            parts.append(shank)
        if proud:
            head = _rod((cx, y1, cz), (cx, y1 + head_h, cz), head_r, steps)
            if head is not None:
                parts.append(head)
    return c.merge_parts(parts)


def _eyebolt(x, crown, scale, n_seg):
    """Lifting eye on frames from 132. Ring in the XZ plane, shank into the crown."""
    shank_r = 0.0045 * scale
    eye_r = 0.013 * scale
    tube_r = 0.0022 * scale
    shank_h = 0.016 * scale
    across = 0.011 * scale
    z_nut = crown + shank_h * 0.45
    z_top = crown + shank_h
    parts = []
    shank = _rod((x, 0.0, crown - 0.004 * scale), (x, 0.0, z_top), shank_r, 8)
    nut = _bolt((x, 0.0, crown), (x, 0.0, z_nut), across, (1.0, 0.0, 0.0))
    for piece in (shank, nut):
        if piece is not None:
            parts.append(piece)
    cz = z_top + eye_r
    for i in range(n_seg):
        a0 = 2.0 * np.pi * i / n_seg
        a1 = 2.0 * np.pi * (i + 1) / n_seg
        p0 = (x + eye_r * np.sin(a0), 0.0, cz + eye_r * np.cos(a0))
        p1 = (x + eye_r * np.sin(a1), 0.0, cz + eye_r * np.cos(a1))
        seg = _rod(p0, p1, tube_r, 4)
        if seg is not None:
            parts.append(seg)
    return c.merge_parts(parts)


# ====================================================================== radial dust fan
#
# VR 280-46 No.5, execution 1 (Ventinform pasport). Numbers live in data/radial_fan.json (mm).
# Local frame: wheel axis = +X, the inlet looks to -X, the motor sits on +X, x=0 is the housing
# mid plane (the pasport "base plane"), frame underside z=0, axis at z=h. Right rotation Pr means
# the wheel turns clockwise seen from the motor side (from +X); the housing grows clockwise and the
# outlet leaves on the -Y side going up (outlet_deg=0). Other positions turn the housing clockwise.

FAN_DATA = Path(__file__).resolve().parent / "data" / "radial_fan.json"
FAN_POSITIONS = (0, 45, 90, 135, 270, 315)
FAN_PARTS = ("volute", "inlet", "outlet", "frame", "motor", "bolts", "wheel", "stool")
FAN_SIZE = 5


def _fan_table(data):
    if data is None:
        data = json.loads(FAN_DATA.read_text(encoding="utf-8"))
    return data


def _fv(table, *path):
    node = table
    for key in path:
        node = node[key]
    return float(node["v"]) / 1000.0


def _spiral_r(theta_deg, r0, k, dip=0.0):
    """Archimedean housing radius r0 + k*theta at the angle theta (deg, clockwise from the top)."""
    th = np.asarray(theta_deg, float)
    r = r0 + k * th
    if dip:
        bump = np.where((th > 105.0) & (th < 122.0), np.sin(np.pi * (th - 105.0) / 17.0) ** 2, 0.0)
        r = r - dip * bump
    return r


def _fit_spiral(right, bottom, end):
    """r0, k of r = r0 + k*theta so the housing reaches `right` (m) sideways, `bottom` down and `end` at 270 deg.

    The pasport b and the housing-position tables are reaches (extents), not radii at fixed angles, so the
    three numbers are matched as extents by a two-parameter least squares.
    """
    th = np.linspace(0.0, 270.0, 2701)
    s, cth = np.sin(np.radians(th)), np.cos(np.radians(th))

    def extents(p):
        r = p[0] + p[1] * th
        return np.array([np.max(r * s), np.max(-r * cth), r[-1]])

    want = np.array([right, bottom, end])
    p = np.array([end - 270.0 * (end - right) / 180.0, (end - right) / 180.0])
    for _ in range(12):
        f = extents(p) - want
        jac = np.column_stack([(extents(p + [1e-6, 0]) - extents(p)) / 1e-6, (extents(p + [0, 1e-6]) - extents(p)) / 1e-6])
        p = p - np.linalg.lstsq(jac, f, rcond=None)[0]
    return float(p[0]), float(p[1])


def _yz_rot(yz, deg):
    """Clockwise turn seen from +X (y right, z up)."""
    a = np.radians(deg)
    ca, sa = np.cos(a), np.sin(a)
    yz = np.asarray(yz, float)
    return np.column_stack([yz[:, 0] * ca + yz[:, 1] * sa, -yz[:, 0] * sa + yz[:, 1] * ca])


def _cross2(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _seg_hit(p, q, a, b):
    d1, d2 = _cross2(p, q, a), _cross2(p, q, b)
    d3, d4 = _cross2(a, b, p), _cross2(a, b, q)
    return d1 * d2 < -1e-18 and d3 * d4 < -1e-18


def _in_tri(p, a, b, c):
    return _cross2(a, b, p) >= -1e-15 and _cross2(b, c, p) >= -1e-15 and _cross2(c, a, p) >= -1e-15


def _earclip(pts):
    """Triangles (i, j, k) of a counter-clockwise polygon; duplicated bridge vertices are allowed."""
    pts = [tuple(p) for p in pts]
    idx = list(range(len(pts)))
    tris = []
    guard = 0
    while len(idx) > 3 and guard < 4 * len(pts) ** 2:
        guard += 1
        m = len(idx)
        cut = None
        for k in range(m):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % m]
            a, b, d = pts[i0], pts[i1], pts[i2]
            if _cross2(a, b, d) <= 1e-14:
                continue
            if all(j in (i0, i1, i2) or pts[j] in (a, b, d) or not _in_tri(pts[j], a, b, d) for j in idx):
                cut = k
                tris.append((i0, i1, i2))
                break
        if cut is None:
            flat = [abs(_cross2(pts[idx[k - 1]], pts[idx[k]], pts[idx[(k + 1) % m]])) for k in range(m)]
            cut = int(np.argmin(flat))
        del idx[cut]
    if len(idx) == 3 and _cross2(pts[idx[0]], pts[idx[1]], pts[idx[2]]) > 1e-14:
        tris.append(tuple(idx))
    return tris


def _bridge(outer, hole):
    """Join a clockwise hole to a counter-clockwise outline by a zero-width slit."""
    outer = [tuple(p) for p in outer]
    hole = [tuple(p) for p in hole]
    m = max(range(len(hole)), key=lambda i: hole[i][0])
    order = sorted(range(len(outer)), key=lambda j: (outer[j][0] - hole[m][0]) ** 2 + (outer[j][1] - hole[m][1]) ** 2)
    for j in order:
        ok = True
        for i in range(len(outer)):
            if j in (i, (i + 1) % len(outer)):
                continue
            if _seg_hit(hole[m], outer[j], outer[i], outer[(i + 1) % len(outer)]):
                ok = False
                break
        if ok:
            break
    ring = hole[m:] + hole[:m] + [hole[m]]
    return outer[:j + 1] + ring + [outer[j]] + outer[j + 1:]


def _plate_x(outline, x0, x1, hole_r=0.0, hole_steps=48):
    """Slab with the outline (y, z) and an optional round hole around the axis, between x0 and x1."""
    outline = np.asarray(outline, float)
    if _poly_area(outline) < 0:
        outline = outline[::-1]
    loops = [outline]
    merged = [tuple(p) for p in outline]
    if hole_r > 0:
        a = np.linspace(0.0, -2.0 * np.pi, hole_steps, endpoint=False)
        hole = np.column_stack([hole_r * np.cos(a), hole_r * np.sin(a)])
        loops.append(hole)
        merged = _bridge(outline, hole)
    tris = _earclip(merged)
    n = len(merged)
    m = np.asarray(merged, float)
    v = [np.column_stack([np.full(n, x0), m]), np.column_stack([np.full(n, x1), m])]
    f_top = np.array([[a + n, b + n, d + n] for a, b, d in tris], np.int64)
    f_bot = np.array([[d, b, a] for a, b, d in tris], np.int64)
    parts = [(np.concatenate(v), [f_top, f_bot])]
    for loop in loops:
        k = len(loop)
        ring = np.concatenate([np.column_stack([np.full(k, x0), loop]), np.column_stack([np.full(k, x1), loop])])
        parts.append((ring, c.grid_faces(2, k, wrap_cols=True)))
    return c.merge_parts(parts)


def _poly_area(p):
    p = np.asarray(p, float)
    return 0.5 * float(np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]))


def _sweep_yz(path, x0, x1, t, sign):
    """Strip x0..x1 along an open (y, z) path, thickness t to the right of travel (sign=+1) or the left (-1)."""
    path = np.asarray(path, float)
    d = np.gradient(path, axis=0)
    d /= np.linalg.norm(d, axis=1)[:, None]
    n = np.column_stack([d[:, 1], -d[:, 0]]) * sign
    q = path + n * t
    k = len(path)
    ring = np.stack([
        np.column_stack([np.full(k, x0), path]), np.column_stack([np.full(k, x1), path]),
        np.column_stack([np.full(k, x1), q]), np.column_stack([np.full(k, x0), q]),
    ], axis=1).reshape(-1, 3)
    faces = [c.grid_faces(k, 4, wrap_cols=True), np.array([[3, 2, 1, 0]]), np.array([[4 * (k - 1) + i for i in range(4)]])]
    return ring, faces


def _shell_x(x0, x1, r0, r1, t, steps):
    """Thin conical/cylindrical shell (outer radius r0 at x0 and r1 at x1, wall t), open ends closed by rings."""
    ang = np.linspace(0.0, 2.0 * np.pi, steps, endpoint=False)

    def ring(x, r):
        return np.column_stack([np.full(steps, x), r * np.cos(ang), r * np.sin(ang)])

    v = np.concatenate([ring(x0, r0), ring(x1, r1), ring(x0, r0 - t), ring(x1, r1 - t)])
    f_out = c.grid_faces(2, steps, wrap_cols=True)
    f_in = c.grid_faces(2, steps, wrap_cols=True, offset=2 * steps)[:, ::-1]
    cap0 = np.array([[i, (i + 1) % steps, 2 * steps + (i + 1) % steps, 2 * steps + i] for i in range(steps)])
    cap1 = np.array([[steps + (i + 1) % steps, steps + i, 3 * steps + i, 3 * steps + (i + 1) % steps] for i in range(steps)])
    return v, [f_out, f_in, cap0, cap1]


def _ring_x(x0, x1, r_in, r_out, steps):
    return _shell_x(x0, x1, r_out, r_out, r_out - r_in, steps)


def _fan_bolt(seat, tip, across, shank_r, nut_gap, steps):
    """Hex bolt: the head ends at `seat`, the shank runs to `tip`, a hex nut sits `nut_gap` past the seat (None: no nut)."""
    seat, tip = np.asarray(seat, float), np.asarray(tip, float)
    unit = (tip - seat) / float(np.linalg.norm(tip - seat))
    up = (0.0, 0.0, 1.0) if abs(unit[2]) < 0.9 else (1.0, 0.0, 0.0)
    head_h = 0.55 * across
    parts = [_bolt(seat - unit * head_h, seat, across, up), _rod(seat - unit * head_h * 0.5, tip, shank_r, steps)]
    if nut_gap is not None:
        parts.append(_bolt(seat + unit * nut_gap, seat + unit * (nut_gap + 0.8 * across), across, up))
    return [p for p in parts if p is not None]


def _fan_outline(table, faults):
    """Housing outline for hand R, outlet 0, in (y, z) about the axis: spiral law and neck lines."""
    A, A1, B, b, H = (_fv(table, "housing", "A"), _fv(table, "outlet", "A1"), _fv(table, "housing", "B"),
                      _fv(table, "housing", "b"), _fv(table, "housing", "H"))
    r0, k = _fit_spiral(_fv(table, "housing", "r90"), _fv(table, "housing", "r180"), _fv(table, "housing", "r270"))
    flange_t = _fv(table, "outlet", "flange_t")
    y_lo = -(B - b)
    y_c = y_lo + A1 / 2.0
    y_in = y_c + A / 2.0
    dip = float(faults.get("spiral_dip", 0.0))
    scale = float(faults.get("housing_scale", 1.0))
    # Tongue: where the spiral meets the inner neck wall.
    lo, hi = -80.0, -10.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        f = float(_spiral_r(mid, r0, k)) * np.sin(np.radians(mid)) - y_in
        lo, hi = (mid, hi) if f < 0 else (lo, mid)
    return {"r0": r0, "k": k, "dip": dip, "scale": scale, "theta_t": 0.5 * (lo + hi), "y_lo": y_lo, "y_c": y_c,
            "y_in": y_in, "z_neck": H - flange_t, "H": H, "A": A, "A1": A1,
            "A2": _fv(table, "outlet", "A2"), "flange_t": flange_t}


def _mirror_y(verts, faces):
    v = np.asarray(verts, float).copy()
    v[:, 1] = -v[:, 1]
    blocks = faces if isinstance(faces, list) else [faces]
    return v, [np.asarray(f)[:, ::-1] for f in blocks if len(f)]


def radial_fan(kw, size=None, hand="R", outlet_deg=0, *, detail="full", data=None, motor_table=None, faults=None):
    """Radial dust fan VR 280-46 No.5, execution 1: housing, nozzle, outlet, frame, IEC motor on one shaft.

    Returns {"parts": {name: (verts, faces)}, "dims": {...}, "motor_parts": {...}}; metres, local frame in the comment above.
    `data`, `motor_table` and `faults` inject the check's broken cases.
    """
    if size not in (None, FAN_SIZE):
        raise ValueError("only size %d is tabulated" % FAN_SIZE)
    if hand not in ("R", "L"):
        raise ValueError("hand must be R or L")
    if outlet_deg not in FAN_POSITIONS:
        raise ValueError("outlet_deg must be one of %s" % (FAN_POSITIONS,))
    if detail not in ("full", "lod"):
        raise ValueError("detail must be full or lod")
    faults = faults or {}
    table = _fan_table(data)
    lod = detail == "lod"
    n_arc = 40 if lod else 120
    n_ring = 24 if lod else 64
    n_small = 8 if lod else 16

    axis_z = _fv(table, "frame", "h")
    w = _fv(table, "housing", "axial_width") * float(faults.get("housing_w_scale", 1.0))
    t = _fv(table, "housing", "sheet_t")
    wheel_r = _fv(table, "wheel_d") / 2.0
    inlet_od, inlet_flange_od = _fv(table, "inlet", "D"), _fv(table, "inlet", "D1")
    inlet_l = _fv(table, "inlet", "l")
    inlet_t = _fv(table, "inlet", "flange_t")
    throat_r = _fv(table, "inlet", "throat_d") / 2.0
    total_len = _fv(table, "length")
    o = _fan_outline(table, faults)
    sc = o["scale"]
    mirror = hand == "L"

    def place(verts, faces, rot=True):
        v = np.asarray(verts, float).reshape(-1, 3).copy()
        if rot and outlet_deg:
            v[:, 1:] = _yz_rot(v[:, 1:], outlet_deg)
        blocks = faces
        if mirror:
            v[:, 1] = -v[:, 1]
            blocks = [np.asarray(f)[:, ::-1] for f in (faces if isinstance(faces, list) else [faces])]
        v[:, 2] += axis_z
        return v, blocks

    def finish(piece, rot=True):
        return place(piece[0], piece[1], rot)

    # ---------------- housing: spiral band, side plates, neck walls, flange
    th = np.linspace(o["theta_t"], 270.0, n_arc)
    rr = _spiral_r(th, o["r0"], o["k"], o["dip"]) * sc
    spiral = np.column_stack([rr * np.sin(np.radians(th)), rr * np.cos(np.radians(th))])
    z_neck = o["z_neck"]
    y_end = float(spiral[-1, 0])
    outer_wall = np.array([[y_end, 0.0], [y_end, z_neck]])
    inner_wall = np.array([spiral[0], [spiral[0, 0], z_neck]])

    band = _sweep_yz(spiral, -w / 2.0, w / 2.0, t, +1)
    outline = np.vstack([spiral, [[y_end, z_neck], [spiral[0, 0], z_neck]]])
    front = _plate_x(outline, -w / 2.0, -w / 2.0 + t, throat_r, n_ring)
    back_hole = _fv(table, "stool", "outer_d") / 2.0 - 0.005
    back = _plate_x(outline, w / 2.0 - t, w / 2.0, back_hole, n_ring)
    volute = c.merge_parts([finish(band), finish(front), finish(back)])

    # ---------------- outlet: neck walls and flange ring
    neck_w = _sweep_yz(outer_wall, -w / 2.0, w / 2.0, t, +1)
    neck_n = _sweep_yz(inner_wall, -w / 2.0, w / 2.0, t, -1)
    fl_t = o["flange_t"]
    fscale = float(faults.get("outlet_flange_scale", 1.0))
    y0f, y1f = o["y_lo"], o["y_lo"] + o["A1"] * fscale
    xf = o["A2"] / 2.0 * fscale
    ring_in_y = (y_end, spiral[0, 0])
    xin = w / 2.0
    z0f, z1f = o["H"] - fl_t, o["H"]
    bars = [
        c.box((-xf, y0f, z0f), (xf, ring_in_y[0], z1f)),
        c.box((-xf, ring_in_y[1], z0f), (xf, y1f, z1f)),
        c.box((-xf, ring_in_y[0], z0f), (-xin, ring_in_y[1], z1f)),
        c.box((xin, ring_in_y[0], z0f), (xf, ring_in_y[1], z1f)),
    ]
    outlet = c.merge_parts([finish(neck_w), finish(neck_n)] + [finish(bx) for bx in bars])

    # ---------------- inlet: flange ring, pipe, cone to the housing hole
    x_face = -inlet_l
    tube_r = inlet_od / 2.0
    cone_x0 = -w / 2.0 - 0.028
    inlet = c.merge_parts([
        _ring_x(x_face, x_face + inlet_t, tube_r - 0.003, inlet_flange_od / 2.0 * float(faults.get("inlet_flange_scale", 1.0)), n_ring),
        _shell_x(x_face + inlet_t, cone_x0, tube_r, tube_r, 0.003, n_ring),
        _shell_x(cone_x0, -w / 2.0, tube_r, throat_r, 0.003, n_ring),
    ])
    inlet = (inlet[0] + [0.0, 0.0, axis_z], inlet[1])

    # ---------------- motor on the same shaft (IEC motor flipped end for end: shaft toward -X)
    mot = iec_motor(kw, frames=motor_table, detail=detail)
    cover_reach = -float(np.asarray(mot["parts"]["fan_cover"][0])[:, 0].min())
    x0_motor = total_len - inlet_l - cover_reach + float(faults.get("motor_dx", 0.0))
    motor_dz = float(faults.get("motor_dz", 0.0))
    h_motor = float(mot["dims"]["H"])

    def put_motor(piece):
        v = np.asarray(piece[0], float).reshape(-1, 3).copy()
        v[:, 0] = x0_motor - v[:, 0]
        v[:, 1] = -v[:, 1]
        v[:, 2] += axis_z - h_motor + motor_dz
        return v, piece[1]

    motor_parts = {k: put_motor(p) for k, p in mot["parts"].items()}
    motor = c.merge_parts(list(motor_parts.values()))
    shaft_tip = float(motor_parts["shaft"][0][:, 0].min())
    shield_face = float(motor_parts["endshield_de"][0][:, 0].min())
    feet_v = motor_parts["feet"][0]
    foot_x0, foot_x1 = float(feet_v[:, 0].min()), float(feet_v[:, 0].max())
    foot_z = float(feet_v[:, 2].min())

    # ---------------- wheel and shaft extension
    width = _fv(table, "wheel", "width")
    hub_r = _fv(table, "wheel", "hub_d") / 2.0
    blades_n = int(round(float(table["wheel"]["blades"]["v"])))
    xb1 = width / 2.0
    xb0 = -width / 2.0
    wheel_parts = [
        _tube(xb1, xb1 + 0.004, wheel_r, 0.0, n_ring),
        _tube(xb1 - 0.01, xb1 + 0.06, hub_r, 0.0, n_ring),
        _shell_x(xb0 - 0.03, xb0, throat_r - 0.016, wheel_r, 0.003, n_ring),
    ]
    r_in_b = 0.62 * wheel_r
    for i in range(blades_n):
        phi = 2.0 * np.pi * i / blades_n
        a = np.array([r_in_b * np.cos(phi), r_in_b * np.sin(phi)])
        phi2 = phi - np.radians(32.0)
        bpt = np.array([wheel_r * 0.985 * np.cos(phi2), wheel_r * 0.985 * np.sin(phi2)])
        d = bpt - a
        nrm = np.array([-d[1], d[0]]) / np.linalg.norm(d) * 0.0015
        yz = np.array([a - nrm, bpt - nrm, bpt + nrm, a + nrm])
        wheel_parts.append(_along_x(xb0, xb1, yz, 0.0))
    shaft_ext = _rod((shaft_tip + 0.002, 0.0, 0.0), (xb1 + 0.05, 0.0, 0.0), float(mot["dims"]["D"]) / 2.0, n_small)
    wheel_parts.append(shaft_ext)
    wheel = c.merge_parts(wheel_parts)
    wheel = (wheel[0] + [0.0, 0.0, axis_z], wheel[1])

    # ---------------- stool between the housing back wall and the motor shield
    stool_r = _fv(table, "stool", "outer_d") / 2.0
    stool = c.merge_parts([
        _ring_x(w / 2.0, shield_face, stool_r - 0.005, stool_r, n_ring),
        _ring_x(w / 2.0, w / 2.0 + 0.008, stool_r, stool_r + 0.03, n_ring),
        _ring_x(shield_face - 0.008, shield_face, stool_r, stool_r + 0.03, n_ring),
    ])
    stool = (stool[0] + [0.0, 0.0, axis_z], stool[1])

    # ---------------- frame: rails, cross members, motor base, cradle under the housing
    C_, C1, C2 = _fv(table, "frame", "C"), _fv(table, "frame", "C1"), _fv(table, "frame", "C2")
    rail_h, rail_b, rail_tw, rail_tf = (float(x) / 1000.0 for x in table["frame"]["rail"]["v"])
    post = _fv(table, "frame", "post")
    plate_t = _fv(table, "frame", "plate_t")
    x_r0 = -(C2 - C_) - 0.04
    x_r1 = max(C_, foot_x1) + 0.04
    # Webs inboard, flanges outboard: the anchor holes (C1 apart) sit in the open bottom flanges.
    y_rail = C1 / 2.0 - rail_b / 2.0
    chan = st.channel(rail_h, rail_b, rail_tw, rail_tf)
    frame_parts = [
        st.member((x_r0, y_rail, rail_h / 2.0), (x_r1, y_rail, rail_h / 2.0), chan, roll=np.pi),
        st.member((x_r0, -y_rail, rail_h / 2.0), (x_r1, -y_rail, rail_h / 2.0), chan),
    ]
    cross_x = [x_r0 + 0.05, 0.5 * (foot_x0 + foot_x1) - 0.12, 0.5 * (foot_x0 + foot_x1) + 0.12, x_r1 - 0.05]
    for xc in cross_x:
        frame_parts.append(st.member((xc, -y_rail, post / 2.0), (xc, y_rail, post / 2.0), st.shs(post)))
    plate_z1 = foot_z + float(faults.get("plate_dz", 0.0))
    plate = c.box((foot_x0 - 0.04, -0.17, plate_z1 - plate_t), (foot_x1 + 0.04, 0.17, plate_z1))
    frame_parts.append(plate)
    for xc in (cross_x[1], cross_x[2]):
        for yc in (-0.14, 0.14):
            frame_parts.append(st.member((xc, yc, post / 2.0), (xc, yc, plate_z1 - plate_t + 0.002), st.shs(post)))
    # cradle strips follow the lower spiral contour, posts stand on the rails and carry them
    shell_xy = _yz_rot(spiral, outlet_deg) if outlet_deg else spiral.copy()
    if mirror:
        shell_xy[:, 0] = -shell_xy[:, 0]
    shell_xy[:, 1] += axis_z
    low = shell_xy[(np.abs(shell_xy[:, 0]) <= 0.2) & (shell_xy[:, 1] < axis_z - 0.1)]
    low = low[np.argsort(low[:, 0])]
    if len(low) >= 3:
        y_posts = (low[0, 0] + 0.03, low[-1, 0] - 0.03) if low[-1, 0] - low[0, 0] > 0.12 else (float(low[:, 0].mean()),)
        for cx in (-0.09, 0.09):
            frame_parts.append(_sweep_yz(low, cx - 0.025, cx + 0.025, 0.012, +1))
            for yp in y_posts:
                zs = float(np.interp(yp, low[:, 0], low[:, 1])) - 0.012 + 0.006
                frame_parts.append(st.member((cx, yp, rail_h - 0.004), (cx, yp, zs), st.shs(post)))
    if faults.get("frame_clash"):
        # broken case: a post straight through the outlet neck
        yc_n = -(o["y_c"]) if mirror else o["y_c"]
        px = _yz_rot(np.array([[o["y_c"], o["H"] - 0.1]]), outlet_deg)[0]
        py = -px[0] if mirror else px[0]
        frame_parts.append(st.member((0.0, py, 0.0), (0.0, py, axis_z + px[1]), st.shs(0.05)))
    frame = c.merge_parts(frame_parts)

    # ---------------- bolts: outlet flange corners, inlet flange circle, anchor bolts
    bolt_parts = []
    d1 = _fv(table, "outlet", "d1")
    pitch1, pitch2 = _fv(table, "outlet", "a1"), _fv(table, "outlet", "a2")
    across1 = 1.7 * d1
    for sy in (-0.5, 0.5):
        for sx in (-0.5, 0.5):
            hy, hx = o["y_c"] + sy * pitch1, sx * pitch2
            for piece in _fan_bolt((hx, hy, o["H"]), (hx, hy, o["H"] - fl_t - 0.012), across1, d1 / 2.0, fl_t, n_small):
                bolt_parts.append(finish(piece))
    n_in = int(table["inlet"]["n"]["v"])
    d_in = _fv(table, "inlet", "d")
    r_bc = _fv(table, "inlet", "bolt_circle") / 2.0
    for i in range(n_in):
        ang = 2.0 * np.pi * (i + 0.5) / n_in
        hy, hz = r_bc * np.cos(ang), axis_z + r_bc * np.sin(ang)
        for piece in _fan_bolt((x_face, hy, hz), (x_face + inlet_t + 0.012, hy, hz), 1.7 * d_in, d_in / 2.0, inlet_t, n_small):
            bolt_parts.append((piece[0], piece[1]))
    d2 = _fv(table, "frame", "d2")
    for xa in (-(C2 - C_), C_):
        for ya in (-C1 / 2.0, C1 / 2.0):
            for piece in _fan_bolt((xa, ya, rail_tf), (xa, ya, 0.0), 1.7 * d2, d2 / 2.0, None, n_small):
                bolt_parts.append((piece[0], piece[1]))
    bolts = c.merge_parts(bolt_parts)

    built = {"volute": volute, "inlet": inlet, "outlet": outlet, "frame": frame, "motor": motor,
             "bolts": bolts, "wheel": wheel, "stool": stool}
    bb_min = np.min([np.asarray(p[0]).min(axis=0) for p in built.values()], axis=0)
    bb_max = np.max([np.asarray(p[0]).max(axis=0) for p in built.values()], axis=0)
    flange_top = np.asarray(outlet[0], float)
    flange_top = flange_top[flange_top[:, 2] >= flange_top[:, 2].max() - 1e-9]
    dims = {
        "outlet": {"y": 0.5 * float(flange_top[:, 1].max() + flange_top[:, 1].min()), "z": float(flange_top[:, 2].max()),
                   "neck": o["A"], "flange_y": float(flange_top[:, 1].max() - flange_top[:, 1].min()),
                   "flange_x": float(flange_top[:, 0].max() - flange_top[:, 0].min())},
        "size": FAN_SIZE, "hand": hand, "outlet_deg": outlet_deg, "kw": float(kw),
        "motor_frame": mot["dims"]["frame"], "axis_z": axis_z, "wheel_d": 2.0 * wheel_r,
        "housing_w": w, "inlet_face_x": x_face, "length": float(np.asarray(motor[0])[:, 0].max()) - x_face,
        "foot_z": foot_z, "motor_x0": x0_motor, "mass_kg": float(table["motor"]["mass_kg"]["v"]),
        "bbox": {"min": bb_min.tolist(), "max": bb_max.tolist()},
        "faces": sum(_count_faces(p[1]) for p in built.values()),
    }
    return {"parts": built, "dims": dims, "motor_parts": motor_parts}


# ====================================================================== shaft-mounted gearmotor
#
# SEW KA..T helical-bevel gear unit on a hollow shaft with a torque arm, IEC motor on the input flange.
# Numbers live in data/gearmotor_ka.json (mm). Local frame: the output (hollow shaft) axis is Y through the
# origin, the origin sits in the case mid plane; -Y is the driven side (the hollow shaft goes onto the conveyor
# shaft from -Y, the dust cap closes +Y); the motor axis runs along +X at z = -DB, y = 0 (EST: input axis in the
# mid plane); Z up; the case bottom (torque arm face) is z = -SA. The torque arm hangs down (A-side mounting: the
# bushing toward -Y); its clevis bracket ends on the casing wall plane y = wall_y = -(EA + wall_gap).

GM_DATA = Path(__file__).resolve().parent / "data" / "gearmotor_ka.json"
GM_PARTS = ("case", "ribs", "covers", "hollow_shaft", "torque_arm", "support", "bearing", "bolts", "motor")
# EST, not lettered anywhere: chamfer of the case front-top edge, side-rib proud, cover proud, clevis clear under the eye.
GM_CHAMFER = 0.03
GM_RIB_PROUD = 0.008
GM_COVER_T = 0.006
GM_EYE_CLEAR = 0.012
GM_PAD_T = 0.012
GM_PAD_MIN_H = 0.10
GM_BUSH_OF_R = 0.72         # EST: rubber bushing seat radius in eye radii (SEW p.274 section shows a thick boss)
GM_COVER_BOLTS = 8          # EST: Bonvario p.1 patterns show 7-8 holes round the bore


def _gm_table(data):
    if data is None:
        data = json.loads(GM_DATA.read_text(encoding="utf-8"))
    return data


def _gv(node, *path):
    for key in path:
        node = node[key]
    return float(node["v"]) / 1000.0


def _swap_xy(piece):
    """(x, y, z) -> (y, x, z): a part built along X turned onto Y. A swap is a mirror, so the faces are reversed."""
    v = np.asarray(piece[0], float).reshape(-1, 3)[:, [1, 0, 2]]
    blocks = piece[1] if isinstance(piece[1], list) else [piece[1]]
    return v, [np.asarray(b)[:, ::-1] for b in blocks if len(b)]


def _shift(piece, dx=0.0, dy=0.0, dz=0.0):
    return np.asarray(piece[0], float).reshape(-1, 3) + (dx, dy, dz), piece[1]


def _ring_y(y0, y1, r_in, r_out, cx, cz, steps):
    """Thick ring around a Y axis through (cx, cz), from y0 to y1."""
    v, f = _swap_xy(_ring_x(y0, y1, r_in, r_out, steps))
    return v + (cx, 0.0, cz), f


def _rod_y(y0, y1, radius, cx, cz, steps):
    return st.rod((cx, y0, cz), (cx, y1, cz), radius, steps)


def _hull2(pts):
    """Convex hull, counter-clockwise (monotone chain)."""
    pts = sorted({(round(float(p[0]), 9), round(float(p[1]), 9)) for p in pts})
    if len(pts) < 3:
        return np.array(pts)

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and _cross2(out[-2], out[-1], p) <= 1e-15:
                out.pop()
            out.append(p)
        return out

    lo, hi = half(pts), half(pts[::-1])
    return np.array(lo[:-1] + hi[:-1])


def _case_profile(QB, top, SA, FK, A, steps):
    """Side outline (x, z) of the helical housing: rear arc round the output axis (radius QB), flat top at `top`,
    front wall at x = FK with a chamfer, bottom face z = -SA from FK - A to FK. Convex, counter-clockwise."""
    S = np.array([FK - A, -SA])
    t_top = np.pi - np.arcsin(min(top / QB, 1.0))
    # the rear-lower line runs from the bottom corner S tangent to the arc: tangent point at ang(S) - acos(QB/|S|)
    t_low = np.arctan2(S[1], S[0]) % (2.0 * np.pi) - np.arccos(min(QB / float(np.linalg.norm(S)), 1.0))
    arc = np.linspace(t_top, t_low, steps)
    pts = [(FK, -SA), (FK, top - GM_CHAMFER), (FK - GM_CHAMFER, top)]
    pts += [(QB * np.cos(a), QB * np.sin(a)) for a in arc]
    pts.append(tuple(S))
    return _hull2(pts)


def _mirror_z(piece):
    v = np.asarray(piece[0], float).reshape(-1, 3).copy()
    v[:, 2] = -v[:, 2]
    blocks = piece[1] if isinstance(piece[1], list) else [piece[1]]
    return v, [np.asarray(b)[:, ::-1] for b in blocks if len(b)]


def place_frame(parts, origin, ex, ey, up=(0.0, 0.0, 1.0)):
    """Put local parts into the site: local X -> ex, local Y -> ey, local Z -> `up` made square to both.
    When (ex, ey, up) is left-handed the mesh is mirrored and its faces are reversed. Returns {name: (verts, faces)}."""
    ex = np.asarray(ex, float) / np.linalg.norm(ex)
    ey = np.asarray(ey, float)
    ey = ey - ex * float(np.dot(ey, ex))
    ey /= np.linalg.norm(ey)
    ez = np.asarray(up, float)
    ez = ez - ex * float(np.dot(ez, ex)) - ey * float(np.dot(ez, ey))
    ez /= np.linalg.norm(ez)
    m = np.column_stack([ex, ey, ez])
    flip = np.linalg.det(m) < 0
    out = {}
    for name, (v, f) in parts.items():
        v = np.asarray(v, float).reshape(-1, 3) @ m.T + np.asarray(origin, float)
        blocks = f if isinstance(f, list) else [f]
        if flip:
            blocks = [np.asarray(b)[:, ::-1] for b in blocks if len(b)]
        out[name] = (v, blocks)
    return out


def gm_size(kw, data=None):
    """KA size and its data row for a motor rating (nearest tabulated kW)."""
    table = _gm_table(data)
    key = _std_key(kw, table["kw_to_size"])
    name = table["kw_to_size"][key]["size"]
    return name, table["sizes"][name]


def shaft_gearmotor(kw, *, size=None, arm="down", wall_gap=None, wall_z=(-0.25, 0.25), detail="full", data=None,
                    motor_table=None, faults=None):
    """Shaft-mounted helical-bevel gearmotor KA..T: case, covers, ribs, hollow shaft with dust cap, torque arm with
    its rubber-bushed eye, clevis bracket to the casing wall, flange bearing and shaft stub on the wall, IEC motor
    (B5 flange, no feet). Local frame in the comment above; metres.

    `wall_gap`: casing wall to the inner hub end (default data est.wall_gap). `wall_z`: (low, high) z of that wall
    in the local frame; the clevis pad overlaps it from below (arm "down") or from above (arm "up").
    `arm="up"`: the unit turned upside down about the motor axis (the hollow shaft is a through bore, so it is
    driven from -Y either way; B-side arm keeps the bushing on the casing side): the case, arm and clevis are the
    "down" build mirrored in z, the motor axis sits DB above the output axis and the motor itself stays upright
    (terminal box on top). Used where nothing may hang under the casing (decks, drop gates). No breather then
    (it would sit on the new bottom; NOT_FOUND where SEW puts it for that position).
    `data`, `motor_table`, `faults` inject the check's broken cases.
    Returns {"parts", "dims", "motor_parts", "sub"}; "sub" holds the pieces the checks measure.
    """
    if detail not in ("full", "lod"):
        raise ValueError("detail must be full or lod")
    if arm not in ("down", "up"):
        raise ValueError("arm must be down or up")
    up_arm = arm == "up"
    if up_arm:
        wall_z = (-wall_z[1], -wall_z[0])
    faults = faults or {}
    table = _gm_table(data)
    if size is None:
        size, row = gm_size(kw, table)
    else:
        row = table["sizes"][size]
    est = table["est"]
    lod = detail == "lod"
    n_ring = 24 if lod else 64
    n_small = 8 if lod else 16
    n_arc = 10 if lod else 28

    A, B, DB = _gv(row, "A"), _gv(row, "B"), _gv(row, "DB")
    B *= float(faults.get("case_w_scale", 1.0))
    EA, FE, FH, FJ, FK = _gv(row, "EA"), _gv(row, "FE"), _gv(row, "FH"), _gv(row, "FJ"), _gv(row, "FK")
    QB, L2, SA, H = _gv(row, "QB"), _gv(row, "L2"), _gv(row, "SA"), _gv(row, "H")
    in_r = _gv(row, "input_d") / 2.0
    cover_bc = _gv(row, "cover_bolt_circle") / 2.0
    U = _gv(row, "U") * float(faults.get("bore_scale", 1.0))
    UF = _gv(row, "UF")
    bolt_d = _gv(row, "MC_d")
    arm = row["arm"]
    BA, FC, G, O, R = _gv(arm, "BA"), _gv(arm, "FC"), _gv(arm, "G"), _gv(arm, "O"), _gv(arm, "R")
    FN, FU, FV = _gv(arm, "FN"), _gv(arm, "FU"), _gv(arm, "FV")
    alpha = np.radians(float(arm["alpha"]["v"]))
    top = H - SA
    flange_t = _gv(est, "input_flange_t")
    wall_gap = _gv(est, "wall_gap") if wall_gap is None else float(wall_gap)
    wall_y = -(EA + wall_gap)
    cheek_t = _gv(est, "cheek_t")
    gap = _gv(est, "clevis_gap")
    pad_over = _gv(est, "pad_over")
    rib_t = _gv(est, "rib_t")
    web_t = float(est["web_t"]["v"]) * FV

    # ---------------- case: helical housing (round rear = the cylinder round the output), bevel chamber, input flange
    prof = _case_profile(QB, top, SA, FK, A, n_arc)
    housing = st.member((0.0, -B / 2.0, 0.0), (0.0, B / 2.0, 0.0), prof, up=(0.0, 0.0, 1.0))
    r0 = 0.95 * min(B / 2.0, top + DB, SA - DB)
    r1 = 0.85 * in_r
    x_cone0, x_cone1 = FK - 0.01, L2 - flange_t
    cone = _frustum_x(x_cone0, x_cone1, r0, r1, -DB, n_ring)
    flange = _ring_x(x_cone1, L2, 0.0005, in_r, n_ring)
    case = c.merge_parts([housing, cone, _shift(flange, dz=-DB)])

    # ---------------- ribs: two vertical ribs per side face, a lip round the bottom face
    ribs = []
    cov_r = cover_bc + 0.018
    span = FK - cov_r - 2.0 * rib_t
    for xr in (cov_r + rib_t + 0.15 * span, cov_r + rib_t + 0.85 * span):
        z_hi = top - 0.01 if xr < FK - GM_CHAMFER else top - GM_CHAMFER - 0.01
        for s in (-1.0, 1.0):
            y_in, y_out = s * B / 2.0, s * (B / 2.0 + GM_RIB_PROUD)
            ribs.append(c.box((xr - rib_t / 2.0, min(y_in, y_out), -SA + 0.012), (xr + rib_t / 2.0, max(y_in, y_out), z_hi)))
    ribs.append(c.box((FK - A - 0.004, -B / 2.0 - 0.004, -SA), (FK + 0.004, B / 2.0 + 0.004, -SA + 0.012)))
    ribs = c.merge_parts(ribs)

    # ---------------- covers: output bearing covers with bolts, intermediate covers, dust cap, breather
    covers = []
    xi, zi = 0.3 * FK, -0.6 * SA
    ri = min(0.21 * SA, float(np.hypot(xi, zi)) - cov_r - 0.005)
    bolts = []
    for s in (-1.0, 1.0):
        y0, y1 = s * B / 2.0, s * (B / 2.0 + GM_COVER_T)
        covers.append(_ring_y(min(y0, y1), max(y0, y1), UF / 2.0 + 0.003, cov_r, 0.0, 0.0, n_ring))
        if ri > 0.02:
            covers.append(_ring_y(min(y0, y1), max(y0, y1), 0.0005, ri, xi, zi, n_ring))
        across = max(0.010, 0.75 * bolt_d)
        for k in range(GM_COVER_BOLTS):
            a = 2.0 * np.pi * (k + 0.5) / GM_COVER_BOLTS
            px, pz = cover_bc * np.cos(a), cover_bc * np.sin(a)
            seat = np.array([px, y1, pz])
            bolts.append(_bolt(seat, seat + (0.0, s * 0.5 * across, 0.0), across, (0.0, 0.0, 1.0)))
    cap = _ring_y(EA, EA + 0.008, 0.0005, UF / 2.0 + 0.003, 0.0, 0.0, n_ring)
    covers.append(cap)
    covers.append(_rod_y(EA + 0.008, EA + 0.014, 0.35 * U, 0.0, 0.0, n_small))
    if not up_arm:
        covers.append(st.rod((0.6 * FK, 0.0, top), (0.6 * FK, 0.0, top + 0.022), 0.012, n_small))
    covers = c.merge_parts(covers)

    # ---------------- hollow shaft (bore U, hub UF, length 2 EA)
    hollow = _ring_y(-EA, EA, U / 2.0, UF / 2.0, 0.0, 0.0, n_ring)

    # ---------------- torque arm: flange under the bottom face, web down to the eye, eye boss, rubber bushing
    arm_dz = float(faults.get("arm_dz", 0.0))
    eye = np.array([FC, -O + arm_dz])
    y_c = -EA + BA + FV / 2.0
    holes = [(FK - A + FH + dx, sy * FE / 2.0) for dx in (0.0, FJ) for sy in (-1.0, 1.0)]
    drop = (O - SA - G)
    half_w = drop / np.tan(alpha) + R / np.sin(alpha)
    px0 = max(FK - A, min(FC - half_w, holes[0][0] - 1.5 * bolt_d))
    px1 = min(FK, max(FC + half_w, holes[-1][0] + 1.5 * bolt_d))
    py = min(B / 2.0, FE / 2.0 + 1.5 * bolt_d)
    z_plate = -SA + arm_dz
    plate = c.box((px0, -py, z_plate - G), (px1, py, z_plate))
    r_b = GM_BUSH_OF_R * R
    circ = [(R * np.cos(a), R * np.sin(a)) for a in np.linspace(0.0, 2.0 * np.pi, n_ring, endpoint=False)]
    w_top = O - SA - G
    outline = _hull2(circ + [(-half_w, w_top), (half_w, w_top)])
    web = _plate_x(outline, y_c - web_t / 2.0, y_c + web_t / 2.0, r_b, n_ring)
    web = _swap_xy(web)
    web = _shift(web, eye[0], 0.0, eye[1])
    boss = _ring_y(y_c - FN / 2.0, y_c + FN / 2.0, r_b, R, eye[0], eye[1], n_ring)
    bush = _ring_y(y_c - FV / 2.0, y_c + FV / 2.0, FU / 2.0, r_b - 0.0005, eye[0], eye[1], n_ring)
    torque_arm = c.merge_parts([plate, web, boss, bush])
    for hx, hy in holes:
        seat = np.array([hx, hy, -SA - G])
        bolts.extend(_fan_bolt(seat, seat + (0.0, 0.0, G + 1.5 * bolt_d), 1.5 * bolt_d, bolt_d / 2.0, None, n_small))

    # ---------------- clevis bracket ("opora"): cheeks round the bushing, base, wall pad, gusset, pin
    cy_in, cy_out = FV / 2.0 + gap, FV / 2.0 + gap + cheek_t
    cw = 1.1 * R
    z_base = eye[1] - R - GM_EYE_CLEAR
    cheeks = [c.box((eye[0] - cw, y_c - cy_out, z_base), (eye[0] + cw, y_c - cy_in, eye[1] + R)),
              c.box((eye[0] - cw, y_c + cy_in, z_base), (eye[0] + cw, y_c + cy_out, eye[1] + R))]
    pad_y = wall_y + float(faults.get("wall_dy", 0.0))
    base = c.box((eye[0] - cw, pad_y + GM_PAD_T, z_base - cheek_t), (eye[0] + cw, y_c + cy_out, z_base))
    pad_top = max(z_base + GM_PAD_MIN_H, wall_z[0] + pad_over)
    pad_top = min(pad_top, wall_z[1])
    pw = 1.5 * R
    pad = c.box((eye[0] - pw, pad_y, z_base - cheek_t), (eye[0] + pw, pad_y + GM_PAD_T, pad_top))
    support = [base, pad] + cheeks
    g_y0, g_y1 = pad_y + GM_PAD_T, y_c - cy_out
    if g_y1 - g_y0 > 0.02:
        g_h = min(pad_top - z_base, g_y1 - g_y0)
        gv = np.array([[eye[0] - cheek_t / 2.0, g_y0, z_base], [eye[0] - cheek_t / 2.0, g_y1, z_base],
                       [eye[0] - cheek_t / 2.0, g_y0, z_base + g_h],
                       [eye[0] + cheek_t / 2.0, g_y0, z_base], [eye[0] + cheek_t / 2.0, g_y1, z_base],
                       [eye[0] + cheek_t / 2.0, g_y0, z_base + g_h]])
        support.append((gv, [np.array([[0, 2, 1], [3, 4, 5]]), np.array([[0, 1, 4, 3], [1, 2, 5, 4], [2, 0, 3, 5]])]))
    if faults.get("support_clash"):
        # broken case: a strut from the clevis base straight up into the gear case
        support.append(st.member((eye[0], y_c, z_base), (eye[0], y_c, -0.3 * SA), st.shs(0.03)))
    body = c.merge_parts(support)
    pin_len = cy_out + 0.6 * FU
    pin = _rod_y(y_c - pin_len, y_c + pin_len, FU / 2.0 - 0.0005, eye[0], eye[1], n_small)
    nut_a = 1.6 * FU
    pin_nuts = [_bolt((eye[0], y_c + s * cy_out, eye[1]), (eye[0], y_c + s * (cy_out + 0.8 * FU), eye[1]), nut_a, (0.0, 0.0, 1.0))
                for s in (-1.0, 1.0)]
    pad_bolt_z = 0.5 * (max(z_base, wall_z[0]) + pad_top)
    pad_bolts = []
    for sx in (-1.0, 1.0):
        seat = np.array([eye[0] + sx * 0.9 * R, pad_y + GM_PAD_T, pad_bolt_z])
        pad_bolts.extend(_fan_bolt(seat, seat - (0.0, GM_PAD_T + 0.01, 0.0), 0.018, 0.006, None, n_small))
    support_all = c.merge_parts([body, pin] + [p for p in pin_nuts if p is not None] + pad_bolts)

    # ---------------- flange bearing on the wall and the conveyor shaft stub
    bs = 2.2 * U + 0.06
    bearing = c.merge_parts([
        c.box((-bs / 2.0, wall_y, -bs / 2.0), (bs / 2.0, wall_y + 0.012, bs / 2.0)),
        _ring_y(wall_y + 0.012, wall_y + max(0.03, wall_gap - 0.02), U / 2.0 + 0.002, 1.1 * U, 0.0, 0.0, n_ring),
        _rod_y(wall_y - 0.01, EA - 0.004, U / 2.0 - 0.0005, 0.0, 0.0, n_ring),
    ])
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            seat = np.array([sx * (bs / 2.0 - 0.018), wall_y + 0.012, sz * (bs / 2.0 - 0.018)])
            bolts.extend(_fan_bolt(seat, seat - (0.0, 0.012, 0.0), 0.017, 0.006, None, n_small))

    # ---------------- motor: IEC frame for the kW, feet and shaft dropped (shaft is inside the case), B5 flange
    mot = iec_motor(kw, frames=motor_table, detail=detail)
    frame = mot["dims"]["frame"]
    fl = table["motor_flange"][frame]
    LA, M_, P_, S_ = (_gv(fl, k) for k in ("LA", "M", "P", "S"))
    n_holes = int(fl["holes"]["v"])
    mH = float(mot["dims"]["H"])
    shoulder = float(np.asarray(mot["parts"]["endshield_de"][0])[:, 0].max())
    seal_r = max(float(mot["dims"]["D"]) / 2.0 * 1.65, 0.008)
    flange = [_ring_x(shoulder - LA, shoulder, seal_r + 0.001, P_ / 2.0, n_ring)]
    flange[0] = (flange[0][0] + (0.0, 0.0, mH), flange[0][1])
    for k in range(n_holes):
        a = np.pi / 4.0 + 2.0 * np.pi * k / n_holes
        cc = np.array([0.0, M_ / 2.0 * np.cos(a), mH + M_ / 2.0 * np.sin(a)])
        flange.append(_bolt(cc + (shoulder - LA - 0.45 * S_, 0.0, 0.0), cc + (shoulder - LA, 0.0, 0.0), 1.5 * S_, (0.0, 0.0, 1.0)))
    m_parts = {k: v for k, v in mot["parts"].items() if k not in ("feet", "shaft")}
    m_parts["flange"] = c.merge_parts([p for p in flange if p is not None])
    x0 = L2 + shoulder + float(faults.get("motor_dx", 0.0))
    dz = (DB if up_arm else -DB) - mH + float(faults.get("motor_dz", 0.0))

    def put_motor(piece):
        v = np.asarray(piece[0], float).reshape(-1, 3).copy()
        v[:, 0] = x0 - v[:, 0]
        v[:, 1] = -v[:, 1]
        v[:, 2] += dz
        return v, piece[1]

    motor_parts = {k: put_motor(p) for k, p in m_parts.items()}
    motor = c.merge_parts(list(motor_parts.values()))

    bolt_parts = [b for b in bolts if b is not None]
    bolts_m = c.merge_parts(bolt_parts)
    built = {"case": case, "ribs": ribs, "covers": covers, "hollow_shaft": hollow, "torque_arm": torque_arm,
             "support": support_all, "bearing": bearing, "bolts": bolts_m}
    sub = {"plate": plate, "eye_boss": boss, "pin": pin, "pad": pad, "support_body": body}
    sign = 1.0
    if up_arm:
        sign = -1.0
        built = {k: _mirror_z(v) for k, v in built.items()}
        sub = {k: _mirror_z(v) for k, v in sub.items()}
        wall_z = (-wall_z[1], -wall_z[0])
    built["motor"] = motor
    sub["flange"] = motor_parts["flange"]
    bb_min = np.min([np.asarray(p[0]).min(axis=0) for p in built.values()], axis=0)
    bb_max = np.max([np.asarray(p[0]).max(axis=0) for p in built.values()], axis=0)
    dims = {
        "size": size, "kw": float(kw), "motor_frame": frame, "flange": fl["flange"],
        "arm": arm, "out_axis": [0.0, 0.0], "motor_axis": [0.0, -sign * DB], "flange_x": L2,
        "eye": [float(eye[0]), sign * float(eye[1])], "eye_y": y_c, "wall_y": wall_y,
        "wall_z": [float(wall_z[0]), float(wall_z[1])], "pad_edge": sign * pad_top,
        "clevis_end": sign * (z_base - cheek_t), "holes": holes, "hub_y": [-EA, EA],
        "bbox": {"min": bb_min.tolist(), "max": bb_max.tolist()},
        "faces": sum(_count_faces(p[1]) for p in built.values()),
    }
    return {"parts": built, "dims": dims, "motor_parts": motor_parts, "sub": sub}


# ======================================================================= shaft-mount reducer with a belt drive
# Dodge Torque-Arm II TA6307H25 on the head pulley shaft (straight bore), TA6307MM belt-drive motor mount in
# position B (motor above the reducer), IEC motor, V-belt sheaves under a guard, TA6307RA torque-arm rod down to a
# stand on the platform. Numbers live in data/reducer_ta6307h.json (mm). Local frame: the output (hollow shaft)
# axis is Y through the origin; y = 0 is the split plane of the two case halves; the input shaft sticks out to -Y
# (outboard, catalogue G1-80 side view: input on the side away from the driven-shaft bearing), so the driven
# equipment is on +Y; Z up. The end view of G1-80 looks from the input side, so its "right" is +X here.

RD_DATA = Path(__file__).resolve().parent / "data" / "reducer_ta6307h.json"
RD_PARTS = ("case", "bolts", "input_shaft", "mount", "sheaves", "belts", "guard", "torque_arm", "stand", "motor")
IN = 0.0254
# Read off the TorqueArmII.pdf drawings by the C3 agent (inches). The data file has the numbers, but some of its
# "what is it" notes differ from this reading; the reading is given per item.
RD_READ = {
    # G1-80 end view: 1.78 is the horizontal distance between the output CL and the vertical line through the
    # input-shaft centre (the data file files it as a turnbuckle segment). With 9.17 (output CL down to the centre
    # of the 4-bolt input cover, i.e. the input shaft) it places the input shaft.
    "input_dx": 1.78,
    # G1-80 side view: 4.83 runs from the input boss face to the torque-arm rod axis, the rod axis is the split
    # plane (4.83 + 5.41 = 10.24 = boss face .. outer hub end, 5.42 = split plane .. hub end); 6.35 runs from the
    # input-shaft end to the boss face. So the boss face is 4.83 and the shaft end 4.83 + 6.35 = 11.18 out of the
    # split plane. (The data file reads 4.83 / 6.35 as rod widths, and 5.35 as a shaft-to-shaft distance; on the
    # drawing 5.35 is the shaft end .. hub end, an axial length: the input shaft is 9.17 below the output.)
    "boss_face": 4.83,
    "input_stick": 6.35,
    # G1-80 end view: the torque-arm case pin is 6.11 right of and 16.44 below the output CL; the rod is drawn at
    # 90 deg to the line from the output CL to that pin (the 90 deg mark next to 6.11).
    "pin_dx": 6.11,
    # G1-84 Position B: support channel 1.75 deep, motor plate at least 2.09 over it and 4.53 of travel on the
    # threaded rods; mount post 2.50 thick; post outer face 10.42 from the input-shaft end (B + C = 1.59 + 8.83 =
    # 5.91 + 4.51, G1-85), C = shaft end .. plate end, 4.51-8.83.
    "support_depth": 1.75, "plate_gap": 2.09, "plate_travel": 4.53, "post_t": 2.50, "post_from_tip": 10.42,
    "plate_end_C": (4.51, 8.83),
    # G1-80 end view outline at 14.65 px/in (+-0.2 in): top flat +-4.3, upper corners down to +4.2 on the sides,
    # sides down to -8.7, bottom flat +-6.6. Only 20.55 x 25.23 and 10.28 are lettered.
    "top_flat": 4.3, "side_top": 4.2, "side_bot": -8.7, "bot_flat": 6.6,
    # G1-80: the large round cover around the output is ~6.0 in radius on the end view (not lettered).
    "cover_r": 6.0,
}
# EST, not lettered anywhere: case corner radius, flange lip, shell edge round, boss and cover sizes, bolt counts,
# plate and bar thickness, rod and turnbuckle diameters, stand section, guard clearance and sheet.
RD_CORNER = 0.040
RD_LIP = 0.020           # split-flange lip left visible around the case shells
RD_FLANGE_T = 0.008      # half thickness of the split flange
RD_BOSS_R = 0.058        # input bearing boss radius
RD_COVER_HALF = 0.055    # input cover: rounded square, half size
RD_BOLTS = 18            # split-flange bolts round the outline
RD_BAR_T = 0.019         # mount bars (flat), thickness across X
RD_WEB_T = 0.0095        # support channel web, 3/8 in
RD_PLATE_T = 0.0127      # motor plate, 1/2 in
RD_ROD_R = 0.0095        # 3/4 in threaded rods of the plate
RD_ARM_R = 0.016         # torque-arm rod, 1-1/4 in
RD_TB_R = 0.026          # turnbuckle body
RD_LUG_T = 0.025         # case lug (fulcrum) in the split plane
RD_LUG_PIN_R = 0.0127    # 1 in case pin
RD_BRK_W = 0.0762        # bracket base width across, 3 in
RD_BRK_T = 0.0127        # bracket base thickness
RD_BRK_LUG_T = 0.019     # bracket lug, 3/4 in
RD_CHEEK = 0.012         # clevis cheek at the case end
RD_STAND = 0.100         # stand post SHS 100 (judgment: no drawing of the support)
RD_STAND_BASE = (0.22, 0.016)
RD_STAND_CAP = (0.16, 0.012)
RD_GUARD_CLEAR = 0.030   # guard inside clear of the sheave rims
RD_GUARD_T = 0.003
RD_GAP = 0.0005          # clearance left between parts that bear on each other (so BVH does not read contact)
# V-belt drive: 3 x SPB (EST), ISO 4183 groove pitch e = 19, edge f = 12.5, top width ~16.5, depth ~17.5 (EST);
# the reducer sheave pitch diameter 200 mm (EST, above the 157.48 minimum of G1-28); motor 1475 rpm (EST, 4-pole
# 50 Hz at load); belt section 16 x 13 (SPB, EST).
RD_GROOVES = 3
RD_E, RD_F = 0.019, 0.0125
RD_GROOVE_TOP, RD_GROOVE_DEPTH = 0.0165, 0.0175
RD_SHEAVE_PD = 0.200
RD_MOTOR_RPM = 1475.0
RD_BELT = (0.016, 0.013)
# EST axial layout of the belt plane: sheave centre 240 mm out of the split plane, motor shoulder 55 mm inside it.
RD_BELT_S = 0.240
RD_SHOULDER_S = 0.185


def _rd_table(data):
    if data is None:
        data = json.loads(RD_DATA.read_text(encoding="utf-8"))
    return data


def _rv(node, *path):
    for key in path:
        node = node[key]
    v = node["v"] if isinstance(node, dict) else node
    return float(v) / 1000.0


def _outward(p, q):
    d = np.subtract(q, p)
    n = np.array([d[1], -d[0]], float)
    return n / np.linalg.norm(n)


def _round_core(poly, radius):
    """Corners of a convex counter-clockwise polygon moved in by `radius` along both edge normals."""
    poly = np.asarray(poly, float)
    n = len(poly)
    core, normals = [], []
    for i in range(n):
        n0 = _outward(poly[i - 1], poly[i])
        n1 = _outward(poly[i], poly[(i + 1) % n])
        m = np.array([n0, n1])
        b = np.array([poly[i] @ n0 - radius, poly[i] @ n1 - radius])
        core.append(np.linalg.solve(m, b))
        normals.append((n0, n1))
    return np.array(core), normals


def _round_ring(core, normals, d, k):
    """Outline at distance d from the core polygon: straight edges plus corner arcs of radius d (k points each)."""
    pts = []
    for q, (n0, n1) in zip(core, normals):
        a0, a1 = np.arctan2(n0[1], n0[0]), np.arctan2(n1[1], n1[0])
        if a1 <= a0:
            a1 += 2.0 * np.pi
        for a in np.linspace(a0, a1, k):
            pts.append(q + d * np.array([np.cos(a), np.sin(a)]))
    return np.array(pts)


def _loft_y(rings, ys, cx=0.0, cz=0.0):
    """Closed solid through outlines (x, z) of equal length at the given y; flat n-gon caps at both ends."""
    m = len(rings[0])
    v = np.concatenate([np.column_stack([r[:, 0] + cx, np.full(m, y), r[:, 1] + cz]) for r, y in zip(rings, ys)])
    faces = [c.grid_faces(len(rings), m, wrap_cols=True), np.arange(m)[::-1][None, :],
             (np.arange(m) + (len(rings) - 1) * m)[None, :]]
    return v, faces


def _revolve_y(profile, cx, cy, cz, steps):
    """Solid of revolution about a Y axis through (cx, cz): closed profile of (r, y) points, y relative to cy."""
    prof = np.asarray(profile, float)
    k = len(prof)
    ang = np.linspace(0.0, 2.0 * np.pi, steps, endpoint=False)
    v = np.array([[cx + r * np.cos(a), cy + y, cz + r * np.sin(a)] for a in ang for r, y in prof])
    f = []
    for i in range(steps):
        i1 = (i + 1) % steps
        for j in range(k):
            j1 = (j + 1) % k
            f.append([i * k + j, i * k + j1, i1 * k + j1, i1 * k + j])
    return v, np.array(f, np.int64)


def _sheave(pd, bore_r, cx, cy, cz, steps):
    """V-belt sheave (RD_GROOVES grooves), centre plane at y = cy, axis along Y through (cx, cz)."""
    w = 2.0 * RD_F + (RD_GROOVES - 1) * RD_E
    r_o = pd / 2.0 + 0.0035                     # EST: rim 3.5 mm above the pitch line
    r_b = r_o - RD_GROOVE_DEPTH
    r_rim = r_b - 0.008
    r_hub = max(bore_r * 1.8, bore_r + 0.018)
    top, bot = RD_GROOVE_TOP / 2.0, RD_GROOVE_TOP / 2.0 - RD_GROOVE_DEPTH * np.tan(np.radians(19.0))
    prof = [(r_o, -w / 2.0)]
    for g in range(RD_GROOVES):
        yc = -w / 2.0 + RD_F + g * RD_E
        prof += [(r_o, yc - top), (r_b, yc - bot), (r_b, yc + bot), (r_o, yc + top)]
    prof += [(r_o, w / 2.0)]
    if r_rim - r_hub > 0.01:
        prof += [(r_rim, w / 2.0), (r_rim, 0.011), (r_hub, 0.011), (r_hub, w / 2.0)]
        prof += [(bore_r, w / 2.0), (bore_r, -w / 2.0), (r_hub, -w / 2.0), (r_hub, -0.011), (r_rim, -0.011), (r_rim, -w / 2.0)]
    else:
        prof += [(bore_r, w / 2.0), (bore_r, -w / 2.0)]
    # the profile runs r_o side first, then inward: reverse so the solid is consistently wound
    return _revolve_y(prof[::-1], cx, cy, cz, steps), r_o, w


def _belt_loops(c1, r1, c2, r2, ys, steps):
    """Closed V-belts round two pitch circles (x, z), one per y in ys: hull of the circles, section RD_BELT."""
    ang = np.linspace(0.0, 2.0 * np.pi, steps, endpoint=False)
    pts = [(c1[0] + r1 * np.cos(a), c1[1] + r1 * np.sin(a)) for a in ang]
    pts += [(c2[0] + r2 * np.cos(a), c2[1] + r2 * np.sin(a)) for a in ang]
    path = _hull2(pts)
    k = len(path)
    nrm = []
    for i in range(k):
        t = path[(i + 1) % k] - path[i - 1]
        n = np.array([t[1], -t[0]])
        nrm.append(n / np.linalg.norm(n))
    nrm = np.array(nrm)
    bw, bh = RD_BELT
    out = []
    for y in ys:
        # section corners: (radial offset from the pitch line, y)
        sec = [(0.0035, y - bw / 2.0), (0.0035, y + bw / 2.0), (-(bh - 0.0035), y + bw / 2.0 - 0.004), (-(bh - 0.0035), y - bw / 2.0 + 0.004)]
        v = np.array([[p[0] + nr[0] * dr, yy, p[1] + nr[1] * dr] for p, nr in zip(path, nrm) for dr, yy in sec])
        f = []
        for i in range(k):
            i1 = (i + 1) % k
            for j in range(4):
                j1 = (j + 1) % 4
                f.append([i * 4 + j, i1 * 4 + j, i1 * 4 + j1, i * 4 + j1])
        out.append((v, np.array(f, np.int64)))
    return c.merge_parts(out), float(sum(np.linalg.norm(path[(i + 1) % k] - path[i]) for i in range(k)))


def _flat_member(p0, p1, half_w, y0, y1):
    """Plate along p0 -> p1 in the XZ plane, half width half_w across, from y0 to y1 (thickness along Y)."""
    prof = np.array([(-half_w, y0), (half_w, y0), (half_w, y1), (-half_w, y1)])
    return st.member(p0, p1, prof, up=(0.0, 1.0, 0.0))


def rd_select(kw, output_rpm, data=None):
    """G1-28 Class III row for the motor and the output speed; only the 30 HP (22 kW), 61-80 rpm row is in the data."""
    table = _rd_table(data)
    sel = table["selection"]
    lo, hi = (float(x) for x in str(sel["output_rpm_band"]["v"]).split("-"))
    hp = float(sel["motor_hp"]["v"])
    if abs(kw / 0.7457 - hp) > 1.0 or not lo <= output_rpm <= hi:
        raise ValueError(f"no TA6307H row in the data for {kw} kW at {output_rpm} rpm (have {hp:g} HP, {lo:g}-{hi:g} rpm)")
    return sel["reducer"]["v"], float(sel["actual_ratio_h25"]["v"])


def shaft_mount_reducer(kw=22.0, *, output_rpm, floor_z, centers=None, arm_len=None, bore=0.090, detail="full", data=None,
                        motor_table=None, faults=None):
    """Dodge TA6307H25 shaft-mount reducer with a belt drive (local frame in the comment above; metres).

    output_rpm: driven-shaft speed (sets the motor sheave). floor_z: z of the floor the torque-arm stand stands on.
    centers: belt centre distance (default: middle of the M1 range for a 284T/286T-size motor, G1-85).
    arm_len: torque-arm rod pin to pin (default: middle of 29.50-35.50 in). bore: the driven shaft diameter (the
    straight bore is made to order up to 3-15/16 in, G1-121). `data`, `motor_table`, `faults` inject the check's cases.
    Returns {"parts", "dims", "motor_parts", "sub"}; "sub" holds the pieces the checks measure.
    """
    if detail not in ("full", "lod"):
        raise ValueError("detail must be full or lod")
    faults = faults or {}
    table = _rd_table(data)
    t = table["ta6307h"]
    lod = detail == "lod"
    n_ring = 24 if lod else 64
    n_small = 8 if lod else 16
    n_arc = 3 if lod else 8
    reducer, ratio = rd_select(kw, output_rpm, table)
    if bore / 2.0 > _rv(t, "output_bore_straight_max") / 2.0:
        raise ValueError(f"shaft {bore * 1000:.0f} mm is over the straight-bore maximum")

    # ---------------- case: two halves split at y = 0, rounded outline of the G1-80 end view
    W, H = _rv(t, "housing_end_view_horizontal"), _rv(t, "housing_end_view_vertical")
    top = _rv(t, "output_cl_to_top")
    bot = top - H
    H *= float(faults.get("case_h_scale", 1.0))
    top, bot = top * float(faults.get("case_h_scale", 1.0)), bot * float(faults.get("case_h_scale", 1.0))
    hw = W / 2.0                                    # EST: output centred across (14.65 px/in reading: 10.2 / 10.4 in)
    tf, st_, sb, bf = (RD_READ[k] * IN for k in ("top_flat", "side_top", "side_bot", "bot_flat"))
    poly = np.array([(-bf, bot), (bf, bot), (hw, sb), (hw, st_), (tf, top), (-tf, top), (-hw, st_), (-hw, sb)])
    core, normals = _round_core(poly, RD_CORNER)
    half = _rv(t, "housing_axial_inner") / 2.0      # 7.62 in: case faces at +-3.81 in
    flange = _loft_y([_round_ring(core, normals, RD_CORNER, n_arc)] * 2, [-RD_FLANGE_T, RD_FLANGE_T])
    shells = []
    for sgn in (-1.0, 1.0):
        ds = [RD_CORNER - RD_LIP, RD_CORNER - RD_LIP, RD_CORNER - RD_LIP - 0.006, RD_CORNER - RD_LIP - 0.016]
        ys = [sgn * RD_FLANGE_T, sgn * (half - 0.012), sgn * (half - 0.004), sgn * half]
        rings = [_round_ring(core, normals, d, n_arc) for d in ds]
        if sgn < 0:
            rings, ys = rings[::-1], ys[::-1]
        shells.append(_loft_y(rings, ys))
    housing = c.merge_parts([flange] + shells)

    A_len, hub_od = _rv(t, "straight_bore_length_A"), _rv(t, "straight_bore_hub_od_B")
    hub = _ring_y(-A_len / 2.0, A_len / 2.0, bore / 2.0, hub_od / 2.0, 0.0, 0.0, n_ring)
    cov_r = RD_READ["cover_r"] * IN
    covers = [_ring_y(-half - 0.006, -half + 0.001, hub_od / 2.0 + 0.002, cov_r, 0.0, 0.0, n_ring),
              _ring_y(half - 0.001, half + 0.006, hub_od / 2.0 + 0.002, cov_r, 0.0, 0.0, n_ring)]

    in_x = RD_READ["input_dx"] * IN + float(faults.get("input_dx", 0.0))
    in_z = -_rv(t, "end_view_vertical_9_17")
    in_r = _rv(t, "input_shaft_diameter") / 2.0
    boss_face = -RD_READ["boss_face"] * IN
    tip = boss_face - RD_READ["input_stick"] * IN
    boss = _rod_y(boss_face + 0.006, -half + 0.001, RD_BOSS_R, in_x, in_z, n_ring)
    sq = np.array([(-1, -1), (1, -1), (1, 1), (-1, 1)], float) * RD_COVER_HALF
    qc, qn = _round_core(sq, 0.018)
    cov4 = _loft_y([_round_ring(qc, qn, 0.018, n_arc)] * 2, [boss_face, boss_face + 0.006], in_x, in_z)
    case_parts = [housing, hub, boss, cov4] + covers
    # plugs: breather high on the -Y face, level plug at the side, magnetic drain at the bottom (G1-5, G1-132)
    plugs = [(-0.15, 0.15, 0.014), (-0.20, -0.10, 0.011), (0.10, -0.33, 0.012)]
    for px, pz, pr in plugs:
        case_parts.append(_rod_y(-half - 0.018, -half + 0.001, pr, px, pz, n_small))
    # torque-arm fulcrum lug on the case (split plane), pin at (6.11, -16.44) in
    p1 = np.array([RD_READ["pin_dx"] * IN, -_rv(t, "output_cl_down_16_44")])
    lug_r = 0.036
    lug_out = _hull2([(0.05, bot + 0.03), (0.20, bot + 0.07)] +
                     [(p1[0] + lug_r * np.cos(a), p1[1] + lug_r * np.sin(a)) for a in np.linspace(0, 2 * np.pi, n_ring, endpoint=False)])
    lug = _swap_xy(_plate_x(lug_out, -RD_LUG_T / 2.0, RD_LUG_T / 2.0))
    case_parts.append(lug)
    case = c.merge_parts(case_parts)

    # ---------------- bolts: split flange round the outline, round covers, input cover
    bolts = []
    ring_b = _round_ring(core, normals, RD_CORNER - RD_LIP / 2.0, 2)
    per = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(np.vstack([ring_b, ring_b[:1]]), axis=0), axis=1))])
    for k in range(RD_BOLTS):
        s_at = per[-1] * (k + 0.5) / RD_BOLTS
        i = int(np.searchsorted(per, s_at) - 1)
        f = (s_at - per[i]) / (per[i + 1] - per[i])
        q = ring_b[i] + f * (ring_b[(i + 1) % len(ring_b)] - ring_b[i])
        for sg in (-1.0, 1.0):
            seat = np.array([q[0], sg * RD_FLANGE_T, q[1]])
            b = _bolt(seat, seat + (0.0, sg * 0.009, 0.0), 0.016, (0.0, 0.0, 1.0))
            if b is not None:
                bolts.append(b)
    for sg in (-1.0, 1.0):
        for k in range(8):
            a = 2.0 * np.pi * (k + 0.5) / 8
            seat = np.array([0.135 * np.cos(a), sg * (half + 0.006), 0.135 * np.sin(a)])
            bolts.append(_bolt(seat, seat + (0.0, sg * 0.008, 0.0), 0.014, (0.0, 0.0, 1.0)))
    for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        seat = np.array([in_x + sx * 0.040, boss_face, in_z + sz * 0.040])
        bolts.append(_bolt(seat, seat + (0.0, -0.007, 0.0), 0.012, (0.0, 0.0, 1.0)))

    # ---------------- input shaft (2-3/16 in) with its 1/2 x 1/2 key on top
    key = table["ta6307h"]["input_shaft_key"]["v"]
    kw_, kh = float(key["w"]) / 1000.0, float(key["h"]) / 1000.0
    in_rod = _rod_y(tip, boss_face + 0.006, in_r, in_x, in_z, n_ring)
    key_len = min(float(key["length"]) / 1000.0, boss_face - tip - 0.004)
    in_key = c.box((in_x - kw_ / 2.0, tip + 0.004, in_z + in_r - kh / 2.0), (in_x + kw_ / 2.0, tip + 0.004 + key_len, in_z + in_r + kh / 2.0 - 0.001))
    input_shaft = c.merge_parts([in_rod, in_key])

    # ---------------- belt drive: centres, motor height, sheaves
    m1 = [float(x) / 1000.0 for x in t["mount_286T_position_B"]["belt_centers_M1"]["v"]]
    C = sum(m1) / 2.0 if centers is None else float(centers)
    z_m = float(np.sqrt(C * C - in_x * in_x)) + in_z + float(faults.get("motor_dz", 0.0))
    mot = iec_motor(kw, frames=motor_table, detail=detail)
    mH = float(mot["dims"]["H"])
    n_in = output_rpm * ratio
    pd_r = RD_SHEAVE_PD
    pd_m = pd_r * n_in / RD_MOTOR_RPM
    min_pd = _rv(table, "selection", "min_sheave_pd")
    if pd_r < min_pd:
        raise ValueError("reducer sheave under the G1-28 minimum")
    y_b = -RD_BELT_S
    (sh_r, r_or, w_sh) = _sheave(pd_r, in_r, in_x, y_b, in_z, n_ring)
    (sh_m, r_om, _) = _sheave(pd_m, float(mot["dims"]["D"]) / 2.0, 0.0, y_b + float(faults.get("sheave_dy", 0.0)), z_m, n_ring)
    sheaves = c.merge_parts([sh_r, sh_m])
    grooves = [y_b - w_sh / 2.0 + RD_F + g * RD_E for g in range(RD_GROOVES)]
    belts, belt_len = _belt_loops((in_x, in_z), pd_r / 2.0, (0.0, z_m), pd_m / 2.0, grooves, 24 if lod else 72)

    # ---------------- motor mount TA6307MM, position B: bars at the case sides, support channel, plate on rods
    plate_w = _rv(t, "mount_plate_position_B", "width")
    plate_l = _rv(t, "mount_plate_position_B", "side_plate_length")
    rods_l = _rv(t, "mount_plate_position_B", "side_plate_inner")
    z_sup = float(t["mount_plate_position_B"]["rows_from_output_cl"]["v"][0]) / 1000.0   # M1 row, 11.18 in
    z_sup += float(faults.get("support_dz", 0.0))
    s_end = tip + RD_READ["plate_end_C"][0] * IN       # plate end at the minimum C (closest to the belt plane)
    y0p, y1p = s_end, s_end + plate_l
    xo = plate_w / 2.0
    xi = xo - RD_BAR_T
    if xi <= hw:
        raise ValueError("mount bars do not clear the case")
    z_sup_bot = z_sup - RD_READ["support_depth"] * IN
    z_plate_top = z_m - mH                                # motor feet on the plate
    z_plate_bot = z_plate_top - RD_PLATE_T
    z_plate_min = z_sup + RD_READ["plate_gap"] * IN
    travel = z_plate_bot - z_plate_min
    post0 = tip + RD_READ["post_from_tip"] * IN       # post outer face (toward the input side)
    post1 = post0 + RD_READ["post_t"] * IN
    mount = []
    sub_support = []
    for sx in (-1.0, 1.0):
        xa, xb = sorted((sx * xi, sx * xo))
        mount.append(c.box((xa, post0, bot - 0.04), (xb, post1, z_sup_bot)))                        # bar
        mount.append(c.box((xa, y0p, z_sup_bot), (xb, y1p, z_sup - RD_WEB_T)))                       # channel flange
        knee = [(post1, z_sup_bot), (post1 + 0.16, z_sup_bot), (post1, z_sup_bot - 0.15)]            # gusset under the channel
        gv = np.array([[x, yy, zz] for x in (xa, xb) for yy, zz in knee])
        mount.append((gv, [np.array([[0, 2, 1], [3, 4, 5]]), np.array([[0, 1, 4, 3], [1, 2, 5, 4], [2, 0, 3, 5]])]))
        for zc in (st_ - 0.05, sb + 0.05):                                                              # clips to the flange
            ca, cb = sorted((sx * (hw - 0.017), sx * (xi - RD_GAP)))
            mount.append(c.box((ca, RD_FLANGE_T + RD_GAP, zc - 0.03), (cb, RD_FLANGE_T + 0.012, zc + 0.03)))
    web = c.box((-xo, y0p, z_sup - RD_WEB_T), (xo, y1p, z_sup))
    sub_support.append(web)
    mount.append(web)
    plate = c.box((-xo, y0p, z_plate_bot), (xo, y1p, z_plate_top))
    mount.append(plate)
    ry = ((plate_l - rods_l) / 2.0)
    for sx in (-1.0, 1.0):
        for yy in (y0p + ry, y1p - ry):
            x = sx * (xo - 0.026)
            mount.append(st.rod((x, yy, z_sup), (x, yy, z_plate_top + 0.04), RD_ROD_R, n_small))
            for zz in (z_plate_bot - 0.016, z_plate_top):
                mount.append(_bolt((x, yy, zz), (x, yy, zz + 0.016), 0.029, (1.0, 0.0, 0.0)))
            mount.append(_bolt((x, yy, z_sup), (x, yy, z_sup + 0.016), 0.029, (1.0, 0.0, 0.0)))
    mount = c.merge_parts([m for m in mount if m is not None])

    # ---------------- motor on the plate: shaft to -Y into the belt plane, feet on the plate top
    shoulder = float(np.asarray(mot["parts"]["endshield_de"][0])[:, 0].max())
    s_sh = -RD_SHOULDER_S

    def put_motor(piece):
        v = np.asarray(piece[0], float).reshape(-1, 3)
        out = np.column_stack([v[:, 1], s_sh - (v[:, 0] - shoulder), v[:, 2] + z_plate_top])
        return out, piece[1]

    motor_parts = {k: put_motor(p) for k, p in mot["parts"].items()}
    motor = c.merge_parts(list(motor_parts.values()))

    # ---------------- belt guard: hull of both rims + clearance, from just past the motor shoulder to past the shaft ends
    gs = float(faults.get("guard_scale", 1.0))
    ring_pts = []
    for (gx, gz), rr in (((in_x, in_z), r_or), ((0.0, z_m), r_om)):
        ring_pts += [(gx + (rr + RD_GUARD_CLEAR) * np.cos(a), gz + (rr + RD_GUARD_CLEAR) * np.sin(a))
                     for a in np.linspace(0, 2 * np.pi, n_ring, endpoint=False)]
    g_out = _hull2(ring_pts)
    g_mid = g_out.mean(axis=0)
    g_out = g_mid + (g_out - g_mid) * gs
    g_back = s_sh - 0.006
    shaft_end = min(tip, s_sh - float(mot["dims"]["E"]))
    g_front = shaft_end - 0.010
    guard_body = _swap_xy(_plate_x(g_out, g_front - RD_GUARD_T, g_back))
    guard = [guard_body]
    for gx, gz in ((-0.06, -0.20), (0.15, -0.20)):                      # straps to the case face
        guard.append(c.box((gx - 0.02, g_back, gz - 0.003), (gx + 0.02, -half - 0.007 - RD_GAP, gz + 0.003)))
    guard.append(c.box((0.09, g_back, z_plate_top - 0.03), (0.13, y0p - RD_GAP, z_plate_top)))   # bracket to the plate
    guard = c.merge_parts(guard)

    # ---------------- torque arm TA6307RA: at 90 deg to the output CL -> case pin line, down toward -X
    a_min, a_max = _rv(t, "torque_arm_length_min"), _rv(t, "torque_arm_length_max")
    L_arm = (a_min + a_max) / 2.0 if arm_len is None else float(arm_len)
    L_arm = float(faults.get("arm_len", L_arm))
    rad = p1 / np.linalg.norm(p1)
    tv = np.array([rad[1], -rad[0]])
    if tv[0] > 0:
        tv = -tv
    p2 = p1 + L_arm * tv
    t3 = np.array([tv[0], 0.0, tv[1]])
    P1, P2 = np.array([p1[0], 0.0, p1[1]]), np.array([p2[0], 0.0, p2[1]])
    cw = _rv(t, "torque_arm_clevis_width") / 2.0
    gap_c = RD_LUG_T / 2.0 + 0.001
    arm = [_flat_member(P1 - 0.030 * t3, P1 + 0.075 * t3, 0.024, gap_c, gap_c + RD_CHEEK),          # clevis at the case lug
           _flat_member(P1 - 0.030 * t3, P1 + 0.075 * t3, 0.024, -gap_c - RD_CHEEK, -gap_c)]
    arm.append(_flat_member(P1 + 0.055 * t3, P1 + 0.080 * t3, 0.024, -gap_c - RD_CHEEK, gap_c + RD_CHEEK))
    gb = RD_BRK_LUG_T / 2.0 + 0.001
    arm.append(_flat_member(P2 - 0.075 * t3, P2 + 0.030 * t3, 0.021, gb, cw))
    arm.append(_flat_member(P2 - 0.075 * t3, P2 + 0.030 * t3, 0.021, -cw, -gb))
    arm.append(_flat_member(P2 - 0.080 * t3, P2 - 0.055 * t3, 0.021, -cw, cw))
    mid = (P1 + P2) / 2.0
    tb = 0.150                                                        # EST turnbuckle body length
    arm.append(st.rod(P1 + 0.080 * t3, mid - 0.5 * tb * t3, RD_ARM_R, n_small))
    arm.append(st.rod(mid + 0.5 * tb * t3, P2 - 0.080 * t3, RD_ARM_R, n_small))
    hexr = np.array([(RD_TB_R * np.cos(a), RD_TB_R * np.sin(a)) for a in np.arange(6) * np.pi / 3])
    arm.append(st.member(mid - 0.5 * tb * t3, mid + 0.5 * tb * t3, hexr, up=(0.0, 1.0, 0.0)))
    for e in (-1.0, 1.0):
        nut = mid + e * (0.5 * tb + 0.012) * t3
        arm.append(st.member(nut - 0.011 * t3, nut + 0.011 * t3, hexr * 1.05, up=(0.0, 1.0, 0.0)))
    arm_body = c.merge_parts(arm)
    pin_case = _rod_y(-gap_c - RD_CHEEK - 0.012, gap_c + RD_CHEEK + 0.012, RD_LUG_PIN_R, p1[0], p1[1], n_small)
    bolt_r = 0.5 * 5.0 / 8.0 * IN                                       # 5/8 in bracket bolt (G1-80)
    pin_brk = _rod_y(-cw - 0.012, cw + 0.012, bolt_r, p2[0], p2[1], n_small)
    torque_arm = c.merge_parts([arm_body, pin_case, pin_brk])

    # ---------------- bracket (4.75 x 2.00 in, G1-80) on a stand post down to the floor
    b_len, b_h = _rv(t, "torque_arm_bracket_length"), _rv(t, "torque_arm_bracket_height")
    zb0 = p2[1] - b_h
    brk_base = c.box((p2[0] - b_len / 2.0, -RD_BRK_W / 2.0, zb0), (p2[0] + b_len / 2.0, RD_BRK_W / 2.0, zb0 + RD_BRK_T))
    lug_pts = [(p2[0] - 0.035, zb0 + RD_BRK_T), (p2[0] + 0.035, zb0 + RD_BRK_T)]
    lug_pts += [(p2[0] + 0.020 * np.cos(a), p2[1] + 0.020 * np.sin(a)) for a in np.linspace(0, np.pi, n_small)]
    brk_lug = _swap_xy(_plate_x(_hull2(lug_pts), -RD_BRK_LUG_T / 2.0, RD_BRK_LUG_T / 2.0))
    cap_w, cap_t = RD_STAND_CAP
    base_w, base_t = RD_STAND_BASE
    z_floor = float(floor_z) + float(faults.get("stand_gap", 0.0))
    if zb0 - cap_t - base_t - z_floor < 0.10:
        raise ValueError(f"torque-arm bracket {zb0 - float(floor_z):.3f} m over the floor: no room for a stand")
    post = st.member((p2[0], 0.0, z_floor + base_t), (p2[0], 0.0, zb0 - cap_t), st.shs(RD_STAND), up=(1.0, 0.0, 0.0))
    cap = c.box((p2[0] - cap_w / 2.0, -cap_w / 2.0, zb0 - cap_t), (p2[0] + cap_w / 2.0, cap_w / 2.0, zb0 - RD_GAP))
    base = c.box((p2[0] - base_w / 2.0, -base_w / 2.0, z_floor), (p2[0] + base_w / 2.0, base_w / 2.0, z_floor + base_t))
    stand = [post, cap, base]
    for sx in (-1.0, 1.0):
        g = _gusset(p2[0] + sx * RD_STAND / 2.0, p2[0] + sx * (base_w / 2.0 - 0.01), -0.004, 0.004, z_floor + base_t, z_floor + base_t + 0.09)
        gv = np.asarray(g[0], float).copy()
        # right triangle: the peak goes onto the post face
        gv[[2, 5], 0] = p2[0] + sx * RD_STAND / 2.0
        stand.append((gv, g[1]))
        for sy in (-1.0, 1.0):
            seat = np.array([p2[0] + sx * (base_w / 2.0 - 0.03), sy * (base_w / 2.0 - 0.03), z_floor + base_t])
            stand.append(_bolt(seat, seat + (0.0, 0.0, 0.012), 0.024, (1.0, 0.0, 0.0)))
    for sx in (-1.0, 1.0):
        seat = np.array([p2[0] + sx * (b_len / 2.0 - 0.016), 0.0, zb0 + RD_BRK_T])
        stand.append(_bolt(seat, seat + (0.0, 0.0, 0.010), 0.024, (1.0, 0.0, 0.0)))
    stand_all = c.merge_parts([brk_base, brk_lug] + [s for s in stand if s is not None])
    pedestal = c.merge_parts([post, cap, base])

    built = {"case": case, "bolts": c.merge_parts([b for b in bolts if b is not None]), "input_shaft": input_shaft,
             "mount": mount, "sheaves": sheaves, "belts": belts, "guard": guard, "torque_arm": torque_arm,
             "stand": stand_all, "motor": motor}
    sub = {"housing": housing, "hub": hub, "input_rod": in_rod, "sheave_r": sh_r, "sheave_m": sh_m, "plate": plate,
           "support": c.merge_parts(sub_support), "guard_body": guard_body, "arm_body": arm_body, "pin_case": pin_case,
           "pin_bracket": pin_brk, "bracket_base": brk_base, "bracket_lug": brk_lug, "pedestal": pedestal}
    bb_min = np.min([np.asarray(p[0]).min(axis=0) for p in built.values()], axis=0)
    bb_max = np.max([np.asarray(p[0]).max(axis=0) for p in built.values()], axis=0)
    out_rpm = RD_MOTOR_RPM * pd_m / pd_r / ratio
    dims = {
        "reducer": reducer, "ratio": ratio, "kw": float(kw), "motor_frame": mot["dims"]["frame"],
        "output_rpm": float(output_rpm), "output_rpm_model": float(out_rpm), "input_rpm": float(n_in),
        "sheave_pd": [pd_r, float(pd_m)], "belt_centers": float(C), "belt_plane_y": y_b, "belt_pitch_length": belt_len,
        "belt_speed_m_s": float(np.pi * pd_m * RD_MOTOR_RPM / 60.0),
        "input_axis": [float(in_x), float(in_z)], "input_tip_y": float(tip), "motor_axis": [0.0, float(z_m)],
        "plate_travel": float(travel), "plate_travel_max": RD_READ["plate_travel"] * IN,
        "pin_case": p1.tolist(), "pin_bracket": p2.tolist(), "arm_len": float(L_arm), "floor_z": float(floor_z),
        "stand_height": float(zb0 - floor_z), "split_half": half, "hub_y": [-A_len / 2.0, A_len / 2.0],
        "motor_y": [float(motor[0][:, 1].min()), float(motor[0][:, 1].max())],
        "bbox": {"min": bb_min.tolist(), "max": bb_max.tolist()},
        "faces": sum(_count_faces(p[1]) for p in built.values()),
    }
    return {"parts": built, "dims": dims, "motor_parts": motor_parts, "sub": sub}


# ====================================================================== duct axial fan, motor under the roof (C7a)
#
# Silo roof fan (SITE silo_roof.fans; research/silo_equipment.md §4): an axial fan in the throat of a roof vent, Ø0.40
# impeller, 0.25 kW, the motor below the roof (analog Symaga HCDF-40, rec_98965c19). Sourced: axial type, impeller
# ≈ 400 mm, 0.25 kW, motor Ø140 × 200 below the roof. The motor frame is the IEC 71 of iec_motor(0.25) (AC 141 ≈ Ø140,
# housing 200 mm), shaft up, its feet bolted to a plate that two ribs weld to the casing. Every other number is EST.
#
# Local frame: axis +Z = flow (out of the silo), origin on the axis in the plane of the motor drive-end shoulder, the
# shaft points +Z into the hub, the motor feet face -Y. The casing hangs below the origin around the motor and rises
# to `top`; its outer radius is the roof hole radius.

DF_BLADES = 6              # EST: 5-8 blades on a Ø0.4 duct fan
DF_STAGGER_TIP = 22.0      # EST: blade angle to the rotation plane at the tip, deg
DF_CHORD = (0.070, 0.062)  # EST: blade chord at the root / tip, m
DF_THICK = (0.09, 0.06)    # EST: thickness / chord, root / tip
DF_CAMBER = 0.05           # EST: camber / chord
DF_HUB_R = 0.070           # EST: hub = motor fin radius, hub / tip diameter ratio 0.35
DF_HUB_LEN = 0.070         # EST: hub axial length, covers the shaft end (E = 30 mm) with 40 mm to spare
DF_TIP_GAP = 0.005         # EST: tip clearance 5 mm = 1.25 % D (small fans 0.5-2 % D)
DF_SHEET = 0.003           # EST: casing sheet
DF_THROAT_H = 0.030        # EST: throat ring half height beyond the blade section
DF_PLATE_T = 0.008         # EST: motor foot plate
DF_RIB_T = 0.010           # EST: rib between plate and casing
DF_WIRE_R = 0.0015         # EST: grille wire Ø3
DF_GRILLE_PITCH = 0.025    # EST: grille ring pitch 25 mm
DF_SPOKES = 12             # EST
DF_FLANGE_W = 0.045        # EST: top flange ring width
DF_GAP = 0.0005            # parts that bear on each other keep 0.5 mm, so BVH does not read contact


def _torus_z(radius, z, tube_r, n_seg, n_tube):
    """Closed wire ring in the XY plane at height z: n_tube-sided section of radius tube_r along a circle."""
    a = np.linspace(0.0, 2.0 * np.pi, n_seg + 1)
    b = np.linspace(0.0, 2.0 * np.pi, n_tube, endpoint=False)
    rr = radius + tube_r * np.cos(b)
    zz = z + tube_r * np.sin(b)
    rows = [np.column_stack([rr * np.cos(a_), rr * np.sin(a_), zz]) for a_ in a]
    return np.concatenate(rows), c.grid_faces(n_seg + 1, n_tube, wrap_cols=True)


def duct_axial_fan(d_impeller, kw, *, hole_d, top, blades=DF_BLADES, detail="full", motor_table=None, faults=None):
    """Axial duct fan for a roof vent: casing (shell, rolled lip, throat ring, top flange), impeller (hub, twisted cambered
    blades), finger guard (concentric wire rings + spokes), IEC motor `iec_motor(kw)` shaft up, foot plate on two ribs.

    `hole_d`: roof hole Ø = casing outer Ø. `top`: casing top above the shoulder plane (m). `faults` inject the check's broken
    cases: impeller_d_err (m), tip_gap (m), rotor_dz (m, impeller + hub moved on the shaft), motor_dx (m), plate_dy (m,
    foot plate moved off the feet), blades (int), no_twist (every section at the tip angle), grille ("plate": solid disc
    instead of wires).
    Returns {"parts", "dims", "motor_parts", "sub"}; metres.
    """
    if detail not in ("full", "lod"):
        raise ValueError("detail must be full or lod")
    faults = faults or {}
    lod = detail == "lod"
    n_ring = 40 if lod else 120
    n_hub = 16 if lod else 40
    n_small = 6 if lod else 10
    m_foil = 7 if lod else 14
    n_st = 4 if lod else 8
    n_wire = 28 if lod else 72
    blades = int(faults.get("blades", blades))

    d = float(d_impeller) + float(faults.get("impeller_d_err", 0.0))
    r_tip = d / 2.0
    gap = float(faults.get("tip_gap", DF_TIP_GAP))
    r_casing = float(hole_d) / 2.0
    t = DF_SHEET
    r_in = r_casing - t
    r_throat = r_tip + gap
    if r_throat > r_in:
        raise ValueError("impeller Ø%.3f does not fit the Ø%.3f casing" % (d, hole_d))

    # ---------------- motor, shaft up the axis; motor-local x is axial (NDE housing face at 0)
    mot = iec_motor(kw, frames=motor_table, detail=detail)
    mp = mot["parts"]
    H = float(mot["dims"]["H"])
    shoulder = float(np.asarray(mp["endshield_de"][0])[:, 0].max())
    tip = float(np.asarray(mp["shaft"][0])[:, 0].max())
    cowl = float(np.asarray(mp["fan_cover"][0])[:, 0].min())
    fv = np.asarray(mp["feet"][0], float)
    mdx = float(faults.get("motor_dx", 0.0))

    def put_motor(piece):
        v = np.asarray(piece[0], float).reshape(-1, 3)
        return np.column_stack([v[:, 1] + mdx, v[:, 2] - H, v[:, 0] - shoulder]), piece[1]

    motor_parts = {k: put_motor(p) for k, p in mp.items()}
    z_nose = cowl - shoulder                              # motor fan-cowl nose, negative

    # ---------------- impeller on the shaft end; blades centred on the hub, the whole rotor can slide for the broken case
    rdz = float(faults.get("rotor_dz", 0.0))
    a_h0 = 0.006 + rdz
    a_h1 = a_h0 + DF_HUB_LEN
    a_b = 0.5 * (a_h0 + a_h1)
    r_h = DF_HUB_R
    beta_root = _blade_angle(r_h, r_tip, np.radians(DF_STAGGER_TIP))
    c_root = min(DF_CHORD[0], (a_h1 - a_h0 - 0.016) / np.sin(beta_root))
    radii = np.linspace(r_h - 0.003, r_tip, n_st)
    blade_meshes = []
    for k in range(blades):
        th0 = -2.0 * np.pi * k / blades
        loops = []
        for r in radii:
            s = (r - radii[0]) / (radii[-1] - radii[0])
            chord = c_root + (DF_CHORD[1] - c_root) * s
            ratio = DF_THICK[0] + (DF_THICK[1] - DF_THICK[0]) * s
            beta = (np.radians(DF_STAGGER_TIP) if faults.get("no_twist")
                    else _blade_angle(max(r, r_h), r_tip, np.radians(DF_STAGGER_TIP)))
            loops.append(_blade_loop(r, th0, a_b, chord, beta, ratio, DF_CAMBER, m_foil))
        blade_meshes.append(_foil_mesh(loops))
    bz = np.concatenate([np.asarray(b[0])[:, 2] for b in blade_meshes])
    b_lo, b_hi = float(bz.min()), float(bz.max())
    fair = 0.5 * r_h
    hub_p = [
        _x_to_z(_tube(a_h0, a_h1, r_h, 0.0, n_hub)),
        _x_to_z(_disk_x(a_h0, 0.0, r_h, n_hub)),
        _x_to_z(_frustum_x(a_h1, a_h1 + fair, r_h, 0.010, 0.0, n_hub)),
        _x_to_z(_disk_x(a_h1 + fair, 0.0, 0.010, n_hub)),
    ]
    impeller = c.merge_parts(hub_p + blade_meshes)

    # ---------------- casing: sheet shell, rolled lip under the motor, throat ring at the blades, top flange
    z_bot = z_nose - 0.020
    z_top = float(top)
    thr0, thr1 = b_lo - DF_THROAT_H, b_hi + DF_THROAT_H
    casing = c.merge_parts([
        _x_to_z(_shell_x(z_bot, z_top, r_casing, r_casing, t, n_ring)),
        _x_to_z(_shell_x(z_bot - 0.025, z_bot, r_casing + 0.020, r_casing, t, n_ring)),
        _x_to_z(_ring_x(thr0, thr1, r_throat, r_in + 0.0005, n_ring)),
        _x_to_z(_ring_x(z_top - 0.008, z_top, r_in + 0.0005, r_casing + DF_FLANGE_W, n_ring)),
    ])

    # ---------------- finger guard on the top flange: concentric wire rings and spokes (or a solid plate, broken case)
    z_g = z_top + DF_WIRE_R
    if faults.get("grille") == "plate":
        grille = _x_to_z(_disk_x(z_g, 0.0, r_in, n_ring))
    else:
        parts = []
        k_rings = int(np.floor((r_in - r_h) / DF_GRILLE_PITCH))
        for i in range(1, k_rings + 1):
            parts.append(_torus_z(r_h + i * DF_GRILLE_PITCH if i < k_rings else r_in - DF_WIRE_R, z_g, DF_WIRE_R, n_wire, 6))
        for k in range(DF_SPOKES):
            a = 2.0 * np.pi * k / DF_SPOKES
            parts.append(st.rod((0.01 * np.cos(a), 0.01 * np.sin(a), z_g), ((r_in - DF_WIRE_R) * np.cos(a), (r_in - DF_WIRE_R) * np.sin(a), z_g),
                                DF_WIRE_R, n_small))
        parts.append(_x_to_z(_disk_x(z_g, 0.0, 0.012, n_small * 2)))
        grille = c.merge_parts(parts)

    # ---------------- foot plate behind the feet, two ribs back to the casing wall
    px = max(abs(float(fv[:, 1].min())), abs(float(fv[:, 1].max()))) + 0.010
    fz = np.concatenate([np.asarray(motor_parts["feet"][0])[:, 2]])
    pz0, pz1 = float(fz.min()) - 0.015, float(fz.max()) + 0.015
    py1 = -H - DF_GAP + float(faults.get("plate_dy", 0.0))
    py0 = py1 - DF_PLATE_T
    plate = c.box((-px, py0, pz0), (px, py1, pz1))
    br = [plate]
    for sx in (-1.0, 1.0):
        xr = sx * (px - 0.012)
        y_wall = -float(np.sqrt(r_in ** 2 - xr ** 2))
        br.append(c.box((xr - DF_RIB_T / 2.0, y_wall - 0.002, pz0), (xr + DF_RIB_T / 2.0, py0 + 0.001, pz1)))
    bracket = c.merge_parts(br)
    motor = c.merge_parts(list(motor_parts.values()))
    built = {"casing": casing, "impeller": impeller, "grille": grille, "bracket": bracket, "motor": motor}
    sub = {"blades": c.merge_parts(blade_meshes), "hub": c.merge_parts(hub_p), "plate": plate,
           "throat": _x_to_z(_ring_x(thr0, thr1, r_throat, r_in + 0.0005, n_ring))}

    all_v = np.concatenate([np.asarray(p[0]).reshape(-1, 3) for p in built.values()])
    lo, hi = _bbox(all_v)
    part_dims = {}
    for name, (verts, faces) in built.items():
        p0, p1 = _bbox(verts)
        part_dims[name] = {"min": p0.tolist(), "max": p1.tolist(), "faces": _count_faces(faces)}
    dims = {
        "d_impeller": float(d_impeller), "kw": float(kw), "motor_frame": mot["dims"]["frame"], "blades": int(blades),
        "tip_gap": gap, "r_tip": r_tip, "r_casing": r_casing, "r_throat": r_throat, "hub_r": r_h,
        "stagger_deg": [float(np.degrees(beta_root)), DF_STAGGER_TIP], "chord": [float(c_root), DF_CHORD[1]],
        "z_blades": [b_lo, b_hi], "z_hub": [a_h0, a_h1 + fair], "z_shoulder": 0.0, "z_nose": z_nose,
        "z_casing": [z_bot - 0.025, z_top], "z_grille": z_g, "motor_housing_len": float(np.asarray(mp["body"][0])[:, 0].max()),
        "motor_dia": 2.0 * float(mot["dims"]["parts"]["fan_cover"]["max"][1]),
        "bbox": {"min": lo.tolist(), "max": hi.tolist()},
        "faces": sum(_count_faces(p[1]) for p in built.values()), "parts": part_dims,
    }
    return {"parts": built, "dims": dims, "motor_parts": motor_parts, "sub": sub}


# ====================================================================== axial fan, motor in the air stream
#
# STRAHL FR dryer fans after GCS «Опис конструкції» p.4-5 (research/design/dryer/strahl_fr_anatomy.md §2): axial
# fans, steel rotor Ø1000 mm straight on the motor shaft (direct drive, no transmission), a row of guide vanes under
# the rotor that carries the motor and matches the blade direction, the motor sits in the air stream and is cooled by
# a tube of outside air (GCS p.5). Sourced: axial type, Ø1000, direct drive, vanes under the rotor carrying the motor,
# cooling tube, the kW of each fan (22 / 11, PDF p.1). Every other number below is EST.
#
# Local frame: axis +Z = flow direction (inlet below, vanes, then the rotor), origin on the axis in the shroud inlet
# plane (z=0; the inlet bell flares below it). The motor shaft points +Z into the rotor hub, the motor feet face -Y
# and bolt to a bracket plate that two ribs tie to the vane hub ring; the cooling tube leaves the motor fan cowl
# along +X. The rotor turns toward -theta (clockwise seen from the outlet); the vanes pre-swirl against it.

AF_PARTS = ("shroud", "rotor", "vanes", "bracket", "motor", "cooling")
AF_BLADES = 8              # EST: blade count not given (adjustable-pitch axial fans of this size carry 6-12)
AF_VANES = 7               # EST: vane count not given; odd and prime to the blade count (no blade-pass coincidence)
AF_STAGGER_TIP = 22.0      # EST: blade angle to the rotation plane at the tip, deg (dealer FR sheets: variable pitch)
AF_CHORD = (0.14, 0.16)    # EST: blade chord at the root / tip, m (root shortened to fit the hub when needed)
AF_THICK = (0.08, 0.05)    # EST: blade thickness / chord at the root / tip (NACA 4-digit thickness law)
AF_CAMBER = 0.04           # EST: blade camber / chord
AF_HUB_OF_D = 0.35         # EST: hub-to-tip diameter ratio
AF_TIP_GAP = 0.004         # EST: blade tip clearance 4 mm = 0.4 % D (fan texts give 0.1-1 % D)
AF_SHEET = 0.004           # EST: shroud, vane and ring sheet
AF_PLATE_T = 0.012         # EST: motor bracket plate
AF_VANE_H = 0.12           # EST: vane axial length
AF_VANE_GAP = 0.04         # EST: axial gap vanes -> blades
AF_VANE_TURN = 18.0        # EST: vane exit angle off the axis, deg
AF_INLET = 0.08            # EST: shroud inlet plane under the vanes
AF_OUTLET = 0.08           # EST: shroud past the blades
AF_BELL = (0.06, 0.06)     # EST: inlet bell depth and flare
AF_COOL_R = 0.035          # EST: cooling tube Ø70 (GCS p.5 names the tube, no size)
AF_GAP = 0.0005            # parts that bear on each other keep 0.5 mm (as RD_GAP), so BVH does not read contact


def _x_to_z(piece):
    """Turn a piece built along +X (axis through y=z=0) to the +Z axis: (x, y, z) -> (y, z, x), right-handed."""
    v = np.asarray(piece[0], float).reshape(-1, 3)
    return v[:, [1, 2, 0]].copy(), piece[1]


def _foil_mesh(loops):
    """Closed section loops (upper LE->TE, then lower TE->LE, 2m points each) stacked root -> tip, with end caps."""
    loops = [np.asarray(lp, float) for lp in loops]
    n, k = len(loops), len(loops[0])
    m = k // 2
    verts = np.concatenate(loops)
    side = c.grid_faces(n, k, wrap_cols=True)
    cap = np.array([[i, i + 1, k - 2 - i, k - 1 - i] for i in range(m - 1)], np.int64)
    return verts, [side, cap[:, ::-1], cap + (n - 1) * k]


def _naca_half(xi, ratio, chord, t_min):
    y = 5.0 * ratio * (0.2969 * np.sqrt(xi) - 0.1260 * xi - 0.3516 * xi ** 2 + 0.2843 * xi ** 3 - 0.1015 * xi ** 4)
    return np.maximum(y * chord, t_min / 2.0)


def _blade_loop(r, theta0, a_mid, chord, beta, ratio, camber, m):
    """One blade section on the cylinder of radius r: chord at `beta` to the rotation plane, leading edge upstream on
    the side the blade moves to (-theta), camber bulging to the suction side. Returns a (2m, 3) loop."""
    xi = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, m)))
    half = _naca_half(xi, ratio, chord, 0.0015)
    eta_c = camber * chord * 4.0 * xi * (1.0 - xi)
    d = np.array([np.cos(beta), np.sin(beta)])             # (s, a) along the chord, LE -> TE
    nrm = np.array([-np.sin(beta), np.cos(beta)])          # chord normal, pressure side
    u = (xi - 0.5) * chord

    def side(sign):
        eta = -eta_c + sign * half
        return u[:, None] * d[None, :] + eta[:, None] * nrm[None, :]
    sa = np.vstack([side(1.0), side(-1.0)[::-1]])
    th = theta0 + sa[:, 0] / r
    return np.column_stack([r * np.cos(th), r * np.sin(th), a_mid + sa[:, 1]])


def _vane_loop(r, theta0, a0, a1, turn, t, m):
    """Guide vane section: axial at the inlet, turned `turn` toward +theta (against the rotor) at the outlet, sheet t."""
    u = np.linspace(0.0, 1.0, m)
    h = a1 - a0
    s = 0.5 * h * np.tan(turn) * u ** 2
    a = a0 + h * u
    ds = h * np.tan(turn) * u
    nrm = np.column_stack([np.full(m, h), -ds])
    nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    up = np.column_stack([s, a]) + nrm * t / 2.0
    lo = np.column_stack([s, a]) - nrm * t / 2.0
    sa = np.vstack([up, lo[::-1]])
    th = theta0 + sa[:, 0] / r
    return np.column_stack([r * np.cos(th), r * np.sin(th), sa[:, 1]])


def _blade_angle(r, r_tip, beta_tip):
    """Blade angle to the rotation plane: tan(beta) * r = const (axial inflow, free vortex), EST law."""
    return float(np.arctan(np.tan(beta_tip) * r_tip / r))


def axial_fan(d_rotor, kw, *, blades=AF_BLADES, vanes=AF_VANES, tip_gap=AF_TIP_GAP, cool_reach=None, deck_r=None,
              detail="full", motor_table=None, faults=None):
    """Axial fan with the motor in the air stream (STRAHL FR, GCS p.4): shroud with inlet bell and outlet flange,
    rotor (hub, tail fairing, twisted cambered blades), guide vanes under the rotor on a hub ring, motor bracket plate
    on two ribs to that ring, IEC B3 motor iec_motor(kw) on the axis, cooling tube from the motor cowl out along +X.

    `cool_reach`: the cooling-tube end along +X from the axis (default 0.15 m past the shroud). `deck_r`: outer radius
    of a mounting deck ring in the inlet plane (None: no deck). `faults` inject the check's broken cases: rotor_d_err
    (m, the whole fan built for a wrong diameter), tip_gap (m), vanes_dz (m), motor_dx (m).
    Returns {"parts", "dims", "motor_parts", "sub"}; metres, local frame in the comment above.
    """
    if detail not in ("full", "lod"):
        raise ValueError("detail must be full or lod")
    faults = faults or {}
    lod = detail == "lod"
    n_ring = 32 if lod else 128
    n_hub = 16 if lod else 48
    n_small = 8 if lod else 20
    m_foil = 7 if lod else 16
    n_st = 4 if lod else 9

    d = float(d_rotor) + float(faults.get("rotor_d_err", 0.0))
    r_tip = d / 2.0
    gap = float(faults.get("tip_gap", tip_gap))
    r_sh = r_tip + gap
    t = AF_SHEET
    r_h = AF_HUB_OF_D * r_tip

    # ---------------- motor, shaft up the axis; motor-local x is the axial coordinate (NDE housing face at x=0)
    mot = iec_motor(kw, frames=motor_table, detail=detail)
    mp = mot["parts"]
    H = float(mot["dims"]["H"])
    shoulder = float(np.asarray(mp["endshield_de"][0])[:, 0].max())
    tip = float(np.asarray(mp["shaft"][0])[:, 0].max())
    cowl = float(np.asarray(mp["fan_cover"][0])[:, 0].min())
    fv = np.asarray(mp["feet"][0], float)

    # ---------------- rotor: hub over the shaft end, blades centred on the hub (axial a: NDE housing face at 0)
    a_h0, a_h1 = shoulder + 0.006, tip + 0.010
    a_b = 0.5 * (a_h0 + a_h1)
    beta_root = _blade_angle(r_h, r_tip, np.radians(AF_STAGGER_TIP))
    c_root = min(AF_CHORD[0], (a_h1 - a_h0 - 0.016) / np.sin(beta_root))
    radii = np.linspace(r_h - 0.003, r_tip, n_st)
    blade_meshes = []
    for k in range(blades):
        th0 = -2.0 * np.pi * k / blades
        loops = []
        for r in radii:
            s = (r - radii[0]) / (radii[-1] - radii[0])
            chord = c_root + (AF_CHORD[1] - c_root) * s
            ratio = AF_THICK[0] + (AF_THICK[1] - AF_THICK[0]) * s
            beta = _blade_angle(max(r, r_h), r_tip, np.radians(AF_STAGGER_TIP))
            loops.append(_blade_loop(r, th0, a_b, chord, beta, ratio, AF_CAMBER, m_foil))
        blade_meshes.append(_foil_mesh(loops))
    bz = np.concatenate([np.asarray(b[0])[:, 2] for b in blade_meshes])
    b_lo, b_hi = float(bz.min()), float(bz.max())

    # ---------------- vanes under the blades; the shroud inlet plane AF_INLET under the vanes is the local origin
    shift = -(b_lo - AF_VANE_GAP - AF_VANE_H - AF_INLET)        # z_local = a + shift
    a_v1 = b_lo - AF_VANE_GAP + float(faults.get("vanes_dz", 0.0))
    a_v0 = a_v1 - AF_VANE_H

    # bracket plate behind the feet (the feet face -Y, their sole at Y = -H) and the hub ring that carries it
    fx0, fx1 = float(fv[:, 0].min()), float(fv[:, 0].max())
    px = max(abs(float(fv[:, 1].min())), abs(float(fv[:, 1].max()))) + 0.010
    pz0, pz1 = fx0 - 0.015, fx1 + 0.015
    py1 = -H - AF_GAP
    py0 = py1 - AF_PLATE_T
    a_r0, a_r1 = min(a_v0, pz1 - 0.10), a_v1
    mdx = float(faults.get("motor_dx", 0.0))

    def z(a):
        return a + shift

    def put_motor(piece):
        v = np.asarray(piece[0], float).reshape(-1, 3)
        return np.column_stack([v[:, 1] + mdx, v[:, 2] - H, v[:, 0] + shift]), piece[1]

    motor_parts = {k: put_motor(p) for k, p in mp.items()}
    body = np.concatenate([np.asarray(v[0]) for k, v in motor_parts.items() if k != "shaft"])
    band = body[(body[:, 2] >= z(a_r0) - 0.005) & (body[:, 2] <= z(a_r1) + 0.005)]
    reach = float(np.hypot(band[:, 0] - mdx, band[:, 1]).max()) if len(band) else 0.0
    r_ring = max(reach, float(np.hypot(px, py0))) + 0.010
    if r_ring + t > r_sh - 0.05:
        raise ValueError("motor too large for the hub ring inside a Ø%.3f shroud" % d)

    # ---------------- shroud: cylinder, inlet bell, outlet flange, optional deck ring in the inlet plane
    z_top = z(b_hi) + AF_OUTLET
    shroud_p = [
        _x_to_z(_shell_x(0.0, z_top, r_sh + t, r_sh + t, t, n_ring)),
        _x_to_z(_shell_x(-AF_BELL[0], 0.0, r_sh + t + AF_BELL[1], r_sh + t, t, n_ring)),
        _x_to_z(_ring_x(z_top - 0.008, z_top, r_sh + t - 0.0005, r_sh + 0.045, n_ring)),
    ]
    if deck_r is not None:
        shroud_p.append(_x_to_z(_ring_x(0.0, 0.006, r_sh + t - 0.0005, float(deck_r), n_ring)))
    shroud = c.merge_parts(shroud_p)

    # ---------------- rotor: hub, tail fairing (downstream; the motor body is the nose upstream), blades
    fair = 0.7 * r_h
    rotor_p = [
        _x_to_z(_tube(z(a_h0), z(a_h1), r_h, 0.0, n_hub)),
        _x_to_z(_disk_x(z(a_h0), 0.0, r_h, n_hub)),
        _x_to_z(_frustum_x(z(a_h1), z(a_h1) + fair, r_h, 0.012, 0.0, n_hub)),
        _x_to_z(_disk_x(z(a_h1) + fair, 0.0, 0.012, n_hub)),
    ]
    blades_placed = [(np.asarray(v, float) + [0.0, 0.0, shift], f) for v, f in blade_meshes]
    rotor = c.merge_parts(rotor_p + blades_placed)

    # ---------------- vanes on the hub ring, welded 1 mm into the shroud wall
    vane_p = [_x_to_z(_shell_x(z(a_r0), z(a_r1), r_ring + t, r_ring + t, t, n_ring))]
    v_radii = np.linspace(r_ring + t - 0.001, r_sh + 0.001, 3 if lod else 5)
    for k in range(vanes):
        th0 = 2.0 * np.pi * (k + 0.5) / vanes
        vane_p.append(_foil_mesh([_vane_loop(r, th0, z(a_v0), z(a_v1), np.radians(AF_VANE_TURN), t, m_foil) for r in v_radii]))
    vanes_m = c.merge_parts(vane_p)

    # ---------------- motor bracket: plate behind the feet, two ribs back to the hub ring
    plate = c.box((-px, py0, z(pz0)), (px, py1, z(pz1)))
    br = [plate]
    rz0, rz1 = max(z(pz0), z(a_r0)), z(pz1)
    for sx in (-1.0, 1.0):
        xr = sx * (px - 0.012)
        y_ring = -float(np.sqrt(r_ring ** 2 - xr ** 2))
        br.append(c.box((xr - 0.005, y_ring - 0.002, rz0), (xr + 0.005, py0 + 0.001, rz1)))
    bracket = c.merge_parts(br)

    # ---------------- cooling tube: bell under the motor fan cowl, down, then out along +X to outside air
    a_c = z(cowl) - 0.006
    fin_r = float(mot["dims"]["parts"]["fan_cover"]["max"][1])
    reach_x = float(cool_reach) if cool_reach is not None else r_sh + 0.15
    z_e = a_c - 0.06 - 1.5 * AF_COOL_R
    cool = c.merge_parts([
        _x_to_z(_shell_x(a_c - 0.06, a_c, AF_COOL_R + 0.003, 0.92 * fin_r, 0.003, n_hub)),
        st.rod((0.0, 0.0, a_c - 0.059), (0.0, 0.0, z_e - AF_COOL_R), AF_COOL_R, n_small),
        st.rod((-AF_COOL_R, 0.0, z_e), (reach_x, 0.0, z_e), AF_COOL_R, n_small),
        _shift(_ring_x(reach_x - 0.012, reach_x, AF_COOL_R - 0.002, AF_COOL_R + 0.02, n_small), dz=z_e),
    ])
    motor = c.merge_parts(list(motor_parts.values()))
    built = {"shroud": shroud, "rotor": rotor, "vanes": vanes_m, "bracket": bracket, "motor": motor, "cooling": cool}
    sub = {"blades": c.merge_parts(blades_placed), "hub": c.merge_parts(rotor_p), "plate": plate, "vane_ring": vane_p[0]}

    all_v = np.concatenate([np.asarray(p[0]).reshape(-1, 3) for p in built.values()])
    lo, hi = _bbox(all_v)
    part_dims = {}
    for name, (verts, faces) in built.items():
        p0, p1 = _bbox(verts)
        part_dims[name] = {"min": p0.tolist(), "max": p1.tolist(), "faces": _count_faces(faces)}
    dims = {
        "d_rotor": float(d_rotor), "kw": float(kw), "motor_frame": mot["dims"]["frame"], "blades": int(blades),
        "vanes": int(vanes), "tip_gap": gap, "r_tip": r_tip, "r_shroud": r_sh, "hub_r": r_h, "ring_r": r_ring,
        "stagger_deg": [float(np.degrees(beta_root)), AF_STAGGER_TIP], "chord": [float(c_root), AF_CHORD[1]],
        "z_blades": [z(b_lo), z(b_hi)], "z_vanes": [z(a_v0), z(a_v1)], "z_hub": [z(a_h0), z(a_h1) + fair],
        "z_outlet": z_top, "z_motor": [z(cowl), z(tip)], "cool_end": [reach_x, 0.0, z_e],
        "bbox": {"min": lo.tolist(), "max": hi.tolist()},
        "faces": sum(_count_faces(p[1]) for p in built.values()), "parts": part_dims,
    }
    return {"parts": built, "dims": dims, "motor_parts": motor_parts, "sub": sub}
