"""Check of the control center simulator: data, flow core, control and interlocks, dryer, state contract
(CONTROL_CENTER_SPEC.md §1.3, §2.3, §3.2, §0.3).

Plain Python (no bpy); check_all runs it in Blender like the others.
    python world/build/check_sim.py
    blender --background --python world/build/check_sim.py

Every rule is checked against numbers computed here independently of the simulator (SITE t/h, params, geometry,
Graph.flow / start_order / trip / bottleneck of kit/process.py, the residual formula), never against the
simulator's own report. Each rule has a broken variant that must fail on that rule.
"""

import json
import math
import random
import sys
from contextlib import ExitStack, contextmanager
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORLD))

from kit import process as pr  # noqa: E402
from sim import control as ctl  # noqa: E402
from sim import core  # noqa: E402
from sim import schema  # noqa: E402
from sim.control import Plant  # noqa: E402
from sim.core import Sim  # noqa: E402
from sim.scenario import Runner, load  # noqa: E402

H = 3600.0
ALLOWED = {"sourced", "analog", "derived", "designed", "STD", "research", "EST", "judgment"}
G = pr.Graph()
P = core.load_params()
GEO = core.load_geometry()
RHO = P["grain"]["bulk_density_t_m3"]["value"]
TOL = P["sim"]["mass_tol_t"]["value"]
R182 = "TRUCK_IN -> SCALES_IN -> PIT -> T1 -> H1 -> NODE_1 -> GRAVITY_PIPE -> SEP5 -> SH1 -> TOWER_PIT -> H3 -> T7 -> T8 -> S1"
R193 = "TRUCK_IN -> SCALES_IN -> PIT -> T1 -> H1 -> NODE_1 -> GRAVITY_PIPE -> SEP5 -> SH1 -> TOWER_PIT -> H4 -> T5 -> OS2"
R6 = "S1 -> T9 -> H5 -> T10 -> GRAVITY_PIPE -> SEP5 -> SH1 -> TRUCK_OUT -> SCALES_OUT -> TRUCK_EXIT"
ROUTES = {G.describe(r): r for r in G.routes()}


@contextmanager
def patched(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def t_h_of(n):
    """Declared capacity: SITE t/h or the EST of params (independent of the simulator)."""
    t = G.nodes[n].get("t_h")
    return P["t_h_missing"]["nodes"][n]["value"] if t is None else t


def sep_limit(moisture_pct):
    """Separator 5 capacity for grain of this moisture (params separator, independent of the simulator)."""
    sp = P["separator"]
    over = max(0.0, moisture_pct - sp["base_moisture_pct"]["value"])
    return t_h_of("SEP5") * (1 - sp["derate_pct_per_pct"]["value"] / 100 * over)


def speed_of(n):
    b = P["belt_speed_m_s"]
    v = G.nodes[n]
    if n in b:
        return b[n]["value"]
    if v["kind"] == "noria":
        return b["noria_existing"]["value"]
    if v["kind"] in b:
        return b[v["kind"]]["value"]
    return (b["conveyor_designed"] if v.get("layer") == "designed" else b["conveyor_existing"])["value"]


def length_of(n):
    m = GEO["movers"][n]
    return m.get("lift_m", m.get("run_m"))


def passable(e, gates):
    """Independent of Sim.edge_open: may grain pass edge `e` with these gate objects."""
    ids = e["gates"] + e.get("alt_gates", [])
    if not ids:
        return True
    op = {g: gates[g].pos >= 1 - 1e-9 for g in ids}
    if e.get("alt_gates"):
        return any(op.values())
    return (any if e.get("gate_logic") == "any" else all)(op[g] for g in e["gates"])


# ================================================================== scenario runs with monitors

class Watch:
    """Collects per-tick facts of a run: closed-gate flow, capacity, balances, state transitions, first flows."""

    def __init__(self, plant):
        self.p = plant
        self.gate_leaks, self.cap_over, self.dryer_over = [], [], []
        self.max_bal, self.max_wbal = 0.0, 0.0
        self.first_edge = {}
        self.run_at, self.start_at, self.stop_at = {}, {}, {}
        self.prev = {m: "off" for m in plant.sim.movers}
        self.schema_errors = []
        self.samples = []
        self.max_edge = {}

    def __call__(self):
        s = self.p.sim
        for key, m in s.edge_t.items():
            if m <= core.EPS:
                continue
            self.first_edge.setdefault(key, s.t)
            self.max_edge[key] = max(self.max_edge.get(key, 0.0), m * H / s.dt)
            a, b = key.split("->")
            es = [e for e in G.out[a] if e["to"] == b]
            if es and not any(passable(e, s.gates) for e in es):
                self.gate_leaks.append((round(s.t), key, m))
        for n, mv in s.movers.items():
            if mv.state == "run" or mv.line:
                took = mv.line[-1][0] if mv.line else 0.0
                lim = t_h_of(n) / H * s.dt
                if took > lim * (1 + 1e-9) + 1e-12:
                    self.cap_over.append((round(s.t), n, took * H / s.dt))
            st = mv.state
            if st != self.prev[n]:
                if st == "starting":
                    self.start_at.setdefault(n, s.t)
                if st == "run":
                    self.run_at.setdefault(n, s.t)
                if st == "stopping":
                    self.stop_at.setdefault(n, s.t)
                self.prev[n] = st
        lim = P["dryer"]["t_h_wet"]["value"] / H * s.dt
        if s.dryer["in_t"] > lim * (1 + 1e-9):
            self.dryer_over.append((round(s.t), s.dryer["in_t"] * H / s.dt))
        self.max_bal = max(self.max_bal, abs(s.balance()))
        self.max_wbal = max(self.max_wbal, abs(s.water_balance()))
        if int(s.t) % 1800 == 0:
            st = self.p.state()
            self.schema_errors += schema.validate(st)
            self.samples.append((s.t, {k: v["mass_t"] for k, v in st.get("stores", {}).items()}))


def run_scenario(name, until=None, dt=None, plant=None):
    sc = load(name)
    p = plant or Plant(dt=dt)
    r = Runner(sc, plant=p)
    w = Watch(p)
    until = sc["until_s"] if until is None else until
    while p.sim.t < until - 1e-9:
        r.tick()
        w()
    return sc, p, w


# ================================================================== rules

def r_sources():
    bad = []

    def walk(d, path):
        if isinstance(d, dict):
            if "basis" in d:
                if d["basis"] not in ALLOWED:
                    bad.append(f"{path}: basis {d['basis']}")
                if not str(d.get("src", "")).strip():
                    bad.append(f"{path}: no src")
                if d["basis"] == "EST" and not (d.get("wait") or "EST" in str(d.get("src", "")) or len(str(d.get("src", ""))) > 20):
                    bad.append(f"{path}: EST without reason")
            elif "value" in d:
                bad.append(f"{path}: value without basis")
            for k, v in d.items():
                walk(v, f"{path}.{k}")
    walk(P, "params")
    return not bad, bad[:5] or "every number has basis + src"


def r_geometry():
    movers = [n for n, v in G.nodes.items() if v["kind"] in pr.MOVERS]
    bad = [n for n in movers if n not in GEO["movers"] or not (length_of(n) or 0) > 0]
    heap = GEO["silo"]["heap_vs_spec_pct"]
    ok = not bad and abs(heap) <= 2.0
    return ok, f"{len(movers)} movers, missing/zero {bad}; silo heap vs spec volume {heap} % (≤ 2 %)"


def r_balance(runs):
    worst = max(w.max_bal for _, _, w in runs.values())
    wworst = max(w.max_wbal for _, _, w in runs.values())
    return worst <= TOL and wworst <= TOL, f"max |mass balance| {worst:.2e} t, water {wworst:.2e} t (≤ {TOL} t), every tick of {len(runs)} scenarios"


def r_closed_gates(runs):
    leaks = [x for _, _, w in runs.values() for x in w.gate_leaks]
    return not leaks, leaks[:3] or "no grain through a closed gate on any tick"


def transfer(r, share_test=None):
    """Run route `r` (or a gate set) in a bare Sim: grain from the source, share arriving at each sink."""
    s = Sim()
    src = r[0]["from"]
    nodes = G.route_nodes(r)
    for gid in (share_test or G.route_gates(r)):
        s.gates[gid].pos = s.gates[gid].target = 1.0
    for n in nodes:
        if n in s.movers:
            s.movers[n].state = "run"
    if share_test:
        for n in share_test.get("run", []):
            s.movers[n].state = "run"
    if "DRYER" in nodes:
        s.dryer["state"] = "run"
    if "TRUCK_OUT" in nodes:
        s.trucks_out = 1000
    if src in s.stores:
        s.set_store(src, min(4000.0, s.stores[src].cap * 0.95))
    else:
        s.trucks_in.extend([{"mass": 30.0, "moisture": 14.0}] * 2)
    out = 0.0
    arrived = {}
    for i in range(80000):
        s.step()
        first = f"{r[0]['from']}->{r[0]['to']}"
        out += s.edge_t.get(first, 0.0)
        if i == 900 and src in s.stores:
            for e in G.out[src]:
                for gid in e["gates"] + e.get("alt_gates", []):
                    s.gates[gid].target = 0.0
        for key, m in s.edge_t.items():
            a, b = key.split("->")
            if b in s.stores or b in s.sinks or b == "TRUCK_OUT":
                arrived[b] = arrived.get(b, 0.0) + m
        busy = s.transit() > 1e-9 or s.dryer["bin"][0] > 1e-9 or any(s.stores[x].mass > 1e-9 for x in ("PIT", "SH1")) \
            or s.trucks_in or s.truck_in is not None
        if i > 1000 and not busy:
            break
    if src not in s.stores:
        out = s.totals["received_t"]
    arrived.pop("PIT", None)
    arrived.pop("SH1", None)
    if "TRUCK_OUT" in arrived:
        arrived["TRUCK_EXIT"] = arrived.pop("TRUCK_OUT")
    return out, arrived, s


def r_graph_flow():
    bad = []
    for rid, r in ROUTES.items():
        out, arrived, s = transfer(r)
        sink = r[-1]["to"]
        want = G.flow(r[0]["from"], set(G.route_gates(r)))
        got = {k: v / out for k, v in arrived.items()} if out > 0 else {}
        if out <= 0 or any(abs(got.get(k, 0) - v) > 1e-6 for k, v in want.items()) or \
                any(k not in want for k, v in got.items() if v > 1e-9):
            bad.append((rid, round(out, 3), {k: round(v, 4) for k, v in got.items()}, want))
    # equal split of a 45° splitter and the first open outlet of a chain conveyor
    r = ROUTES[R6]
    splits = {
        "H5 splitter 6.6 + 6.8": {"gates": ["S1.c", "6.6", "6.8", "T8.mid", "T10.head", "6.9", "T5.mid"],
                                  "run": ["T9", "H5", "T8", "T10", "T5"]},
        "T8 mid + head (first outlet)": {"gates": ["S1.c", "6.6", "T8.mid", "T8.head"], "run": ["T9", "H5", "T8"]},
    }
    for name, cfg in splits.items():
        want = G.flow("S1", set(cfg["gates"]))
        fake = [dict(r[0])]
        out, arrived, s = transfer(fake, share_test=_ShareCfg(cfg))
        got = {k: v / out for k, v in arrived.items() if k != "S1"} if out > 0 else {}
        if any(abs(got.get(k, 0) - v) > 1e-6 for k, v in want.items() if k != "S1"):
            bad.append((name, {k: round(v, 4) for k, v in got.items()}, want))
    return not bad, bad[:2] or f"{len(ROUTES)} routes: 100 % to the sink as Graph.flow; splitter shares and chain order as Graph.flow"


class _ShareCfg(list):
    """A gate list that also carries the movers to run (for transfer())."""

    def __init__(self, cfg):
        super().__init__(cfg["gates"])
        self.cfg = cfg

    def get(self, k, default=None):
        return self.cfg.get(k, default)


def r_capacity(runs):
    over = [x for _, _, w in runs.values() for x in w.cap_over]
    _, p, w = runs["ship_out"]
    # steady unloading rate of T9 between 1 h and 8 h (S1 above its residual) = route bottleneck
    t9 = [m for t, m in RATE_T9]
    rate = sum(t9) / len(t9) if t9 else 0.0
    (bt, bn), _ = G.bottleneck(ROUTES[R6], {n: t_h_of(n) for n in G.nodes if G.nodes[n]["kind"] in pr.MOVERS})
    ok = not over and abs(rate - bt) <= 0.01 * bt
    return ok, (over[:3] if over else f"no mover took more than its t/h; S1 unloading {rate:.2f} t/h over {len(t9) / H:.1f} h "
                                      f"of centre gravity = bottleneck {bt} t/h ({bn})")


RATE_T9 = []


def ship_out_with_rate(plant=None):
    RATE_T9.clear()
    sc = load("ship_out")
    p = plant or Plant()
    r = Runner(sc, plant=p)
    w = Watch(p)
    m0 = next(e["cmd"]["mass"] for e in sc["events"] if e["cmd"]["op"] == "store")
    gravity = residual_expect(m0, False) + 5.0            # the centre outlet still flows while S1 is over this
    while p.sim.t < sc["until_s"] - 1e-9:
        r.tick()
        w()
        if p.sim.t >= 1 * H and p.sim.stores["S1"].mass > gravity:
            RATE_T9.append((p.sim.t, p.sim.movers["T9"].out_t * H / p.sim.dt))
    return sc, p, w


def r_level(runs):
    sc, p, w = runs["wet_season"]
    trip = next((e["t_s"] for e in p.sim.events if e["kind"] == "trip" and "OS2" in e["text"]), None)
    cap = G.nodes["OS2"]["volume_m3"] * RHO
    wet = next(e["cmd"]["moisture"] for e in sc["events"] if e["cmd"]["op"] == "truck_in")
    feed = next(e["cmd"]["t_h"] for e in sc["events"] if e["cmd"]["op"] == "feed")
    q_in = min(feed, sep_limit(wet))                                  # intake: the pit feed, the wet separator
    d = P["dryer"]
    extra = d["bin_hi_frac"]["value"] * d["bin_t"]["value"]           # the dryer's first bin fill
    t0 = w.first_edge.get("T5->OS2", 0.0)
    expect = t0 + (cap + extra) / (q_in - d["t_h_wet"]["value"]) * H
    sep = w.max_edge.get("SEP5->SH1", 0.0)
    ok = (trip is not None and abs(trip - expect) <= 0.02 * expect and sep <= sep_limit(wet) + 1e-6
          and max(m.get("OS2", 0) for _, m in w.samples) <= cap + TOL)
    at = "none" if trip is None else f"{trip / H:.3f} h"
    return ok, (f"OS2 upper level trip at {at}, derived {expect / H:.3f} h (±2 %: intake {q_in:.0f} t/h - dryer "
                f"{d['t_h_wet']['value']} t/h); separator 5 at {wet:.0f} % passed ≤ {sep:.1f} t/h (limit {sep_limit(wet):.0f})")


def r_separator(plant=None):
    """Wet grain through separator 5 with the pit feed fully open: the separator passes its derated capacity,
    the rest backs up into H1 and its plug sensor trips (the finding of 2026-09-29)."""
    p = plant or Plant()
    p.cmd({"op": "truck_in", "count": 5, "mass": 30, "moisture": 20})
    p.cmd({"op": "route", "id": R193, "action": "start"})
    w = Watch(p)
    while p.sim.t < 0.5 * H:
        p.tick()
        w()
    sep = w.max_edge.get("SEP5->SH1", 0.0)
    lim = sep_limit(20)
    plug = next((e["t_s"] for e in p.sim.events if e["kind"] == "trip" and "H1" in e["text"]), None)
    ok = lim * 0.98 <= sep <= lim + 1e-6 and plug is not None
    return ok, f"20 % grain, pit feed open: separator 5 passed ≤ {sep:.1f} t/h (limit {lim:.0f}); H1 plug trip at {plug} s"


def r_delay(runs):
    _, p, w = runs["receive_s1"]
    t0 = w.first_edge.get("PIT->T1")
    t1 = w.first_edge.get("T8->S1")
    movers = ["T1", "H1", "H3", "T7", "T8"]
    lo = sum(length_of(n) / speed_of(n) for n in movers)
    hi = lo + (len(movers) + 1) * p.sim.dt
    got = None if t0 is None or t1 is None else t1 - t0
    return got is not None and lo - 1e-9 <= got <= hi, f"pit -> S1 first grain {got} s, Σ L/v = {lo:.1f} s (≤ +{hi - lo:.0f} s rounding)"


def r_dt():
    a = run_scenario("receive_s1", until=1 * H, dt=1.0)[1].sim.stores["S1"].mass
    b = run_scenario("receive_s1", until=1 * H, dt=0.5)[1].sim.stores["S1"].mass
    ok = a > 0 and abs(a - b) <= 0.01 * a
    return ok, f"S1 after 1 h: dt 1 s {a:.2f} t, dt 0.5 s {b:.2f} t (≤ 1 %)"


def r_determinism():
    h = [run_scenario("receive_s1", until=1.5 * H)[1].journal_hash() for _ in range(2)]
    return h[0] == h[1], f"journal {h[0][:12]} / {h[1][:12]}"


def r_dryer(runs):
    _, p, w = runs["wet_season"]
    s = p.sim
    s1 = s.stores["S1"]
    w_s1 = 100 * s1.lot[1] / s1.lot[0] if s1.mass > 0 else None
    w_out = P["dryer"]["w_out_pct"]["value"]
    evap = s.totals["evaporated_t"]
    dried = s1.mass + sum(mv.transit for n, mv in s.movers.items() if n in ("T4", "H3", "T7", "T8")) + s.dryer["backlog"][0]
    # dry matter balance: evaporated = dried * (w_in - w_out) / (100 - w_in) for 20 -> 15 %
    w_in = P["dryer"]["w_in_pct"]["value"]
    expect = dried * (w_in - w_out) / (100 - w_in)
    ok = (w_s1 is not None and abs(w_s1 - w_out) < 1e-6 and not w.dryer_over and abs(evap - expect) <= max(0.01, 0.002 * expect))
    return ok, (f"S1 moisture {w_s1 and round(w_s1, 6)} % (= {w_out}), dryer feed over 29.3 t/h: {len(w.dryer_over)}; "
                f"evaporated {evap:.3f} t vs dry-matter balance {expect:.3f} t")


def residual_expect(mass, side):
    r, tan = GEO["silo"]["r_in_m"], math.tan(math.radians(P["silo_discharge"]["drained_angle_deg"]["value"]))
    h = mass / RHO / (math.pi * r * r)
    if not side:
        r0 = min(r, h / tan)
        return min(mass, (2 * math.pi * tan * r0 ** 3 / 3 + math.pi * h * (r * r - r0 * r0)) * RHO)
    n, v = 2000, 0.0
    for i in range(n):
        y = (i + 0.5) * r / n
        v += min(h, y * tan) * 2 * math.sqrt(r * r - y * y) * r / n
    return min(mass, 2 * v * RHO)


def r_residual(runs):
    sc, p, w = runs["ship_out"]
    at = dict((round(t), m) for t, m in w.samples)
    m0 = next(e["cmd"]["mass"] for e in sc["events"] if e["cmd"]["op"] == "store")
    t_side = next(e["t_s"] for e in sc["events"] if e["cmd"]["op"] == "gate" and e["cmd"]["id"] == "S1.s")
    t_sweep = next(e["t_s"] for e in sc["events"] if e["cmd"]["op"] == "sweep")
    c, l = residual_expect(m0, False), residual_expect(m0, True)
    m10, m14 = at.get(round(t_side), {}).get("S1"), at.get(round(t_sweep), {}).get("S1")   # just before side gates / sweep
    end = p.sim.stores["S1"].mass
    ok = m10 is not None and m14 is not None and abs(m10 - c) <= 0.5 and abs(m14 - l) <= 0.5 and end <= TOL
    return ok, f"S1 after centre gravity {m10} t (formula {c:.1f}), after side gates {m14} t (formula {l:.1f}), after sweep {end:.3f} t"


def r_start_order(runs):
    bad = []
    for name, rid in (("receive_s1", R182), ("wet_season", "OS2 -> T2 -> H2 -> T3 -> DRYER -> T4 -> H3 -> T7 -> T8 -> S1")):
        _, p, w = runs[name]
        r = ROUTES[rid]
        order = G.start_order(r)
        got = sorted((m for m in order if m in w.run_at), key=lambda m: w.run_at[m])
        seq_ok = got == order
        after = all(w.start_at[b] >= w.run_at[a] - 1e-9 for a, b in zip(order, order[1:]) if a in w.run_at and b in w.start_at)
        siren = next((e["t_s"] for e in p.sim.events if e["kind"] == "siren"), None)
        first = w.start_at.get(order[0]) if order else None
        siren_ok = siren is not None and first is not None and first - siren >= P["control"]["siren_s"]["value"] - 1e-9
        if not (seq_ok and after and siren_ok):
            bad.append((name, got, order, f"siren {siren} first start {first}"))
    return not bad, bad[:2] or (f"motors reach speed in Graph.start_order, each starts after the one below is at speed; "
                                f"siren ≥ {P['control']['siren_s']['value']:.0f} s before the first motor (НПАОП)")


def r_trip(runs):
    _, p, w = runs["trip_h5_plug"]
    r = ROUTES[R6]
    now, _ = G.trip(r, "H5")
    t_trip = next((e["t_s"] for e in p.sim.events if e["kind"] == "trip"), None)
    stopped_now = {m for m, t in w.stop_at.items() if t_trip is not None and abs(t - t_trip) <= p.sim.dt + 1e-9}
    t10_last = w.stop_at.get("T10")
    ok = (t_trip is not None and stopped_now == set(now) and p.sensors.get("H5.plug") == "trip"
          and t10_last is not None and t10_last > t_trip and p.sim.movers["T10"].transit <= 1e-9)
    return ok, f"plug H5 trip at {t_trip} s stops {sorted(stopped_now)} (Graph.trip {now}); T10 ran empty and stopped at {t10_last} s"


def r_stop_drains(plant=None):
    p = plant or Plant()
    p.cmd({"op": "truck_in", "count": 5, "mass": 30, "moisture": 14})
    p.cmd({"op": "route", "id": R182, "action": "start"})
    p.run_until(0.3 * H)
    carried = p.sim.transit()
    p.cmd({"op": "route", "id": R182, "action": "stop"})
    while R182 in p.active and p.sim.t < 4 * H:
        p.tick()
    units = [n for n in G.route_nodes(ROUTES[R182]) if n in p.sim.movers]
    ok = R182 not in p.active and all(p.sim.movers[n].state == "off" for n in units) and p.sim.transit() <= 1e-9 \
        and abs(p.sim.balance()) <= TOL
    return ok, (f"stopped mid-flow with {carried:.2f} t on the line: after the stop {p.sim.transit():.4f} t left on movers, "
                f"PIT {p.sim.stores['PIT'].mass:.1f} t, S1 {p.sim.stores['S1'].mass:.1f} t")


def r_reject(plant=None):
    p = plant or Plant()
    p.sim.gates["6.8"].pos = p.sim.gates["6.8"].target = 1.0
    a = p.cmd({"op": "motor", "id": "H5", "action": "start"})
    b = p.cmd({"op": "motor", "id": "T10", "action": "start"})              # no open outlet
    ok = (not a["ok"] and "T10" in a["reason"]) and (not b["ok"] and "виходу" in b["reason"])
    return ok, f"H5 with T10 idle: {a}; T10 with no open outlet: {b}"


def r_conflict(plant=None):
    p = plant or Plant()
    other = next(k for k in ROUTES if k.startswith("TRUCK_IN") and k.endswith("T7 -> T8 -> S2") and "H3" in k)
    a = p.cmd({"op": "route", "id": R182, "action": "start"})
    b = p.cmd({"op": "route", "id": other, "action": "start"})
    ok = a["ok"] and not b["ok"] and "T8" in b["reason"]
    return ok, f"second route over T8 to S2: {b}"


def r_schema(runs):
    errs = [e for _, _, w in runs.values() for e in w.schema_errors]
    n = sum(len(w.samples) for _, _, w in runs.values())
    return not errs, errs[:3] or f"{n} states of 4 scenarios match STATE_SCHEMA.json"


def r_expect(runs):
    out = []
    s = runs["receive_s1"][1].sim
    out.append(("receive_s1 S1 = 10 x 30 t", abs(s.stores["S1"].mass - 300) <= TOL and abs(s.totals["received_t"] - 300) <= TOL))
    s = runs["ship_out"][1].sim
    shipped = s.totals["shipped_t"] + (s.truck_out["lot"][0] if s.truck_out else 0)
    out.append(("ship_out all 2000 t out of S1", abs(shipped - 2000) <= TOL and s.stores["S1"].mass <= TOL))
    s = runs["wet_season"][1].sim
    out.append(("wet_season intake stopped, trucks waiting", len(s.trucks_in) > 0 and s.stores["PIT"].mass > 0))
    bad = [n for n, ok in out if not ok]
    return not bad, bad or [n for n, _ in out]


# ================================================================== runner

def all_runs():
    runs = {n: run_scenario(n) for n in ("receive_s1", "wet_season", "trip_h5_plug")}
    runs["ship_out"] = ship_out_with_rate()
    return runs


def rules(runs):
    return [
        ("sources: every simulator number has basis + src", r_sources()),
        ("geometry.json covers every mover; silo heap = spec volume", r_geometry()),
        ("mass and water balance every tick", r_balance(runs)),
        ("closed gates pass nothing", r_closed_gates(runs)),
        ("flow shares = Graph.flow (207 routes, splitter, chain order)", r_graph_flow()),
        ("capacity: no mover over its t/h; unloading = bottleneck", r_capacity(runs)),
        ("upper level stops the feed in derived time", r_level(runs)),
        ("separator 5 derates wet grain; the surplus plugs H1", r_separator()),
        ("transit delay = Σ L / v", r_delay(runs)),
        ("time step independence", r_dt()),
        ("determinism: same journal", r_determinism()),
        ("dryer: 29.3 t/h, shrink to 15 %, evaporation = dry matter balance", r_dryer(runs)),
        ("flat-floor residual = formula (centre, side, sweep)", r_residual(runs)),
        ("route start against the grain (Graph.start_order)", r_start_order(runs)),
        ("plug trip = Graph.trip, below runs empty", r_trip(runs)),
        ("normal stop leaves no grain on movers", r_stop_drains()),
        ("interlock rejects a start with an idle mover below", r_reject()),
        ("conflicting routes are rejected", r_conflict()),
        ("state matches STATE_SCHEMA.json", r_schema(runs)),
        ("scenario outcomes", r_expect(runs)),
    ]


def run_good():
    runs = all_runs()
    res = rules(runs)
    ok_all = True
    for name, (ok, info) in res:
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)
    return ok_all


def broken():
    """Each variant breaks the simulator in one place; the named rule must fail."""
    def leak(orig):
        def take(self, m, a, seen):
            if m == "S1":
                a = [a[0] * 0.99, a[1] * 0.99]             # 1 % of the grain into S1 disappears
            return orig(self, m, a, seen)
        return take

    def ignore_gate(orig):
        def edge_open(self, e):
            if "T8.mid" in e["gates"]:
                return True
            return orig(self, e)
        return edge_open

    def split_7030(orig):
        def deliver(self, n, a, seen=frozenset()):
            live = self.live_edges(n)
            if len(live) == 2 and n == "H5":
                rest = [0.0, 0.0]
                for e, k in zip(live, (0.7, 0.3)):
                    p = [a[0] * k, a[1] * k]
                    left = self.take(e["to"], p, seen | {n})
                    self.edge_t[f"{e['from']}->{e['to']}"] += p[0] - left[0]
                    rest = core.add(rest, left)
                return rest
            return orig(self, n, a, seen)
        return deliver

    def mover_init(orig, fn):
        def init(self, *a, **k):
            orig(self, *a, **k)
            fn(self)
        return init

    def no_shrink(orig):
        def step(self):
            wo = self.dryer["w_out"]
            self.dryer["w_out"] = 99.0                    # never shrinks
            orig(self)
            self.dryer["w_out"] = wo
        return step

    def seq_forward(orig):
        def start(self, rid, r):
            ok = orig(self, rid, r)
            if rid in self.active:
                self.active[rid]["queue"] = list(self.route_units(r))
            return ok
        return start

    def trip_only(orig):
        def trip(self, m, text, sensor=None):
            self.mover(m).command(False)
            self.latched.add(m)
            if sensor:
                self.sensors[sensor] = "trip"
            self.alarm(sensor or m, "trip", text)
        return trip

    def stop_all(orig):
        def tick(self, rid, a):
            if a["state"] == "stopping":
                for u in self.route_units(a["route"]):
                    if u in self.sim.movers:
                        self.mover(u).command(False)
                if all(self.mover(u).state == "off" for u in self.route_units(a["route"]) if u in self.sim.movers):
                    del self.active[rid]
                return
            return orig(self, rid, a)
        return tick

    def no_level(plant):
        plant.sensors.pop("OS2.level_hi")
        return plant

    def no_plug(plant):
        plant.sensors.pop("H5.plug")
        return plant

    def params_with(path, value):
        q = json.loads(json.dumps(P))
        d = q
        for k in path:
            d = d[k]
        d["value"] = value
        return q

    def random_trucks(orig):
        def f(self, c):
            c = dict(c)
            c["moisture"] = float(c.get("moisture", 14)) + random.random()
            return orig(self, c)
        return f

    def bad_state(orig):
        def f(self, events=60):
            st = orig(self, events)
            del st["stores"]
            return st
        return f

    variants = [
        ("1 % leak into S1", "mass and water balance every tick",
         lambda: [patched(Sim, "take", leak(Sim.take))], None),
        ("T8.mid gate ignored", "closed gates pass nothing",
         lambda: [patched(Sim, "edge_open", ignore_gate(Sim.edge_open))], None),
        ("splitter 70 / 30", "flow shares = Graph.flow (207 routes, splitter, chain order)",
         lambda: [patched(Sim, "deliver", split_7030(Sim.deliver))], None),
        ("T9 capacity x 1.5", "capacity: no mover over its t/h; unloading = bottleneck",
         lambda: [patched(core.Mover, "__init__", mover_init(core.Mover.__init__,
                                                             lambda m: setattr(m, "cap", m.cap * 1.5) if m.id == "T9" else None))], None),
        ("OS2 upper level sensor missing", "upper level stops the feed in derived time", lambda: [], no_level),
        ("zero transit delay", "transit delay = Σ L / v",
         lambda: [patched(core.Mover, "__init__", mover_init(core.Mover.__init__, _one_cell))], None),
        ("capacity not scaled by dt", "time step independence",
         lambda: [patched(core.Mover, "__init__", mover_init(core.Mover.__init__, lambda m: setattr(m, "cap", m.t_h / 3600.0)))], None),
        ("random truck moisture", "determinism: same journal",
         lambda: [patched(Plant, "_cmd_truck_in", random_trucks(Plant._cmd_truck_in))], None),
        ("dryer without shrink", "dryer: 29.3 t/h, shrink to 15 %, evaporation = dry matter balance",
         lambda: [patched(Sim, "_dryer_step", no_shrink(Sim._dryer_step))], None),
        ("drained angle 27° (the filling cone angle)", "flat-floor residual = formula (centre, side, sweep)",
         lambda: [patched(core, "load_params", lambda path=None: params_with(["silo_discharge", "drained_angle_deg"], 27.0))], None),
        ("separator not derated for wet grain", "separator 5 derates wet grain; the surplus plugs H1",
         lambda: [patched(core, "load_params", lambda path=None: params_with(["separator", "derate_pct_per_pct"], 0.0))], None),
        ("no siren before the start", "route start against the grain (Graph.start_order)",
         lambda: [patched(core, "load_params", lambda path=None: params_with(["control", "siren_s"], 0.0))], None),
        ("route started with the grain", "route start against the grain (Graph.start_order)",
         lambda: [patched(Plant, "route_start", seq_forward(Plant.route_start))], None),
        ("trip stops only the motor", "plug trip = Graph.trip, below runs empty",
         lambda: [patched(Plant, "trip", trip_only(Plant.trip))], None),
        ("H5 plug sensor missing", "plug trip = Graph.trip, below runs empty", lambda: [], no_plug),
        ("stop all motors at once", "normal stop leaves no grain on movers",
         lambda: [patched(Plant, "_route_tick", stop_all(Plant._route_tick))], None),
        ("start interlock off", "interlock rejects a start with an idle mover below",
         lambda: [patched(Plant, "can_start", lambda self, m: (True, ""))], None),
        ("no conflict check", "conflicting routes are rejected",
         lambda: [patched(Plant, "diverters", lambda self, r: set())], None),
        ("state without stores", "state matches STATE_SCHEMA.json",
         lambda: [patched(Plant, "state", bad_state(Plant.state))], None),
    ]
    ok_all = True
    for name, rule, patches, plant_fn in variants:
        with ExitStack() as es:
            for cm in patches():
                es.enter_context(cm)
            if plant_fn is not None:
                orig_init = Plant.__init__

                def init(self, *a, _f=plant_fn, _o=orig_init, **k):
                    _o(self, *a, **k)
                    _f(self)
                es.enter_context(patched(Plant, "__init__", init))
            try:
                res = dict(rules_for(rule))
                failed = not res[rule][0]
                info = res[rule][1]
            except Exception as e:                       # noqa: BLE001  a crash also rejects the variant
                failed, info = True, f"crash {type(e).__name__}: {e}"
        ok_all &= failed
        print(f"{'PASS' if failed else 'FAIL'}  broken variant must be rejected — {name}: {rule} -> "
              f"{'failed' if failed else 'passed'} ({str(info)[:150]})", flush=True)
    return ok_all


def _one_cell(m):
    m.n = 1
    m.line = core.deque([[0.0, 0.0]])
    m.lsum = [0.0, 0.0]


def rules_for(rule):
    """Only the runs a rule needs, so a broken variant costs little."""
    need = {
        "mass and water balance every tick": ("all",),
        "closed gates pass nothing": ("receive_s1",),
        "capacity: no mover over its t/h; unloading = bottleneck": ("ship_out",),
        "upper level stops the feed in derived time": ("wet_season",),
        "transit delay = Σ L / v": ("receive_s1",),
        "dryer: 29.3 t/h, shrink to 15 %, evaporation = dry matter balance": ("wet_season",),
        "flat-floor residual = formula (centre, side, sweep)": ("ship_out",),
        "route start against the grain (Graph.start_order)": ("receive_s1", "wet_season"),
        "plug trip = Graph.trip, below runs empty": ("trip_h5_plug",),
        "state matches STATE_SCHEMA.json": ("receive_s1",),
    }.get(rule, ())
    runs = {}
    names = ("receive_s1", "wet_season", "trip_h5_plug", "ship_out") if need == ("all",) else need
    for n in names:
        runs[n] = ship_out_with_rate() if n == "ship_out" else run_scenario(n)
    fn = {
        "sources: every simulator number has basis + src": r_sources,
        "mass and water balance every tick": lambda: r_balance(runs),
        "closed gates pass nothing": lambda: r_closed_gates(runs),
        "flow shares = Graph.flow (207 routes, splitter, chain order)": r_graph_flow,
        "capacity: no mover over its t/h; unloading = bottleneck": lambda: r_capacity(runs),
        "upper level stops the feed in derived time": lambda: r_level(runs),
        "separator 5 derates wet grain; the surplus plugs H1": r_separator,
        "transit delay = Σ L / v": lambda: r_delay(runs),
        "time step independence": r_dt,
        "determinism: same journal": r_determinism,
        "dryer: 29.3 t/h, shrink to 15 %, evaporation = dry matter balance": lambda: r_dryer(runs),
        "flat-floor residual = formula (centre, side, sweep)": lambda: r_residual(runs),
        "route start against the grain (Graph.start_order)": lambda: r_start_order(runs),
        "plug trip = Graph.trip, below runs empty": lambda: r_trip(runs),
        "normal stop leaves no grain on movers": r_stop_drains,
        "interlock rejects a start with an idle mover below": r_reject,
        "conflicting routes are rejected": r_conflict,
        "state matches STATE_SCHEMA.json": lambda: r_schema(runs),
    }[rule]
    return [(rule, fn())]


def main():
    ok = run_good()
    ok &= broken()
    print("RESULT", "ALL PASS" if ok else "FAILED", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
