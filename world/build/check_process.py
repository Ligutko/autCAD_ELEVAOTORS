"""Phase 7A/7B check: the process graph (SITE.json `process`, `equipment`) against the sheet 1 schema,
the spec (p.8-12), the geometry of the model and, for the designed layer (7B), the functions of a real
elevator, the НПАОП sensors and the interlocks. Constants below are typed from the drawing and the
spec independently of SITE.json. Design notes and designed sizes: check_design.py.

FAIL (drawing / spec):
  every edge joins known nodes, every gate is in the register, every spec gate 6.1-6.15 is used once;
  the register = spec lines (model, count, kW), installed kW summed;
  loading points of each chain conveyor = spec (T7 3, T8 3, T10 2, T11 2, T12 2, T14 1, T15 2);
  every drawn edge has geometry and its ends meet: spout ends on the receiving conveyor, a conveyor head
  over the next conveyor, silo drops over the silo centre in the right order, silo outlets over the
  tunnel conveyor, tunnel outlet into the noria pit, receiving spouts from the head to T7 / the pipe;
  every route of the schema exists: pit -> each silo, each silo -> each silo, each silo -> T10 outlets
  (cleaning, T5, T3), H3 / H4 -> silos;
  opening the gates of a route sends all grain to its sink (no leak, no jam) and every gate is needed;
  spec capacity of every mover on a route >= 100 t/h.
WARN (own recommendation): capacity from the modelled buckets under 100 t/h (H6).
FINDING: open ends that 7B has to design (T5, T3, old routes, feeds of H3 / H4, ...).

Broken variants that must fail: S2 drop moved 2 m, T14 head off T10, no T7 -> T11 edge, T9 outlet
outside the H5 pit, T8 outlets swapped, gate 6.7 renamed, drawn edge without geometry, gate 6.7 also on
the H5 -> T8 branch.

Run:
    blender --background --python world/build/check_process.py
"""

import copy
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import noria_n100 as nn  # noqa: E402
from kit import process as pr  # noqa: E402
from kit import receiving as rc  # noqa: E402

# spec p.8-12 (inbox/raw/ocr/page_08-12.txt): model -> (count on the whole site, kW each)
SPEC = {
    "конвеєр радіально-поворотний": (6, 18.5), "тягач конвеєра": (6, 1.1), "вентилятор аерації": (24, 11.0),
    "даховий вентилятор": (12, 0.25), "У13-ТЗА-400": (8, 0.18), "У13-ТЗР-400": (6, None),
    "У13-ТЗА-350": (36, 0.18), "У13-ТЗР-350": (36, None), "У13-УН175": (1, 22.0), "У13-УН100": (1, 22.0),
    "У13-ТЦС-320": (7, None), "У13-ТЛ-50К": (3, 5.5), "У13-ТЗА-300": (15, 0.18),
    "засувка проміжна ТЦС": (6, 0.18), "засувка приводної секції ТЦС": (6, 0.18),
    "ввід одинарний 45° 300": (3, None), "ввід тройний 45° 300": (2, None), "ввід двойний 45° 300": (1, None),
}
TCS_KW = {"T7": 11.0, "T8": 15.0, "T10": 11.0, "T11": 11.0, "T12": 15.0, "T14": 11.0, "T15": 15.0}
LOAD_POINTS = {"T7": 3, "T8": 3, "T10": 2, "T11": 2, "T12": 2, "T14": 1, "T15": 2}    # spec «точки завантаження»
SPEC_GATES = [f"6.{k}" for k in range(1, 16)]
NEED_T_H = 100.0                                                                     # spec: real 100 t/h
SILOS = ["S1", "S2", "S3", "S4", "S5", "S6"]
WET = ["OS2", "OS3"]
SPEC_KINDS = ("motor", "gate", "gate_manual", "splitter")
TOL = 0.12
# НПАОП 15.0-1.01-17 (research/design/sensors_interlocks.md): a trip must be detectable on every mover
NEED_SENSOR = {"noria": ("speed", "plug"), "conveyor_belt": ("speed",), "conveyor_chain": ("plug",)}


# ------------------------------------------------------------------ geometry of the conveyors
def conveyor(site, cid):
    """Axis as a function of the run coordinate: dict(axis 'x'|'y', lat, span, dir, top(u), bot(u), half_w)."""
    for ln in site["silo_top_galleries"]["lines"]:
        if ln["id"] == cid:
            cz = site["silo_top_galleries"]["conveyor"]["casing_z"]
            return {"axis": "x", "lat": ln["row_y"], "tail": ln["tail_x"], "head": ln["head_x"],
                    "top": lambda u, z=cz[1]: z, "bot": lambda u, z=cz[0]: z,
                    "half_w": site["silo_top_galleries"]["conveyor"]["casing_w"] / 2}
    for br in site["bridges"]:
        for cv in br.get("conveyors", []):
            if cv["id"] == cid:
                h = cv.get("casing_h", 0.5) / 2
                z = lambda u, cv=cv: rc.conveyor_z(cv, u)
                return {"axis": "y", "lat": cv["x"], "tail": cv["tail"][0], "head": cv["head"][0],
                        "top": lambda u, z=z, h=h: z(u) + h, "bot": lambda u, z=z, h=h: z(u) - h,
                        "half_w": cv.get("casing_w", 0.4) / 2}
    for t in site["tunnels"]:
        cv = t["conveyor"]
        if cv["id"] == cid:
            return {"axis": "x", "lat": t["row_y"], "tail": cv["tail_x"], "head": cv["drive_x"],
                    "top": lambda u, z=cv["casing_z"][1]: z, "bot": lambda u, z=cv["casing_z"][0]: z,
                    "half_w": cv["width"] / 2, "casing_x": cv["casing_x"], "tunnel": t}
    return None


def run_lat(c, p):
    return (p[0], p[1]) if c["axis"] == "x" else (p[1], p[0])


def lands_on(c, p):
    """Spout end p lands on conveyor c: inside the run, over the casing, 0-0.6 m above its top."""
    u, v = run_lat(c, p)
    lo, hi = sorted((c["tail"], c["head"]))
    dz = p[2] - c["top"](u)
    ok = lo - 0.05 <= u <= hi + 0.05 and abs(v - c["lat"]) <= c["half_w"] + 0.05 and -0.1 <= dz <= 0.6
    return ok, f"u {u:.2f} in [{lo:.2f}, {hi:.2f}], off axis {abs(v - c['lat']):.2f}, {dz:+.2f} over the top"


def leaves(c, p):
    """Spout start p hangs under conveyor c (intermediate gate): inside the run, on the axis, below it."""
    u, v = run_lat(c, p)
    lo, hi = sorted((c["tail"], c["head"]))
    dz = c["bot"](u) - p[2]
    return lo <= u <= hi and abs(v - c["lat"]) <= c["half_w"] + 0.05 and -0.05 <= dz <= 1.5, f"u {u:.2f}, {dz:.2f} under"


def dist_spout(site, tower, to, frm):
    d = next(d for d in site["distribution"] if d["tower"] == tower)
    return d, next((s for s in d["spouts"] if s["to"] == to and s.get("from_conveyor") == frm), None)


def geom_ok(site, g, e, spouts):
    k = e["geom"]["k"]
    if k == "open":
        return None, "no geometry (open end)"
    if k in ("dspout", "dspout2"):
        gm = e["geom"]
        d, sp = dist_spout(site, gm["tower"], gm["to"], gm["from_conveyor"])
        if sp is None:
            return False, "spout missing in distribution"
        p0, p1 = sp["path"][0], sp["path"][-1]
        ok1, i1 = lands_on(conveyor(site, gm["to"]), p1)
        if k == "dspout2":                       # T11 head -> double splitter -> branch
            _, feed = dist_spout(site, gm["tower"], f"{gm['from_conveyor']} head", None)
            spl = next(s for s in d["splitters"] if s.get("from_conveyor") == gm["from_conveyor"])
            c11 = conveyor(site, gm["from_conveyor"])
            u, v = run_lat(c11, feed["path"][0])
            ok0 = (feed is not None and abs(u - c11["head"]) <= 0.3 and abs(v - c11["lat"]) <= 0.1
                   and math.dist(feed["path"][-1], spl["at"]) <= 0.1
                   and min(math.dist(p0, b) for b in spl["branches"]) <= 0.05)
            return ok0 and ok1, f"feed at the {gm['from_conveyor']} head, splitter, branch; end: {i1}"
        if gm["from_conveyor"]:
            ok0, i0 = leaves(conveyor(site, gm["from_conveyor"]), p0)
        else:
            ho = d["head_outlet"]
            ok0 = any(abs(s["at"][0] - ho[0]) <= 0.05 and abs(s["at"][1] - ho[1]) <= 0.05 and s["at"][2] < ho[2]
                      and min(math.dist(p0, b) for b in s["branches"]) <= 0.05 for s in d["splitters"])
            i0 = "start on a branch of the splitter under the head"
        return ok0 and ok1, f"{i0}; end {i1}"
    if k == "head_over":
        a, b = conveyor(site, e["from"]), conveyor(site, e["to"])
        lo, hi = sorted((b["tail"], b["head"]))
        gap = a["bot"](a["head"]) - b["top"](a["head"])
        ok = a["axis"] == b["axis"] and lo < a["head"] < hi and abs(a["lat"] - b["lat"]) <= 0.1 and 0.0 <= gap <= 1.0
        return ok, f"{e['from']} head {a['head']:.2f} over {e['to']} [{lo:.2f}, {hi:.2f}], casing gap {gap:.2f}"
    if k == "silo_drop":
        c = conveyor(site, e["from"])
        s = next(s for s in site["silos"] if s["id"] == e["to"])
        ln = next(ln for ln in site["silo_top_galleries"]["lines"] if ln["id"] == e["from"])
        on = any(abs(x - s["x"]) <= 0.1 for x in ln["drops_x"]) and abs(ln["row_y"] - s["y"]) <= 0.05
        sib = [f for f in g.out[e["from"]] if f["geom"]["k"] == "silo_drop" and f is not e]
        order_ok = True
        for f in sib:
            o = next(s2 for s2 in site["silos"] if s2["id"] == f["to"])
            near_tail = abs(s["x"] - c["tail"]) < abs(o["x"] - c["tail"])
            order_ok &= near_tail == (e["order"] < f["order"])
        at_head = e["order"] == 1 or abs(s["x"] - c["head"]) <= 0.15
        return on and order_ok and at_head, f"drop over {e['to']} centre {on}, order along the run {order_ok}, head drop at the drum {at_head}"
    if k == "silo_outlets":
        c = conveyor(site, e["to"])
        s = next(s for s in site["silos"] if s["id"] == e["from"])
        xs = [s["x"] + o for o in site["silo_gates"]["offsets_along_row"]]
        ok = abs(c["lat"] - s["y"]) <= 0.05 and all(c["casing_x"][0] < x < c["casing_x"][1] for x in xs) \
            and e["from"] in c["tunnel"]["conveyor"].get("silos", [])
        return ok, f"7 outlets x {xs[0]:.2f}..{xs[-1]:.2f} over casing {c['casing_x']}"
    if k == "boot_feed":
        c = conveyor(site, e["from"])
        tw = next(t for t in site["noria_towers"] if t["id"] == e["to"])
        cx, w = tw["pit"]["inner_center"][0], tw["pit"]["inner_size"][0] / 2
        x = c["tunnel"]["conveyor"]["outlet_xz"][0]
        ok = c["tunnel"]["tower"] == e["to"] and cx - w < x < cx + w
        return ok, f"outlet x {x:.2f} in pit [{cx - w:.2f}, {cx + w:.2f}]"
    if k == "t1_pit":
        r = site["receiving"]
        t1 = next(cv for cv in r["conveyors"] if cv["id"] == "T1")
        lo, hi = sorted(t1["y"])
        ok = all(abs(o[0] - t1["x"]) <= t1["w"] / 2 and lo <= o[1] <= hi for o in r["pit"]["outlets"])
        return ok, f"pit outlets {r['pit']['outlets']} over T1 x {t1['x']}"
    if k == "t1_boot":
        r = site["receiving"]
        t1 = next(cv for cv in r["conveyors"] if cv["id"] == "T1")
        h1 = next(n for n in r["norias"] if n["id"] == "H1")
        end = min(t1["y"])
        ok = abs(t1["x"] - h1["axis"][0]) <= 0.05 and abs(end - h1["axis"][1]) <= r["noria_generic"]["boot_len"] / 2
        return ok, f"T1 end y {end} at the H1 boot y {h1['axis'][1]}"
    if k == "rspout":
        sp = spouts.get(e["geom"]["name"])
        if sp is None:
            return False, "receiving spout missing"
        p0, p1 = np.array(sp[0]), np.array(sp[1])
        r = site["receiving"]
        src, dst = e["from"], e["to"]
        if src in ("H1", "H3", "H4"):
            n = next(n for n in r["norias"] if n["id"] == src)
            h = n["head_len"] / 2 + 0.1
            ok0 = abs(p0[0] - n["axis"][0]) <= h and abs(p0[1] - n["axis"][1]) <= h and n["head_z"][0] - 0.3 <= p0[2] <= n["head_z"][1]
        elif src == "T10":
            ok0 = leaves(conveyor(site, "T10"), p0)[0] or abs(p0[1] - conveyor(site, "T10")["head"]) <= 0.2
        else:
            ok0 = True                            # existing nodes: only the spout's existence is checked
        if dst == "T7":
            ok1, info = lands_on(conveyor(site, "T7"), p1)
        elif dst == "GRAVITY_PIPE" and src == "T10":
            gp = r["cleaning_tower"]["gravity_pipe"]
            a, b = np.array([gp["x"], *gp["from"]]), np.array([gp["x"], *gp["to"]])
            t = np.clip((p1 - a) @ (b - a) / ((b - a) @ (b - a)), 0, 1)
            dd = float(np.linalg.norm(p1 - (a + (b - a) * t)))
            ok1, info = dd <= 0.1, f"end {dd:.2f} m from the gravity pipe"
        else:
            ok1, info = True, "end is an open / existing node"
        return bool(ok0 and ok1), info
    return False, f"unknown geometry kind {k}"


# ------------------------------------------------------------------ checks
def checks(site):
    out = []
    g = pr.Graph(site)
    reg = g.equipment

    bad = [(e["from"], e["to"]) for e in g.edges if e["from"] not in g.nodes or e["to"] not in g.nodes]
    out.append(("every edge joins known nodes", not bad, f"{bad}"))
    used = [x for e in g.edges for x in e["gates"] + e.get("alt_gates", [])]
    missing = sorted({x for x in used if x not in reg or not reg[x]["kind"].startswith("gate")})
    out.append(("every gate on an edge is in the equipment register", not missing, f"missing {missing}"))
    cnt = Counter(x for e in g.edges for x in e["gates"] if x in SPEC_GATES)
    wrong = {x: cnt.get(x, 0) for x in SPEC_GATES if cnt.get(x, 0) != 1}
    out.append(("spec gates 6.1-6.15 each on exactly one edge (schema p.1)", not wrong, f"off {wrong}"))
    vias = sorted({e["via"] for e in g.edges if "via" in e})
    out.append(("every splitter on an edge is in the register", all(v in reg for v in vias), f"{vias}"))

    have = Counter()
    kw = {}
    for m in reg.values():
        if m["layer"] == "drawn" and m["kind"] in SPEC_KINDS:
            have[m["model"]] += m["qty"]
            kw.setdefault(m["model"], set()).add(m["kw"])
    diff = {k: (have.get(k, 0), n) for k, (n, _) in SPEC.items() if have.get(k, 0) != n}
    kwd = {k: (kw.get(k), w) for k, (_, w) in SPEC.items() if w is not None and kw.get(k) != {w}}
    tcs = {t: reg[t]["kw"] for t in TCS_KW if reg.get(t, {}).get("kw") != TCS_KW[t]}
    extra = sorted(set(have) - set(SPEC))
    out.append(("equipment register = spec p.8-12 (model, count, kW)", not diff and not kwd and not tcs and not extra,
                f"count {diff}, kW {kwd}, ТЦС {tcs}, not in spec {extra}"))
    total = sum((m["kw"] or 0) * m["qty"] for m in reg.values() if m["layer"] == "drawn" and m["kind"] in SPEC_KINDS)
    spec_total = sum(n * (w or 0) for n, w in SPEC.values()) + sum(TCS_KW.values())
    out.append(("installed power of the new stage = spec lines", abs(total - spec_total) < 0.01,
                f"register {total:.2f} kW, spec {spec_total:.2f} kW"))

    lp = {t: len(g.inn[t]) for t in LOAD_POINTS}
    out.append(("loading points of each chain conveyor = spec", lp == LOAD_POINTS, f"{lp}"))

    spouts = {n: (p0, p1) for n, p0, p1, _ in rc.spouts(site["receiving"], site)}
    geo_bad, no_geo, opened = [], [], []
    for e in g.edges:
        ok, info = geom_ok(site, g, e, spouts)
        tag = f"{e['from']}->{e['to']}"
        if ok is None:
            (no_geo if e["layer"] == "drawn" else opened).append(tag)
        elif not ok:
            geo_bad.append(f"{tag}: {info}")
    out.append(("every drawn edge has geometry", not no_geo, f"without {no_geo}"))
    out.append(("edge ends meet in the model (spouts, heads, drops, outlets, boots)", not geo_bad, f"{geo_bad[:4]}"))

    routes = g.routes()
    via = lambda r, *ns: all(n in g.route_nodes(r) for n in ns)
    pairs = {(r[0]["from"], r[-1]["to"]) for r in routes}
    need = [("TRUCK_IN", s) for s in SILOS] + [(a, b) for a in SILOS for b in SILOS] + [(s, "TRUCK_EXIT") for s in SILOS]
    lost = [p for p in need if p not in pairs]
    for s in SILOS:                                               # sheet 1: T10 -> 6.9 T5 / 6.10 T3 from every silo
        for mid in ("T5", "T3"):
            if not any(r[0]["from"] == s and via(r, "T10", mid) for r in routes):
                lost.append((s, f"T10->{mid}"))
    for h in ("H3", "H4"):                                        # sheet 1: H3 (6.3), H4 (6.5) -> T7 -> new silos
        if not any(via(r, h, "T7") and r[-1]["to"] in SILOS for r in routes):
            lost.append((h, "T7->silo"))
    out.append(("every route of the schema exists (truck -> silo, silo <-> silo, silo -> cleaning -> truck, T5 / T3, H3 / H4 -> T7)",
                not lost, f"{len(need) + 14 - len(lost)}/{len(need) + 14}, lost {lost[:6]}"))

    # functions of a real elevator (research/design/*.md): intake dry / wet, drying, dispatch over the scales
    fn = {
        "dry intake: truck -> scales -> pit -> new silo": [r for r in routes if r[0]["from"] == "TRUCK_IN" and r[-1]["to"] in SILOS
                                                           and via(r, "SCALES_IN", "PIT")],
        "wet intake: truck -> pre-cleaning (separator 5) -> wet silo": [r for r in routes if r[0]["from"] == "TRUCK_IN"
                                                                       and r[-1]["to"] in WET and via(r, "SEP5")],
        "drying: each wet silo -> dryer -> new silo": [w for w in WET if any(r[0]["from"] == w and r[-1]["to"] in SILOS
                                                                              and via(r, "DRYER") for r in routes)],
        "dispatch: each silo -> separator 5 -> Ш1 -> truck -> scales out": [s for s in SILOS if any(
            r[0]["from"] == s and r[-1]["to"] == "TRUCK_EXIT" and via(r, "SEP5", "SH1", "SCALES_OUT") for r in routes)],
    }
    wet_part, dry_part = set(), set()
    for r in routes:
        ns = g.route_nodes(r)
        if "DRYER" in ns:
            k = ns.index("DRYER")
            wet_part |= set(ns[:k])
            dry_part |= set(ns[k + 1:])
    mixed = sorted((wet_part & dry_part) - set(SILOS))
    out.append(("wet grain before the dryer and dry grain after it share no node (no mixing)", not mixed, f"shared {mixed}"))
    missing_fn = [k for k, v in fn.items() if not v or (k.startswith(("drying", "dispatch")) and len(v) < (2 if "drying" in k else 6))]
    out.append(("functions of a real elevator exist (dry / wet intake, drying, dispatch over the scales)", not missing_fn,
                f"missing {missing_fn}"))

    leaks, spare = [], []
    for r in routes:
        gates = set(g.route_gates(r))
        f = g.flow(r[0]["from"], gates)
        if abs(f.get(r[-1]["to"], 0) - 1.0) > 1e-9:
            leaks.append(f"{g.describe(r)}: {f}")
        for x in gates:
            if abs(g.flow(r[0]["from"], gates - {x}).get(r[-1]["to"], 0) - 1.0) <= 1e-9:
                spare.append(f"{g.describe(r)}: {x}")
    out.append(("opening a route's gates sends all grain to its sink (no leak, no jam)", not leaks, f"{len(leaks)} {leaks[:2]}"))
    out.append(("every gate of a route is needed", not spare, f"{len(spare)} {spare[:3]}"))

    low, unknown, dry = [], set(), Counter()
    for r in routes:
        (t, n), unk = g.bottleneck(r)
        unknown |= set(unk)
        drawn = [m for m in g.route_motors(r) if g.nodes[m]["layer"] == "drawn" and g.nodes[m]["t_h"] < NEED_T_H]
        if drawn:
            low.append((g.describe(r), drawn))
        if g.category(r) == "dry":
            dry[(n, t)] += 1
    out.append(("spec capacity of every drawn mover on a route >= 100 t/h", not low, f"{low[:3]}; no number (existing): {sorted(unknown)}"))
    out.append(("drying routes: FINDING", True, f"bottleneck {dict(dry)}: the dryer takes ≈{24 * g.nodes['DRYER']['t_h']:.0f} t/day "
                f"of wet grain against 100 t/h intake"))

    # sensors and interlocks (research/design/sensors_interlocks.md)
    sens = {}
    for m in reg.values():
        if m["kind"] == "sensor" and m.get("on"):
            sens.setdefault(m["on"], set()).add(m["id"].split(".")[-1])
    on_routes = {m for r in routes for m in g.route_motors(r)}
    blind = []
    for m in sorted(on_routes):
        k = g.nodes[m]["kind"]
        need_s = NEED_SENSOR.get(k, ("speed", "plug"))
        if not any(s in sens.get(m, ()) for s in need_s):
            blind.append(m)
        if k == "noria" and not {"speed", "plug"} <= sens.get(m, set()):
            blind.append(f"{m} (noria needs speed + plug)")
    out.append(("every mover on a route has a trip sensor (НПАОП: noria speed + plug, belt speed, chain plug)", not blind, f"blind {blind}"))
    brakes = [h for h in g.nodes if g.nodes[h]["kind"] == "noria" and f"{h}.brake" not in reg]
    out.append(("every noria has a brake against run-back (НПАОП, >= 50 t/h)", not brakes, f"without {brakes}"))
    bad_trip = []
    for r in routes:
        m = g.route_motors(r)
        for k, x in enumerate(m):
            stop, run = g.trip(r, x)
            if set(stop) != set(m[:k + 1]) or set(run) != set(m[k + 1:]) or g.start_order(r)[-1] != m[0]:
                bad_trip.append(f"{g.describe(r)} @ {x}")
    rules = {i["id"] for i in site["process"].get("interlocks", [])}
    out.append(("interlocks: start against the grain, a trip stops all upstream, downstream runs empty",
                not bad_trip and {"start", "trip", "stop", "plug", "speed"} <= rules, f"{bad_trip[:2]}, rules {sorted(rules)}"))

    model = {}
    for t in site["noria_towers"]:
        mdl = nn.MODELS[t["noria_model"]]
        model[t["id"]] = round(nn.capacity_t_h(mdl, t["feed"]), 1)
    slow = {k: v for k, v in model.items() if v < NEED_T_H}
    worst = min(model.items(), key=lambda kv: kv[1])
    n_via = sum(1 for r in routes if worst[0] in g.route_nodes(r))
    out.append(("capacity from the modelled buckets" + (": WARN" if slow else ""), True,
                f"{model} t/h; {worst[0]} is the bottleneck of {n_via} routes" + (f", {slow} under {NEED_T_H:.0f}" if slow else "")))

    ex = next(r for r in routes if r[0]["from"] == "S3" and r[-1]["to"] == "S1")
    out.append(("start against the grain, stop with it (example)", g.start_order(ex)[0] == g.route_motors(ex)[-1],
                f"{g.describe(ex)}: start {g.start_order(ex)}, gates {g.route_gates(ex)}"))
    cats = Counter(g.category(r) for r in routes)
    out.append(("routes: FINDING", True, f"{len(routes)} routes {dict(cats)}"))
    out.append(("open ends for 7B: FINDING", True, f"{opened}; gaps {site['process']['gaps']}"))
    return out


def main():
    run(json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8")))


def run(site):
    ok_all = True
    for name, ok, info in checks(site):
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)

    def edge(s, a, b):
        return next(e for e in s["process"]["edges"] if e["from"] == a and e["to"] == b)

    def v_drop(s):
        ln = next(ln for ln in s["silo_top_galleries"]["lines"] if ln["id"] == "T8")
        ln["drops_x"] = [-16.5, -38.5]
    def v_t14(s):
        next(cv for b in s["bridges"] for cv in b.get("conveyors", []) if cv["id"] == "T14")["head"][0] = 24.5
    def v_no_t7_t11(s):
        s["process"]["edges"].remove(edge(s, "T7", "T11"))
    def v_t9(s):
        next(t for t in s["tunnels"] if t["id"] == "T9")["conveyor"]["outlet_xz"][0] = 3.0
    def v_swap(s):
        a, b = edge(s, "T8", "S2"), edge(s, "T8", "S1")
        a["order"], b["order"] = 2, 1
    def v_rename(s):
        edge(s, "H5", "T11")["gates"] = ["6.16"]
    def v_open(s):
        edge(s, "H6", "T15")["geom"] = {"k": "open"}
    def v_gate(s):
        edge(s, "H5", "T8")["gates"] = ["6.6", "6.7"]

    def v_plug(s):
        s["equipment"]["items"] = [m for m in s["equipment"]["items"] if m["id"] != "H6.plug"]
    def v_h2(s):
        s["process"]["edges"].remove(edge(s, "H2", "T3"))
    def v_scales(s):
        edge(s, "SCALES_IN", "PIT")["from"] = "TRUCK_IN"
        s["process"]["edges"].remove(edge(s, "TRUCK_IN", "SCALES_IN"))

    def v_mix(s):
        edge(s, "T4", "H3")["to"] = "TOWER_PIT"                  # the first trace: dry grain back into the pit
        edge(s, "T6", "H2")["to"] = "TOWER_PIT"

    variants = [("dry and wet grain through the tower pit (first trace)", v_mix), ("H6 without a plug sensor", v_plug), ("no H2 -> T3 edge (wet silo 2 cut off from the dryer)", v_h2),
                ("trucks bypass the scales", v_scales), ("S2 drop moved 2 m", v_drop), ("T14 head off T10", v_t14), ("no T7 -> T11 edge", v_no_t7_t11),
                ("T9 outlet outside the H5 pit", v_t9), ("T8 outlets swapped", v_swap), ("gate 6.7 renamed 6.16", v_rename),
                ("drawn edge H6 -> T15 without geometry", v_open), ("gate 6.7 also on the H5 -> T8 branch", v_gate)]
    for name, patch in variants:
        bad = copy.deepcopy(site)
        patch(bad)
        failed = [n for n, ok, _ in checks(bad) if not ok]
        ok_all &= bool(failed)
        print(f"{'PASS' if failed else 'FAIL'}  broken variant must be rejected — {name}: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
