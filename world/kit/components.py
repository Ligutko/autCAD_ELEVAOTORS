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
    y_rail = C1 / 2.0 + rail_b / 2.0
    chan = st.channel(rail_h, rail_b, rail_tw, rail_tf)
    frame_parts = [
        st.member((x_r0, y_rail, rail_h / 2.0), (x_r1, y_rail, rail_h / 2.0), chan),
        st.member((x_r0, -y_rail, rail_h / 2.0), (x_r1, -y_rail, rail_h / 2.0), chan, roll=np.pi),
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
    dims = {
        "size": FAN_SIZE, "hand": hand, "outlet_deg": outlet_deg, "kw": float(kw),
        "motor_frame": mot["dims"]["frame"], "axis_z": axis_z, "wheel_d": 2.0 * wheel_r,
        "housing_w": w, "inlet_face_x": x_face, "length": float(np.asarray(motor[0])[:, 0].max()) - x_face,
        "foot_z": foot_z, "motor_x0": x0_motor, "mass_kg": float(table["motor"]["mass_kg"]["v"]),
        "bbox": {"min": bb_min.tolist(), "max": bb_max.tolist()},
        "faces": sum(_count_faces(p[1]) for p in built.values()),
    }
    return {"parts": built, "dims": dims, "motor_parts": motor_parts}
