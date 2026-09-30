"""Operator room of the АПК block (HERO_DETAIL_SPEC place 9): the SCADA console facing the south windows onto the
inbound scales, the weigher's desk at the window, a 2 x 2 video wall on the east wall, the PLC cabinet, lamps.

Data: world/kit/data/operator_room.json (Grok T7a: Knürr Dacobas console, Dell P2422H, LG 55VH7E, ISO 11064,
ДСанПіН 3.3.2.007-98). The room is the east 4.5 m of the АПК (SITE designed.site_plan.apk rooms: lab 9 x 9,
operator room 4.5 x 9), short walls south (onto the in-lane and the scales) and north. Site frame, metres.

    build(site) -> {part: (material key, smooth, (verts, faces))}, plus layout(site) with the numbers the check uses.
"""

import json
from pathlib import Path

import numpy as np

from . import common as c
from . import controls as ctl
from . import steel as st

DATA = Path(__file__).resolve().parent / "data" / "operator_room.json"
WALL = 0.25                 # EST: block wall
WIN = (1.5, 1.3, 0.8)       # EST: window width, height, sill (opening NOT_FOUND; sill 0.8: the scales stay in view)
EYE_BACK = 0.20             # EST: seated eye this far behind the console front edge
EYE_Z = 1.20                # EST: seated eye over the floor (seat 0.45 + trunk)
WALL_LOW = 1.0              # EST: video wall bottom over the floor (NOT_FOUND)


def _d():
    return json.loads(DATA.read_text(encoding="utf-8"))


def layout(site):
    """Room box, console, monitors, eye, windows, video wall, desk (site frame)."""
    d = _d()
    ap = site["designed"]["site_plan"]["apk"]
    g = c.ground_z()
    w_room = d["room"]["операторська_в_плані_мм"]["v"][0] / 1000
    x1 = ap["x"][1]
    x0 = x1 - w_room
    y0, y1 = ap["y"]
    h = ap["h"]
    cw = d["console_dacobas"]["ширина_рами_мм"]["v"] / 1000
    cd = d["console_dacobas"]["глибина_тумби_мм"]["v"][0] / 1000
    ch = d["console_dacobas"]["висота_стільниці_мм"]["v"] / 1000
    eye_d = d["ergonomics"]["дистанція_рекомендована_мм"]["v"] / 1000
    mw, mh, md = (v / 1000 for v in d["monitor_desk"]["зі_стійкою_ШВГ_мм"]["v"])
    aw, ah = (v / 1000 for v in d["monitor_desk"]["активне_ШВ_мм"]["v"])
    cx = x0 + WALL + 0.8 + (x1 - x0 - 2 * WALL - 0.8) / 2           # console centred in the room past the weigher's desk
    front = y0 + WALL + 2.4                                          # console front edge (operator side, north)
    eye = np.array([cx, front + EYE_BACK, g + EYE_Z])
    screen_y = eye[1] - eye_d - 0.005                                # bezel face 5 mm past the recommended distance
    ww, wh, wd = (v / 1000 for v in d["video_wall_55"]["ШВГ_мм"]["v"])
    return {"g": g, "room": (x0, y0, x1, y1, h), "console": (cx - cw / 2, front - cd, cx + cw / 2, front, ch),
            "monitor": (mw, mh, md, aw, ah), "screen_y": screen_y, "eye": eye,
            "windows": [(cx, y0), (x0 + WALL + 0.95, y0)], "vwall": (x1 - WALL, (y0 + y1) / 2 + 0.8, 2 * ww, 2 * wh, wd),
            "desk": (x0 + WALL + 0.05, y0 + WALL + 0.05, 1.4, 0.8, d["стіл_вдт_дсанпін"]["стіл_вагаря_мм"]["v"]["h"] / 1000)}


def _chair(x, y, g, face_y):
    """Operator chair: five-star base, gas lift, seat 0.45, back on the far side from face_y."""
    parts = [c.cylinder(0.3, g + 0.06, g + 0.09, steps=5, center=(x, y)), st.rod((x, y, g + 0.09), (x, y, g + 0.42), 0.025, 12),
             c.box((x - 0.24, y - 0.24, g + 0.42), (x + 0.24, y + 0.24, g + 0.5))]
    by = y - face_y * 0.26
    parts.append(c.box((x - 0.24, by - 0.03, g + 0.55), (x + 0.24, by + 0.03, g + 1.25)))
    parts.append(st.rod((x, by, g + 0.5), (x, by, g + 0.55), 0.02, 8))
    return parts


def build(site):
    L = layout(site)
    g = L["g"]
    x0, y0, x1, y1, h = L["room"]
    parts = {}
    # shell: walls with the two south windows and a north door, floor, ceiling (the roof stays with the АПК block)
    walls = [c.box((x0, y1 - WALL, g), (x1, y1, g + h)), c.box((x1 - WALL, y0, g), (x1, y1, g + h)),
             c.box((x0, y0, g), (x0 + WALL, y1, g + h))]
    ww, wh, sill = WIN
    xs = sorted(x for x, _ in L["windows"])
    cuts = [x0]
    for x in xs:
        cuts += [x - ww / 2, x + ww / 2]
    cuts.append(x1)
    for a, b in zip(cuts[::2], cuts[1::2]):
        walls.append(c.box((a, y0, g), (b, y0 + WALL, g + h)))
    frames = []
    for x in xs:
        walls.append(c.box((x - ww / 2, y0, g), (x + ww / 2, y0 + WALL, g + sill)))
        walls.append(c.box((x - ww / 2, y0, g + sill + wh), (x + ww / 2, y0 + WALL, g + h)))
        frames += [c.box((x - ww / 2, y0 + 0.1, g + sill), (x + ww / 2, y0 + 0.16, g + sill + 0.05)),
                   c.box((x - ww / 2, y0 + 0.1, g + sill + wh - 0.05), (x + ww / 2, y0 + 0.16, g + sill + wh)),
                   c.box((x - 0.025, y0 + 0.1, g + sill), (x + 0.025, y0 + 0.16, g + sill + wh))]
    parts["op_walls"] = ("white", False, c.merge_parts(walls))
    parts["op_window_frames"] = ("galv", False, c.merge_parts(frames))
    parts["op_floor"] = ("dark", False, c.box((x0, y0, g - 0.1), (x1, y1, g)))
    parts["op_ceiling"] = ("white", False, c.box((x0, y0, g + h - 0.05), (x1, y1, g + h)))
    parts["op_door"] = ("dark", False, c.box((x0 + 1.2, y1 - WALL - 0.035, g + 0.005), (x0 + 2.1, y1 - WALL - 0.005, g + 2.1)))
    # SCADA console (Knürr Dacobas, one frame): pedestal, top 30 mm, two monitors side by side on the back edge
    ax0, ay0, ax1, ay1, top = L["console"]
    cons = [c.box((ax0, ay0, g), (ax1, ay0 + 0.5, g + top - 0.03)), c.box((ax0 - 0.05, ay0, g + top - 0.03), (ax1 + 0.05, ay1, g + top))]
    parts["op_console"] = ("dark", False, c.merge_parts(cons))
    mw, mh, md, aw, ah = L["monitor"]
    cx = (ax0 + ax1) / 2
    sy = L["screen_y"]
    mon, scr = [], []
    for k in (-1, 1):
        mx = cx + k * (mw / 2 + 0.01)
        mon += [c.box((mx - 0.12, sy - 0.12, g + top), (mx + 0.12, sy + 0.08, g + top + 0.02)),
                st.rod((mx, sy - 0.05, g + top), (mx, sy - 0.05, g + top + 0.15), 0.025, 10),
                c.box((mx - mw / 2, sy - 0.05, g + top + mh - 0.33), (mx + mw / 2, sy, g + top + mh))]
        scr.append(c.box((mx - aw / 2, sy, g + top + mh - 0.33 + 0.02), (mx + aw / 2, sy + 0.002, g + top + mh - 0.33 + 0.02 + ah)))
    mon.append(c.box((cx - 0.23, ay1 - 0.3, g + top), (cx + 0.23, ay1 - 0.15, g + top + 0.02)))            # keyboard
    parts["op_monitors"] = ("dark", False, c.merge_parts(mon))
    parts["op_screens"] = ("screen", False, c.merge_parts(scr))
    ex, ey, _ = L["eye"]
    # weigher's desk at the west window, its chair, and the operator chair
    dx, dy, dw, dd, dh = L["desk"]
    desk = [c.box((dx, dy, g + dh - 0.03), (dx + dw, dy + dd, g + dh))]
    desk += [c.box((xx, yy, g), (xx + 0.05, yy + 0.05, g + dh - 0.03)) for xx in (dx + 0.03, dx + dw - 0.08) for yy in (dy + 0.03, dy + dd - 0.08)]
    parts["op_desk"] = ("white", False, c.merge_parts(desk))
    parts["op_chairs"] = ("dark", False, c.merge_parts(_chair(ex, ey + 0.1, g, -1) + _chair(dx + dw / 2, dy + dd + 0.35, g, -1)))
    # video wall 2 x 2 LG 55" on the east wall
    vx, vy, vw, vh, vd = L["vwall"]
    parts["op_video_wall"] = ("screen", False, c.box((vx - vd - 0.01, vy - vw / 2, g + WALL_LOW), (vx - 0.01, vy + vw / 2, g + WALL_LOW + vh)))
    # PLC cabinet in the north-east corner, ceiling lamps
    cab = ctl.cabinet(1, hmi=False)
    cv = []
    for name, (v, f) in cab["parts"].items():
        cv.append((np.asarray(v, float) + (x1 - WALL - 0.9, y1 - WALL - 0.61, g), f))   # back to the north wall, doors to the room
    parts["op_cabinet"] = ("white", False, c.merge_parts(cv))
    lamps = [c.box((x - 0.3, y - 0.3, g + h - 0.08), (x + 0.3, y + 0.3, g + h - 0.05)) for x in ((x0 + x1) / 2,)
             for y in np.linspace(y0 + 1.5, y1 - 1.5, 4)]
    parts["op_lamps"] = ("lamp", False, c.merge_parts(lamps))
    return parts
