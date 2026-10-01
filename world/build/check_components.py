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

Насадний мотор-редуктор KA..T (shaft_gearmotor, data/gearmotor_ka.json), 5,5 / 11 / 15 / 18,5 кВт, з вершин:
- gm_size: кВт → KA67/132S, KA97/160M, KA97/160L, KA97/180M (літерали тут), фланець B5 для рами є в даних;
- gm_case: Q, QB, L2, H, SA, B, A, FK корпусу = дані ±5 мм;
- gm_axes: вісь виходу по Y через 0, вісь двигуна по X на z = -DB (центри фланця і кожуха вентилятора) ±2 мм;
- gm_hollow: отвір U, маточина UF, довжина EH = дані ±5 мм;
- gm_flange: фланець двигуна торкається вхідного фланця редуктора (0 ± 2 мм), P = дані ±5 мм;
- gm_arm: плита тяги на дні корпусу (0 ± 2 мм), чотири отвори під плитою, вухо в (FC, -O) і R ±5 мм;
- gm_support: накладка опори на площині стінки кожуха (0 ± 2 мм), перекриває стінку ≥ 50 мм, палець співвісний з вухом ±2 мм;
- gm_clash: двигун × тяга, двигун/корпус/тяга/підшипник × опора — без перетинів (BVH);
- gm_mesh: індекси, NaN, вироджені грані.
Зламані варіанти: 15 кВт → KA67 у копії таблиці, корпус ширший на 4 %, двигун на 30 мм вище, отвір +15 %,
двигун на 10 мм від фланця, тяга на 10 мм нижче дна, накладка на 20 мм від стінки, стійка крізь тягу в корпус, вироджена грань.

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


# ---------------------------------------------------------------- насадний мотор-редуктор KA..T

GM_TOL = 0.005
GM_TOL_AXIS = 0.002
GM_TOL_GAP = 0.002
GM_OVERLAP = 0.05           # накладка опори на стінку кожуха, м (pad_over у даних = 80 мм)
GM_WALL_Z = (-0.255, 0.255)  # стінка кожуха ТЦС-320 ±0,255 м від осі (casing_z у SITE.json)
# Літерали, вписані тут окремо від JSON: кВт → типорозмір KA і рама двигуна.
GM_EXPECT = {5.5: ("KA67", "132S"), 11.0: ("KA97", "160M"), 15.0: ("KA97", "160L"), 18.5: ("KA97", "180M")}


def _gm_data():
    return json.loads(comp.GM_DATA.read_text(encoding="utf-8"))


def _gm_build(data, faults, kw):
    return comp.shaft_gearmotor(kw, wall_z=GM_WALL_Z, data=data, faults=faults)


def _mid(v, k):
    return 0.5 * (float(v[:, k].max()) + float(v[:, k].min()))


def evaluate_gm(data, faults=None, mutate=None):
    """Список (rule_id, ok, label, info) для shaft_gearmotor; усі чотири кВт. Геометрію міряємо з вершин, розміри — з JSON."""
    faults = faults or None
    bad = {k: [] for k in ("gm_size", "gm_case", "gm_axes", "gm_hollow", "gm_flange", "gm_arm", "gm_support", "gm_clash", "gm_mesh")}
    seen = {}
    for kw, (want_size, want_frame) in GM_EXPECT.items():
        item = _gm_build(data, faults, kw)
        if mutate:
            mutate(item)
        p, sub, d = item["parts"], item["sub"], item["dims"]
        tag = f"{kw:g} кВт"
        # gm_size
        if d["size"] != want_size or d["motor_frame"] != want_frame or want_frame not in data["motor_flange"]:
            bad["gm_size"].append(f"{tag}: {d['size']}/{d['motor_frame']}")
        row = data["sizes"][d["size"]]
        mm = lambda *k: _fan_mm(row, *k)  # noqa: E731
        A, B, DB, EA, FE, FH, FJ, FK = (mm(k) for k in ("A", "B", "DB", "EA", "FE", "FH", "FJ", "FK"))
        Q, QB, L2, SA, H = (mm(k) for k in ("Q", "QB", "L2", "SA", "H"))
        # gm_case
        cv = _verts(p["case"])
        hous = cv[cv[:, 0] < FK - 0.002]
        bot = cv[np.abs(cv[:, 2] - cv[:, 2].min()) < 1e-6]
        got = {"Q": float(cv[:, 0].max() - cv[:, 0].min()), "QB": float(-cv[:, 0].min()), "L2": float(cv[:, 0].max()),
               "H": float(cv[:, 2].max() - cv[:, 2].min()), "SA": float(-cv[:, 2].min()),
               "B": float(hous[:, 1].max() - hous[:, 1].min()), "A": float(bot[:, 0].max() - bot[:, 0].min()), "FK": float(bot[:, 0].max())}
        want = {"Q": Q, "QB": QB, "L2": L2, "H": H, "SA": SA, "B": B, "A": A, "FK": FK}
        bad["gm_case"] += [f"{tag} {k} {got[k] * 1000:.1f}≠{want[k] * 1000:.1f}" for k in got if abs(got[k] - want[k]) > GM_TOL]
        seen.setdefault("case", f"{d['size']}: " + ", ".join(f"{k} {got[k] * 1000:.0f}" for k in got))
        # gm_axes: вихід = вісь порожнистого вала (Y через 0), двигун = центри фланця і кожуха вентилятора (y=0, z=-DB)
        hv = _verts(p["hollow_shaft"])
        out_x, out_z = _mid(hv, 0), _mid(hv, 2)
        along_y = float(np.ptp(hv[:, 1])) > float(np.ptp(hv[:, 0]))
        axes = []
        for name in ("flange", "fan_cover"):
            mv = np.asarray(item["motor_parts"][name][0], float)
            axes.append((name, _mid(mv, 1), _mid(mv, 2)))
        off = [f"{n} y {y * 1000:.1f} z {z * 1000:.1f}" for n, y, z in axes if abs(y) > GM_TOL_AXIS or abs(z + DB) > GM_TOL_AXIS]
        if abs(out_x) > GM_TOL_AXIS or abs(out_z) > GM_TOL_AXIS or not along_y or off:
            bad["gm_axes"].append(f"{tag}: вихід ({out_x * 1000:.1f}, {out_z * 1000:.1f}) по Y {along_y}; двигун {off or 'ok'}; DB {DB * 1000:.1f}")
        # gm_hollow
        r = np.hypot(hv[:, 0] - out_x, hv[:, 2] - out_z)
        hol = {"U": 2.0 * float(r.min()), "UF": 2.0 * float(r.max()), "EH": float(np.ptp(hv[:, 1]))}
        want_h = {"U": mm("U"), "UF": mm("UF"), "EH": 2.0 * EA}
        bad["gm_hollow"] += [f"{tag} {k} {hol[k] * 1000:.1f}≠{want_h[k] * 1000:.1f}" for k in hol if abs(hol[k] - want_h[k]) > GM_TOL]
        # gm_flange: фланець двигуна торкається вхідного фланця редуктора, P = дані
        mt = _verts(p["motor"])
        gap = float(mt[:, 0].min()) - float(cv[:, 0].max())
        fv = np.asarray(sub["flange"][0], float)
        # P — навколо власного центра фланця: де лежить вісь, міряє gm_axes
        P_got = 2.0 * float(np.hypot(fv[:, 1] - _mid(fv, 1), fv[:, 2] - _mid(fv, 2)).max())
        P_want = _fan_mm(data["motor_flange"][d["motor_frame"]], "P")
        if abs(gap) > GM_TOL_GAP or abs(P_got - P_want) > GM_TOL:
            bad["gm_flange"].append(f"{tag}: зазор {gap * 1000:.2f} мм, P {P_got * 1000:.1f}/{P_want * 1000:.0f}")
        seen.setdefault("flange", f"зазор {gap * 1000:.2f} мм, P {P_got * 1000:.1f}")
        # gm_arm: плита тяги під дном корпусу (0 ± 2 мм), отвори під плитою, вухо в (FC, -O), радіус R
        arm = row["arm"]
        FC, O, R = _fan_mm(arm, "FC"), _fan_mm(arm, "O"), _fan_mm(arm, "R")
        pl = np.asarray(sub["plate"][0], float)
        g_arm = -SA - float(pl[:, 2].max())
        bolt_r = _fan_mm(row, "MC_d") / 2.0
        holes = [(FK - A + FH + dx, sy * FE / 2.0) for dx in (0.0, FJ) for sy in (-1.0, 1.0)]
        out_h = [h for h in holes if not (pl[:, 0].min() <= h[0] - bolt_r and h[0] + bolt_r <= pl[:, 0].max()
                                          and pl[:, 1].min() <= h[1] - bolt_r and h[1] + bolt_r <= pl[:, 1].max())]
        bv = np.asarray(sub["eye_boss"][0], float)
        ex, ez, er = _mid(bv, 0), _mid(bv, 2), 0.5 * float(np.ptp(bv[:, 2]))
        if abs(g_arm) > GM_TOL_GAP or out_h or abs(ex - FC) > GM_TOL or abs(ez + O) > GM_TOL or abs(er - R) > GM_TOL:
            bad["gm_arm"].append(f"{tag}: зазор плити {g_arm * 1000:.2f} мм, отвори поза плитою {len(out_h)}, "
                                 f"вухо ({ex * 1000:.1f}, {ez * 1000:.1f}) / ({FC * 1000:.0f}, {-O * 1000:.0f}), R {er * 1000:.1f}")
        seen.setdefault("arm", f"зазор {g_arm * 1000:.2f} мм, вухо ({ex * 1000:.1f}, {ez * 1000:.1f}), R {er * 1000:.1f}")
        # gm_support: накладка на площині стінки (0 ± 2 мм), перекриває стінку, палець співвісний з вухом
        wall_y = -(EA + _fan_mm(data["est"], "wall_gap"))
        pad = np.asarray(sub["pad"][0], float)
        pad_gap = float(pad[:, 1].min()) - wall_y
        over = min(float(pad[:, 2].max()), GM_WALL_Z[1]) - max(float(pad[:, 2].min()), GM_WALL_Z[0])
        pv = np.asarray(sub["pin"][0], float)
        px, pz = _mid(pv, 0), _mid(pv, 2)
        pin_y = float(np.ptp(pv[:, 1])) > float(np.ptp(pv[:, 0]))
        if abs(pad_gap) > GM_TOL_GAP or over < GM_OVERLAP or abs(px - ex) > GM_TOL_AXIS or abs(pz - ez) > GM_TOL_AXIS or not pin_y:
            bad["gm_support"].append(f"{tag}: накладка від стінки {pad_gap * 1000:.2f} мм, перекриття {over * 1000:.0f} мм, "
                                     f"палець Δx {abs(px - ex) * 1000:.2f} Δz {abs(pz - ez) * 1000:.2f} мм, по Y {pin_y}")
        seen.setdefault("support", f"накладка {pad_gap * 1000:.2f} мм від стінки, перекриття {over * 1000:.0f} мм, палець Δz {abs(pz - ez) * 1000:.2f} мм")
        # gm_clash
        pairs = (("motor", p["motor"], "torque_arm", p["torque_arm"]), ("motor", p["motor"], "опора", sub["support_body"]),
                 ("case", p["case"], "опора", sub["support_body"]), ("torque_arm", p["torque_arm"], "опора", sub["support_body"]),
                 ("bearing", p["bearing"], "опора", sub["support_body"]))
        bad["gm_clash"] += [f"{tag} {a}×{b}" for a, pa, b, pb in pairs if _bvh_pair(pa, pb)]
        # gm_mesh
        for name, part in p.items():
            verts = _verts(part)
            if not np.isfinite(verts).all():
                bad["gm_mesh"].append(f"{tag} {name} NaN")
            for face in _iter_faces(part[1]):
                if face.size and (int(face.min()) < 0 or int(face.max()) >= len(verts)):
                    bad["gm_mesh"].append(f"{tag} {name} індекс")
                    break
                if face.size and _face_area(verts, face) < DEGEN_M2:
                    bad["gm_mesh"].append(f"{tag} {name} вироджена")
                    break
        seen.setdefault("faces", [])
        seen["faces"].append(item["dims"]["faces"])
    labels = {
        "gm_size": ("кВт → KA і рама двигуна", "5,5→KA67/132S, 11→KA97/160M, 15→KA97/160L, 18,5→KA97/180M"),
        "gm_case": ("корпус редуктора Q, QB, L2, H, SA, B, A, FK", "допуск 5 мм; " + seen.get("case", "")),
        "gm_axes": ("осі: вихід по Y через 0, двигун по X на z = -DB", "допуск 2 мм"),
        "gm_hollow": ("порожнистий вал U, UF, EH", "допуск 5 мм"),
        "gm_flange": ("двигун торкається вхідного фланця, P фланця B5", "допуск 2 / 5 мм; " + seen.get("flange", "")),
        "gm_arm": ("реактивна тяга кріпиться до дна корпусу, вухо в (FC, -O)", "допуск 2 / 5 мм; " + seen.get("arm", "")),
        "gm_support": ("опора тяги на стінці кожуха, палець у вусі", "допуск 2 мм, перекриття ≥ 50 мм; " + seen.get("support", "")),
        "gm_clash": ("двигун, тяга, корпус, підшипник не перетинають опору", "BVH, 5 пар × 4 кВт"),
        "gm_mesh": ("сітка мотор-редуктора без вироджених граней", f"граней {seen.get('faces')}"),
    }
    return [(rid, not bad[rid], labels[rid][0], f"{labels[rid][1]}; {bad[rid][:4] or 'ok'}") for rid in bad]


def _gm_degenerate(item):
    verts, faces = item["parts"]["bolts"]
    verts = np.asarray(verts, float).reshape(-1, 3)
    n = len(verts)
    verts = np.vstack([verts, verts[:1], verts[:1], verts[:1]])
    blocks = faces if isinstance(faces, list) else [faces]
    item["parts"]["bolts"] = (verts, list(blocks) + [np.array([[n, n + 1, n + 2]], np.int64)])


GM_VARIANTS = (
    ("gm_size", "15 кВт → KA67 у копії таблиці", "size", None, None),
    ("gm_case", "корпус ширший вздовж вала на 4 %", None, {"case_w_scale": 1.04}, None),
    ("gm_axes", "двигун на 30 мм вище осі входу", None, {"motor_dz": 0.03}, None),
    ("gm_hollow", "отвір порожнистого вала більший на 15 %", None, {"bore_scale": 1.15}, None),
    ("gm_flange", "двигун відсунуто від фланця на 10 мм", None, {"motor_dx": 0.01}, None),
    ("gm_arm", "реактивна тяга на 10 мм нижче дна корпусу", None, {"arm_dz": -0.01}, None),
    ("gm_support", "накладка опори на 20 мм не доходить до стінки", None, {"wall_dy": 0.02}, None),
    ("gm_clash", "стійка від опори вгору крізь тягу в корпус", None, {"support_clash": True}, None),
    ("gm_mesh", "у болтах вироджена грань", None, None, _gm_degenerate),
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

    gm_data = _gm_data()
    gm_base = evaluate_gm(gm_data)
    gm_fail = _failed(gm_base)
    for rid, ok, label, info in gm_base:
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}: {info}", flush=True)
    gm_caught = 0
    for rid, title, which, faults, mutate in GM_VARIANTS:
        data = gm_data
        if which == "size":
            data = copy.deepcopy(gm_data)
            data["kw_to_size"]["15"]["size"] = "KA67"
        got_rows = evaluate_gm(data, faults, mutate)
        got = _failed(got_rows)
        extra = got - gm_fail - {rid}
        info = next(i for r, _ok, _l, i in got_rows if r == rid)
        seen = rid in got and not extra
        gm_caught += bool(seen)
        ok_all &= seen
        if seen:
            print(f"EXPECTED FAIL {title} -> OK ({rid})", flush=True)
        else:
            print(f"FAIL  EXPECTED FAIL {title} -> rules={sorted(got)} extra={sorted(extra)} detail={info}", flush=True)

    print(f"CASES {atomic} base + {len(variants)} broken, caught {caught}/{len(variants)}", flush=True)
    print(f"GEARMOTOR {len(gm_base)} rules + {len(GM_VARIANTS)} broken, caught {gm_caught}/{len(GM_VARIANTS)}", flush=True)
    print(f"FAN {len(fan_base)} rules + {len(FAN_VARIANTS)} broken, caught {fan_caught}/{len(FAN_VARIANTS)}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
