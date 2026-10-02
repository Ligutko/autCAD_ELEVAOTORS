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

    layout(site, assign=None) -> numbers the check uses; build(site, L=None) -> {part: (material, smooth, (v, f))};
    add_scene_extras(site, collection, materials) adds the ceiling area lights and the cabinet plate texts (bpy).
"""

import math
import re

import numpy as np

from . import common as c
from . import controls as ctl
from . import steel as st

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
       "двері МСС відчиняються назовні; камери трансформаторів закриті, стіна між ними не моделюється"]


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
              c.box((rx1 - li, ry0, g), (rx1, ry1, g + h))]
    return {"mcc_walls": ("concrete", False, c.merge_parts(walls)),
            "ktp_trafo": ("concrete", False, c.box((rx1, y0, g), (x1, y1, g + h))),
            "mcc_lining": ("white", False, c.merge_parts(lining)),
            "mcc_floor": ("dark", False, c.box((rx0, ry0, g - 0.1), (rx1, ry1, g))),
            "mcc_ceiling": ("white", False, c.box((rx0 + li, ry0 + li, L["ceiling"]), (rx1 - li, ry1 - li, g + h))),
            "ktp_roof": ("galv_old", False, c.box((x0 - 0.2, y0 - 0.2, g + h), (x1 + 0.2, y1 + 0.2, g + h + 0.15)))}


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
    return parts


def dims(site):
    """What the check and the report read: cabinets with their motors and slots, rows, tray, est."""
    L = layout(site)
    return {"cabinets": [{k: cb[k] for k in ("name", "kind", "motors", "slots", "groups", "row", "label")} for cb in L["cabinets"]],
            "rows": [{k: r[k] for k in ("id", "n", "y", "front")} for r in L["rows"]], "tray": L["tray"], "est": EST}


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
        cu.size = 0.018
        cu.align_x, cu.align_y = "CENTER", "CENTER"
        cu.space_line = 1.05
        cu.materials.append(ink)
        ob = bpy.data.objects.new("MCC_PLATE_" + cb["name"], cu)
        ob.location = tuple(cb["plate_centre"])
        ob.rotation_euler = (math.radians(90.0), 0.0, math.radians(cb["rot"]))
        collection.objects.link(ob)
