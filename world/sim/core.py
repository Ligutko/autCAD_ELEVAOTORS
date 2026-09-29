"""Control center, module S: the grain flow of the facility in time (CONTROL_CENTER_SPEC.md §1, §3).

Plain Python, no bpy, no network, no randomness: the same commands give the same journal.
The graph, capacities, volumes and sensor ids come from SITE.json (kit/process.py); the simulator numbers from
world/sim/params.json; conveyor lengths and noria lifts from world/sim/geometry.json (derived from the kits).

One step of `dt` seconds:
  1. gates travel, motors run up / coast down;
  2. every running mover (noria, conveyor) pops the grain that reached its head this step and pushes it along
     its live outlets (the same rule as Graph.flow: the first open outlet along a chain conveyor, an equal split
     between the open gates of a 45° splitter); what nobody takes stays as its backlog (a plug if it grows);
  3. the dryer discharges its column (shrink by the dry matter balance) and feeds the column from its bin;
  4. trucks: weighing, then tipping into the pit; the truck under Ш1 departs when full;
  5. stores (silos, wet silos, the pit, bin Ш1) give what their open outlets can take this step;
  6. the grain each running mover took in this step enters its tail: it reaches the head L / v later.
A mover moves grain only in state `run`; stopped with grain on it, the grain stays where it is.

Masses are lots [t, water t]: moisture travels with the grain and mixes by mass.
Sensors, interlocks, routes and commands are control.py; this module only reports the raw signals
(backlog, fill, blocked outlets).
"""

import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kit import process as pr  # noqa: E402

SIM = Path(__file__).resolve().parent
EPS = 1e-9

MOVER_KINDS = pr.MOVERS
STORE_KINDS = ("silo", "pit", "bin")
DRYER = "DRYER"
TRUCK_IN, TRUCK_OUT = "TRUCK_IN", "TRUCK_OUT"


def load_params(path=None):
    return json.loads(Path(path or SIM / "params.json").read_text(encoding="utf-8"))


def load_geometry(path=None):
    return json.loads(Path(path or SIM / "geometry.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ lots [mass t, water t]

def lot(m=0.0, moisture_pct=None):
    return [m, m * (moisture_pct or 0.0) / 100.0]


def add(a, b):
    return [a[0] + b[0], a[1] + b[1]]


def sub(a, b):
    return [a[0] - b[0], a[1] - b[1]]


def part(a, m):
    """The first `m` t of lot `a` (same moisture)."""
    if a[0] <= EPS:
        return [0.0, 0.0]
    k = min(1.0, max(0.0, m / a[0]))
    return [a[0] * k, a[1] * k]


def moisture(a):
    return 100.0 * a[1] / a[0] if a[0] > EPS else None


# ------------------------------------------------------------------ parts of the plant

class Gate:
    def __init__(self, gid, travel_s):
        self.id, self.travel_s = gid, travel_s
        self.pos, self.target, self.fault = 0.0, 0.0, False

    @property
    def state(self):
        if self.fault:
            return "fault"
        if self.pos >= 1.0 - EPS and self.target >= 1.0:
            return "open"
        if self.pos <= EPS and self.target <= 0.0:
            return "closed"
        return "opening" if self.target > self.pos else "closing"

    @property
    def is_open(self):
        """Grain passes a fully open gate only (judgment: conservative, no partial flow while travelling)."""
        return self.pos >= 1.0 - EPS and not self.fault

    def step(self, dt):
        if self.fault:
            return
        d = dt / self.travel_s
        self.pos = min(self.target, self.pos + d) if self.target > self.pos else max(self.target, self.pos - d)


class Mover:
    """A noria or a conveyor: a delay line of ceil(L / (v dt)) cells, each the grain that entered in one step."""

    def __init__(self, nid, kind, t_h, t_h_basis, v, length, dt, start_s, stop_s, kw):
        self.id, self.kind = nid, kind
        self.t_h, self.t_h_basis = t_h, t_h_basis
        self.v, self.length = v, length
        self.n = max(1, math.ceil(length / (v * dt) - 1e-9))
        self.line = deque([0.0, 0.0] for _ in range(self.n))
        self.lsum = [0.0, 0.0]                             # running sum of the line (a sum per tick is too slow)
        self.cap = t_h / 3600.0 * dt
        self.start_s, self.stop_s, self.kw = start_s, stop_s, kw
        self.state, self.timer, self.run_s = "off", 0.0, 0.0
        self.backlog, self.inbox = [0.0, 0.0], [0.0, 0.0]
        self.budget, self.out_t = 0.0, 0.0
        self.speed_pct, self.bearing_c = 100.0, None      # disturbances set by scenarios

    def pop(self):
        head = self.line.popleft()
        self.lsum = sub(self.lsum, head)
        if self.lsum[0] < 1e-12:                          # float drift of the running sum: the line is empty
            self.lsum = [sum(c[0] for c in self.line), sum(c[1] for c in self.line)]
        return head

    def push(self, a):
        self.line.append(a)
        self.lsum = add(self.lsum, a)

    @property
    def transit(self):
        return self.lsum[0] + self.backlog[0] + self.inbox[0]

    def transit_lot(self):
        return add(add(self.backlog, self.inbox), self.lsum)

    def command(self, on):
        if on and self.state in ("off", "stopping"):
            self.state, self.timer = "starting", self.start_s
        elif not on and self.state in ("starting", "run"):
            self.state, self.timer = "stopping", self.stop_s

    def step_state(self, dt):
        if self.state in ("starting", "stopping"):
            self.timer -= dt
            if self.timer <= EPS:
                self.state = "run" if self.state == "starting" else "off"
                self.run_s = 0.0
        elif self.state == "run":
            self.run_s += dt


class Residual:
    """Grain a flat-floor silo keeps after gravity discharge (params silo_discharge.residual, derived).

    The level is taken flat at the volume of the grain when the discharge began (judgment: the filling cone is
    levelled into the same volume). The surface left slopes at the repose angle down to the open outlets:
      centre outlet only        z(r) = min(h, r tan phi)             integrated over the disk;
      centre + side outlets     z(y) = min(h, |y| tan phi)           |y| from the tunnel line (outlets on the whole
                                                                     chord, a lower bound)."""

    def __init__(self, r, repose_deg, rho, n=400):
        self.r, self.tan, self.rho, self.n = r, math.tan(math.radians(repose_deg)), rho, n

    def centre(self, h):
        r, tan = self.r, self.tan
        r0 = min(r, h / tan)
        return (2 * math.pi * tan * r0 ** 3 / 3 + math.pi * h * (r * r - r0 * r0)) * self.rho

    def line(self, h):
        r, tan, n = self.r, self.tan, self.n
        dy = r / n
        v = 0.0
        for i in range(n):
            y = (i + 0.5) * dy
            v += min(h, y * tan) * 2 * math.sqrt(r * r - y * y) * dy
        return 2 * v * self.rho

    def level(self, mass):
        return mass / self.rho / (math.pi * self.r ** 2)

    def full(self):
        """Residual when the level is over r tan phi (centre, line), t."""
        h = self.r * self.tan * 1.0001
        return self.centre(h), self.line(h)


class Store:
    """A silo, a wet silo, the receiving pit, bin Ш1."""

    def __init__(self, sid, kind, cap_t, residual=None):
        self.id, self.kind, self.cap = sid, kind, cap_t
        self.lot = [0.0, 0.0]
        self.temp_c = None
        self.residual = residual              # Residual for flat-floor silos, None when all of it flows out
        self.ref_mass = 0.0                   # grain when the gravity discharge began (refreshed by filling)
        self._res = {}
        self.sweep = "off"
        self.fans = "off"
        self.feed_t_h = None                  # outlet throttled by the operator (a partly open feed gate), t/h
        self.got = 0.0                        # t taken in this step
        self.refused = 0.0                    # t it could not take this step (full up to the top)

    @property
    def mass(self):
        return self.lot[0]

    def space(self):
        return max(0.0, self.cap - self.lot[0])

    def residual_t(self, side):
        if self.residual is None:
            return 0.0
        key = (round(self.ref_mass, 3), side)
        if key not in self._res:
            if len(self._res) > 64:
                self._res.clear()
            h = self.residual.level(self.ref_mass)
            self._res[key] = min(self.ref_mass, self.residual.line(h) if side else self.residual.centre(h))
        return self._res[key]


# ------------------------------------------------------------------ the simulator

class Sim:
    def __init__(self, site=None, params=None, geometry=None, dt=None):
        self.g = pr.Graph(site)
        self.site = self.g.site
        self.P = params or load_params()
        self.G = geometry or load_geometry()
        P, G = self.P, self.G
        self.dt = float(dt if dt is not None else P["sim"]["dt_s"]["value"])
        self.t = 0.0
        self.rho = P["grain"]["bulk_density_t_m3"]["value"]
        reg = {m["id"]: m for m in self.site["equipment"]["items"]}
        self.registry = reg
        self.sensor_ids = [m["id"] for m in self.site["equipment"]["items"] if m["kind"] == "sensor"]

        # movers
        self.movers = {}
        miss = P["t_h_missing"]["nodes"]
        for n, v in self.g.nodes.items():
            if v["kind"] not in MOVER_KINDS:
                continue
            t_h, basis = v.get("t_h"), "SITE"
            if t_h is None:
                assert n in miss, f"{n}: no t_h in SITE and not listed in params t_h_missing"
                t_h, basis = miss[n]["value"], miss[n]["basis"]
            geo = G["movers"][n]
            length = geo["lift_m"] if v["kind"] == "noria" else geo["run_m"]
            speed = self._belt_speed(n, v)
            kw = reg[n]["kw"] if n in reg else None
            self.movers[n] = Mover(n, v["kind"], t_h, basis, speed, length, self.dt,
                                   P["motor"]["start_s"]["value"], P["motor"]["stop_s"]["value"], kw)

        # stores
        self.stores = {}
        st = P["storage"]
        sg = G["silo"]
        # the grain left after gravity discharge stands at the angle of repose when it slides (drained), not the
        # angle of the filling cone (geometry repose_deg): params silo_discharge.drained_angle_deg
        self.res_model = Residual(sg["r_in_m"], P["silo_discharge"]["drained_angle_deg"]["value"], self.rho)
        self.residual_t = self.res_model.full()
        for n, v in self.g.nodes.items():
            if v["kind"] == "silo":
                flat = v.get("role") != "wet"          # the old wet silos «2», «3»: judgment, hopper bottom
                self.stores[n] = Store(n, "silo", v["volume_m3"] * self.rho, self.res_model if flat else None)
        self.stores["PIT"] = Store("PIT", "pit", st["PIT"]["value"])
        self.stores["SH1"] = Store("SH1", "bin", st["SH1"]["value"])
        self.pass_nodes = set(P["pass_through"]["nodes"])
        self.pass_cap = {n: self.movers_cap_missing(n) for n in self.pass_nodes}
        self.sinks = {n for n, v in self.g.nodes.items() if v["kind"] == "sink"}
        unknown = set(self.g.nodes) - set(self.movers) - set(self.stores) - self.pass_nodes - self.sinks \
            - {DRYER, TRUCK_IN, TRUCK_OUT}
        assert not unknown, f"nodes with no role in the simulator: {sorted(unknown)}"

        # gates: every id on an edge, plus the silo side gates (alt_gates)
        travel = P["gate"]["travel_s"]["value"]
        self.gates = {gid: Gate(gid, travel) for gid in self.g.gates()}

        # dryer
        d = P["dryer"]
        self.dryer = {
            "state": "off", "cap": d["t_h_wet"]["value"] / 3600.0 * self.dt,
            "w_out": d["w_out_pct"]["value"], "bin": [0.0, 0.0], "bin_cap": d["bin_t"]["value"],
            "column": deque([0.0, 0.0] for _ in range(max(1, math.ceil(d["residence_s"]["value"] / self.dt)))),
            "csum": [0.0, 0.0], "backlog": [0.0, 0.0], "in_t": 0.0, "out_t": 0.0, "water_t": 0.0, "w_in": None,
        }

        # trucks
        tr = P["truck"]
        self.truck_cfg = {k: tr[k]["value"] for k in ("payload_t", "unload_s", "weigh_s", "load_t_h")}
        self.trucks_in = deque()            # waiting: {"mass", "moisture"}
        self.truck_in = None                # current: {"lot", "phase", "timer", "rate"}
        self.trucks_out = 0                 # empty trucks waiting to be loaded under Ш1
        self.truck_out = None               # current: {"lot", "cap", "timer"}

        self.totals = {"received_t": 0.0, "shipped_t": 0.0, "evaporated_t": 0.0}
        self.water = {"initial": 0.0, "received": 0.0, "shipped": 0.0}   # t of water (evaporated = totals)
        self.edge_t = defaultdict(float)    # t moved along each edge in the last step
        self.events = []
        self.initial_t = 0.0

    # -------------------------------------------------------------- setup helpers
    def _belt_speed(self, n, v):
        b = self.P["belt_speed_m_s"]
        if n in b:
            return b[n]["value"]
        layer = v.get("layer")
        if v["kind"] == "noria":
            return b["noria_existing"]["value"]
        if v["kind"] in b:
            return b[v["kind"]]["value"]
        return (b["conveyor_designed"] if layer == "designed" else b["conveyor_existing"])["value"]

    def movers_cap_missing(self, n):
        """t per step a pass-through node can take (SEP5 has a t/h; others none)."""
        v = self.g.nodes[n]
        t_h = v.get("t_h")
        miss = self.P["t_h_missing"]["nodes"]
        if t_h is None and n in miss:
            t_h = miss[n]["value"]
        return None if t_h is None else t_h / 3600.0 * self.dt

    def derate(self, n, a):
        """Capacity factor of a separator for wet grain: -k % per % of moisture over the base (params separator)."""
        sp = self.P["separator"]
        if n not in sp["nodes"]:
            return 1.0
        w = moisture(a)
        over = max(0.0, (w or 0.0) - sp["base_moisture_pct"]["value"])
        return max(0.05, 1.0 - sp["derate_pct_per_pct"]["value"] / 100.0 * over)

    def set_store(self, sid, mass, moisture_pct=None, temp_c=None):
        """Initial condition (scenario only): put `mass` t in store `sid`."""
        s = self.stores[sid]
        assert mass <= s.cap + EPS, f"{sid}: {mass} t > capacity {s.cap:.1f} t"
        w = moisture_pct if moisture_pct is not None else self.P["grain"]["default_moisture_pct"]["value"]
        old, old_w = s.lot[0], s.lot[1]
        s.lot = lot(mass, w)
        s.ref_mass = mass
        s.temp_c = temp_c if temp_c is not None else self.P["grain"]["default_temp_c"]["value"]
        self.initial_t += s.lot[0] - old          # grain put in by hand is not "received"
        self.water["initial"] += s.lot[1] - old_w

    def log(self, kind, text):
        self.events.append({"t_s": round(self.t, 3), "kind": kind, "text": text})

    # -------------------------------------------------------------- the graph with the live gates
    def edge_open(self, e):
        gates = e["gates"] + e.get("alt_gates", [])
        if not gates:
            return True
        if e.get("alt_gates"):                      # silo outlet: centre or side gates
            return any(self.gates[g].is_open for g in gates)
        test = any if e.get("gate_logic") == "any" else all
        return test(self.gates[g].is_open for g in e["gates"])

    def open_gates(self):
        return {g for g, x in self.gates.items() if x.is_open}

    def live_edges(self, n):
        live = [e for e in self.g.out[n] if self.edge_open(e)]
        if not live:
            return []
        first = min(e["order"] for e in live)
        return [e for e in live if e["order"] == first]

    # -------------------------------------------------------------- moving grain
    def deliver(self, n, a, seen=frozenset()):
        """Push lot `a` out of node `n` along its live outlets; returns the part nobody took."""
        if a[0] <= EPS:
            return [0.0, 0.0]
        live = self.live_edges(n)
        if not live:
            return a
        k = len(live)
        rest = [0.0, 0.0]
        for e in live:
            p = [a[0] / k, a[1] / k]
            left = self.take(e["to"], p, seen | {n})
            took = p[0] - left[0]
            if took > EPS:
                self.edge_t[f"{e['from']}->{e['to']}"] += took
            rest = add(rest, left)
        return rest

    def take(self, m, a, seen):
        """Node `m` takes what it can of lot `a`; returns the rest."""
        if m in seen:
            return a                                 # a loop in the open gates: the grain backs up
        if m in self.movers:
            mv = self.movers[m]
            acc = min(a[0], mv.budget)
            got = part(a, acc)
            mv.budget -= acc
            mv.inbox = add(mv.inbox, got)
            return sub(a, got)
        if m in self.stores:
            s = self.stores[m]
            got = part(a, s.space())
            s.lot = add(s.lot, got)
            s.got += got[0]
            s.refused += a[0] - got[0]
            if got[0] > EPS:
                s.ref_mass = s.lot[0]                # filling rebuilds the surface the discharge starts from
            return sub(a, got)
        if m == DRYER:
            d = self.dryer
            got = part(a, max(0.0, d["bin_cap"] - d["bin"][0]))
            d["bin"] = add(d["bin"], got)
            return sub(a, got)
        if m == TRUCK_OUT:
            tk = self.truck_out
            if tk is None or tk["timer"] > 0:
                return a
            room = min(tk["cap"] - tk["lot"][0], tk["budget"])
            got = part(a, max(0.0, room))
            tk["lot"] = add(tk["lot"], got)
            tk["budget"] -= got[0]
            return sub(a, got)
        if m in self.sinks:
            self.totals["shipped_t"] += a[0]
            self.water["shipped"] += a[1]
            return [0.0, 0.0]
        if m in self.pass_nodes:
            cap = self.pass_budget.get(m)             # in t of dry-grain capacity this step
            over = [0.0, 0.0]
            f = 1.0
            if cap is not None:
                f = self.derate(m, a)
                go = part(a, cap * f)
                over = sub(a, go)
                a = go
            left = self.deliver(m, a, seen)
            if cap is not None:
                self.pass_budget[m] -= (a[0] - left[0]) / f
            return add(left, over)
        raise KeyError(f"take: node {m} has no role")

    # -------------------------------------------------------------- one step
    def step(self):
        dt = self.dt
        self.edge_t = defaultdict(float)
        for x in self.gates.values():
            was = x.state
            x.step(dt)
            if x.state != was and x.state in ("open", "closed"):
                self.log("gate", f"засувка {x.id} {'відкрита' if x.state == 'open' else 'закрита'}")
        for mv in self.movers.values():
            was = mv.state
            mv.step_state(dt)
            if mv.state != was:
                self.log("motor", f"{mv.id} {'на швидкості' if mv.state == 'run' else 'зупинено'}")
            # a slipping belt (speed relay disturbance) lifts / carries proportionally less
            mv.budget = mv.cap * min(1.0, mv.speed_pct / 100.0) if mv.state == "run" else 0.0
            mv.out_t = 0.0
        for s in self.stores.values():
            s.got = s.refused = 0.0
        self.pass_budget = {n: c for n, c in self.pass_cap.items() if c is not None}
        if self.truck_out is not None:
            self.truck_out["budget"] = self.truck_cfg["load_t_h"] / 3600.0 * dt

        # 2. movers push what reached their heads
        popped = []
        for n in sorted(self.movers):
            mv = self.movers[n]
            if mv.state != "run":
                continue
            head = mv.pop()
            out = add(head, mv.backlog)
            left = self.deliver(n, out)
            mv.out_t = out[0] - left[0]
            mv.backlog = left
            popped.append(mv)

        # 3. dryer
        self._dryer_step()

        # 4. trucks
        self._trucks_step()

        # 5. stores give what their outlets take
        for n in sorted(self.stores):
            self._store_out(self.stores[n])

        # 6. what each running mover took enters its tail
        for mv in popped:
            mv.push(mv.inbox)
            mv.inbox = [0.0, 0.0]
        self.t += dt

    def _store_out(self, s):
        if s.lot[0] <= EPS or not self.live_edges(s.id):
            return
        avail = s.lot[0]
        if s.residual is not None:
            outs = [e for e in self.g.out[s.id] if e.get("alt_gates")]
            side = any(self.gates[g].is_open for e in outs for g in e["alt_gates"])
            res = s.residual_t(side)
            if s.sweep == "run":
                avail = min(avail, max(0.0, avail - res) + self.P["silo_discharge"]["sweep_t_h"]["value"] / 3600 * self.dt)
            else:
                avail = max(0.0, avail - res)
        if s.feed_t_h is not None:
            avail = min(avail, s.feed_t_h / 3600.0 * self.dt)
        if avail <= EPS:
            return
        offer = part(s.lot, avail)
        left = self.deliver(s.id, offer)
        s.lot = sub(s.lot, sub(offer, left))
        if s.lot[0] < 1e-12:
            s.lot = [0.0, 0.0]

    def _dryer_step(self):
        d = self.dryer
        d["in_t"] = d["out_t"] = d["water_t"] = 0.0
        if d["state"] != "run":
            return
        if d["backlog"][0] > EPS:                    # the discharge is blocked: hold the column
            left = self.deliver(DRYER, d["backlog"])
            d["out_t"] = d["backlog"][0] - left[0]
            d["backlog"] = left
            return
        head = d["column"].popleft()
        d["csum"] = sub(d["csum"], head)
        if d["csum"][0] < 1e-12:
            d["csum"] = [sum(c[0] for c in d["column"]), sum(c[1] for c in d["column"])]
        out = head
        if head[0] > EPS:
            dry = head[0] - head[1]
            w_out = d["w_out"]
            if moisture(head) > w_out:               # shrink: the dry matter stays, water leaves
                m_out = dry / (1.0 - w_out / 100.0)
                out = [m_out, m_out - dry]
                d["water_t"] = head[0] - m_out
                self.totals["evaporated_t"] += d["water_t"]
        left = self.deliver(DRYER, out)
        d["out_t"] = out[0] - left[0]
        d["backlog"] = left
        feed = part(d["bin"], min(d["bin"][0], d["cap"]))
        d["bin"] = sub(d["bin"], feed)
        d["column"].append(feed)
        d["csum"] = add(d["csum"], feed)
        d["in_t"] = feed[0]
        if feed[0] > EPS:
            d["w_in"] = moisture(feed)

    def _trucks_step(self):
        dt, cfg = self.dt, self.truck_cfg
        tk = self.truck_in
        if tk is None and self.trucks_in:
            nxt = self.trucks_in.popleft()
            tk = self.truck_in = {"lot": lot(nxt["mass"], nxt["moisture"]), "phase": "weigh", "timer": cfg["weigh_s"],
                                  "rate": nxt["mass"] / cfg["unload_s"]}
            self.log("truck", f"авто {nxt['mass']:.0f} т, вологість {nxt['moisture']:.1f} % — на ваги в'їзду")
        if tk is not None:
            if tk["phase"] == "weigh":
                tk["timer"] -= dt
                if tk["timer"] <= EPS:
                    tk["phase"] = "unload"
                    self.log("truck", f"зважено {tk['lot'][0]:.1f} т, розвантаження в яму")
            else:
                chunk = part(tk["lot"], min(tk["lot"][0], tk["rate"] * dt))
                left = self.deliver(TRUCK_IN, chunk)
                got = sub(chunk, left)
                tk["lot"] = sub(tk["lot"], got)
                self.totals["received_t"] += got[0]
                self.water["received"] += got[1]
                if tk["lot"][0] <= 1e-6:
                    self.totals["received_t"] += tk["lot"][0]
                    self.water["received"] += tk["lot"][1]
                    self.stores["PIT"].lot = add(self.stores["PIT"].lot, tk["lot"])
                    self.truck_in = None
                    self.log("truck", "авто розвантажено")

        to = self.truck_out
        if to is None and self.trucks_out > 0:
            self.trucks_out -= 1
            to = self.truck_out = {"lot": [0.0, 0.0], "cap": cfg["payload_t"], "timer": cfg["weigh_s"], "budget": 0.0}
            self.log("truck", f"порожнє авто під Ш1 ({cfg['payload_t']:.0f} т)")
        if to is not None:
            if to["timer"] > 0:
                to["timer"] -= dt
            elif to["lot"][0] >= to["cap"] - 1e-6:
                self.totals["shipped_t"] += to["lot"][0]
                self.water["shipped"] += to["lot"][1]
                self.edge_t["TRUCK_OUT->SCALES_OUT"] += to["lot"][0]
                self.log("truck", f"відвантажено {to['lot'][0]:.1f} т, авто на ваги виїзду")
                self.truck_out = None

    # -------------------------------------------------------------- totals
    def stored(self):
        s = sum(x.lot[0] for x in self.stores.values()) + self.dryer["bin"][0]
        if self.truck_out is not None:
            s += self.truck_out["lot"][0]
        return s

    def transit(self):
        d = self.dryer
        return (sum(mv.transit for mv in self.movers.values()) + d["csum"][0] + d["backlog"][0])

    def balance(self):
        """initial + received - (stored + transit + shipped + evaporated); 0 when no grain is lost or made."""
        T = self.totals
        return self.initial_t + T["received_t"] - (self.stored() + self.transit() + T["shipped_t"] + T["evaporated_t"])

    def water_balance(self):
        """The same balance for the water in the grain: the dryer must remove exactly what it reports."""
        d = self.dryer
        stored = sum(x.lot[1] for x in self.stores.values()) + d["bin"][1]
        if self.truck_out is not None:
            stored += self.truck_out["lot"][1]
        transit = sum(mv.transit_lot()[1] for mv in self.movers.values()) + d["csum"][1] + d["backlog"][1]
        W = self.water
        return W["initial"] + W["received"] - (stored + transit + W["shipped"] + self.totals["evaporated_t"])
