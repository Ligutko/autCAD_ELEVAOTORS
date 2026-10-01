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

    print(f"CASES {atomic} base + {len(variants)} broken, caught {caught}/{len(variants)}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
