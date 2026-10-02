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

Broken variants, one per rule, each must fail only its own rule.

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
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
