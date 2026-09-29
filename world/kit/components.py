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
