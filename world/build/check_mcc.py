"""MCC room check (world/kit/mcc_room.py): the switch room in the КТП block, on the meshes and the layout numbers.

FAIL:
- registry:     every register motor (SITE equipment.items, kind "motor") lands in exactly one cabinet, no foreign ids;
- fill:         the feeder places a cabinet needs (mcc_room.feeder x qty) fit its CAB_SLOTS (EST capacity);
- labels:       every cabinet carries a plate on its own door, centre 1.5-2.0 m over the floor (EST), whose text names
                exactly its motors (the incoming cabinet: «ВВІД»);
- aisle_width:  clear width in front of each row >= 0.8 m along its whole length, measured by rays from the handles
                at heights 0.05-1.89 m to the first obstacle (ПУЭ-7 п. 4.1.23, analog for the Ukrainian ПУЕ);
- aisle_height: clear height over the whole passage >= 1.9 m (same clause): rays up from the floor; tray, lamps,
                stack light all count;
- doors:        every cabinet door (leaf, handle, door lamps, plate) swings 10-90° about its hinge without touching
                walls, neighbours, the tray, lamps or anything else (BVH, every 5°);
- floor:        every cabinet stands on the floor (plinth at the ground +-1 mm) inside the room's inner faces;
- tray:         the tray boxes form one connected run, the exit piece meets the end of the cable trestle tray
                (SITE site_plan.cable_trestle pts[0], +z) face to face, and every cabinet lies under the tray;
- exit:         the room has a door on an outer wall with DOOR_CLEAR of free floor inside, and two exits when a row is
                longer than 7 m (ПУЭ-7 п. 4.1.23, analog);
- clash:        no intersection between the cabinets, the tray, lamps, the stack light, the door and the shell (BVH,
                things standing on something tested 2 mm up).
WARN (own recommendation): two opposite doors open at once leave < 0.6 m (the 0.6 m local narrowing of 4.1.23);
a cabinet filled over FILL_MAX (design reserve).

C7b, the two transformer chambers (kit/transformer.py TMG-630/10/0.4 on the catalogue dimensions, research/design/ktp/NOTES.md),
measured on the meshes (PUE-7 chapter 4.2, analog for the Ukrainian ПУЕ). FAIL:
- tr_clearance:  from the most protruding parts of each transformer at <= 1.9 m over the floor: to the back and side walls
                 >= 0.3 m, to the door leaf >= 0.6 m (4.2.217, up to 0.63 MVA); each chamber has its own door in the south wall;
- tr_rollers:    the four rollers of each transformer stand on the rails (contact within 1 mm of the rail top, wheels over the rails);
- tr_insulators: the 10 kV bushings reach up inside the chamber: top >= 0.12 m under the earthed ceiling (table 4.2.7), live parts
                 of the phases >= 0.13 m apart and >= 0.12 m from the walls;
- tr_bus:        each LV bus: the four stud tops under the junction box, the duct drop lands on the incoming cabinet ШВ-1
                 (within 5 mm of its top, inside its plan), the duct passes every partition through an opening with a gap of
                 0..20 mm (a collar closes it, 4.2.108);
- tr_vents:      each chamber has a low inlet and a high outlet, each open in the wall (ray through the mesh), the free area of each
                 >= the area that carries the losses away with <= 15 K air heating by natural draught (4.2.104, 4.2.222),
                 mesh cell <= 10 mm;
- tr_earth:      each transformer is joined to the earth bus on the north wall: the strap starts on the base lug, ends on the bus;
- tr_rollout:    the transformer rolls out through its door on rollers: door >= width + 0.1 m, door height, the sweep from outside to
                 its place touches no wall (4.2.216, 4.2.220);
- tr_clash:      no intersection between the transformers, rails, bus, collars, earth, louvres, the shell and the MCC side (BVH).
WARN (own recommendation): the bus of T2 crosses chamber T1 (4.2.111: transit through a chamber is not allowed as a rule);
inlet and outlet centres closer than 1.5 m in height.

Broken variants, one per rule, each must fail only its own rule (the MCC room: ten, the transformer chambers: eight).

Run:
    blender --background --python world/build/check_mcc.py
"""

import copy
import json
import math
import sys
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import common as c  # noqa: E402
from kit import mcc_room as mcc  # noqa: E402

SITE = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
AISLE_W = 0.8          # ПУЭ-7 п. 4.1.23 (analog)
AISLE_H = 1.9          # same
NARROW = 0.6           # same clause: local narrowing, used as the WARN limit with two doors open
PLATE_Z = (1.5, 2.0)   # EST: a plate a standing person reads without bending or a step
TOL = 0.002
SHELL = ("mcc_walls", "mcc_lining", "mcc_floor", "mcc_ceiling", "ktp_trafo")


def _bvh(items, dz=0.0):
    verts, polys, base = [], [], 0
    for v, f in items:
        v = np.asarray(v, float) + (0, 0, dz)
        for b in (f if isinstance(f, list) else [f]):
            polys += [tuple(int(i) + base for i in row) for row in np.asarray(b)]
        verts.append(v)
        base += len(v)
    v = np.concatenate(verts)
    return BVHTree.FromPolygons([Vector(p) for p in v], polys)


def _bb(items):
    v = np.concatenate([np.asarray(x[0], float) for x in items])
    return v.min(0), v.max(0)


def scene(L, parts, extra):
    """Things in the room: {name: [(v, f)]}; cabinets one by one (body + door parts), the shell as one item."""
    out = {"shell": [parts[k][2] for k in SHELL]}
    for i in range(len(L["cabinets"])):
        tr, td, _ = mcc.cabinet_parts(L, i)
        out[f"cab{i}"] = list(tr.values()) + list(td.values())
    out["signal"] = [p[2] for k, p in parts.items() if k.startswith("mcc_signal_")]
    for k in ("mcc_tray", "mcc_lamps", "mcc_door"):
        out[k] = [parts[k][2]]
    for k, v in (extra or {}).items():
        out[k] = [v]
    return out


def checks(site, L=None, parts=None, extra=None):
    out = []
    L = L or mcc.layout(site)
    parts = parts or mcc.build(site, L)
    g = L["g"]
    cabs = L["cabinets"]
    reg = [it for it in site["equipment"]["items"] if it.get("kind") == "motor"]
    by_id = {it["id"]: it for it in reg}

    # registry
    seen = {}
    for cb in cabs:
        for m in cb["motors"]:
            seen[m] = seen.get(m, 0) + 1
    missing = [i for i in by_id if seen.get(i, 0) == 0]
    twice = [i for i, n in seen.items() if n > 1]
    foreign = [i for i in seen if i not in by_id]
    units = sum(int(it.get("qty") or 1) for it in reg)
    n_motor = sum(cb["kind"] == "motor" for cb in cabs)
    out.append(("registry", not (missing or twice or foreign),
                f"{len(reg)} register motors ({units} units) in {n_motor} motor cabinets + "
                f"{len(cabs) - n_motor} incoming" + (f"; missing {missing}, twice {twice}, foreign {foreign}" if missing or twice or foreign else ": each once")))

    # fill (recomputed from the register, not from the cabinet record)
    fills = [sum(mcc.feeder(by_id[m])[1] * int(by_id[m].get("qty") or 1) for m in cb["motors"] if m in by_id) for cb in cabs]
    over = [(cb["name"], s) for cb, s in zip(cabs, fills) if s > mcc.CAB_SLOTS]
    out.append(("fill", not over, f"places per cabinet {fills} (<= {mcc.CAB_SLOTS})" + (f"; over: {over}" if over else "")))
    res = [(cb["name"], s) for cb, s in zip(cabs, fills) if s > mcc.FILL_MAX]
    if res:
        out.append(("fill reserve: WARN", True, f"over {mcc.FILL_MAX} places (design reserve): {res}"))

    # labels
    bad = []
    for i, cb in enumerate(cabs):
        _, td, _ = mcc.cabinet_parts(L, i)
        p0, p1 = _bb([td["plate"]])
        d0, d1 = _bb([td["doors"]])
        normal = 0 if abs(math.sin(math.radians(cb["rot"]))) > 0.5 else 1      # the axis the door faces along
        along = 1 - normal
        on_door = (d0[along] - 1e-6 <= p0[along] and p1[along] <= d1[along] + 1e-6 and d0[2] <= p0[2] and p1[2] <= d1[2]
                   and min(abs(p0[normal] - d1[normal]), abs(p1[normal] - d0[normal])) <= 0.005)
        zc = (p0[2] + p1[2]) / 2 - cb["origin"][2]
        if cb["kind"] == "motor":
            ids = mcc.label_ids(cb["label"])
            text_ok = sorted(ids) == sorted(cb["motors"])
        else:
            text_ok = "ВВІД" in cb["label"]
        if not (on_door and text_ok and PLATE_Z[0] <= zc <= PLATE_Z[1]):
            bad.append(f"{cb['name']}: on door {on_door}, text {text_ok}, centre {zc:.2f}")
    out.append(("labels", not bad, bad[:4] or f"{len(cabs)} plates on their doors, texts match the motor groups"))

    sc = scene(L, parts, extra)
    allbvh = _bvh([x for items in sc.values() for x in items])

    # aisle width: rays from the handle plane of each row across the aisle
    widths = {}
    for row in L["rows"]:
        n = np.array([row["face"], 0.0, 0.0])
        x = row["front"] + row["face"] * 0.051
        worst = (1e9, None)
        for y in np.arange(row["y"][0] + 0.02, row["y"][1] - 0.019, 0.05):
            wy = 1e9
            for z in (0.05, 0.4, 0.8, 1.2, 1.6, 1.89):
                hit = allbvh.ray_cast(Vector((x, y, g + z)), Vector(n), 20.0)
                d = (hit[3] + 0.001) if hit[0] is not None else 1e9
                wy = min(wy, d)
                if d < worst[0]:
                    worst = (d, (round(y, 2), z))
            widths[(row["id"], round(y, 3))] = wy
        row["_w"] = worst
    ok = all(r["_w"][0] >= AISLE_W - 1e-6 for r in L["rows"])
    out.append(("aisle_width", ok, "; ".join(f"row {r['id']}: {r['_w'][0]:.2f} m (y, z {r['_w'][1]})" for r in L["rows"])
                + f" (>= {AISLE_W})"))

    # aisle height: rays up over the passage in front of each row, as wide as it is
    low = (1e9, None)
    for row in L["rows"]:
        x0 = row["front"] + row["face"] * 0.051
        for y in np.arange(row["y"][0] + 0.02, row["y"][1] - 0.019, 0.1):
            w = widths.get((row["id"], round(y, 3)), row["_w"][0])
            for d in np.arange(0.02, min(w, 6.0) - 0.019, 0.1):
                p = Vector((x0 + row["face"] * d, y, g + 0.01))
                hit = allbvh.ray_cast(p, Vector((0, 0, 1)), 10.0)
                z = (hit[0].z - g) if hit[0] is not None else 1e9
                if z < low[0]:
                    low = (z, (round(p.x, 2), round(y, 2)))
    out.append(("aisle_height", low[0] >= AISLE_H - 1e-6, f"clear height {low[0]:.2f} m at {low[1]} (>= {AISLE_H})"))

    # doors: swing 10..90° against everything but the own door parts
    hits = []
    for i, cb in enumerate(cabs):
        tr, _, _ = mcc.cabinet_parts(L, i)
        others = [x for k, items in sc.items() if k != f"cab{i}" for x in items] + list(tr.values())
        st = _bvh(others)
        for a in range(10, 91, 5):
            if _bvh([mcc.door_at(L, i, a)]).overlap(st):
                hits.append(f"{cb['name']} at {a}°")
                break
    out.append(("doors", not hits, hits[:6] or f"{len(cabs)} doors swing to 90° clear"))
    # WARN: two opposite doors open at once
    span = {i: _bb(sc[f"cab{i}"]) for i in range(len(cabs))}
    free = 1e9
    for i, a in enumerate(cabs):
        for j, b in enumerate(cabs):
            (a0, a1), (b0, b1) = span[i], span[j]
            if a["row"] == "W" and b["row"] == "E" and min(a1[1], b1[1]) > max(a0[1], b0[1]):
                free = min(free, _bb([mcc.door_at(L, j, 90)])[0][0] - _bb([mcc.door_at(L, i, 90)])[1][0])
    if free < NARROW:
        out.append(("two opposite doors open: WARN", True, f"{free:.2f} m left between them (< {NARROW})"))
    else:
        out.append(("two opposite doors open", True, f"{free:.2f} m left between them (>= {NARROW})"))

    # floor
    rx0, ry0, rx1, ry1 = L["room"]
    li = mcc.LINING
    bad = []
    for i, cb in enumerate(cabs):
        lo, hi = _bb(sc[f"cab{i}"])
        inside = rx0 + li - 1e-6 <= lo[0] and hi[0] <= rx1 - li + 1e-6 and ry0 + li - 1e-6 <= lo[1] and hi[1] <= ry1 - li + 1e-6
        if abs(lo[2] - g) > 0.001 or not inside:
            bad.append(f"{cb['name']}: base {lo[2] - g:+.3f}, inside {inside}")
    out.append(("floor", not bad, bad[:4] or f"{len(cabs)} cabinets on the floor inside {rx1 - rx0 - 2 * li:.2f} x {ry1 - ry0 - 2 * li:.2f} m"))

    # tray
    boxes = {nm: (np.array(a), np.array(b)) for nm, a, b in L["tray"]}

    def touch(p, q):
        return all(p[0][k] <= q[1][k] + TOL and q[0][k] <= p[1][k] + TOL for k in range(3))

    names = list(boxes)
    comp, todo = {names[0]}, [names[0]]
    while todo:
        a = todo.pop()
        for b in names:
            if b not in comp and touch(boxes[a], boxes[b]):
                comp.add(b)
                todo.append(b)
    ct = site["designed"]["site_plan"]["cable_trestle"]
    ex, ey = ct["pts"][0]
    zt = g + ct["z"]
    e0, e1 = boxes["exit"]
    meet = (abs(e0[0] - ex) <= 0.005 and abs(e0[1] - (ey - mcc.TRAY_W / 2)) <= 0.005 and abs(e1[1] - (ey + mcc.TRAY_W / 2)) <= 0.005
            and abs(e0[2] - zt) <= 0.005 and abs(e1[2] - (zt + mcc.TRAY_H)) <= 0.005)
    under = []
    for i, cb in enumerate(cabs):
        lo, hi = _bb(sc[f"cab{i}"])
        cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        if not any(a[0] <= cx <= b[0] and a[1] <= cy <= b[1] and a[2] > hi[2] for a, b in boxes.values()):
            under.append(cb["name"])
    out.append(("tray", len(comp) == len(names) and meet and not under,
                f"{len(comp)}/{len(names)} pieces connected, exit meets the trestle at ({ex}, {ey}, +{ct['z']}): {meet}, "
                f"cabinets off the tray: {under or 'none'}"))

    # exit
    longest = max(r["y"][1] - r["y"][0] for r in L["rows"])
    need = 2 if longest > mcc.ROW_TWO_EXITS else 1
    good = 0
    notes = []
    for d in L["doors"]:
        outer = d["wall"] in ("south", "north", "west")
        span = rx0 <= d["x"][0] and d["x"][1] <= rx1
        if d["wall"] == "south":
            zone = (d["x"][0], ry0, d["x"][1], ry0 + mcc.DOOR_CLEAR)
        elif d["wall"] == "north":
            zone = (d["x"][0], ry1 - mcc.DOOR_CLEAR, d["x"][1], ry1)
        else:
            zone = None
        clear = True
        if zone:
            for i in range(len(cabs)):
                lo, hi = _bb(sc[f"cab{i}"])
                if lo[0] < zone[2] and zone[0] < hi[0] and lo[1] < zone[3] and zone[1] < hi[1]:
                    clear = False
        good += outer and span and clear
        notes.append(f"{d['wall']} {d['x']}: outer {outer}, in the room {span}, {mcc.DOOR_CLEAR} m inside clear {clear}")
    out.append(("exit", good >= need, f"{good} exits (need {need}: longest row {longest:.2f} m); " + "; ".join(notes)))

    # clash: a pair clashes when it overlaps whichever of the two is lifted 2 mm (a thing standing on another touches it)
    hits = []
    stand = {k for k in sc if k.startswith("cab")} | {"signal"}
    items = [k for k in sc if k != "shell"]
    up = {k: _bvh(sc[k], 0.002 if k in stand else 0.0) for k in items}
    flat = {k: _bvh(sc[k]) for k in items + ["shell"]}
    up["shell"] = flat["shell"]
    for i, a in enumerate(items):
        for b in items[i + 1:] + ["shell"]:
            if up[a].overlap(flat[b]) and up[b].overlap(flat[a]):
                hits.append(f"{a} x {b}")
    out.append(("clash", not hits, hits[:6] or f"{len(items)} items clean"))
    return out


# ---------------------------------------------------------------- C7b: transformer chambers
G_TOL = 0.001
AIR_H_REC = 1.5          # EST recommendation: height between the opening centres
CAP_R = 0.030            # HV bushing cap radius (the live part), EST


def _verts(item):
    return np.asarray(item[0], float)


def _bvh_shift(item, dy, dx=0.0):
    v, f = item
    polys = [tuple(int(i) for i in row) for blk in (f if isinstance(f, list) else [f]) for row in np.asarray(blk)]
    return BVHTree.FromPolygons([tuple(p) for p in np.asarray(v, float) + (dx, dy, 0.0)], polys)


def trafo_scene(site, faults=None):
    """L, T and every mesh the transformer rules need, built under `faults` (MCC side included)."""
    L = mcc.layout(site)
    L["trafo_faults"] = faults or {}
    T = mcc.trafo_layout(site, L, faults or {})
    parts = mcc.build(site, L)
    tr = {ch["name"]: c.merge_parts([(mcc._world(v, ch), f) for v, f in T["trafo"]["parts"].values()]) for ch in T["chambers"]}
    return L, T, parts, tr


def trafo_checks(site, faults=None):
    out = []
    L, T, parts, tr = trafo_scene(site, faults)
    g = L["g"]
    G = T["geom"]
    x0, y0, x1, y1 = G["block"]
    d = T["trafo"]["dims"]
    loss = d["loss_w"]

    # tr_clearance
    bad, notes = [], []
    for ch in T["chambers"]:
        v = _verts(tr[ch["name"]])
        v = v[v[:, 2] <= g + mcc.LOW_Z]
        ix0, iy0, ix1, iy1 = ch["inner"]
        w, e, n, front = v[:, 0].min() - ix0, ix1 - v[:, 0].max(), iy1 - v[:, 1].max(), v[:, 1].min() - y0
        xa, xb = ch["door"]
        own_door = ix0 <= xa and xb <= ix1
        notes.append(f"{ch['name']}: W {w:.2f} E {e:.2f} N {n:.2f} door {front:.2f}")
        if min(w, e, n) < mcc.CLEAR_SIDE - 1e-6 or front < mcc.CLEAR_FRONT - 1e-6 or not own_door:
            bad.append(f"{ch['name']}: W {w:.3f} E {e:.3f} N {n:.3f} door {front:.3f}, own door {own_door}")
    out.append(("tr_clearance", not bad, bad or "; ".join(notes) + f" (sides >= {mcc.CLEAR_SIDE}, door >= {mcc.CLEAR_FRONT} m, PUE 4.2.217)"))

    # tr_rollers
    bad, notes = [], []
    rv = _verts(parts["ktp_rails"][2])
    for ch in T["chambers"]:
        wheels = [(ch["c"][0] + y, ch["c"][1] - x) for x, y in d["rollers"]]                  # local (x, y) -> world (cx + y, cy - x)
        rr = _verts(c.merge_parts([(mcc._world(v, ch), f) for k, (v, f) in T["trafo"]["parts"].items() if k == "rollers"]))
        contact = float(rr[:, 2].min())
        near = rv[np.abs(rv[:, 0] - ch["c"][0]) <= d["cat"]["A1"] / 2 + 0.05]
        top = float(near[:, 2].max())
        over = all(any(abs(wx - rx) <= mcc.RAIL_B / 2 for rx in ch["rail_x"]) and near[:, 1].min() <= wy <= near[:, 1].max() for wx, wy in wheels)
        notes.append(f"{ch['name']}: contact {contact - top:+.4f} m over the rail top, wheels over the rails {over}")
        if abs(contact - top) > G_TOL or not over:
            bad.append(f"{ch['name']}: contact {contact - top:+.4f} m over the rail top, wheels over the rails {over}")
    out.append(("tr_rollers", not bad, bad or "; ".join(notes)))

    # tr_insulators
    bad, notes = [], []
    ceil = G["ceiling"]
    for ch in T["chambers"]:
        hv = [mcc._world(np.array([p]), ch)[0] for p in d["hv"]]
        top = max(p[2] for p in hv)
        pitch = min(math.hypot(a[0] - b[0], a[1] - b[1]) for i, a in enumerate(hv) for b in hv[i + 1:]) - 2 * CAP_R
        ix0, iy0, ix1, iy1 = ch["inner"]
        wall = min(min(p[0] - ix0, ix1 - p[0], p[1] - iy0, iy1 - p[1]) for p in hv) - CAP_R
        notes.append(f"{ch['name']}: top {ceil - top:.2f} m under the ceiling, phases {pitch:.2f}, wall {wall:.2f}")
        if ceil - top < mcc.HV_TO_EARTH or pitch < mcc.HV_PHASE or wall < mcc.HV_TO_EARTH:
            bad.append(f"{ch['name']}: {ceil - top:.3f} under the ceiling, phases {pitch:.3f}, wall {wall:.3f}")
    out.append(("tr_insulators", not bad, bad or "; ".join(notes) + f" (>= {mcc.HV_TO_EARTH} to earth, >= {mcc.HV_PHASE} between phases, 10 kV, table 4.2.7)"))

    # tr_bus
    bad, notes = [], []
    bv = _verts(parts["ktp_bus"][2])
    cb = T["cab_box"]
    holes = mcc._bus_holes(g, T["duct_z"], tuple(ch["lane"] for ch in T["chambers"]))
    for k, ch in enumerate(T["chambers"]):
        lane = ch["lane"]
        studs = [mcc._world(np.array([p]), ch)[0] for p in d["lv"]]
        jb = bv[(np.abs(bv[:, 1] - lane) <= mcc.JUNC[1] / 2 + 1e-6) & (np.abs(bv[:, 0] - ch["lv_x"]) <= mcc.JUNC[0] / 2 + 0.03)
                & (bv[:, 2] < studs[0][2] + mcc.JUNC_UP + mcc.JUNC[2] + 1e-6) & (bv[:, 2] > studs[0][2] + mcc.JUNC_UP - 1e-6)]
        under = all(jb[:, 0].min() <= p[0] <= jb[:, 0].max() and jb[:, 1].min() <= p[1] <= jb[:, 1].max() for p in studs)
        drop = bv[(bv[:, 0] <= cb[2] + 1e-6) & (np.abs(bv[:, 1] - lane) <= mcc.DUCT_W / 2 + 1e-6)]
        low = float(drop[:, 2].min())
        inside = cb[0] <= drop[:, 0].min() and drop[:, 0].max() <= cb[2] and cb[1] <= lane - mcc.DUCT_W / 2 and lane + mcc.DUCT_W / 2 <= cb[3]
        lands = abs(low - T["cab_top"]) <= 0.005 and inside
        gaps = []
        duct = bv[(np.abs(bv[:, 1] - lane) <= mcc.DUCT_W / 2 + 1e-6) & (bv[:, 2] >= g + T["duct_z"] - 1e-6)]       # the horizontal duct (and its riser)
        for wall, span, hl in (("p0", G["p0"], holes["p0"][0]), ("q", G["xq"], holes["q"][0] if k == 1 else None)):
            if hl is None:
                continue
            crosses = duct[:, 0].min() <= span[0] and duct[:, 0].max() >= span[1]
            if not crosses:
                gaps.append(-1.0)
                continue
            # the opening edge each duct faces (the lower duct the south edge, the upper one the north edge); the common p0 opening packs the ducts
            edge = (duct[:, 1].min() - hl[0]) if (wall == "q" or k == 0) else (hl[1] - duct[:, 1].max())
            gaps += [edge, duct[:, 2].min() - hl[2], hl[3] - duct[:, 2].max()]
        sealed = all(0.0 <= x <= 0.020 + 1e-9 for x in gaps)
        if k == 1:                                                                  # the packing between the two ducts in the common opening
            low_duct = bv[(np.abs(bv[:, 1] - T["chambers"][0]["lane"]) <= mcc.DUCT_W / 2 + 1e-6) & (bv[:, 2] >= g + T["duct_z"] - 1e-6)]
            between = duct[:, 1].min() - low_duct[:, 1].max()
            sealed = sealed and 0.0 <= between <= 0.080 + 1e-9
            gaps.append(between)
        notes.append(f"{ch['name']}: studs under the junction {under}, drop {low - T['cab_top']:+.4f} m over ШВ-1 inside its plan {inside}, "
                     f"opening gaps {min(gaps) * 1000:.0f}-{max(gaps) * 1000:.0f} mm")
        if not (under and lands and sealed):
            bad.append(f"{ch['name']}: studs under the junction {under}, drop {low - T['cab_top']:+.4f} m over ШВ-1, inside its plan {inside}, gaps {[round(x * 1000) for x in gaps]} mm")
    out.append(("tr_bus", not bad, bad or "; ".join(notes)))
    t2 = bv[np.abs(bv[:, 1] - T["chambers"][1]["lane"]) <= mcc.DUCT_W / 2 + 1e-6]
    ix0, iy0, ix1, iy1 = T["chambers"][0]["inner"]
    transit = bool(((t2[:, 0] > ix0) & (t2[:, 0] < ix1)).any())
    out.append(("transit of the T2 bus through chamber T1: WARN" if transit else "transit of the T2 bus through chamber T1", True,
                (f"the enclosed duct crosses T1 above the transformer at +{T['duct_z']:.2f} m" if transit else "none")
                + " (PUE 4.2.111: as a rule not allowed; exception: closed enclosure)"))

    # tr_vents
    bad, notes, warn = [], [], []
    walls = _bvh([parts["ktp_trafo"][2]])
    for ch in T["chambers"]:
        vs = {v["kind"]: v for v in G["vents"] if v["ch"] == ch["name"]}
        hc = ((vs["out"]["z0"] + vs["out"]["z1"]) - (vs["in"]["z0"] + vs["in"]["z1"])) / 2
        need = mcc.vent_required(loss, hc)
        for kind, v in vs.items():
            south = v["wall"] == "south"
            face = y0 if south else y1
            ray = walls.ray_cast(Vector((0.5 * (v["x0"] + v["x1"]), face + (-0.5 if south else 0.5), g + 0.5 * (v["z0"] + v["z1"]))), Vector((0, 1 if south else -1, 0)), 3.0)
            through = ray[0] is None or abs(ray[0].y - face) > 0.5
            net = mcc.vent_net(v)
            if net < need or mcc.MESH_MM > 10.0 or not through:
                bad.append(f"{ch['name']} {kind}: free {net:.2f} m2 vs need {need:.2f} m2, mesh {mcc.MESH_MM} mm, open in the wall {through}")
        notes.append(f"{ch['name']}: free {mcc.vent_net(vs['in']):.2f} / {mcc.vent_net(vs['out']):.2f} m2 >= {need:.2f} m2 (P {loss:.0f} W, h {hc:.2f} m)")
        if hc < AIR_H_REC:
            warn.append(f"{ch['name']}: centres only {hc:.2f} m apart")
    out.append(("tr_vents", not bad, bad or "; ".join(notes) + f"; mesh {mcc.MESH_MM:.0f} mm"))
    if warn:
        out.append(("vent heights: WARN", True, "; ".join(warn) + f" (< {AIR_H_REC})"))

    # tr_earth
    bad, notes = [], []
    sv = _verts(parts["ktp_straps"][2])
    ev = _verts(parts["ktp_earth"][2])
    for ch in T["chambers"]:
        lug = mcc._world(np.array([d["earth_pt"]]), ch)[0]
        mine = sv[np.abs(sv[:, 0] - lug[0]) <= 0.02]
        start = float(np.min(np.linalg.norm(mine - lug, axis=1)))
        north = float(mine[:, 1].max())
        z_ok = abs(float(mine[:, 2].max()) - (g + mcc.EARTH_Z)) <= mcc.EARTH_FLAT[0] / 2 + 0.01
        on_bus = ev[:, 1].min() - 0.005 <= north <= ev[:, 1].max() + 0.001 and z_ok and ev[:, 0].min() <= lug[0] <= ev[:, 0].max()
        notes.append(f"{ch['name']}: strap starts {start * 1000:.1f} mm from the lug, ends {1000 * (ev[:, 1].max() - north):.1f} mm from the bus face")
        if start > 0.010 or not on_bus:
            bad.append(f"{ch['name']}: starts {start * 1000:.1f} mm from the lug, north end {north:.3f} vs bus {ev[:, 1].min():.3f}-{ev[:, 1].max():.3f}, z ok {z_ok}")
    out.append(("tr_earth", not bad, bad or "; ".join(notes)))

    # tr_rollout: 50 mm each side, then the sweep through the door
    bad, notes = [], []
    for ch in T["chambers"]:
        v = _verts(tr[ch["name"]])
        width = float(v[:, 0].max() - v[:, 0].min())
        xa, xb = ch["door"]
        tall = float(v[:, 2].max() - g)
        free = (xb - xa) - width
        blocked = None
        dx = 0.5 * (xa + xb) - ch["c"][0]                     # it enters on the door axis (swivel rollers turn it sideways inside)
        for dy in np.arange(-(ch["c"][1] - y0 + 1.0), 0.0001, 0.1):
            if _bvh_shift(tr[ch["name"]], dy, dx).overlap(walls):
                blocked = round(float(ch["c"][1] + dy), 2)
                break
        if free < 0.1 - 1e-9 or tall > mcc.DOOR_H or blocked is not None:
            bad.append(f"{ch['name']}: door {xb - xa:.2f} m for {width:.2f} m (spare {free:.2f}, need 0.10), height {tall:.2f}, blocked at y {blocked}")
        notes.append(f"{ch['name']}: door {xb - xa:.2f} m for {width:.2f} m (spare {free:.2f}), sweep from outside clean")
    out.append(("tr_rollout", not bad, bad or "; ".join(notes)))

    # tr_clash: the shell is one group (its pieces touch face to face), the MCC side another
    shell = [parts[k][2] for k in ("ktp_trafo", "ktp_floor", "ktp_ceiling", "mcc_walls", "mcc_lining", "mcc_ceiling", "mcc_floor")]
    mccside = {"mcc": [parts[k][2] for k in ("mcc_tray", "mcc_cab_body", "mcc_cab_doors", "mcc_signal_body", "mcc_signal_tier_red", "mcc_signal_tier_yellow",
                                              "mcc_signal_tier_green")]}
    groups = {"shell": shell, **mccside, "tr1": [tr["T1"]], "tr2": [tr["T2"]], "rails": [parts["ktp_rails"][2]], "bus": [parts["ktp_bus"][2]],
              "collars": [parts["ktp_collars"][2]], "earth": [parts["ktp_earth"][2]], "straps": [parts["ktp_straps"][2]],
              "louvres": [parts["ktp_louvres"][2]]}
    if "ktp_stray" in parts:
        groups["stray"] = [parts["ktp_stray"][2]]
    trees = {k: _bvh(v) for k, v in groups.items()}
    hits = []
    names = list(groups)
    touch = {("tr1", "straps"), ("tr2", "straps")}                          # the strap is bolted on the lug
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if (a, b) in touch or (b, a) in touch or (a == "shell" and b in mccside):      # the MCC room vs its shell is rule `clash`
                continue
            if trees[a].overlap(trees[b]):
                hits.append(f"{a} x {b}")
    out.append(("tr_clash", not hits, hits[:6] or f"{len(groups)} groups clean"))
    return out


TR_VARIANTS = (
    ("tr_clearance", "T2 0.6 m west: 0.25 m left to the partition (4.2.217 asks 0.3)", {"x2_dx": -0.60}),
    ("tr_rollers", "rails 20 mm lower: the rollers hang over them", {"rail_dz": -0.02}),
    ("tr_insulators", "HV bushings 0.15 m apart (phase clearance 0.09 m)", {"a2": 0.15}),
    ("tr_bus", "bus drop 0.12 m over the cabinet ШВ-1", {"drop_dz": 0.12}),
    ("tr_vents", "T1 outlet half as wide (free area under the loss need)", {"vent_ch": "T1", "vent_kind": "out", "vent_scale": 0.5}),
    ("tr_earth", "earth straps 0.1 m short of the bus", {"earth_dy": 0.10}),
    ("tr_rollout", "doors 0.95 m wide for a 1.0 m transformer", {"door_w": 0.95}),
    ("tr_clash", "a pipe through transformer T1", {"stray": True}),
)


def main():
    sys.stdout.reconfigure(errors="replace")
    ok_all = True
    base = checks(SITE)
    for rid, ok, info in base:
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {rid}: {info}", flush=True)
    base_fail = {r for r, ok, _ in base if not ok}
    L0 = mcc.layout(SITE)
    P0 = mcc.build(SITE, L0)
    names = {cb["name"]: i for i, cb in enumerate(L0["cabinets"])}

    def assign_from(L):
        return [{k: cb[k] for k in ("motors", "slots", "groups")} for cb in L["cabinets"] if cb["kind"] == "motor"]

    def v_registry():
        a = copy.deepcopy(assign_from(L0))
        for cb in a:
            if "S1.roof_fan" in cb["motors"]:
                cb["motors"].remove("S1.roof_fan")
        return checks(SITE, mcc.layout(SITE, a))

    def v_fill():
        a = copy.deepcopy(assign_from(L0))
        src = next(cb for cb in a if "existing:H" in cb["groups"])
        dst = next(cb for cb in a if "S1" in cb["groups"])
        dst["motors"] += src["motors"]
        dst["groups"] += src["groups"]
        src["motors"], src["groups"] = [], []
        return checks(SITE, mcc.layout(SITE, a))

    def v_labels():
        L = mcc.layout(SITE)
        cb = L["cabinets"][names["ШУ-3"]]
        cb["label"] = cb["label"].replace(" S2.fan×4", "")
        return checks(SITE, L, P0)

    def v_width():
        w = next(r for r in L0["rows"] if r["id"] == "W")["front"] + 0.05
        e = next(r for r in L0["rows"] if r["id"] == "E")["front"] - 0.05
        return checks(SITE, mcc.layout(SITE, shift={"E": -(e - w - 0.78)}))

    def v_height():
        L = mcc.layout(SITE)
        L["lamp_z"] = L["g"] + 1.88
        return checks(SITE, L)

    def v_doors():
        g = L0["g"]
        return checks(SITE, None, None, {"duct": c.box((21.0, 28.0, g + 1.95), (21.5, 28.6, g + 2.05))})

    def v_floor():
        L = mcc.layout(SITE)
        cb = L["cabinets"][names["ШУ-6"]]
        cb["origin"] = (cb["origin"][0], cb["origin"][1], cb["origin"][2] + 0.05)
        return checks(SITE, L)

    def v_tray():
        L = mcc.layout(SITE)
        L["tray"] = [(nm, (a[0], 27.25, a[2]), (b[0], 27.75, b[2])) if nm == "exit" else (nm, a, b) for nm, a, b in L["tray"]]
        return checks(SITE, L, P0)

    def v_exit():
        L = mcc.layout(SITE)
        L["doors"] = [dict(L["doors"][0], wall="partition")]
        return checks(SITE, L, P0)

    def v_clash():
        L = mcc.layout(SITE)
        L["column_dz"] = -0.1
        return checks(SITE, L)

    for rid, title, fn in (("registry", "S1.roof_fan не потрапив у шафу", v_registry),
                           ("fill", "існуючі норії перенесено в шафу силосу S1 (17 місць)", v_fill),
                           ("labels", "на табличці ШУ-3 немає S2.fan", v_labels),
                           ("aisle_width", "східний ряд зсунуто: прохід 0,78 м", v_width),
                           ("aisle_height", "світильники опущено на 1,83 м", v_height),
                           ("doors", "короб на 1,95-2,05 м перед західним рядом", v_doors),
                           ("floor", "ШУ-6 стоїть на 50 мм вище підлоги", v_floor),
                           ("tray", "вихід лотка на y 27,5 замість 29", v_tray),
                           ("exit", "двері МСС у перегородці до трансформаторів", v_exit),
                           ("clash", "сигнальна колона на 0,1 м у даху шафи ШВ-1", v_clash)):
        got = {r for r, ok, _ in fn() if not ok}
        seen = rid in got and not (got - base_fail - {rid})
        ok_all &= seen
        print(f"{'EXPECTED FAIL' if seen else 'FAIL  variant'} {title} -> {'OK' if seen else sorted(got)}", flush=True)
    base_tr = trafo_checks(SITE)
    for rid, ok, info in base_tr:
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {rid}: {info}", flush=True)
    tr_fail = {r for r, ok, _ in base_tr if not ok}
    for rid, title, faults in TR_VARIANTS:
        got = {r for r, ok, _ in trafo_checks(SITE, faults) if not ok}
        seen = rid in got and not (got - tr_fail - {rid})
        ok_all &= seen
        print(f"{'EXPECTED FAIL' if seen else 'FAIL  variant'} {title} -> {'OK' if seen else sorted(got)}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
