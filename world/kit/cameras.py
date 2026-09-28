"""D1. Named camera moves, baked to keyframes. Units: metres, seconds.

Every move returns a list of (location, look_at) per frame; `bake` writes them to a camera.
Moves ease in and out (smoothstep) so the camera never jerks, like a real gimbal or a dolly.
"""

import math

import bpy  # noqa: I001  bpy first: the pip module registers mathutils
import numpy as np
from mathutils import Vector

EYE = 1.7            # first-person eye height
WALK_SPEED = 1.2     # m/s, calm walk


def ease(t):
    return t * t * (3 - 2 * t)


def orbit(target, radius, height, start_deg, sweep_deg, frames):
    tx, ty, tz = target
    out = []
    for k in range(frames):
        a = math.radians(start_deg + sweep_deg * ease(k / max(frames - 1, 1)))
        out.append(((tx + radius * math.cos(a), ty + radius * math.sin(a), height), target))
    return out


def dolly(a, b, look_a, look_b, frames):
    a, b, la, lb = (np.asarray(v, float) for v in (a, b, look_a, look_b))
    return [(tuple(a + (b - a) * ease(k / max(frames - 1, 1))), tuple(la + (lb - la) * ease(k / max(frames - 1, 1))))
            for k in range(frames)]


def push_in(start, target, fraction, frames):
    """Move from start towards target by `fraction` of the distance, always looking at it."""
    s, t = np.asarray(start, float), np.asarray(target, float)
    return [(tuple(s + (t - s) * fraction * ease(k / max(frames - 1, 1))), tuple(t)) for k in range(frames)]


def crane(xy, z0, z1, look, frames):
    return [((xy[0], xy[1], z0 + (z1 - z0) * ease(k / max(frames - 1, 1))), look) for k in range(frames)]


def _catmull(pts, u):
    """Point at u in [0, 1] on a centripetal-free (uniform) Catmull-Rom spline through pts."""
    pts = [np.asarray(p, float) for p in pts]
    if len(pts) == 1:
        return pts[0]
    ext = [2 * pts[0] - pts[1]] + pts + [2 * pts[-1] - pts[-2]]
    n = len(pts) - 1
    x = min(max(u, 0.0), 1.0) * n
    i = min(int(x), n - 1)
    t = x - i
    p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
    return 0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3)


def keys(points, looks, frames):
    """Fly through key positions, looking at key targets, both on smooth splines, eased in and out."""
    return [(tuple(_catmull(points, ease(k / max(frames - 1, 1)))), tuple(_catmull(looks, ease(k / max(frames - 1, 1)))))
            for k in range(frames)]


def walk(points, fps, eye=EYE, speed=WALK_SPEED, look_ahead=3.0, bob=0.015):
    """First-person walk along a polyline at eye height (points are floor positions x, y, z).
    Constant speed, gentle head bob, looks `look_ahead` metres down the path."""
    pts = [np.asarray(p, float) for p in points]
    seg = [np.linalg.norm(b - a) for a, b in zip(pts, pts[1:])]
    total = sum(seg)
    frames = max(2, int(total / speed * fps))

    def at(s):
        s = min(max(s, 0.0), total)
        for a, b, L in zip(pts, pts[1:], seg):
            if s <= L:
                return a + (b - a) * (s / L)
            s -= L
        return pts[-1]

    out = []
    for k in range(frames):
        s = total * ease(k / (frames - 1))
        p = at(s) + [0, 0, eye + bob * math.sin(2 * math.pi * 1.8 * k / fps)]
        q = at(s + look_ahead) + [0, 0, eye - 0.15]
        out.append((tuple(p), tuple(q)))
    return out


def bake(cam, path, start_frame=1):
    """Write per-frame location and rotation keyframes (linear) for the given path."""
    cam.animation_data_clear()
    for k, (loc, look) in enumerate(path):
        f = start_frame + k
        cam.location = Vector(loc)
        cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    if cam.animation_data and cam.animation_data.action:
        action = cam.animation_data.action
        curves = getattr(action, "fcurves", None)
        if curves is None:                                   # Blender 4.4+: layered actions
            curves = [fc for layer in action.layers for strip in layer.strips
                      for bag in strip.channelbags for fc in bag.fcurves]
        for fc in curves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    return start_frame + len(path) - 1


FORMATS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}


def set_format(scene, fmt, scale=1.0):
    w, h = FORMATS[fmt]
    scene.render.resolution_x = int(w * scale)
    scene.render.resolution_y = int(h * scale)
