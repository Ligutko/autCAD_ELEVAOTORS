"""MCC room (щитова МСС) in the КТП block (HERO_DETAIL_SPEC row 6, «шафа з кнопками»): the block 12 x 6 m
(SITE designed.site_plan.ktp, rooms «2КТП 2 × 630 кВА», «МСС») is split by a wall into the closed transformer part
(east, its two doors stay) and the MCC room (west, the third door, opening outwards). Two rows of Rittal VX25
800 x 2000 x 600 RAL 7035 (controls.cabinet) with their backs to the long walls face one aisle; the cable tray runs
over the rows and leaves through the west wall onto the cable trestle at (20, 29), +3.0; ceiling lamps over the
aisle; a stack light on the incoming cabinet.

How many cabinets: counted from the motor register (SITE equipment.items, kind "motor"), rule `group_motors`:
- every motor unit (qty counted) has its own feeder; the feeder size comes from the power (EST, judgment):
  direct-on-line starter up to 15 kW = 1 slot; soft starter from 18.5 kW = 2 slots (loaded start of a noria or a
  sweep auger on a 630 kVA transformer; speed control is not needed: every machine runs at its rated capacity, so
  no frequency converters); power unknown (existing machines, designed T3 / T5) = 2 slots, reserved as the largest;
- a cabinet holds CAB_SLOTS slots (EST: plate 699 x 1896, four DIN rows of three feeder places with their relays
  and terminals) and is filled to FILL_MAX (EST: ~17 % spare, usual design reserve);
- motors are grouped by the process unit (one silo; the drawn norias; the drawn conveyors; existing norias; existing
  conveyors; the designed drying loop) and a group is never split while it fits one cabinet; groups are packed
  first-fit decreasing; one incoming cabinet (two feeders from the РУНН of the 2КТП, ATS) is added.

Passage in front of the rows >= 0.8 m wide and >= 1.9 m high (ПУЭ-7 п. 4.1.23, analog for the Ukrainian ПУЕ),
two exits when a row is longer than 7 m (same clause). Site frame, metres. Floor at the ground (SITE ground_z).

C7b: the transformer part holds two chambers (a partition at XQ), each with a TMG-630/10/0.4 (kit/transformer.py) on rails,
a south door opening (the leaf stays in site_plan), a low inlet and a high outlet louvre, an earth bus, and an LV bus duct
to the incoming cabinet ШВ-1 of the MCC room (through the partition openings with fire-stop collars).
    trafo_layout(site, L=None, faults=None) -> numbers the check uses; chamber_parts(site, T) -> {part: (material, smooth, (v, f))}.

    layout(site, assign=None) -> numbers the check uses; build(site, L=None) -> {part: (material, smooth, (v, f))};
    add_scene_extras(site, collection, materials) adds the ceiling area lights and the cabinet plate texts (bpy).
"""

import math
import re

import numpy as np

from . import common as c
from . import controls as ctl
from . import steel as st
from . import transformer as tf

WALL = 0.25            # EST: block wall, as the АПК (operator_room.WALL)
ROOM_W = 4.25          # EST: MCC room from the west face to the partition (outer), the partition 0.25 thick after it
LINING = 0.005         # EST: plaster and paint on the inner faces
BACK = 0.05            # EST: cabinet back off the wall face (uneven wall, cables)
BAY = 0.002            # EST: joint between bayed cabinets
CAB_SLOTS = 12         # EST: feeder places in one 800 x 2000 cabinet (four DIN rows x three places)
FILL_MAX = 10          # EST: design reserve ~17 % (two of twelve places spare)
SOFT_KW = 18.5         # EST, judgment: soft starter from 18.5 kW (sweep augers 18.5, norias 22)
DOL_MAX_KW = 15.0      # EST: direct-on-line up to 15 kW (S0 starter, ~29 A)
UNKNOWN_SLOTS = 2      # EST: power not in the register -> reserve the place of the largest feeder
TRAY_W = 0.5           # the trestle tray width (site_plan.build_services: +-0.25)
TRAY_H = 0.12          # the trestle tray height
TRAY_GAP = 0.005       # EST: clearance of the tray in its wall opening
CEIL = 0.03            # EST: suspended ceiling board
LAMP = (0.2, 1.2, 0.05)  # EST: LED linear luminaire w x l x h, ~4000 lm (flux NOT_FOUND)
LAMP_LM = 4000.0       # EST
LAMP_Y = (-1.3, 0.5)   # EST: lamp centres along the aisle from the room centre (clear of the cross tray)
DOOR = (22.0, 23.2, 2.4)  # the existing MCC door on the south face (site_plan.build_buildings: x0 + 2.0, 1.2 x 2.4)
DOOR_CLEAR = 0.5       # EST: free floor inside the door, no cabinet
ROW_TWO_EXITS = 7.0    # ПУЭ-7 4.1.23 (analog): a board longer than 7 m needs two exits
PLATE = (0.40, 0.17, 0.003)  # EST: engraved plate w x h x t on the door (size NOT_FOUND)
PLATE_Z = 1.80         # EST: plate centre over the floor, above the door lamps (1.40)


def _register(site):
    return [it for it in site["equipment"]["items"] if it.get("kind") == "motor"]


def feeder(item):
    """(starter, slots per unit) for a register motor (EST rule, module docstring)."""
    kw = item.get("kw")
    if kw is None:
        return "кВт немає: місце як для найбільшого", UNKNOWN_SLOTS
    if kw >= SOFT_KW:
        return "плавний пуск", 2
    if kw <= DOL_MAX_KW:
        return "прямий пуск", 1
    return "прямий пуск S2", 2


def group_key(item):
    """Process unit a motor belongs to: the silo (S1.fan -> S1), else layer + machine letter (drawn:H = norias)."""
    m = re.match(r"(S\d+)\.", item["id"])
    if m:
        return m.group(1)
    return f"{item.get('layer')}:{item['id'][0]}"


GROUP_TITLE = {"drawn:H": "норії", "drawn:T": "конвеєри", "existing:H": "існуючі норії", "existing:T": "існуючі транспортери",
               "designed:T": "петля сушарки"}


def group_motors(site, cap=FILL_MAX):
    """Motor cabinets: [{"motors": [ids], "slots": n, "groups": [keys]}] by the rule in the module docstring."""
    groups = {}
    for it in _register(site):
        groups.setdefault(group_key(it), []).append(it)
    units = []                                       # (key, [items], slots); a group over `cap` splits in register order
    for key, items in groups.items():
        cur, s = [], 0
        for it in items:
            need = feeder(it)[1] * int(it.get("qty") or 1)
            if cur and s + need > cap:
                units.append((key, cur, s))
                cur, s = [], 0
            cur.append(it)
            s += need
        units.append((key, cur, s))
    units.sort(key=lambda u: -u[2])                  # stable: register order inside equal sizes
    cabs = []
    for key, items, s in units:
        for cb in cabs:
            if cb["slots"] + s <= cap:
                break
        else:
            cb = {"motors": [], "slots": 0, "groups": []}
            cabs.append(cb)
        cb["motors"] += [it["id"] for it in items]
        cb["slots"] += s
        cb["groups"].append(key)
    return cabs


def label_text(name, cab, reg):
    """Plate text: name, the groups, then the motor ids (qty as ×n)."""
    if cab["kind"] == "incoming":
        return f"{name}\nВВІД: 2 фідери від РУНН 2КТП, АВР"
    q = {it["id"]: int(it.get("qty") or 1) for it in reg}
    ids = [f"{m}×{q[m]}" if q.get(m, 1) > 1 else m for m in cab["motors"]]
    title = ", ".join(GROUP_TITLE.get(g, f"силос {g}") for g in cab["groups"])
    lines, cur = [], ""
    for s in ids:
        if len(cur) + len(s) > 34 and cur:
            lines.append(cur)
            cur = ""
        cur = f"{cur} {s}".strip()
    lines.append(cur)
    return "\n".join([f"{name} · {title}"] + lines)


def label_ids(text):
    """Motor ids a plate text names (the inverse of label_text)."""
    body = text.split("\n")[1:]
    return [re.sub(r"×\d+$", "", t) for ln in body for t in ln.split() if not ln.startswith("ВВІД")]


def _rot(a):
    r = math.radians(a)
    return np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])


def place(v, rot, origin):
    """Cabinet-local verts (x along the row, -y the face, z up) into the site frame."""
    v = np.asarray(v, float)
    xy = v[:, :2] @ _rot(rot).T + np.asarray(origin[:2])
    return np.column_stack([xy, v[:, 2] + origin[2]])


def layout(site, assign=None, shift=None):
    """Room, rows, cabinets (with their groups and plates), tray boxes, lamps, door (site frame).
    assign: motor cabinets as group_motors returns them (default: the rule); shift: {row id: dx} moves a row across
    the aisle (the check's broken variants)."""
    g = c.ground_z()
    t = site["designed"]["site_plan"]["ktp"]
    ct = site["designed"]["site_plan"]["cable_trestle"]
    x0, x1 = t["x"]
    y0, y1 = t["y"]
    h = t["h"]
    room = (x0 + WALL, y0 + WALL, x0 + ROOM_W, y1 - WALL)           # inner faces (west, south, partition, north)
    cw, ch, cd = ctl.cabinet(1)["dims"]["cabinet"]
    plinth = ctl.PLINTH
    pitch = cw + BAY
    reg = _register(site)
    cabs = assign if assign is not None else group_motors(site)
    cabs = [{"kind": "incoming", "motors": [], "slots": 0, "groups": []}] + [dict(cb, kind="motor") for cb in cabs]
    n = len(cabs)
    n_e = n // 2                                                    # east row (partition side, the incoming first)
    rows = []
    iy0, iy1 = room[1] + LINING, room[3] - LINING
    for rid, count, rot in (("E", n_e, -90.0), ("W", n - n_e, 90.0)):
        length = count * pitch - BAY
        ya = (iy0 + iy1) / 2 - length / 2
        if rid == "W":
            ox = room[0] + LINING + BACK + cd
            origins = [(ox, ya + k * pitch, g) for k in range(count)]
            front = room[0] + LINING + BACK + cd
        else:
            ox = room[2] - LINING - BACK - cd
            origins = [(ox, ya + length - k * pitch, g) for k in range(count)]
            front = room[2] - LINING - BACK - cd
        dx = (shift or {}).get(rid, 0.0)
        origins = [(o[0] + dx, o[1], o[2]) for o in origins]
        front += dx
        rows.append({"id": rid, "rot": rot, "n": count, "y": (ya, ya + length), "front": front,
                     "face": 1.0 if rid == "W" else -1.0, "origins": origins})
    k = 0
    for row in rows:
        for o in row["origins"]:
            cb = cabs[k]
            cb.update({"row": row["id"], "rot": row["rot"], "origin": o})
            cb["name"] = "ШВ-1" if cb["kind"] == "incoming" else f"ШУ-{k}"
            cb["label"] = label_text(cb["name"], cb, reg)
            pw, ph, pt = PLATE
            loc = np.array([[cw / 2 - pw / 2, -0.02 - 0.001 - pt, PLATE_Z - ph / 2], [cw / 2 + pw / 2, -0.021, PLATE_Z + ph / 2]])
            pv = place(loc, row["rot"], o)
            cb["plate"] = (pv.min(0), pv.max(0))
            cb["plate_centre"] = place(np.array([[cw / 2, -0.02 - 0.001 - pt - 0.0005, PLATE_Z]]), row["rot"], o)[0]
            k += 1
    # tray: over each row (centre of the cabinet depth), a cross piece over the aisle near the north end, and the exit
    # through the west wall onto the trestle tray end (x0, ct pts[0])
    zt = g + ct["z"]
    ex, ey = ct["pts"][0]
    tray = []
    for row in rows:
        xc = row["front"] - row["face"] * cd / 2
        tray.append(("row_" + row["id"], (xc - TRAY_W / 2, row["y"][0], zt), (xc + TRAY_W / 2, row["y"][1], zt + TRAY_H)))
    w_tr, e_tr = (next(b for nm, *b in tray if nm == "row_" + r) for r in ("W", "E"))
    yc1 = min(w_tr[1][1], e_tr[1][1]) - 0.05
    tray.append(("cross", (w_tr[1][0], yc1 - TRAY_W, zt), (e_tr[0][0], yc1, zt + TRAY_H)))
    tray.append(("exit", (ex, ey - TRAY_W / 2, zt), (w_tr[0][0], ey + TRAY_W / 2, zt + TRAY_H)))
    w_front = next(r for r in rows if r["id"] == "W")["front"]
    e_front = next(r for r in rows if r["id"] == "E")["front"]
    lx = (w_front + 0.05 + e_front - 0.05) / 2
    lamps = [(lx, (iy0 + iy1) / 2 + dy) for dy in LAMP_Y]
    return {"g": g, "block": (x0, y0, x1, y1, h), "room": room, "ceiling": g + h - CEIL, "cabinet": (cw, ch, cd, plinth),
            "rows": rows, "cabinets": cabs, "tray": tray, "trestle": (ex, ey, zt), "lamps": lamps, "lamp_z": g + h - CEIL - 0.001,
            "doors": [{"wall": "south", "x": DOOR[:2], "h": DOOR[2], "outer": True}],
            "column_on": 0, "column_dz": 0.0, "est": EST}


EST = ["стіна 0,25 м; МСС 4,25 м від західного торця, перегородка 0,25 м",
       "шафи 50 мм від стіни, стик 2 мм",
       "місць у шафі 12 (4 рейки × 3), заповнення до 10 (запас ~17 %)",
       "пуск: прямий до 15 кВт = 1 місце; плавний від 18,5 кВт = 2; кВт немає = 2",
       "групи: силос, норії, конвеєри, існуючі норії, існуючі транспортери, петля сушарки",
       "шафа вводу одна (2 фідери від РУНН 2КТП, АВР)",
       "світильники LED 1,2 × 0,2 м, ~4000 лм",
       "табличка 400 × 170 мм на висоті 1,8 м",
       "завіс дверей шафи зліва (з боку, протилежного ручці в controls.cabinet)",
       "двері МСС відчиняються назовні; камери трансформаторів мають свої двері (site_plan), перегородка між ними на x 27,0"]


def cabinet_parts(L, i):
    """Static (body) and door-mounted (door, handle, lamps, plate) parts of cabinet i, site frame: ({k: (v, f)}, {k: (v, f)}),
    with the door hinge (local) in L for the check."""
    cb = L["cabinets"][i]
    cab = ctl.cabinet(1)
    pw, ph, pt = PLATE
    cw = L["cabinet"][0]
    plate = c.box((cw / 2 - pw / 2, -0.02 - 0.001 - pt, PLATE_Z - ph / 2), (cw / 2 + pw / 2, -0.021, PLATE_Z + ph / 2))
    static = {"body": cab["parts"]["body"]}
    door = {k: v for k, v in cab["parts"].items() if k != "body"}
    door["plate"] = plate
    tr = {k: (place(v, cb["rot"], cb["origin"]), f) for k, (v, f) in static.items()}
    td = {k: (place(v, cb["rot"], cb["origin"]), f) for k, (v, f) in door.items()}
    return tr, td, door


HINGE = (0.01, -0.02)   # door leaf pivot, cabinet-local (the leaf runs x 0.01 .. w - 0.01; handle on the right)


def door_at(L, i, angle):
    """Door-mounted parts of cabinet i opened by `angle` degrees about the hinge (outwards, -y), site frame."""
    cb = L["cabinets"][i]
    _, _, door = cabinet_parts(L, i)
    out = []
    a = math.radians(angle)
    for v, f in door.values():
        v = np.asarray(v, float)
        u, t = v[:, 0] - HINGE[0], v[:, 1] - HINGE[1]
        lx = HINGE[0] + u * math.cos(a) + t * math.sin(a)
        ly = HINGE[1] - u * math.sin(a) + t * math.cos(a)
        out.append((place(np.column_stack([lx, ly, v[:, 2]]), cb["rot"], cb["origin"]), f))
    return c.merge_parts(out)


def signal_parts(L):
    """XVU stack light on the top centre of cabinet L["column_on"], bracket to the back: {k: (v, f)}."""
    cb = L["cabinets"][L["column_on"]]
    cw, ch, cd, plinth = L["cabinet"]
    col = ctl.signal_column()
    off = np.array([cw / 2, cd / 2 - 0.05, plinth + ch + L.get("column_dz", 0.0)])
    return {k: (place(np.asarray(v, float) + off, cb["rot"], cb["origin"]), f) for k, (v, f) in col["parts"].items()}


def shell(L):
    """Walls (concrete, the tray opening in the west wall), lining, floor, ceiling, the closed transformer part, roof."""
    g = L["g"]
    x0, y0, x1, y1, h = L["block"]
    rx0, ry0, rx1, ry1 = L["room"]
    ex, ey, zt = L["trestle"]
    hy0, hy1 = ey - TRAY_W / 2 - TRAY_GAP, ey + TRAY_W / 2 + TRAY_GAP
    hz0, hz1 = zt - TRAY_GAP, zt + TRAY_H + TRAY_GAP

    walls = [c.box((x0, y0, g), (rx0, hy0, g + h)), c.box((x0, hy1, g), (rx0, y1, g + h)),
             c.box((x0, hy0, g), (rx0, hy1, hz0)), c.box((x0, hy0, hz1), (rx0, hy1, g + h)),
             c.box((rx0, y0, g), (rx1, ry0, g + h)), c.box((rx0, ry1, g), (rx1, y1, g + h))]
    li = LINING
    lining = [c.box((rx0, ry0, g), (rx0 + li, hy0, g + h)), c.box((rx0, hy1, g), (rx0 + li, ry1, g + h)),
              c.box((rx0, hy0, g), (rx0 + li, hy1, hz0)), c.box((rx0, hy0, hz1), (rx0 + li, hy1, g + h)),
              c.box((rx0 + li, ry0, g), (rx1 - li, ry0 + li, g + h)), c.box((rx0 + li, ry1 - li, g), (rx1 - li, ry1, g + h)),
              ] + _slab((rx1 - li, ry0, g), (rx1, ry1, g + h), "y", _bus_holes(g, float((L.get("trafo_faults") or {}).get("duct_z", DUCT_Z)), lanes(L.get("trafo_faults")))["p0"])
    parts = {"mcc_walls": ("concrete", False, c.merge_parts(walls)),
            "mcc_lining": ("white", False, c.merge_parts(lining)),
            "mcc_floor": ("dark", False, c.box((rx0, ry0, g - 0.1), (rx1, ry1, g))),
            "mcc_ceiling": ("white", False, c.box((rx0 + li, ry0 + li, L["ceiling"]), (rx1 - li, ry1 - li, g + h))),
            "ktp_roof": ("galv_old", False, c.box((x0 - 0.2, y0 - 0.2, g + h), (x1 + 0.2, y1 + 0.2, g + h + 0.15)))}
    parts.update(chamber_shell(L))
    return parts


def tray_parts(L):
    """Tray boxes from L["tray"] (a 1.5 mm sheet is not modelled: solid 0.5 x 0.12) plus M10 hangers to the ceiling."""
    boxes = [c.box(a, b) for _, a, b in L["tray"]]
    hang = []
    for nm, a, b in L["tray"]:
        if nm == "exit":
            continue
        along = 1 if (b[1] - a[1]) > (b[0] - a[0]) else 0
        n = max(1, math.ceil((b[along] - a[along]) / 1.5))
        for k in range(n + 1):
            s = a[along] + 0.1 + (b[along] - a[along] - 0.2) * k / n
            for side in (a[1 - along] + 0.02, b[1 - along] - 0.02):
                p = [0.0, 0.0]
                p[along], p[1 - along] = s, side
                hang.append(st.rod((p[0], p[1], b[2]), (p[0], p[1], L["ceiling"] - 0.001), 0.005, 6))
    return c.merge_parts(boxes + hang)


def lamp_parts(L, z=None):
    w, ln, hh = LAMP
    z = L["lamp_z"] if z is None else z
    return c.merge_parts([c.box((x - w / 2, y - ln / 2, z - hh), (x + w / 2, y + ln / 2, z)) for x, y in L["lamps"]])


def door_parts(L):
    """The MCC door leaf on the inner face of the south wall (the outer leaf stays in site_plan) with a panic bar."""
    g = L["g"]
    ry0 = L["room"][1] + LINING
    out = []
    for d in L["doors"]:
        xa, xb = d["x"]
        out += [c.box((xa, ry0 + 0.001, g + 0.005), (xb, ry0 + 0.04, g + d["h"])),
                c.box((xa + 0.1, ry0 + 0.04, g + 1.0), (xb - 0.1, ry0 + 0.08, g + 1.05))]
    return c.merge_parts(out)


def build(site, L=None):
    L = L or layout(site)
    parts = shell(L)
    body, doors, handles, plates = [], [], [], []
    lamps = {}
    for i in range(len(L["cabinets"])):
        tr, td, _ = cabinet_parts(L, i)
        body.append(tr["body"])
        doors.append(td["doors"])
        handles.append(td["handles"])
        plates.append(td["plate"])
        for k, v in td.items():
            if k.startswith("lamp_"):
                lamps.setdefault(k, []).append(v)
    parts["mcc_cab_body"] = ("ral7035", False, c.merge_parts(body))
    parts["mcc_cab_doors"] = ("ral7035", False, c.merge_parts(doors))
    parts["mcc_cab_handles"] = ("dark", False, c.merge_parts(handles))
    parts["mcc_cab_plates"] = ("white", False, c.merge_parts(plates))
    colour = {"lamp_green": "green", "lamp_yellow": "yellow", "lamp_red": "red"}
    for k, v in lamps.items():
        parts["mcc_cab_" + k] = (colour[k], True, c.merge_parts(v))
    sig = signal_parts(L)
    sc = {"tier_red": "red", "tier_yellow": "yellow", "tier_green": "green"}
    parts["mcc_signal_body"] = ("dark", False, c.merge_parts([v for k, v in sig.items() if k not in sc]))
    for k, m in sc.items():
        parts["mcc_signal_" + k] = (m, True, sig[k])
    parts["mcc_tray"] = ("galv", False, tray_parts(L))
    parts["mcc_lamps"] = ("lamp", False, lamp_parts(L))
    parts["mcc_door"] = ("dark", False, door_parts(L))
    parts.update(chamber_parts(site, trafo_layout(site, L)))
    return parts


def dims(site):
    """What the check and the report read: cabinets with their motors and slots, rows, tray, est."""
    L = layout(site)
    return {"cabinets": [{k: cb[k] for k in ("name", "kind", "motors", "slots", "groups", "row", "label")} for cb in L["cabinets"]],
            "rows": [{k: r[k] for k in ("id", "n", "y", "front")} for r in L["rows"]], "tray": L["tray"], "est": EST, "trafo": trafo_dims(site)}


def add_scene_extras(site, collection, materials):
    """Blender-only: an area light under each ceiling lamp (LAMP_LM lm at 683 lm/W, as kit/lighting.add_lamps) and the
    plate texts (black on the white plate)."""
    import bpy
    L = layout(site)
    w, ln, hh = LAMP
    for k, (x, y) in enumerate(L["lamps"]):
        data = bpy.data.lights.new(f"MCC_LAMP_{k}", type="AREA")
        data.shape = "RECTANGLE"
        data.size, data.size_y = w, ln
        data.energy = LAMP_LM / 683.0
        data.color = (1.0, 0.95, 0.9)
        ob = bpy.data.objects.new(f"MCC_LAMP_{k}", data)
        ob.location = (x, y, L["lamp_z"] - hh - 0.002)            # faces -Z by default
        collection.objects.link(ob)
    font = None
    for path in ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            font = bpy.data.fonts.load(path, check_existing=True)
            break
        except (RuntimeError, OSError):
            continue
    ink = bpy.data.materials.get("MCC_PLATE_INK") or c.mat_painted("MCC_PLATE_INK", (0.01, 0.01, 0.012), 0.5, grime=0.0)
    for cb in L["cabinets"]:
        cu = bpy.data.curves.new("MCC_PLATE_" + cb["name"], "FONT")
        cu.body = cb["label"]
        if font:
            cu.font = font
        cu.size = 0.026
        cu.align_x, cu.align_y = "CENTER", "CENTER"
        cu.space_line = 1.05
        cu.materials.append(ink)
        ob = bpy.data.objects.new("MCC_PLATE_" + cb["name"], cu)
        ob.location = tuple(cb["plate_centre"])
        ob.rotation_euler = (math.radians(90.0), 0.0, math.radians(cb["rot"]))
        collection.objects.link(ob)


# ====================================================================== C7b: transformer chambers
#
# The transformer part of the block (east of the MCC partition) is two closed chambers, one oil transformer TMG-630/10/0.4
# each (kit/transformer.py, catalogue dimensions). Norms (research/design/ktp/NOTES.md, PUE-7 chapter 4.2, analog for the
# Ukrainian ПУЕ): every oil transformer in its own chamber with its own exit outside (4.2.216, 4.2.220); clearances from the
# most protruding parts at <= 1.9 m over the floor: to the back and side walls >= 0.3 m, from the entry side to the door
# leaf >= 0.6 m (transformer up to 0.63 MVA, 4.2.217); oil 394 kg < 600 kg with the door outside: no oil receiver (4.2.102);
# ventilation takes the heat away with <= 15 K air heating, mesh <= 1 x 1 cm (4.2.104, 4.2.222); no transit cables through
# a chamber as a rule (4.2.111); bus openings sealed (4.2.108); 10 kV live part to the earthed ceiling >= 120 mm (table 4.2.7).

XQ = 27.0              # EST: partition between the chambers, west face (both doors stay inside their chamber)
DOOR_SPANS = ((5.0, 6.2), (8.0, 9.2))   # from the block's west face: the two transformer doors (site_plan.build_buildings dx 5.0 / 8.0, 1.2 wide)
DOOR_H = 2.4           # site_plan door height
RAIL_H = 0.08          # EST: [8 channel rails laid on the floor along the roll-out path
RAIL_B = 0.05          # EST: channel flange width
TGAP = 0.0005          # parts that bear on each other keep 0.5 mm (BVH reads no contact)
LANES = (30.32, 30.58)   # EST: bus lane (y) of the LV bus duct of chamber T1 / T2: both land on the incoming cabinet ШВ-1
DUCT_W, DUCT_H = 0.20, 0.16   # EST: LV bus duct (about 1000 A, enclosed)
DUCT_Z = 2.35          # EST: bus duct bottom over the floor (over the ШВ-1 top 2.1 and over the transformer)
JUNC = (0.30, 0.55, 0.14)  # EST: junction box over the LV bushings (x, y, z)
JUNC_UP = 0.15         # EST: stud top to the junction box bottom
OPEN_GAP = 0.015       # EST: wall opening around the duct (collars close it)
COLLAR_W, COLLAR_T = 0.06, 0.02
EARTH_Z = 0.30         # EST: earth bus height on the north wall
EARTH_FLAT = (0.040, 0.004)
MESH_MM = 10.0         # louvres are closed by a mesh with cells <= 1 x 1 cm (4.2.222): data, the mesh itself is not drawn
FREE_RATIO = 0.7       # EST: free area of a louvre with its mesh over the gross opening
MU = 0.6               # EST: flow coefficient of the openings
T_IN = 293.0           # K, EST
DT_AIR = 15.0          # K: the largest air heating (4.2.222 / 4.2.227)
# louvres (chamber, kind, wall, x0, x1, z0, z1 over the floor): inlets low in the south wall, outlets high in the north wall
VENTS = (("T1", "in", "south", 26.30, 26.95, 0.10, 1.60), ("T1", "out", "north", 24.90, 26.50, 2.20, 2.80),
         ("T2", "in", "south", 29.40, 30.10, 0.10, 1.60), ("T2", "out", "north", 28.00, 29.60, 2.20, 2.80))
CLEAR_SIDE = 0.30      # PUE 4.2.217: back and side walls, transformers up to 0.63 MVA
CLEAR_FRONT = 0.60     # same: entry side to the door leaf
LOW_Z = 1.9            # same: parts at 1.9 m over the floor and below
HV_TO_EARTH = 0.120    # PUE table 4.2.7, 10 kV: live part to an earthed structure
HV_PHASE = 0.130       # same, between phases


def _slab(p0, p1, axis, holes=()):
    """A wall box p0..p1 with holes [(a0, a1, za, zb)] along its long axis ('x' or 'y'); returns a list of (v, f) boxes."""
    i = 0 if axis == "x" else 1
    out, cur = [], p0[i]
    for a0, a1, za, zb in sorted(holes):
        for lo_i, hi_i, lo_z, hi_z in ((cur, a0, p0[2], p1[2]), (a0, a1, p0[2], za), (a0, a1, zb, p1[2])):
            lo, hi = list(p0), list(p1)
            lo[i], hi[i], lo[2], hi[2] = lo_i, hi_i, lo_z, hi_z
            if hi[i] > lo[i] and hi[2] > lo[2]:
                out.append(c.box(tuple(lo), tuple(hi)))
        cur = a1
    lo, hi = list(p0), list(p1)
    lo[i] = cur
    if hi[i] > lo[i]:
        out.append(c.box(tuple(lo), tuple(hi)))
    return out


def chamber_geom(L, faults=None):
    """Walls, doors, vents and chamber rectangles of the transformer part (site frame)."""
    f = faults or {}
    g = L["g"]
    x0, y0, x1, y1, h = L["block"]
    rx1 = L["room"][2]
    xq = XQ + float(f.get("xq", 0.0))
    iy = (y0 + WALL, y1 - WALL)
    inner = {"T1": (rx1 + WALL, iy[0], xq, iy[1]), "T2": (xq + WALL, iy[0], x1 - WALL, iy[1])}
    dw = float(f.get("door_w", DOOR_SPANS[0][1] - DOOR_SPANS[0][0]))
    doors = {}
    for name, (a, b) in zip(("T1", "T2"), DOOR_SPANS):
        xc = x0 + 0.5 * (a + b)
        doors[name] = (xc - dw / 2, xc + dw / 2)
    vents = [dict(zip(("ch", "kind", "wall", "x0", "x1", "z0", "z1"), v)) for v in VENTS]
    for v in vents:
        if v["ch"] == f.get("vent_ch") and v["kind"] == f.get("vent_kind"):
            v["x1"] = v["x0"] + (v["x1"] - v["x0"]) * float(f.get("vent_scale", 1.0))
    return {"g": g, "h": h, "block": (x0, y0, x1, y1), "p0": (rx1, rx1 + WALL), "xq": (xq, xq + WALL), "inner": inner, "doors": doors,
            "doors_h": DOOR_H, "ceiling": g + h - CEIL, "iy": iy, "vents": vents, "rx1": rx1}


def lanes(faults=None):
    """Bus lanes (y) of the two ducts; a transformer moved by a broken case takes its lane along (the bus follows it)."""
    f = faults or {}
    return tuple(LANES[k] + float(f.get(f"lane{k + 1}_dy", 0.0)) + float(f.get(f"y{k + 1}_dy", 0.0)) for k in range(2))


def _bus_holes(g, duct_z, lanes_=LANES):
    """Openings of the bus ducts in the partitions: {"p0": [(y0, y1, z0, z1)], "q": [...]}; the duct of T2 also crosses the chamber partition."""
    z = (g + duct_z - OPEN_GAP, g + duct_z + DUCT_H + OPEN_GAP)
    one = lambda lane: (lane - DUCT_W / 2 - OPEN_GAP, lane + DUCT_W / 2 + OPEN_GAP, z[0], z[1])      # noqa: E731
    lo, hi = min(lanes_), max(lanes_)
    # both ducts leave through one opening of the MCC partition (the packing between them is fire-stop mass); T2 also crosses the chamber partition
    return {"p0": [(lo - DUCT_W / 2 - OPEN_GAP, hi + DUCT_W / 2 + OPEN_GAP, z[0], z[1])], "q": [one(lanes_[1])]}


def chamber_shell(L, faults=None):
    """Chamber walls (partitions, outer walls with the door and louvre openings), floor and ceiling: {part: (material, smooth, (v, f))}."""
    faults = faults if faults is not None else L.get("trafo_faults")
    G = chamber_geom(L, faults)
    g, h = G["g"], G["h"]
    x0, y0, x1, y1 = G["block"]
    rx1 = G["rx1"]
    holes = _bus_holes(g, float((faults or {}).get("duct_z", DUCT_Z)), lanes(faults))
    walls = _slab((rx1, G["iy"][0], g), (rx1 + WALL, G["iy"][1], g + h), "y", holes["p0"])
    walls += _slab((G["xq"][0], G["iy"][0], g), (G["xq"][1], G["iy"][1], g + h), "y", holes["q"])
    walls.append(c.box((x1 - WALL, G["iy"][0], g), (x1, G["iy"][1], g + h)))
    south = [(a, b, g, g + DOOR_H) for a, b in G["doors"].values()]
    south += [(v["x0"], v["x1"], g + v["z0"], g + v["z1"]) for v in G["vents"] if v["wall"] == "south"]
    north = [(v["x0"], v["x1"], g + v["z0"], g + v["z1"]) for v in G["vents"] if v["wall"] == "north"]
    if not (faults or {}).get("section"):                                     # section: the render frame cuts the south wall away
        walls += _slab((rx1, y0, g), (x1, y0 + WALL, g + h), "x", south)
    walls += _slab((rx1, y1 - WALL, g), (x1, y1, g + h), "x", north)
    ix0, iy0, ix1, iy1 = rx1 + WALL, G["iy"][0], x1 - WALL, G["iy"][1]
    return {"ktp_trafo": ("concrete", False, c.merge_parts(walls)),
            "ktp_floor": ("dark", False, c.box((ix0, iy0, g - 0.1), (ix1, iy1, g))),
            "ktp_ceiling": ("white", False, c.box((ix0, iy0, G["ceiling"]), (ix1, iy1, g + h)))}


def vent_net(v):
    """Free area of a louvre with its mesh (m2)."""
    return (v["x1"] - v["x0"]) * (v["z1"] - v["z0"]) * FREE_RATIO


def vent_required(loss_w, h_c):
    """Free area of each opening (m2) that carries `loss_w` away with DT_AIR of heating by natural draught over the height h_c
    between the opening centres: Q = P / (rho c dT), v = mu sqrt(2 g h dT / T)."""
    q = loss_w / (1.2 * 1005.0 * DT_AIR)
    v = MU * math.sqrt(2.0 * 9.81 * h_c * DT_AIR / T_IN)
    return q / v


def trafo_layout(site, L=None, faults=None):
    """Numbers of the two chambers: transformer placement, rails, bus, earth, vents (site frame). `faults` feed the check's broken cases."""
    L = L or layout(site)
    f = (faults if faults is not None else L.get("trafo_faults")) or {}
    G = chamber_geom(L, f)
    g = L["g"]
    t = tf.oil_transformer(630, f)
    d = t["dims"]
    lv_mean = sum(p[0] for p in d["lv"]) / len(d["lv"])         # local x of the LV bushing group centre
    cab = L["cabinets"][0]                                      # ШВ-1, the incoming cabinet
    cw, ch_, cd, plinth = L["cabinet"]
    chambers = []
    for k, name in enumerate(("T1", "T2")):
        lane = lanes(f)[k]
        xa, xb = G["doors"][name]
        cx = 0.5 * (xa + xb) + float(f.get(f"x{k + 1}_dx", 0.0))
        cy = lane + lv_mean                                        # world y = cy - local x: the LV group centre lands on the lane
        rail_top = g + RAIL_H + float(f.get("rail_dz", 0.0))
        chambers.append({"name": name, "inner": G["inner"][name], "door": G["doors"][name], "c": (cx, cy), "z0": g + RAIL_H + TGAP,
                         "rail_top": rail_top, "lane": lane, "lv_x": cx + d["lv_row_y"],
                         "rail_x": (cx - d["cat"]["A1"] / 2, cx + d["cat"]["A1"] / 2),
                         "rail_y": (G["inner"][name][1] + 0.001, cy + d["cat"]["L"] / 2 - 0.15)})
    o = cab["origin"]
    body = place(np.array([[0.0, 0.0, 0.0], [cw, cd, plinth + ch_]]), cab["rot"], o)
    return {"g": g, "trafo": t, "chambers": chambers, "geom": G, "cab": cab, "cab_top": g + plinth + ch_,
            "cab_box": (float(body[:, 0].min()), float(body[:, 1].min()), float(body[:, 0].max()), float(body[:, 1].max())),
            "duct_z": float(f.get("duct_z", DUCT_Z)), "drop_dz": float(f.get("drop_dz", 0.0)), "earth_dy": float(f.get("earth_dy", 0.0)),
            "stray": bool(f.get("stray")), "faults": dict(f)}


def _world(verts, ch):
    """Transformer-local verts (X along the length, LV row at -Y) -> site: turned -90 deg about Z, so the LV row looks west."""
    return c.transform(np.asarray(verts, float), rot_z=-math.pi / 2, offset=(ch["c"][0], ch["c"][1], ch["z0"]))


def _ring(x0, y0, y1, z0, z1, w, t):
    """Four boxes around the opening y0..y1 x z0..z1: a fire-stop collar t thick starting at x0."""
    return [c.box((x0, y0 - w, z1), (x0 + t, y1 + w, z1 + w)), c.box((x0, y0 - w, z0 - w), (x0 + t, y1 + w, z0)),
            c.box((x0, y0 - w, z0), (x0 + t, y0, z1)), c.box((x0, y1, z0), (x0 + t, y1 + w, z1))]


def _slat(x0, x1, y_face, z, outward):
    """One louvre slat across x0..x1 from the wall face line, sloping 50 mm down over 70 mm outwards (-1 south, +1 north)."""
    prof = np.array([(0.0, 0.0), (0.07, -0.05), (0.07, -0.046), (0.0, 0.004)])      # u -> -Y for a member along +X
    if outward > 0:
        prof = prof * np.array([-1.0, 1.0])
    return st.member((x0, y_face + outward * TGAP, z), (x1, y_face + outward * TGAP, z), prof)


def chamber_parts(site, T):
    """Transformers, rails, LV bus with collars, earth bus and straps, louvres: {part: (material, smooth, (v, f))}."""
    g = T["g"]
    G = T["geom"]
    t = T["trafo"]
    d = t["dims"]
    out = {}
    grouped = {}
    for ch in T["chambers"]:
        for name, (v, f) in t["parts"].items():
            grouped.setdefault(name, []).append((_world(v, ch), f))
    for name, items in grouped.items():
        out["ktp_tr_" + name] = (tf.MATERIALS[name], False, c.merge_parts(items))
    iy1 = G["iy"][1]
    x_a, x_b = G["inner"]["T1"][0], G["inner"]["T2"][2]
    # (rail height per chamber: the rails stand on the floor, their top is the chamber's rail_top)
    z_d0 = g + T["duct_z"]
    cb = T["cab_box"]
    drop = (cb[0] + 0.41, cb[0] + 0.59)                              # drop duct x range inside the ШВ-1 body, behind its stack light (base plate to x 23.995)
    rails, bus, collar, earth, straps, louv, frame = [], [], [], [], [], [], []
    for ch in T["chambers"]:
        cx, cy = ch["c"]
        h_rail = ch["rail_top"] - g - TGAP
        prof = st.channel(h_rail, RAIL_B, 0.005, min(0.007, h_rail / 3))
        for rx in ch["rail_x"]:
            zc = g + TGAP + h_rail / 2.0
            rails.append(st.member((rx - RAIL_B / 2, ch["rail_y"][0], zc), (rx - RAIL_B / 2, ch["rail_y"][1], zc), prof))
        z_top = ch["z0"] + max(p[2] for p in d["lv"])                # LV stud tops
        z_jb = z_top + JUNC_UP
        lane, lv_x = ch["lane"], ch["lv_x"]
        bus.append(c.box((lv_x - JUNC[0] / 2 - 0.02, lane - JUNC[1] / 2, z_jb), (lv_x + JUNC[0] / 2 - 0.02, lane + JUNC[1] / 2, z_jb + JUNC[2])))
        for p in d["lv"]:
            wx, wy = cx + p[1], cy - p[0]
            bus.append(st.member((wx, wy, z_top + TGAP), (wx, wy, z_jb + 0.01), st.flat(0.06, 0.008)))
        xr = lv_x - 0.05
        bus.append(c.box((xr - DUCT_W / 2, lane - DUCT_W / 2, z_jb + JUNC[2] - 0.01), (xr + DUCT_W / 2, lane + DUCT_W / 2, z_d0 + DUCT_H)))   # riser
        bus.append(c.box((drop[0], lane - DUCT_W / 2, z_d0), (xr + DUCT_W / 2, lane + DUCT_W / 2, z_d0 + DUCT_H)))                            # horizontal
        bus.append(c.box((drop[0], lane - DUCT_W / 2, T["cab_top"] + TGAP + T["drop_dz"]), (drop[1], lane + DUCT_W / 2, z_d0 + 0.01)))        # drop on ШВ-1
        # earth: strap from the lug on the tank base to the earth bus on the north wall
        lug = _world(np.array([[d["earth_pt"][0], d["earth_pt"][1], d["earth_pt"][2]]]), ch)[0]
        straps.append(st.rod((lug[0], lug[1], lug[2]), (lug[0], iy1 - 0.008 - T["earth_dy"], g + EARTH_Z), 0.006, 8))
    for nm in ("T1", "T2"):                                          # one earth bus per chamber (the partition stays closed), bonded outside
        xa_, xb_ = G["inner"][nm][0], G["inner"][nm][2]
        earth.append(st.member((xa_ + 0.001, iy1 - EARTH_FLAT[1] / 2 - 0.0005, g + EARTH_Z), (xb_ - 0.001, iy1 - EARTH_FLAT[1] / 2 - 0.0005, g + EARTH_Z),
                               st.flat(EARTH_FLAT[1], EARTH_FLAT[0]), up=(1.0, 0.0, 0.0)))
    # collars (fire stop, 4.2.108) on both faces of each partition opening; the MCC side stands on the lining
    holes = _bus_holes(g, T["duct_z"], tuple(ch["lane"] for ch in T["chambers"]))
    for (a, b, za, zb) in holes["p0"]:
        collar += _ring(G["p0"][1] + TGAP, a, b, za, zb, COLLAR_W, COLLAR_T) + _ring(G["p0"][0] - LINING - COLLAR_T - TGAP, a, b, za, zb, COLLAR_W, COLLAR_T)
    for (a, b, za, zb) in holes["q"]:
        collar += _ring(G["xq"][1] + TGAP, a, b, za, zb, COLLAR_W, COLLAR_T) + _ring(G["xq"][0] - COLLAR_T - TGAP, a, b, za, zb, COLLAR_W, COLLAR_T)
    # louvres: a frame on the outer face and hoods sloping down and out (rain); the mesh behind is data (MESH_MM)
    for v in G["vents"]:
        z0, z1 = g + v["z0"], g + v["z1"]
        south = v["wall"] == "south"
        y_face = G["block"][1] if south else G["block"][3]
        ya, yb = (y_face - 0.02 - TGAP, y_face - TGAP) if south else (y_face + TGAP, y_face + 0.02 + TGAP)
        frame += [c.box((v["x0"] - 0.03, ya, z0 - 0.03), (v["x1"] + 0.03, yb, z0)), c.box((v["x0"] - 0.03, ya, z1), (v["x1"] + 0.03, yb, z1 + 0.03)),
                  c.box((v["x0"] - 0.03, ya, z0), (v["x0"], yb, z1)), c.box((v["x1"], ya, z0), (v["x1"] + 0.03, yb, z1))]
        n = max(2, int(round((z1 - z0) / 0.10)))
        for k in range(n):
            louv.append(_slat(v["x0"], v["x1"], y_face, z0 + 0.06 + (z1 - z0 - 0.06) * (k + 0.5) / n, -1.0 if south else 1.0))
    out["ktp_rails"] = ("galv", False, c.merge_parts(rails))
    out["ktp_bus"] = ("galv", False, c.merge_parts(bus))
    out["ktp_collars"] = ("white", False, c.merge_parts(collar))
    out["ktp_earth"] = ("yellow", False, c.merge_parts(earth))
    out["ktp_straps"] = ("yellow", False, c.merge_parts(straps))
    out["ktp_louvres"] = ("galv", False, c.merge_parts(louv + frame))
    if T["stray"]:
        ch = T["chambers"][0]
        cx, cy = ch["c"]
        out["ktp_stray"] = ("red", False, c.box((cx - 0.9, cy - 0.1, ch["z0"] + 0.5), (cx + 0.9, cy + 0.1, ch["z0"] + 0.7)))
    return out


def trafo_dims(site):
    T = trafo_layout(site)
    d = T["trafo"]["dims"]
    return {"transformer": {k: d[k] for k in ("kva", "L", "B", "H", "H1", "mass_kg", "oil_kg", "loss_w", "src")},
            "chambers": [{"name": ch["name"], "inner": ch["inner"], "door": ch["door"], "c": ch["c"], "lane": ch["lane"]} for ch in T["chambers"]],
            "est": EST_TRAFO}


EST_TRAFO = ["перегородка між камерами на x 27,0 (обидві двері лишаються у своїх камерах)",
             "рейки [8 по підлозі від дверей до трансформатора, колія 820 (каталог A1)",
             "бак: гофр крок 50 мм, висота гофра 0,13-1,04 м, ядро 1,2 x 0,6 м; ролики Ø90; вушка, маслоуказатель, клапан, терморозетка",
             "шини НН: 4 смуги 60 x 8 від виводів до коробки 0,30 x 0,55 x 0,14, далі короб 0,20 x 0,16 на висоті 2,35 м до шафи ШВ-1",
             "10 кВ-кабелі до ввідів ВН не змодельовано (даних немає); вводи ВН без огорожі: камера замкнена (ПУЕ 4.2.88)",
             "жалюзі: вхід 0,65-0,70 x 1,5 м низько в південній стіні, вихід 1,6 x 0,6 м високо в північній; сітка 10 x 10 мм (дані), коеф. витрати 0,6, вільна площа 0,7",
             "маслозбірник не потрібний: олії 394 кг < 600 кг, двері назовні, перший поверх (ПУЕ 4.2.102)",
             "заземлення: смуга 40 x 4 по північній стіні на 0,3 м, перемичка Ø12 від бака"]
