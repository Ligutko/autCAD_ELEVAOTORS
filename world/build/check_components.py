"""Перевірка двигуна IEC (IM B3) з world/kit/components.py.

Норми (літери — мм у data/iec_motor_frames.json, сітка — у метрах):
- H: вісь вала над площиною z=0, з вершин вала, усі 11 типорозмірів;
- D і виступ E за щит: з вершин вала і щита, не з dims;
- A поперек і B вздовж: центри отворів лап, допуск 1 мм; підошва лап на z=0;
- габарит L (ніс кожуха → торець щита), допуск 5 мм;
- кВт → типорозмір літералами цього файлу, не з kw_to_frame;
- H, A, B, D таблиці не спадають із типорозміром;
- індекси в межах, без NaN/inf і вироджених граней (площа < 1e-12),
  клемна коробка торкається корпусу, вал виступає за щит, full ≤ 12 000 граней;
- два виклики дають ті самі меші.

Навмисно зламані варіанти (лише в пам'яті): (а) 11 кВт → 132S замість 160M;
(б) вал коротший за E на 20 %; (в) лапи на +5 мм; (г) коробка на +0,3 м;
(д) A і B поміняні місцями; (е) монотонність таблиці зламана.

Радіальний вентилятор ВР 280-46 №5 (radial_fan, data/radial_fan.json), міряємо з вершин, не з dims:
- fan_body: B, b, низ корпусу, верх фланця H, ширина вздовж вала = дані ±5 мм; B усіх шести положень корпусу;
- fan_inlet: фланець D1, труба D, виступ фланця l від серединної площини = дані ±5 мм;
- fan_outlet: фланець A1 × A2, горловина A, крок отворів a1 = дані ±5 мм;
- fan_spiral: радіус спіралі не спадає з кутом від язика;
- fan_axis: вісь вала двигуна збігається з віссю колеса ±2 мм;
- fan_stand: зазор лапи двигуна над рамою 0 ± 2 мм;
- fan_clash: вихідний патрубок не перетинає раму в усіх шести положеннях, обидві руки;
- fan_len: довжина L (фланець входу → кришка двигуна) = дані ±5 мм;
- fan_mesh: індекси, NaN, вироджені грані в усіх частинах.
Зламані варіанти вентилятора: спіраль зі спадним радіусом, мотор на 30 мм вище осі, лапа на 10 мм над рамою,
рама крізь патрубок, фланці входу і виходу +4/5 %, корпус ширший на 4 %, мотор зсунуто на 50 мм, вироджена грань.

Запуск:
    blender --background --python world/build/check_components.py
Код виходу 1, якщо будь-який випадок провалено.
"""

import copy
import json
import sys
from pathlib import Path

import bpy  # noqa: F401  first: the pip bpy (cloud) registers mathutils on import
import numpy as np
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import components as comp  # noqa: E402

# Допуски в метрах. 1 мм і 5 мм задані брифом; решта лишається тісною, бо вершини побудовані точно.
TOL_H = 0.0005
TOL_D = 0.0005
TOL_E = 0.0005
TOL_AB = 0.001
TOL_L = 0.005
TOL_Z = 0.0005
DEGEN_M2 = 1e-12
FACE_BUDGET = 12000

# Літерали з kw_to_frame, вписані тут навмисно окремо від JSON.
EXPECT_FRAME = {
    "0.18": "63",
    "0.25": "71",
    "1.1": "90S",
    "4.2": "132S",
    "5.5": "132S",
    "11": "160M",
    "15": "160L",
    "18.5": "180M",
    "22": "180L",
    "33": "225S",
}


def _mm(row, key):
    return float(row[key]["v"])


def _order(names):
    def key(name):
        num = int("".join(ch for ch in name if ch.isdigit()))
        suf = "".join(ch for ch in name if not ch.isdigit())
        return num, {"": 0, "S": 1, "M": 2, "L": 3}.get(suf, 9)

    return sorted(names, key=key)


def _iter_faces(faces):
    blocks = faces if isinstance(faces, list) else [faces]
    for block in blocks:
        arr = np.asarray(block)
        if arr.size == 0:
            continue
        if arr.ndim == 1:
            yield arr.astype(np.int64, copy=False)
        else:
            for row in arr:
                yield np.asarray(row, np.int64)


def _face_area(verts, face):
    p = verts[np.asarray(face, int)]
    if len(p) < 3:
        return 0.0
    area = 0.0
    for i in range(1, len(p) - 1):
        area += float(np.linalg.norm(np.cross(p[i] - p[0], p[i + 1] - p[0])))
    return 0.5 * area


def _verts(part):
    return np.asarray(part[0], float).reshape(-1, 3)


def _shaft_hd(verts):
    """Вісь і діаметр за екваторними вершинами: шпонка зрізає верх, не боки."""
    y = verts[:, 1]
    reach = float(np.max(np.abs(y)))
    sel = verts[np.abs(np.abs(y) - reach) <= 1e-9]
    return float(sel[:, 2].mean()), 2.0 * reach


def _hole_centers(verts, hole_r):
    """Центри отворів: кільця циліндра K на підошві, не з dims."""
    z0 = float(verts[:, 2].min())
    sole = verts[np.abs(verts[:, 2] - z0) <= 1e-7]
    pts = sole[:, :2]
    used = np.zeros(len(pts), dtype=bool)
    reach = hole_r * 2.0 + 0.001
    centers = []
    for i in range(len(pts)):
        if used[i]:
            continue
        cluster = (np.linalg.norm(pts - pts[i], axis=1) <= reach) & ~used
        if int(cluster.sum()) >= 6:
            centers.append(pts[cluster].mean(axis=0))
        used[cluster] = True
    return z0, centers


def _ab(centers):
    c = np.asarray(centers, float)
    return float(c[:, 1].max() - c[:, 1].min()), float(c[:, 0].max() - c[:, 0].min())


def _bvh(part):
    verts = _verts(part)
    polys = [tuple(int(i) for i in face) for face in _iter_faces(part[1]) if len(face) >= 3]
    if len(verts) == 0 or not polys:
        return None
    return BVHTree.FromPolygons([tuple(p) for p in verts], polys)


def _touches(a, b):
    ba, bb = _bvh(a), _bvh(b)
    if ba is None or bb is None:
        return False
    return bool(ba.overlap(bb))


def _faces_equal(a, b):
    aa = list(_iter_faces(a))
    bb = list(_iter_faces(b))
    if len(aa) != len(bb):
        return False
    return all(np.array_equal(x, y) for x, y in zip(aa, bb))


def _same(a, b):
    if set(a["parts"]) != set(b["parts"]):
        return False
    for name in a["parts"]:
        va, fa = a["parts"][name]
        vb, fb = b["parts"][name]
        if not np.array_equal(np.asarray(va), np.asarray(vb)) or not _faces_equal(fa, fb):
            return False
    return True


def _resolve_faults(faults, frame):
    """faults — словник або функція від типорозміру. Для кВт-перевірки кадру ще немає."""
    if callable(faults):
        return faults(frame) if frame else None
    return faults


def _build(table, kw, frame, faults):
    return comp.iec_motor(kw, frame=frame, frames=table, faults=_resolve_faults(faults, frame))


def _geometry(parts):
    """Повертає словник прапорців цілості і кількість граней."""
    bad_index, bad_num, bad_degen = [], [], []
    faces = 0
    for name, part in parts.items():
        verts = _verts(part)
        if not np.isfinite(verts).all():
            bad_num.append(name)
        n = len(verts)
        for face in _iter_faces(part[1]):
            faces += 1
            if face.size == 0:
                continue
            if int(face.min()) < 0 or int(face.max()) >= n:
                bad_index.append(name)
                break
            if _face_area(verts, face) < DEGEN_M2:
                bad_degen.append(name)
                break
    shaft = _verts(parts["shaft"])
    shield = _verts(parts["endshield_de"])
    return {
        "index": bad_index,
        "num": bad_num,
        "degen": bad_degen,
        "box": _touches(parts["terminal_box"], parts["body"]),
        "out": float(shaft[:, 0].max()) > float(shield[:, 0].max()) + 1e-4,
        "faces": faces,
    }


def evaluate(table, faults=None):
    """Список (rule_id, ok, label, info). Геометрію міряємо з вершин, літери — з таблиці."""
    faults = faults or None
    rows = []
    built = {}
    for name in _order(table["frames"]):
        try:
            built[name] = _build(table, 1.1, name, faults)
        except Exception as exc:  # noqa: BLE001 — злам варіанта не має валити весь прогін
            built[name] = exc

    def motor(name):
        item = built[name]
        if isinstance(item, Exception):
            return None, str(item)
        return item, ""

    # 1. H
    worst, bad = 0.0, []
    for name in built:
        item, err = motor(name)
        if item is None:
            bad.append(f"{name} build {err}")
            continue
        got, _ = _shaft_hd(_verts(item["parts"]["shaft"]))
        want = _mm(table["frames"][name], "H") / 1000.0
        err_m = abs(got - want)
        worst = max(worst, err_m)
        if err_m > TOL_H:
            bad.append(f"{name} {got * 1000:.2f}≠{want * 1000:.1f}")
    rows.append(("H", not bad, "висота осі H", f"11 типорозмірів, max |Δ|={worst * 1000:.3f} мм; {bad}"))

    # 2. D і E
    worst, bad = 0.0, []
    for name in built:
        item, err = motor(name)
        if item is None:
            bad.append(name)
            continue
        _, got = _shaft_hd(_verts(item["parts"]["shaft"]))
        want = _mm(table["frames"][name], "D") / 1000.0
        err_m = abs(got - want)
        worst = max(worst, err_m)
        if err_m > TOL_D:
            bad.append(f"{name} {got * 1000:.2f}≠{want * 1000:.1f}")
    rows.append(("D", not bad, "діаметр вала D", f"max |Δ|={worst * 1000:.3f} мм; {bad}"))

    worst, bad = 0.0, []
    for name in built:
        item, err = motor(name)
        if item is None:
            bad.append(name)
            continue
        shaft = _verts(item["parts"]["shaft"])
        shield = _verts(item["parts"]["endshield_de"])
        got = float(shaft[:, 0].max() - shield[:, 0].max())
        want = _mm(table["frames"][name], "E") / 1000.0
        err_m = abs(got - want)
        worst = max(worst, err_m)
        if err_m > TOL_E:
            bad.append(f"{name} {got * 1000:.2f}≠{want * 1000:.1f}")
    rows.append(("E", not bad, "виступ вала E за щит", f"max |Δ|={worst * 1000:.3f} мм; {bad}"))

    # 3. A, B і підошва
    worst, bad = 0.0, []
    zbad, zmax = [], 0.0
    for name in built:
        item, err = motor(name)
        if item is None:
            bad.append(name)
            zbad.append(name)
            continue
        row = table["frames"][name]
        z0, centers = _hole_centers(_verts(item["parts"]["feet"]), _mm(row, "K") / 2000.0)
        zmax = max(zmax, abs(z0))
        if abs(z0) > TOL_Z:
            zbad.append(f"{name} z={z0 * 1000:.2f} мм")
        if len(centers) != 4:
            bad.append(f"{name} центрів {len(centers)}")
            continue
        got_a, got_b = _ab(centers)
        want_a, want_b = _mm(row, "A") / 1000.0, _mm(row, "B") / 1000.0
        ea, eb = abs(got_a - want_a), abs(got_b - want_b)
        worst = max(worst, ea, eb)
        if ea > TOL_AB or eb > TOL_AB:
            bad.append(f"{name} A {got_a * 1000:.2f}/{want_a * 1000:.1f} B {got_b * 1000:.2f}/{want_b * 1000:.1f}")
    rows.append(("AB", not bad, "отвори лап A і B", f"допуск 1 мм, max |Δ|={worst * 1000:.3f} мм; {bad}"))
    rows.append(("z", not zbad, "лапи на z=0", f"max |z|={zmax * 1000:.3f} мм; {zbad}"))

    # 4. L
    worst, bad = 0.0, []
    for name in built:
        item, err = motor(name)
        if item is None:
            bad.append(name)
            continue
        shield = _verts(item["parts"]["endshield_de"])
        cover = _verts(item["parts"]["fan_cover"])
        got = float(shield[:, 0].max() - cover[:, 0].min())
        want = _mm(table["frames"][name], "L") / 1000.0
        err_m = abs(got - want)
        worst = max(worst, err_m)
        if err_m > TOL_L:
            bad.append(f"{name} {got * 1000:.1f}≠{want * 1000:.1f}")
    rows.append(("L", not bad, "габарит L", f"допуск 5 мм, max |Δ|={worst * 1000:.3f} мм; {bad}"))

    # 5. кВт → типорозмір. Ім'я кадру береться з вибору функції; літерали — з цього файлу.
    bad = []
    for kw, expect in EXPECT_FRAME.items():
        try:
            item = comp.iec_motor(float(kw), frames=table, faults=_resolve_faults(faults, None))
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{kw} build {exc}")
            continue
        got = item["dims"]["frame"]
        if got != expect:
            bad.append(f"{kw}→{got}≠{expect}")
    rows.append(("kw", not bad, "кВт → типорозмір", f"{len(EXPECT_FRAME)} потужностей; {bad}"))

    # 6. Монотонність таблиці
    drops = []
    names = _order(table["frames"])
    for letter in ("H", "A", "B", "D"):
        vals = [_mm(table["frames"][n], letter) for n in names]
        for prev, nxt, a, b in zip(names, names[1:], vals, vals[1:]):
            # B залежить від довжини корпусу (S<M<L) і за IEC не зростає між висотами осі:
            # 160L B=254, далі 180M B=241. Порівнюємо B лише в межах однієї висоти H.
            if letter == "B" and _mm(table["frames"][prev], "H") != _mm(table["frames"][nxt], "H"):
                continue
            if b < a:
                drops.append(f"{letter} {prev}={a:g} → {nxt}={b:g}")
    rows.append(("mono", not drops, "монотонність H, A, D і B в межах однієї H", drops or "не спадають"))

    # 7. Ціла геометрія і бюджет
    idx, num, degen, box, out, faces = [], [], [], [], [], []
    for name in built:
        item, err = motor(name)
        if item is None:
            idx.append(name)
            continue
        g = _geometry(item["parts"])
        idx += [f"{name}:{p}" for p in g["index"]]
        num += [f"{name}:{p}" for p in g["num"]]
        degen += [f"{name}:{p}" for p in g["degen"]]
        if not g["box"]:
            box.append(name)
        if not g["out"]:
            out.append(name)
        faces.append((name, g["faces"]))
    over = [f"{n}={k}" for n, k in faces if k > FACE_BUDGET]
    peak = max((k for _, k in faces), default=0)
    rows.append(("index", not idx, "індекси граней у межах", idx or "ok"))
    rows.append(("num", not num, "немає NaN/inf", num or "ok"))
    rows.append(("degen", not degen, "немає вироджених граней", degen or "ok"))
    rows.append(("box", not box, "клемна коробка торкається корпусу", box or "так"))
    rows.append(("out", not out, "вал виступає за щит", out or "так"))
    rows.append(("budget", not over, "бюджет граней full", f"пік {peak} ≤ {FACE_BUDGET}; {over}"))

    # 8. Детермінованість
    drift = []
    for name in list(built)[:11]:
        item, err = motor(name)
        if item is None:
            drift.append(name)
            continue
        again = _build(table, 1.1, name, faults)
        if not _same(item, again):
            drift.append(name)
    rows.append(("det", not drift, "два виклики дають ті самі меші", drift or "11 типорозмірів"))
    return rows


# ---------------------------------------------------------------- радіальний вентилятор

FAN_TOL = 0.005
FAN_TOL_AXIS = 0.002
FAN_TOL_GAP = 0.002
FAN_KW = 7.5


def _fan_data():
    return json.loads(comp.FAN_DATA.read_text(encoding="utf-8"))


def _fan_mm(data, *path):
    node = data
    for key in path:
        node = node[key]
    return float(node["v"]) / 1000.0


def _fan_build(data, faults, deg=0, hand="R"):
    return comp.radial_fan(FAN_KW, outlet_deg=deg, hand=hand, data=data, faults=faults)


def _fan_cat(item, names):
    return np.vstack([_verts(item["parts"][n]) for n in names])


def _spiral_points(item, data):
    """Вершини переднього краю спіралі (x = мін. корпусу, поза отвором і шийкою): (кут, радіус) від язика."""
    v = _verts(item["parts"]["volute"])
    axis = _fan_mm(data, "frame", "h")
    z_neck = _fan_mm(data, "housing", "H") - _fan_mm(data, "outlet", "flange_t")
    x0 = float(v[:, 0].min())
    edge = v[np.abs(v[:, 0] - x0) < 1e-9]
    y, z = edge[:, 1], edge[:, 2] - axis
    r = np.hypot(y, z)
    keep = (r > 1.2 * _fan_mm(data, "inlet", "throat_d") / 2.0) & (z < z_neck - 1e-4)
    ang = np.degrees(np.arctan2(y[keep], z[keep]))
    ang = np.where(ang < -60.0, ang + 360.0, ang)
    # Язик лежить на ≈ -33° (y = -176 мм за даними); від нього спіраль росте. Точки шийки лишаються лівіше -30°.
    late = ang >= -30.0
    ang, y, z, keep_r = ang[late], y[keep][late], z[keep][late], r[keep][late]
    # Кромка має два сліди (зовнішній і внутрішній бік листа), тому беремо найбільший радіус у смузі 4° (крок точок 2,5°).
    bins = np.floor(ang / 4.0).astype(int)
    out_a, out_r = [], []
    for b in sorted(set(bins.tolist())):
        sel = bins == b
        out_a.append(float(ang[sel].max()))
        out_r.append(float(keep_r[sel].max()))
    return np.array(out_a), np.array(out_r)


def _bvh_pair(a, b):
    ba, bb = _bvh(a), _bvh(b)
    return ba is not None and bb is not None and bool(ba.overlap(bb))


def evaluate_fan(data, faults=None, mutate=None):
    """Список (rule_id, ok, label, info) для radial_fan. Геометрію міряємо з вершин, розміри — з JSON."""
    faults = faults or None
    rows = []
    item = _fan_build(data, faults)
    if mutate:
        mutate(item)
    parts = item["parts"]
    axis = _fan_mm(data, "frame", "h")
    ref_x = lambda v: 0.5 * (float(v[:, 0].min()) + float(v[:, 0].max()))  # noqa: E731

    # fan_body
    body = _fan_cat(item, ("volute", "outlet"))
    vol = _verts(parts["volute"])
    got = {
        "B": float(body[:, 1].max() - body[:, 1].min()),
        "b": float(body[:, 1].max()),
        "низ": float(axis - body[:, 2].min()),
        "H": float(body[:, 2].max() - axis),
        "ширина": float(vol[:, 0].max() - vol[:, 0].min()),
    }
    want = {"B": _fan_mm(data, "housing", "B"), "b": _fan_mm(data, "housing", "b"),
            "низ": _fan_mm(data, "housing", "r180"), "H": _fan_mm(data, "housing", "H"),
            "ширина": _fan_mm(data, "housing", "axial_width")}
    bad = [f"{k} {got[k] * 1000:.1f}≠{want[k] * 1000:.1f}" for k in got if abs(got[k] - want[k]) > FAN_TOL]
    pos_bad = []
    for deg_s, row in data["housing"]["positions"]["v"].items():
        for hand in ("R", "L"):
            other = _fan_build(data, faults, int(deg_s), hand)
            ov = _fan_cat(other, ("volute", "outlet"))
            width = float(ov[:, 1].max() - ov[:, 1].min())
            if abs(width - row["B"] / 1000.0) > FAN_TOL:
                pos_bad.append(f"{deg_s}{hand} {width * 1000:.0f}≠{row['B']}")
    rows.append(("fan_body", not bad and not pos_bad, "корпус вентилятора B, b, низ, H, ширина",
                 f"допуск 5 мм; 0°: " + ", ".join(f"{k} {got[k] * 1000:.1f}" for k in got) + f"; B шести положень {pos_bad or 'ok'}; {bad}"))

    # fan_inlet
    inl = _verts(parts["inlet"])
    mid = ref_x(vol)
    face = float(mid - inl[:, 0].min())
    rad = np.hypot(inl[:, 1], inl[:, 2] - axis)
    flange_od = 2.0 * float(rad.max())
    tube = (inl[:, 0] > inl[:, 0].min() + 0.012) & (inl[:, 0] < mid - 0.185)
    pipe_od = 2.0 * float(rad[tube].max())
    want_in = (_fan_mm(data, "inlet", "D1"), _fan_mm(data, "inlet", "D"), _fan_mm(data, "inlet", "l"))
    ok = (abs(flange_od - want_in[0]) <= FAN_TOL and abs(pipe_od - want_in[1]) <= FAN_TOL
          and abs(face - want_in[2]) <= FAN_TOL)
    rows.append(("fan_inlet", ok, "вхідний патрубок D1, D, виступ l",
                 f"допуск 5 мм; D1 {flange_od * 1000:.1f}/{want_in[0] * 1000:.0f}, D {pipe_od * 1000:.1f}/{want_in[1] * 1000:.0f}, "
                 f"l {face * 1000:.1f}/{want_in[2] * 1000:.0f}"))

    # fan_outlet
    out = _verts(parts["outlet"])
    top = out[out[:, 2] > out[:, 2].max() - 1e-4]
    fl_y, fl_x = float(top[:, 1].max() - top[:, 1].min()), float(top[:, 0].max() - top[:, 0].min())
    z_neck = axis + _fan_mm(data, "housing", "H") - _fan_mm(data, "outlet", "flange_t")
    neck = out[(np.abs(out[:, 2] - z_neck) < 1e-6) & (np.abs(out[:, 0]) <= 0.5 * got["ширина"] + 1e-6)]
    neck_w = float(neck[:, 1].max() - neck[:, 1].min()) if len(neck) else float("nan")
    bolts = _verts(parts["bolts"])
    heads = bolts[bolts[:, 2] > axis + _fan_mm(data, "housing", "H") + 0.004]
    y_mid = 0.5 * (float(top[:, 1].max()) + float(top[:, 1].min()))
    left, right = heads[heads[:, 1] < y_mid], heads[heads[:, 1] >= y_mid]
    pitch = (float(right[:, 1].mean() - left[:, 1].mean()) if len(left) and len(right) else float("nan"))
    want_out = (_fan_mm(data, "outlet", "A1"), _fan_mm(data, "outlet", "A2"), _fan_mm(data, "housing", "A"),
                _fan_mm(data, "outlet", "a1"))
    got_out = (fl_y, fl_x, neck_w, pitch)
    ok = all(abs(g - w_) <= FAN_TOL for g, w_ in zip(got_out, want_out))
    rows.append(("fan_outlet", ok, "вихідний патрубок A1 × A2, A, крок a1",
                 "допуск 5 мм; " + ", ".join(f"{n} {g * 1000:.1f}/{w_ * 1000:.1f}" for n, g, w_ in zip(("A1", "A2", "A", "a1"), got_out, want_out))))

    # fan_spiral
    ang, r = _spiral_points(item, data)
    drops = [f"{a0:.0f}°→{a1:.0f}°: {r0 * 1000:.0f}→{r1 * 1000:.0f}" for a0, a1, r0, r1 in zip(ang, ang[1:], r, r[1:])
             if r1 < r0 - 1e-6]
    rows.append(("fan_spiral", len(ang) >= 20 and not drops, "радіус спіралі росте з кутом",
                 f"{len(ang)} смуг по 4°, {ang.min():.0f}°…{ang.max():.0f}°, r {r.min() * 1000:.0f}…{r.max() * 1000:.0f} мм; {drops[:3] or 'не спадає'}"))

    # fan_axis
    mshaft = item["motor_parts"]["shaft"][0]
    m_z, _ = _shaft_hd(np.asarray(mshaft, float))
    m_y = 0.5 * (float(mshaft[:, 1].max()) + float(mshaft[:, 1].min()))
    wv = _verts(parts["wheel"])
    w_y = 0.5 * (float(wv[:, 1].max()) + float(wv[:, 1].min()))
    w_z = 0.5 * (float(wv[:, 2].max()) + float(wv[:, 2].min()))
    dy, dz = abs(m_y - w_y), abs(m_z - w_z)
    rows.append(("fan_axis", dy <= FAN_TOL_AXIS and dz <= FAN_TOL_AXIS, "вісь двигуна = вісь колеса",
                 f"допуск 2 мм; Δy {dy * 1000:.2f}, Δz {dz * 1000:.2f} мм (колесо z {w_z * 1000:.1f}, вал {m_z * 1000:.1f})"))

    # fan_stand
    feet = np.asarray(item["motor_parts"]["feet"][0], float)
    fz = float(feet[:, 2].min())
    fr = _verts(parts["frame"])
    near = fr[(fr[:, 0] >= feet[:, 0].min() - 0.06) & (fr[:, 0] <= feet[:, 0].max() + 0.06)
              & (np.abs(fr[:, 1]) <= 0.2) & (fr[:, 2] <= fz + 0.05)]
    top_z = float(near[:, 2].max()) if len(near) else float("nan")
    deck = near[np.abs(near[:, 2] - top_z) < 1e-6] if len(near) else near
    covers = (len(deck) > 0 and float(deck[:, 0].min()) <= float(feet[:, 0].min()) and float(deck[:, 0].max()) >= float(feet[:, 0].max())
              and float(np.abs(deck[:, 1]).max()) >= float(np.abs(feet[:, 1]).max()))
    gap = fz - top_z
    rows.append(("fan_stand", abs(gap) <= FAN_TOL_GAP and covers, "двигун стоїть на рамі",
                 f"допуск 2 мм; зазор {gap * 1000:.2f} мм, плита перекриває лапи: {covers}"))

    # fan_clash: усі шість положень, обидві руки
    clash = []
    for deg in comp.FAN_POSITIONS:
        for hand in ("R", "L"):
            other = item if (deg == 0 and hand == "R") else _fan_build(data, faults, deg, hand)
            if _bvh_pair(other["parts"]["outlet"], other["parts"]["frame"]):
                clash.append(f"{deg}{hand}")
    rows.append(("fan_clash", not clash, "вихідний патрубок не перетинає раму", f"12 положень; перетин: {clash or 'немає'}"))

    # fan_len
    mt = _verts(parts["motor"])
    length = float(mt[:, 0].max() - inl[:, 0].min())
    want_len = _fan_mm(data, "length")
    rows.append(("fan_len", abs(length - want_len) <= FAN_TOL, "довжина L",
                 f"допуск 5 мм; {length * 1000:.1f}/{want_len * 1000:.0f} мм"))

    # fan_mesh
    bad_idx, bad_num, bad_deg = [], [], []
    for name, part in parts.items():
        verts = _verts(part)
        if not np.isfinite(verts).all():
            bad_num.append(name)
        for face in _iter_faces(part[1]):
            if face.size and (int(face.min()) < 0 or int(face.max()) >= len(verts)):
                bad_idx.append(name)
                break
            if face.size and _face_area(verts, face) < DEGEN_M2:
                bad_deg.append(name)
                break
    rows.append(("fan_mesh", not (bad_idx or bad_num or bad_deg), "сітка вентилятора без вироджених граней",
                 f"{item['dims']['faces']} граней; індекси {bad_idx or 'ok'}, NaN {bad_num or 'ok'}, вироджені {bad_deg or 'ok'}"))
    return rows


def _degenerate_bolt(item):
    verts, faces = item["parts"]["bolts"]
    verts = np.asarray(verts, float).reshape(-1, 3)
    n = len(verts)
    verts = np.vstack([verts, verts[:1], verts[:1], verts[:1]])
    blocks = faces if isinstance(faces, list) else [faces]
    item["parts"]["bolts"] = (verts, list(blocks) + [np.array([[n, n + 1, n + 2]], np.int64)])


FAN_VARIANTS = (
    ("fan_spiral", "спіраль з радіусом, що спадає на ділянці 105…122°", {"spiral_dip": 0.04}, None),
    ("fan_axis", "двигун і його стійка на 30 мм вище осі колеса", {"motor_dz": 0.03}, None),
    ("fan_stand", "плита під двигуном на 10 мм нижче лап", {"plate_dz": -0.01}, None),
    ("fan_clash", "стійка рами крізь вихідний патрубок", {"frame_clash": True}, None),
    ("fan_inlet", "фланець входу більший на 4 %", {"inlet_flange_scale": 1.04}, None),
    ("fan_outlet", "фланець виходу більший на 5 %", {"outlet_flange_scale": 1.05}, None),
    ("fan_body", "корпус ширший вздовж вала на 4 %", {"housing_w_scale": 1.04}, None),
    ("fan_len", "двигун зсунуто вздовж вала на 50 мм", {"motor_dx": 0.05}, None),
    ("fan_mesh", "у болтах вироджена грань", None, _degenerate_bolt),
)


def _failed(rows):
    return {rid for rid, ok, _label, _info in rows if not ok}


def _load():
    return json.loads(comp.DATA.read_text(encoding="utf-8"))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    table = _load()
    ok_all = True
    base = evaluate(table)
    base_fail = _failed(base)
    # H D E AB z L × 11, десять кВт, одна монотонність, шість цілості, детермінізм.
    atomic = 11 * 6 + len(EXPECT_FRAME) + 1 + 6 + 1
    for rid, ok, label, info in base:
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}: {info}", flush=True)

    # Підміна лише копії таблиці або faults=. Файли кіта не чіпаємо.
    broken_table = copy.deepcopy(table)
    broken_table["kw_to_frame"]["11"]["frame"] = "132S"
    mono_table = copy.deepcopy(table)
    mono_table["frames"]["71"]["H"]["v"] = 50
    variants = (
        ("kw", "11 кВт → 132S замість 160M", broken_table, None, None),
        ("E", "вал коротший за E на 20 %", table, {"shaft_scale": 0.8}, None),
        ("z", "лапи піднято на 5 мм", table, {"feet_z": 0.005}, None),
        ("box", "клемна коробка зсунута на 0,3 м", table, {"box_dy": 0.3}, None),
        # swap_ab на 63 і 71 кладе отвір на внутрішній край лапи і дає нульовий квад.
        # Тоді падає сусіднє правило вироджених граней. На решті кадрів міняються лише A і B.
        ("AB", "A і B поміняно місцями", table, lambda name: None if name in ("63", "71") else {"swap_ab": True}, None),
        ("mono", "таблиця з порушеною монотонністю", mono_table, None, "H 63=63"),
    )
    caught = 0
    for rid, title, data, faults, needle in variants:
        got_rows = evaluate(data, faults)
        got = _failed(got_rows)
        extra = got - base_fail - {rid}
        info = next(i for r, _ok, _l, i in got_rows if r == rid)
        seen = rid in got and not extra and (needle is None or needle in str(info))
        caught += bool(seen)
        ok_all &= seen
        if seen:
            print(f"EXPECTED FAIL {title} -> OK", flush=True)
        else:
            print(f"FAIL  EXPECTED FAIL {title} -> rules={sorted(got)} extra={sorted(extra)} detail={info}", flush=True)

    fan_data = _fan_data()
    fan_base = evaluate_fan(fan_data)
    fan_fail = _failed(fan_base)
    for rid, ok, label, info in fan_base:
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}: {info}", flush=True)
    fan_caught = 0
    for rid, title, faults, mutate in FAN_VARIANTS:
        got_rows = evaluate_fan(fan_data, faults, mutate)
        got = _failed(got_rows)
        extra = got - fan_fail - {rid}
        info = next(i for r, _ok, _l, i in got_rows if r == rid)
        seen = rid in got and not extra
        fan_caught += bool(seen)
        ok_all &= seen
        if seen:
            print(f"EXPECTED FAIL {title} -> OK ({rid})", flush=True)
        else:
            print(f"FAIL  EXPECTED FAIL {title} -> rules={sorted(got)} extra={sorted(extra)} detail={info}", flush=True)

    print(f"CASES {atomic} base + {len(variants)} broken, caught {caught}/{len(variants)}", flush=True)
    print(f"FAN {len(fan_base)} rules + {len(FAN_VARIANTS)} broken, caught {fan_caught}/{len(FAN_VARIANTS)}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
