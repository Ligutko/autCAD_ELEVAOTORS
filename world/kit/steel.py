"""Structural steel kit: profiles, members, grating, handrails, stairs.

Sizes follow common rolled sections (STD EN 10219 SHS, EN 10056 angles, EN 10365 HEA/IPE)
and EN ISO 14122-2/3 for walkways, stairs and guard rails.
"""

import math

import bpy  # noqa: F401,I001  bpy first: the pip module registers mathutils
import numpy as np

from . import common as c

# ------------------------------------------------------------------ profiles (u, v) in metres


def shs(b, t=None):
    """Square hollow section, outer outline only (ends are capped)."""
    h = b / 2
    return np.array([(-h, -h), (h, -h), (h, h), (-h, h)])


def angle(b, t):
    """Equal angle L b x b x t, heel at the origin."""
    return np.array([(0, 0), (b, 0), (b, t), (t, t), (t, b), (0, b)])


def i_beam(h, b, tw, tf):
    """I / H section centred on the web."""
    hh, hb, ht = h / 2, b / 2, tw / 2
    return np.array([(-hb, -hh), (hb, -hh), (hb, -hh + tf), (ht, -hh + tf), (ht, hh - tf), (hb, hh - tf),
                     (hb, hh), (-hb, hh), (-hb, hh - tf), (-ht, hh - tf), (-ht, -hh + tf), (-hb, -hh + tf)])


def flat(b, t):
    return np.array([(-t / 2, -b / 2), (t / 2, -b / 2), (t / 2, b / 2), (-t / 2, b / 2)])


def channel(h, b, tw, tf):
    hh = h / 2
    return np.array([(0, -hh), (b, -hh), (b, -hh + tf), (tw, -hh + tf), (tw, hh - tf), (b, hh - tf),
                     (b, hh), (0, hh)])


SHS_200 = shs(0.200)
SHS_150 = shs(0.150)
SHS_100 = shs(0.100)
SHS_60 = shs(0.060)
L90 = angle(0.090, 0.008)
L75 = angle(0.075, 0.007)
L50 = angle(0.050, 0.005)
HEA200 = i_beam(0.190, 0.200, 0.0065, 0.010)
IPE160 = i_beam(0.160, 0.082, 0.005, 0.0074)
UPN160 = channel(0.160, 0.065, 0.0075, 0.0105)
FLAT_60x10 = flat(0.060, 0.010)


def member(p0, p1, profile, up=(0.0, 0.0, 1.0), roll=0.0):
    """Extrude a 2D profile from p0 to p1. Profile u axis -> side, v axis -> up."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    length = np.linalg.norm(d)
    if length < 1e-6:
        return np.zeros((0, 3)), np.zeros((0, 4), int)
    d /= length
    up = np.asarray(up, float)
    if abs(np.dot(up, d)) > 0.99:
        up = np.array([1.0, 0.0, 0.0]) if abs(d[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    side = np.cross(d, up)
    side /= np.linalg.norm(side)
    upv = np.cross(side, d)
    if roll:
        cr, sr = math.cos(roll), math.sin(roll)
        side, upv = side * cr + upv * sr, -side * sr + upv * cr
    prof = np.asarray(profile, float)
    k = len(prof)
    ring = prof[:, 0:1] * side[None, :] + prof[:, 1:2] * upv[None, :]
    v = np.concatenate([p0 + ring, p1 + ring])
    f = [c.grid_faces(2, k, wrap_cols=True), np.arange(k)[::-1][None, :], np.arange(k, 2 * k)[None, :]]
    return v, f


def rod(p0, p1, radius, steps=8):
    a = np.linspace(0, 2 * math.pi, steps, endpoint=False)
    prof = np.column_stack([radius * np.cos(a), radius * np.sin(a)])
    return member(p0, p1, prof)


# ------------------------------------------------------------------ grating

def mat_grating(name="GRATING", pitch_bearing=0.034, pitch_cross=0.100, bar=0.004):
    """Pressed galvanised grating 34 x 100 mm (STD). Holes are real: alpha-masked in Cycles."""
    mat = c.mat_galvanized(name, age=0.5, spangle_scale=40.0)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tex = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(tex.outputs["Object"], sep.inputs[0])

    def bars(axis, pitch):
        wrap = nodes.new("ShaderNodeMath")
        wrap.operation = "PINGPONG"
        wrap.inputs[1].default_value = pitch / 2
        links.new(sep.outputs[axis], wrap.inputs[0])
        thr = nodes.new("ShaderNodeMath")
        thr.operation = "LESS_THAN"
        thr.inputs[1].default_value = bar / 2
        links.new(wrap.outputs[0], thr.inputs[0])
        return thr

    solid = nodes.new("ShaderNodeMath")
    solid.operation = "MAXIMUM"
    links.new(bars("X", pitch_bearing).outputs[0], solid.inputs[0])
    links.new(bars("Y", pitch_cross).outputs[0], solid.inputs[1])
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(solid.outputs[0], mix.inputs["Fac"])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(bsdf.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def grating_panel(x0, y0, x1, y1, z, depth=0.030):
    """Grating slab: top at z, 30 mm deep bearing bars, frame edge."""
    return c.box((x0, y0, z - depth), (x1, y1, z))


# ------------------------------------------------------------------ guard rails

RAIL_TOP = 1.10       # EN ISO 14122-3: >= 1.1 m
RAIL_KNEE = 0.55
TOE_H = 0.15
POST_STEP = 1.5       # EN ISO 14122-3: <= 1.5 m
RAIL_R = 0.0212       # Ø42.4 tube


def guard_rail(points, z, closed=False):
    """Posts, top rail, knee rail and toe board along a polyline at floor level z.

    Returns (tubes, toe_boards) as merged (verts, faces).
    """
    pts = [np.array([p[0], p[1], z], float) for p in points]
    if closed:
        pts.append(pts[0])
    tubes, toes = [], []
    for a, b in zip(pts, pts[1:]):
        seg = b - a
        length = np.linalg.norm(seg[:2])
        if length < 1e-6:
            continue
        n_post = max(1, int(math.ceil(length / POST_STEP)))
        for k in range(n_post + 1):
            p = a + seg * k / n_post
            tubes.append(rod(p, p + [0, 0, RAIL_TOP], 0.024, 8))
        for h in (RAIL_TOP, RAIL_KNEE):
            tubes.append(rod(a + [0, 0, h], b + [0, 0, h], RAIL_R, 10))
        toes.append(member(a + [0, 0, TOE_H / 2], b + [0, 0, TOE_H / 2], flat(TOE_H, 0.004)))
    return c.merge_parts(tubes), c.merge_parts(toes)


# ------------------------------------------------------------------ stairs

RISER = 0.20          # EN ISO 14122-3: 0.15 <= h <= 0.25
TREAD = 0.215         # 600 <= g + 2h <= 660 -> 0.215 + 0.40 = 0.615


def stair_flight(x, y0, z0, z1, width=0.80, direction=1):
    """Straight flight along +Y (direction=1) or -Y from (x, y0, z0) to z1, centred on x.

    Returns (stringers, treads, rails) as merged parts.
    """
    rise = z1 - z0
    n = max(1, int(round(rise / RISER)))
    h = rise / n
    run = TREAD * (n - 1)
    y1 = y0 + direction * run
    hw = width / 2
    stringers, treads, rails = [], [], []
    for sx in (x - hw - 0.005, x + hw + 0.005):
        stringers.append(member((sx, y0, z0), (sx, y1, z1), channel(0.18, 0.07, 0.006, 0.009),
                                up=(0, 0, 1), roll=0.0))
    for k in range(1, n):
        yk = y0 + direction * TREAD * (k - 1)
        zk = z0 + h * k
        v, f = c.box((x - hw, min(yk, yk + direction * TREAD) - 0.0, zk - 0.03),
                     (x + hw, max(yk, yk + direction * TREAD), zk))
        treads.append((v, f))
    for sx in (x - hw - 0.03, x + hw + 0.03):
        a = np.array([sx, y0, z0 + 1.0])
        b = np.array([sx, y1, z1 + 1.0])
        rails.append(rod(a, b, RAIL_R, 10))
        rails.append(rod(a - [0, 0, 0.5], b - [0, 0, 0.5], RAIL_R, 10))
        for t in np.linspace(0, 1, max(2, int(run / 1.2) + 1)):
            p = np.array([sx, y0 + (y1 - y0) * t, z0 + rise * t])
            rails.append(rod(p, p + [0, 0, 1.0], 0.02, 8))
    return c.merge_parts(stringers), c.merge_parts(treads), c.merge_parts(rails), y1
