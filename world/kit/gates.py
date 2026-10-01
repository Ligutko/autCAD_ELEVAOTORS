"""Silo slide gates of the tunnel stacks: electric ТЗА (Lubnymash У13-ТЕА.М) and manual ТЗР (У13-ТЗР.М).

Sizes come from world/kit/data/gates_tza_tzr.json (Lubnymash site tables: bore square, bolt square, body height,
blade 3 mm, 0.18 kW). The shape follows the catalogue renders inbox/raw/web/lubnymash.com/u13-tea.png and
u13-tzr.png. Everything the catalogue does not give is EST and listed in dims["est"].

Local frame of one gate: bore centred on the origin, top flange face at z = 0, body below. The blade travels
along X: it opens towards -X (into the ТЗА pocket / the ТЗР sled frame). The drive side is +Y by default,
side=-1 puts it on -Y. Metres.

    gate_tza(size, open_fraction=0.0, side=1) -> {"parts": {name: (verts, faces)}, "dims": {...}}
    gate_tzr(size, open_fraction=0.0, side=1) -> the same
"""

import json
import math
from pathlib import Path

import numpy as np

from . import common as c
from . import components as comp
from . import steel as st

DATA = Path(__file__).resolve().parent / "data" / "gates_tza_tzr.json"

# EST: catalogue gives bore, bolt square, body height and blade only
FLANGE_EDGE = 0.025        # flange edge beyond the bolt square (Grok T4a estimate 0.022, rounded)
FLANGE_T = 0.006           # flange plate
WALL = 0.004               # body sheet
WALL_GAP = 0.004           # bore edge to the inner wall face: the blade runs in slots of the side walls
BOLT_HEAD = 0.019          # M12 hex across flats (the bolts of a 402/450 bolt square)
POCKET_H = 0.05            # ТЗА blade pocket height: the blade must retract somewhere (judgment, the render hides that side)
MOTOR_KW = 0.18            # data: 0.18 kW
WHEEL_D = {350: 0.25, 400: 0.275}   # data: 250-300 judgment for ТЗР-400; 350 scaled down (EST)
SLED_EXTRA = 0.12          # ТЗР sled frame beyond the blade travel (render: end bar well past the blade)


def _data():
    return json.loads(DATA.read_text(encoding="utf-8"))


def _v(model, key):
    node = _data()["models"][model][key]
    return float(node["v"]) / 1000.0


def _hex(x, y, z, af, h, steps=6):
    r = af / math.sqrt(3.0)
    return c.cylinder(r, z, z + h, steps=steps, center=(x, y))


def _frame_plate(half_out, half_in, z0, z1):
    """Square ring plate: outer half-size half_out (x, y), inner half_in."""
    ox, oy = half_out
    ix, iy = half_in
    return [c.box((-ox, -oy, z0), (ox, -iy, z1)), c.box((-ox, iy, z0), (ox, oy, z1)),
            c.box((-ox, -iy, z0), (-ix, iy, z1)), c.box((ix, -iy, z0), (ox, iy, z1))]


def _bolts_on_square(half, z, per_side):
    """Hex heads on a bolt square of half-size `half`, `per_side` bolts per side including the corners."""
    pts = set()
    for k in range(per_side):
        t = -half + 2 * half * k / (per_side - 1)
        for p in ((t, -half), (t, half), (-half, t), (half, t)):
            pts.add((round(p[0], 6), round(p[1], 6)))
    return [_hex(x, y, z, BOLT_HEAD, 0.008) for x, y in sorted(pts)], len(pts)


def _torus(center, axis_y, r_major, r_minor, n_major=40, n_minor=10):
    """Ring in the XZ plane (axis along Y) at `center`."""
    a = np.linspace(0, 2 * math.pi, n_major, endpoint=False)
    b = np.linspace(0, 2 * math.pi, n_minor, endpoint=False)
    A, B = np.meshgrid(a, b, indexing="ij")
    rr = r_major + r_minor * np.cos(B)
    x = center[0] + rr * np.cos(A)
    z = center[2] + rr * np.sin(A)
    y = center[1] + axis_y * r_minor * np.sin(B)
    v = np.stack([x, y, z], axis=-1).reshape(-1, 3)
    i = np.arange(n_major)[:, None]
    j = np.arange(n_minor)[None, :]
    q0 = i * n_minor + j
    q1 = ((i + 1) % n_major) * n_minor + j
    q2 = ((i + 1) % n_major) * n_minor + (j + 1) % n_minor
    q3 = i * n_minor + (j + 1) % n_minor
    return v, np.stack([q0, q1, q2, q3], axis=-1).reshape(-1, 4)


def _common(model, size):
    s = size / 1000.0
    r = _v(model, "рейсмус_мм")
    h = _v(model, "висота_корпусу_мм")
    blade_t = _v(model, "товщина_полотна_мм")
    return s, r, h, blade_t, r / 2 + FLANGE_EDGE


def _flanges_and_bolts(s, r, h, fo, per_side):
    fl = _frame_plate((fo, fo), (s / 2, s / 2), -FLANGE_T, 0.0) + _frame_plate((fo, fo), (s / 2, s / 2), -h, -h + FLANGE_T)
    # fasteners sit on the inner faces of the flange lips (head under the top lip, nut over the bottom lip), so
    # a stacked gate or the sleeve flange bears on a flat face
    bolts, n = _bolts_on_square(r / 2, -FLANGE_T - 0.008, per_side)
    low, _ = _bolts_on_square(r / 2, -h + FLANGE_T, per_side)
    return fl, bolts + low, 2 * n


def _motor(kw, at):
    """IEC motor without feet (flange-mounted on the gearbox): axis along X through `at`, the drive-end shield face
    on x = at[0], the body towards -X, the shaft pushed into the gearbox adapter."""
    m = comp.iec_motor(kw)
    parts = {k: v for k, v in m["parts"].items() if k != "feet"}
    de_face = float(np.asarray(m["parts"]["endshield_de"][0])[:, 0].max())
    out = []
    for v, f in parts.values():
        v = np.array(v, float) - (de_face, 0.0, m["dims"]["H"])
        out.append((v + np.asarray(at, float), f))
    return c.merge_parts(out), m["dims"]


def gate_tza(size, open_fraction=0.0, side=1):
    """Electric slide gate У13-ТЗА-350/400 (catalogue У13-ТЕА-04М/05М)."""
    model = f"ТЗА-{size}"
    s, r, h, bt, fo = _common(model, size)
    frac = min(max(float(open_fraction), 0.0), 1.0)
    travel = s + 0.02                         # EST: bore + 20 mm overlap
    est = [f"фланець {2 * fo:.3f} м (рейсмус + 2×{FLANGE_EDGE})", f"хід полотна {travel:.3f} м",
           f"кишеня полотна {POCKET_H} м заввишки", "черв'ячний редуктор 0.13 × 0.11 × 0.13 м", "стінка 4 мм, фланець 6 мм"]
    parts = {}
    # body: four walls between the flanges, side stiffener ribs
    w = s / 2 + WALL_GAP + WALL                # walls hug the bore, the bolts stand on the flange lip outside them
    body = [c.box((-w, -w, -h + FLANGE_T), (w, -w + WALL, -FLANGE_T)),
            c.box((-w, w - WALL, -h + FLANGE_T), (w, w, -FLANGE_T)),
            c.box((-w, -w, -h + FLANGE_T), (-w + WALL, w, -FLANGE_T)),
            c.box((w - WALL, -w, -h + FLANGE_T), (w, w, -FLANGE_T))]
    for x in (-fo * 0.5, fo * 0.5):
        for sy in (-1, 1):
            y = sy * w
            body.append(c.box((x - 0.003, min(y, y + sy * 0.03), -h + FLANGE_T), (x + 0.003, max(y, y + sy * 0.03), -FLANGE_T)))
    # blade pocket on -X: a flat sheet box the blade slides into
    zb = -h / 2
    px0 = -(s / 2 + 0.01 + travel) - 0.01 - WALL   # the open blade end + 10 mm, then the end wall (was 32 mm short, C4)
    body += [c.box((px0, -s / 2 - 0.03, zb - POCKET_H / 2), (-w, s / 2 + 0.03, zb - POCKET_H / 2 + WALL)),
             c.box((px0, -s / 2 - 0.03, zb + POCKET_H / 2 - WALL), (-w, s / 2 + 0.03, zb + POCKET_H / 2)),
             c.box((px0, -s / 2 - 0.03, zb - POCKET_H / 2), (px0 + WALL, s / 2 + 0.03, zb + POCKET_H / 2)),
             c.box((px0, -s / 2 - 0.03, zb - POCKET_H / 2), (-w, -s / 2 - 0.03 + WALL, zb + POCKET_H / 2)),
             c.box((px0, s / 2 + 0.03 - WALL, zb - POCKET_H / 2), (-w, s / 2 + 0.03, zb + POCKET_H / 2))]
    parts["body"] = c.merge_parts(body)
    fl, bolts, nb = _flanges_and_bolts(s, r, h, fo, 4 if size >= 400 else 3)
    parts["flanges"] = c.merge_parts(fl)
    parts["bolts"] = c.merge_parts(bolts)
    # blade: bore plate shifted towards -X as it opens
    dx = -frac * travel
    parts["blade"] = c.box((-s / 2 - 0.01 + dx, -s / 2 - WALL_GAP, zb - bt / 2), (s / 2 + 0.01 + dx, s / 2 + WALL_GAP, zb + bt / 2))
    # drive on the +Y face (side): screw in a slot along the lower wall, worm gearbox at +X, motor lying along -X
    ys = side * (fo + 0.005)
    zs = -h + 0.055
    drive = [st.rod((-fo + 0.03, ys + side * 0.02, zs), (fo + 0.02, ys + side * 0.02, zs), 0.011, 12),     # lead screw
             c.box((-fo + 0.02, min(ys, ys + side * 0.045), zs - 0.03), (fo - 0.02, max(ys, ys + side * 0.045), zs - 0.024)),
             c.box((-fo + 0.02, min(ys, ys + side * 0.045), zs + 0.024), (fo - 0.02, max(ys, ys + side * 0.045), zs + 0.03))]
    nut_x = fo - 0.06 + dx * (2 * fo - 0.1) / travel
    drive.append(c.box((nut_x - 0.025, min(ys, ys + side * 0.04), zs - 0.02), (nut_x + 0.025, max(ys, ys + side * 0.04), zs + 0.02)))
    parts["screw"] = c.merge_parts(drive)
    gx0, gx1 = fo - 0.10, fo + 0.03
    gy0, gy1 = sorted((ys + side * 0.01, ys + side * 0.12))
    zg = -h / 2 + 0.01
    gear = [c.box((gx0, gy0, zg - 0.065), (gx1, gy1, zg + 0.065))]
    gear.append(st.rod(((gx0 + gx1) / 2, gy1 if side > 0 else gy0, zg), ((gx0 + gx1) / 2, (gy1 + 0.02) if side > 0 else (gy0 - 0.02), zg), 0.045, 24))
    gear.append(st.rod((gx0 - 0.02, (gy0 + gy1) / 2, zg), (gx0, (gy0 + gy1) / 2, zg), 0.05, 24))          # motor adapter flange
    parts["gearbox"] = c.merge_parts(gear)
    mot, md = _motor(MOTOR_KW, (gx0 - 0.02, (gy0 + gy1) / 2, zg))
    parts["motor"] = mot
    # limit switch box and conduit under the gearbox; position pointer on the pocket side
    sw_y0, sw_y1 = sorted((ys + side * 0.03, ys + side * 0.10))
    zsw0, zsw1 = -h + FLANGE_T + 0.004, zs - 0.035                  # between the bottom flange and the screw slot
    parts["switches"] = c.merge_parts([c.box((gx0 - 0.14, sw_y0, zsw0), (gx0 - 0.06, sw_y1, zsw1)),
                                       c.box((gx0 - 0.23, sw_y0, zsw0), (gx0 - 0.15, sw_y1, zsw1))])
    ptr_x = px0 + 0.02 + (1 - frac) * (travel - 0.06)
    parts["indicator"] = c.merge_parts([c.box((px0 + 0.01, side * (s / 2 + 0.03) - 0.001, zb + POCKET_H / 2),
                                              (-w, side * (s / 2 + 0.03) + 0.001, zb + POCKET_H / 2 + 0.03)),
                                        c.box((ptr_x - 0.006, side * (s / 2 + 0.03) - 0.004, zb + POCKET_H / 2),
                                              (ptr_x + 0.006, side * (s / 2 + 0.03) + 0.004, zb + POCKET_H / 2 + 0.045))])
    dims = {"model": model, "bore": s, "bolt_square": r, "body_h": h, "blade_t": bt, "flange": 2 * fo, "travel": travel,
            "open_fraction": frac, "bolts": nb, "motor_frame": md["frame"], "motor_kw": MOTOR_KW, "est": est}
    return {"parts": parts, "dims": dims}


def gate_tzr(size, open_fraction=0.0, side=1):
    """Manual rack-and-pinion slide gate У13-ТЗР-350/400: flat body, open sled frame, handwheel on a cross shaft."""
    model = f"ТЗР-{size}"
    s, r, h, bt, fo = _common(model, size)
    frac = min(max(float(open_fraction), 0.0), 1.0)
    travel = s + 0.02
    wheel_d = WHEEL_D[size]
    est = [f"фланець {2 * fo:.3f} м", f"хід полотна {travel:.3f} м", f"рама-сани {travel + SLED_EXTRA:.3f} м за корпусом",
           f"штурвал Ø{wheel_d:.3f} м", "рейка 30 × 12 мм, шестерня в корпусі 0.09 × 0.07 × 0.06 м"]
    parts = {}
    zb = -h / 2
    w = s / 2 + WALL_GAP + WALL
    body = [c.box((-w, -w, -h + FLANGE_T), (w, -w + WALL, -FLANGE_T)),
            c.box((-w, w - WALL, -h + FLANGE_T), (w, w, -FLANGE_T)),
            c.box((w - WALL, -w, -h + FLANGE_T), (w, w, -FLANGE_T)),
            # -X wall with the blade slot: two strips above and below the slot
            c.box((-w, -w, -h + FLANGE_T), (-w + WALL, w, zb - 0.004)),
            c.box((-w, -w, zb + 0.004), (-w + WALL, w, -FLANGE_T))]
    parts["body"] = c.merge_parts(body)
    fl, bolts, nb = _flanges_and_bolts(s, r, h, fo, 4 if size >= 400 else 3)
    parts["flanges"] = c.merge_parts(fl)
    parts["bolts"] = c.merge_parts(bolts)
    dx = -frac * travel
    parts["blade"] = c.box((-s / 2 - 0.01 + dx, -s / 2 - WALL_GAP, zb - bt / 2), (s / 2 + 0.01 + dx, s / 2 + WALL_GAP, zb + bt / 2))
    # sled frame: two angle rails from the -X wall, an end bar with an upturned stop
    x0, x1 = -w, -w - travel - SLED_EXTRA
    ry = s / 2 + 0.04
    frame = []
    for sy in (-1, 1):
        frame.append(st.member((x0, sy * ry, zb - 0.02), (x1, sy * ry, zb - 0.02), st.angle(0.04, 0.004), up=(0, 0, 1), roll=0 if sy > 0 else math.pi / 2))
    frame.append(st.member((x1, -ry - 0.02, zb - 0.02), (x1, ry + 0.02, zb - 0.02), st.shs(0.03, 0.003)))
    frame.append(st.member((x1, -ry, zb - 0.005), (x1 - 0.02, -ry, zb + 0.05), st.flat(0.03, 0.005)))
    frame.append(st.member((x1, ry, zb - 0.005), (x1 - 0.02, ry, zb + 0.05), st.flat(0.03, 0.005)))
    parts["frame"] = c.merge_parts(frame)
    # rack on the blade centre line, riding with the blade
    parts["rack"] = c.merge_parts([c.box((-s / 2 + dx, -0.015, zb + bt / 2), (s / 2 + 0.01 + dx, 0.015, zb + bt / 2 + 0.012))] +
                                  [c.box((-s / 2 + dx + k * 0.01, -0.015, zb + bt / 2 + 0.012), (-s / 2 + dx + k * 0.01 + 0.005, 0.015, zb + bt / 2 + 0.018))
                                   for k in range(int(s / 0.01))])
    # cross shaft on the rails just outside the body, pinion housing on the centre line, handwheel past the rail
    xs = -fo - 0.08
    zs = zb + bt / 2 + 0.045
    shaft_end = side * (ry + 0.22)
    parts["pinion"] = c.merge_parts([c.box((xs - 0.045, -0.035, zs - 0.035), (xs + 0.045, 0.035, zs + 0.035)),
                                     c.box((xs - 0.03, -ry - 0.01, zb - 0.02), (xs + 0.03, ry + 0.01, zb - 0.012))])
    shaft = [st.rod((xs, -side * (ry + 0.01), zs), (xs, shaft_end, zs), 0.013, 16)]
    for y in (-ry, ry):
        shaft.append(c.box((xs - 0.025, y - 0.02, zb - 0.02), (xs + 0.025, y + 0.02, zs + 0.025)))      # bearing blocks
    parts["shaft"] = c.merge_parts(shaft)
    rw = wheel_d / 2
    hub = (xs, shaft_end, zs)
    wheel = [_torus(hub, side, rw - 0.012, 0.012, 48, 10), st.rod((xs, shaft_end - side * 0.02, zs), (xs, shaft_end + side * 0.03, zs), 0.025, 16)]
    for k in range(3):
        a = math.pi / 2 + 2 * math.pi * k / 3
        wheel.append(st.rod(hub, (xs + (rw - 0.012) * math.cos(a), shaft_end, zs + (rw - 0.012) * math.sin(a)), 0.008, 8))
    a = math.pi / 2 + math.pi / 3
    kx, kz = xs + (rw - 0.012) * math.cos(a), zs + (rw - 0.012) * math.sin(a)
    wheel.append(st.rod((kx, shaft_end, kz), (kx, shaft_end + side * 0.09, kz), 0.012, 12))            # spinner knob
    parts["handwheel"] = c.merge_parts(wheel)
    dims = {"model": model, "bore": s, "bolt_square": r, "body_h": h, "blade_t": bt, "flange": 2 * fo, "travel": travel,
            "open_fraction": frac, "bolts": nb, "wheel_d": wheel_d, "shaft_axis": (xs, zs), "est": est}
    return {"parts": parts, "dims": dims}
