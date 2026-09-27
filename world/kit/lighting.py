"""Phase W1c. Site lighting (designed layer, research/design/environment.md): floodlight masts and building-mounted
floodlights with a real photometry file (IES), point-by-point horizontal illuminance with shadows from the scene,
upward light, and the mast geometry and Blender lamps for the night preset.

Head frame: x = the luminaire's C 0 (its throw direction), z up. A head is turned to azimuth `az` (degrees from +x,
anticlockwise) and tilted by `tilt` (degrees, + raises the throw above the flat position: glass facing down).
Data: SITE.json `designed.environment.lighting`.
"""

import functools
import math

import numpy as np

from . import common as c
from .photometry import Photometry, direction_to_cg


def _site():
    from . import receiving as rc
    return rc._site()


def spec(site=None):
    return (site or _site())["designed"]["environment"]["lighting"]


@functools.lru_cache(maxsize=4)
def photometry(rel_path):
    return Photometry(c.SITE_JSON.parents[2] / rel_path)


def rotation(az, tilt):
    """World-from-head rotation: yaw by az about z after pitching the throw up by tilt."""
    a, t = math.radians(az), math.radians(tilt)
    rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    ry = np.array([[math.cos(t), 0, -math.sin(t)], [0, 1, 0], [math.sin(t), 0, math.cos(t)]])
    return rz @ ry


def luminaire(site, key):
    """Luminaire type: {ies, throw_c (the C angle of the file that points along the throw), size}."""
    return spec(site)["luminaires"][key]


def heads(site=None):
    """Every floodlight: [{id, pos (3,), R (3, 3), az, tilt, support, lum}] in the site frame."""
    site = site or _site()
    ls = spec(site)
    g = c.ground_z()
    out = []
    for kind in ("masts", "mounts"):
        for m in ls.get(kind, []):
            z = g + (m["h"] if kind == "masts" else m["z"])
            for k, (az, tilt) in enumerate(m["heads"]):
                off = ls["crown_r"] if kind == "masts" else 0.0          # heads sit on a ring round the mast top
                pos = np.array([m["xy"][0] + off * math.cos(math.radians(az)), m["xy"][1] + off * math.sin(math.radians(az)), z])
                out.append({"id": f"{m['id']}.{k + 1}", "pos": pos, "R": rotation(az, tilt), "az": az, "tilt": tilt,
                            "support": m["id"], "kind": kind, "lum": m.get("lum", ls["default_lum"])})
    return out


def head_photometry(site, head):
    lu = luminaire(site, head["lum"])
    return photometry(lu["ies"]), lu["throw_c"]


def intensity_world(site, head, dirs):
    """cd of one head toward world unit directions dirs (n, 3)."""
    ph, throw_c = head_photometry(site, head)
    local = np.asarray(dirs) @ head["R"]                                   # R^T d for each row
    cc, gg = direction_to_cg(local)
    return ph.intensity(cc + throw_c, gg)


def illuminance(site, pts, blocked=None, mf=None, per_head=False):
    """Maintained horizontal illuminance, lx, at points pts (n, 3) with the surface facing up.
    blocked(p0 (n,3), p1 (n,3)) -> bool (n,) tells which point-to-lamp segments are shadowed; mf defaults to the data."""
    site = site or _site()
    ls = spec(site)
    mf = ls["mf"] if mf is None else mf
    pts = np.asarray(pts, float)
    total = np.zeros(len(pts))
    parts = {}
    for h in heads(site):
        d = pts - h["pos"]                                                 # lamp -> point
        r = np.linalg.norm(d, axis=1)
        u = d / r[:, None]
        cos_i = np.clip(-u[:, 2], 0.0, None)                               # light coming down onto an up-facing plane
        e = intensity_world(site, h, u) * cos_i / r ** 2
        if blocked is not None:
            live = e > 1e-3
            if live.any():
                idx = np.where(live)[0]
                sh = blocked(pts[idx], np.repeat(h["pos"][None, :], len(idx), axis=0))
                e[idx[sh]] = 0.0
        total += e
        if per_head:
            parts[h["id"]] = e * mf
    return (total * mf, parts) if per_head else total * mf


def upward_ratio(site=None, n=240):
    """ULR: share of the installation's flux emitted above the horizontal."""
    site = site or _site()
    th = (np.arange(n) + 0.5) * math.pi / n
    phi = (np.arange(2 * n) + 0.5) * math.pi / n
    T, P = np.meshgrid(th, phi)
    dirs = np.stack([np.sin(T) * np.cos(P), np.sin(T) * np.sin(P), np.cos(T)], axis=-1).reshape(-1, 3)
    dom = (np.sin(T) * (math.pi / n) ** 2).ravel()
    up = tot = 0.0
    for h in heads(site):
        i = intensity_world(site, h, dirs) * dom
        tot += i.sum()
        up += i[dirs[:, 2] > 0].sum()
    return up / tot


def near_horizontal_peak(site=None, band=(-10.0, 0.0)):
    """Highest intensity of any head toward directions between band[0] and band[1] degrees of elevation
    (toward the neighbours and the public road: the potentially glaring direction of ДБН В.2.5-28 табл. 8.11)."""
    site = site or _site()
    el = np.radians(np.linspace(band[0], band[1], 11))
    az = np.radians(np.arange(0, 360, 2.0))
    E, A = np.meshgrid(el, az)
    dirs = np.stack([np.cos(E) * np.cos(A), np.cos(E) * np.sin(A), np.sin(E)], axis=-1).reshape(-1, 3)
    return max((float(intensity_world(site, h, dirs).max()), h["id"]) for h in heads(site))


# ---------------------------------------------------------------- geometry and lamps

def _prism(r0, r1, z0, z1, n=8, center=(0.0, 0.0)):
    """Tapered n-sided shaft (faceted galvanized pole)."""
    a = np.linspace(0, 2 * math.pi, n, endpoint=False) + math.pi / n
    v = np.concatenate([np.column_stack([center[0] + r0 * np.cos(a), center[1] + r0 * np.sin(a), np.full(n, z0)]),
                        np.column_stack([center[0] + r1 * np.cos(a), center[1] + r1 * np.sin(a), np.full(n, z1)])])
    return v, [c.grid_faces(2, n, wrap_cols=True), np.arange(n, 2 * n)[None, :]]


def build(site=None):
    """Masts (faceted tapered poles on a concrete plinth, a crown ring), floodlight housings with brackets."""
    site = site or _site()
    ls = spec(site)
    g = c.ground_z()
    poles, plinths, housings, glass = [], [], [], []
    for m in ls["masts"]:
        x, y = m["xy"]
        plinths.append(c.cylinder(0.45, g - 0.05, g + 0.25, steps=20, center=(x, y)))
        poles.append(_prism(0.16, 0.07, g + 0.25, g + m["h"] + 0.3, center=(x, y)))
        a = np.linspace(0, 2 * math.pi, 24, endpoint=False)
        ring = []
        for k in range(24):                                                # crown ring the heads hang from
            p0 = (x + ls["crown_r"] * math.cos(a[k]), y + ls["crown_r"] * math.sin(a[k]))
            p1 = (x + ls["crown_r"] * math.cos(a[(k + 1) % 24]), y + ls["crown_r"] * math.sin(a[(k + 1) % 24]))
            ring.append(c.box((min(p0[0], p1[0]) - 0.02, min(p0[1], p1[1]) - 0.02, g + m["h"] + 0.12),
                              (max(p0[0], p1[0]) + 0.02, max(p0[1], p1[1]) + 0.02, g + m["h"] + 0.18)))
        poles += ring
    for h in heads(site):
        R, p = h["R"], h["pos"]
        L, W, H = luminaire(site, h["lum"])["size"]
        # housing box in the head frame: glass face down at the lamp position
        corners = np.array([[sx * L / 2, sy * W / 2, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (0.0, H)])
        v = corners @ R.T + p
        housings.append((v, np.array([(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])))
        gl = np.array([[sx * (L / 2 - 0.03), sy * (W / 2 - 0.03), -0.002] for sx in (-1, 1) for sy in (-1, 1)]) @ R.T + p
        glass.append((gl[[0, 2, 3, 1]], np.array([(0, 1, 2, 3)])))
        top = p + R @ np.array([0, 0, H])                                  # bracket up to the crown ring / the wall
        housings.append(c.box((top[0] - 0.02, top[1] - 0.02, top[2]), (top[0] + 0.02, top[1] + 0.02, top[2] + 0.2)))
    return {"light_poles": ("galv", False, c.merge_parts(poles)), "light_plinths": ("concrete", False, c.merge_parts(plinths)),
            "light_housings": ("dark", False, c.merge_parts(housings)), "light_glass": ("lamp_glass", False, c.merge_parts(glass))}


CYCLES_IES_PER_CD = 0.0707    # Cycles IES texture output per file candela, measured 2026-09-28 in Blender 4.5.2 on both
                              # files (a Lambert plane under one lamp); check_lighting re-measures it by rendering
CYCLES_C0_ANGLE = 270.0       # Cycles puts the file's C 0 along the lamp's -Y and counts C clockwise seen from above


def add_lamps(site, collection=None, lumens_to_watts=683.0):
    """Blender point lamps carrying the IES file, one per head, for the night preset. Cycles feeds the file's candela
    straight into the lamp (times CYCLES_IES_PER_CD), so every lamp gets P = 4 pi / (683 k) W and gives I(C, gamma)
    candela in every direction. Turned so the file's throw direction runs along the head's x (throw-symmetric files
    only: Cycles mirrors C, which check_lighting guards)."""
    import bpy
    from mathutils import Matrix
    site = site or _site()
    objs = []
    for h in heads(site):
        lu = luminaire(site, h["lum"])
        ph, throw_c = head_photometry(site, h)
        name = "IES_" + h["lum"]
        text = bpy.data.texts.get(name)
        if text is None:
            text = bpy.data.texts.load(str(c.SITE_JSON.parents[2] / lu["ies"]))
            text.name = name
        data = bpy.data.lights.new("LAMP_" + h["id"], type="POINT")
        data.shadow_soft_size = 0.15
        data.energy = 4 * math.pi / (lumens_to_watts * CYCLES_IES_PER_CD)
        data.color = (1.0, 0.93, 0.85)                                   # 4000 K
        data.use_nodes = True
        nt = data.node_tree
        ies = nt.nodes.new("ShaderNodeTexIES")
        ies.mode = "INTERNAL"
        ies.ies = text
        emit = next(n for n in nt.nodes if n.type == "EMISSION")
        nt.links.new(ies.outputs["Fac"], emit.inputs["Strength"])
        obj = bpy.data.objects.new("LAMP_" + h["id"], data)
        (collection or bpy.context.scene.collection).objects.link(obj)
        # the nadir (gamma 0) is the lamp's -Z; the file's throw_c sits at CYCLES_C0_ANGLE - throw_c in the lamp frame,
        # so turning the lamp by throw_c - CYCLES_C0_ANGLE puts the throw on the head's x
        a = math.radians(throw_c - CYCLES_C0_ANGLE)
        rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
        m = np.eye(4)
        m[:3, :3] = h["R"] @ rz
        m[:3, 3] = h["pos"] - h["R"] @ np.array([0, 0, 0.01])
        obj.matrix_world = Matrix(m.tolist())
        objs.append(obj)
    return objs
