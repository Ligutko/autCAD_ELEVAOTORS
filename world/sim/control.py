"""Control center, module C: commands, routes, interlocks and sensors over the simulator (CONTROL_CENTER_SPEC.md §2).

The rules are SITE.json `process.interlocks` (research/design/sensors_interlocks.md):
  start   a route starts against the grain: the next motor starts when the previous one is at speed and the route
          gates are in their end positions; the source opens last;
  trip    an emergency stop of a motor stops at once every motor above it; the ones below run until empty;
  stop    a normal stop goes with the grain: the source first, then each motor once it has run empty;
  plug    a plug sensor stops its mover (and everything above, by the trip rule);
  speed   the speed relay: alarm at -10 %, trip at -20 % held 10 s, monitored 10 s after the start;
  bearing a hot bearing (60 °C) trips.
Routes are the routes of kit/process.py (Graph.routes), named by Graph.describe.

Commands are dicts, every answer is {"ok": bool, "reason": str}; every command and state change goes to the journal.
"""

import hashlib
import json
from collections import defaultdict

from .core import DRYER, EPS, Sim

LEVEL = "level_hi"


class Plant:
    def __init__(self, sim=None, **kw):
        self.sim = sim or Sim(**kw)
        s = self.sim
        self.g = s.g
        self.routes_all = self.g.routes()
        self.route_by_id = {self.g.describe(r): r for r in self.routes_all}
        self.active = {}                       # rid -> run record
        self.sensors = {sid: "ok" for sid in s.sensor_ids}
        self.latched = set()                   # movers stopped by a trip, waiting for reset
        self.alarms = {}                       # id -> {"id", "level", "t_s", "text"}
        self.low_speed_s = defaultdict(float)
        self.speed, self.paused, self.scenario = 1.0, False, None
        il = {i["id"]: i for i in s.site["process"]["interlocks"]}
        self.speed_alarm = il["speed"]["alarm_pct"]
        self.speed_trip = il["speed"]["trip_pct"]
        self.speed_delay = il["speed"]["delay_s"]
        self.bearing_trip = il["bearing"]["trip_c"]
        self.plug_t = s.P["motor"]["plug_backlog_t"]["value"]
        self.level_frac = s.P["storage"]["silo_level_hi_frac"]["value"]
        d = s.P["dryer"]
        self.bin_lo, self.bin_hi = d["bin_lo_frac"]["value"], d["bin_hi_frac"]["value"]
        self.siren_s = s.P["control"]["siren_s"]["value"]
        self.gas_per = d["gas_m3_per_pct_t"]["value"]

    # ============================================================== helpers
    def log(self, kind, text):
        self.sim.log(kind, text)

    def mover(self, m):
        return self.sim.movers[m]

    def downstream(self, n):
        """What the grain of `n` reaches first through the open outlets (through pass-through nodes)."""
        s, out, seen = self.sim, [], set()

        def walk(x):
            for e in s.live_edges(x):
                m = e["to"]
                if m in seen:
                    continue
                seen.add(m)
                if m in s.pass_nodes:
                    walk(m)
                else:
                    out.append(m)
        walk(n)
        return out

    def feeders(self, n):
        """Movers that deliver into `n` now (through open edges and pass-through nodes, not through stores)."""
        s, out, seen = self.sim, [], set()

        def walk(x):
            for e in self.g.inn[x]:
                m = e["from"]
                if m in seen or not s.edge_open(e):
                    continue
                seen.add(m)
                if m in s.movers:
                    out.append(m)
                elif m in s.pass_nodes:
                    walk(m)
        walk(n)
        return out

    def upstream(self, n):
        """All movers above `n` through open edges, across pass-through nodes, stopping at stores and the dryer."""
        res, todo = [], [n]
        while todo:
            x = todo.pop()
            for m in self.feeders(x):
                if m not in res:
                    res.append(m)
                    todo.append(m)
        return res

    def route_units(self, r):
        """Movers and the dryer along the grain flow."""
        return [n for n in self.g.route_nodes(r) if n in self.sim.movers or n == DRYER]

    @staticmethod
    def source_gates(g, r):
        for e in r:
            gates = e["gates"][:1] if e.get("gate_logic") == "any" else e["gates"]
            if gates:
                return list(gates)
        return []

    def diverters(self, r):
        """Gates on the other outlets of the route nodes: closed so no grain leaves the route."""
        own = {(e["from"], e["to"]) for e in r}
        need = set(self.g.route_gates(r))
        close = set()
        for n in self.g.route_nodes(r)[:-1]:
            for e in self.g.out[n]:
                if (e["from"], e["to"]) in own:
                    continue
                close |= {x for x in e["gates"] + e.get("alt_gates", []) if x not in need}
        return close

    def resolve_route(self, rid):
        if isinstance(rid, int) or (isinstance(rid, str) and rid.isdigit()):
            i = int(rid)
            if 0 <= i < len(self.routes_all):
                r = self.routes_all[i]
                return self.g.describe(r), r
            return None, None
        return (rid, self.route_by_id[rid]) if rid in self.route_by_id else (None, None)

    def alarm(self, aid, level, text):
        if aid not in self.alarms:
            self.alarms[aid] = {"id": aid, "level": level, "t_s": round(self.sim.t, 3), "text": text}
            self.log("alarm" if level == "alarm" else "trip", text)

    # ============================================================== commands
    def cmd(self, c):
        op = c.get("op")
        f = getattr(self, f"_cmd_{op}", None)
        if f is None:
            return self._answer(c, False, f"невідома команда {op!r}")
        try:
            ok, reason = f(c)
        except KeyError as e:
            ok, reason = False, f"немає такого id: {e.args[0]}"
        return self._answer(c, ok, reason)

    def _answer(self, c, ok, reason):
        brief = json.dumps(c, ensure_ascii=False, sort_keys=True)
        self.log("cmd" if ok else "reject", f"{brief} -> {'ok' if ok else 'відмова: ' + reason}")
        return {"ok": ok, "reason": reason}

    def _cmd_gate(self, c):
        x = self.sim.gates[c["id"]]
        if c["action"] not in ("open", "close"):
            return False, "action: open | close"
        x.target = 1.0 if c["action"] == "open" else 0.0
        return True, ""

    def _cmd_motor(self, c):
        m = c["id"]
        mv = self.mover(m)
        if c["action"] == "start":
            ok, why = self.can_start(m)
            if not ok:
                return False, why
            mv.command(True)
            mv.timer += self.siren_s                   # НПАОП: warning signal 15-20 s before a remote start
            self.log("siren", f"сирена перед пуском {m}")
            return True, ""
        if c["action"] == "stop":
            above = [x for x in self.upstream(m) if self.mover(x).state in ("starting", "run")]
            mv.command(False)
            for x in above:
                self.mover(x).command(False)
            return True, ("блокування: зупинено вищі " + ", ".join(above)) if above else ""
        return False, "action: start | stop"

    def can_start(self, m):
        mv = self.mover(m)
        if m in self.latched:
            return False, f"{m} зупинено аварійно — спершу скинути тривогу"
        if mv.state in ("starting", "run"):
            return False, f"{m} уже працює"
        nxt = self.downstream(m)
        if not nxt:
            return False, f"у {m} немає відкритого виходу — зерно піде в завал"
        idle = [x for x in nxt if x in self.sim.movers and self.mover(x).state != "run"]
        if idle:
            return False, f"блокування пуску: нижчий механізм {', '.join(idle)} не працює (пуск проти потоку)"
        if DRYER in nxt and self.sim.dryer["state"] != "run":
            return False, "блокування пуску: сушарка не працює"
        return True, ""

    def _cmd_trip(self, c):
        self.trip(c["id"], f"аварійний стоп {c['id']} (кнопка)")
        return True, ""

    def _cmd_reset(self, c):
        cleared = sorted(self.latched)
        self.latched.clear()
        for sid, v in self.sensors.items():
            if v == "trip":
                self.sensors[sid] = "ok"
        self.alarms.clear()
        return True, ("скинуто: " + ", ".join(cleared)) if cleared else ""

    def _cmd_route(self, c):
        rid, r = self.resolve_route(c["id"])
        if r is None:
            return False, f"немає маршруту {c['id']!r}"
        if c["action"] == "start":
            return self.route_start(rid, r)
        if c["action"] == "stop":
            if rid not in self.active:
                return False, "маршрут не працює"
            self.route_stop(rid)
            return True, ""
        return False, "action: start | stop"

    def _cmd_dryer(self, c):
        d = self.sim.dryer
        if c["action"] == "start":
            if not self.downstream(DRYER) or any(self.mover(x).state != "run" for x in self.downstream(DRYER)
                                                 if x in self.sim.movers):
                return False, "блокування пуску: вихід сушарки (T4) не працює"
            d["state"] = "run"
            return True, ""
        d["state"] = "off"
        return True, ""

    def _cmd_sweep(self, c):
        s = self.sim.stores[c["id"]]
        if s.residual is None:
            return False, f"у {c['id']} немає зачисного шнека"
        if c["action"] == "start":
            side = any(self.sim.gates[x].is_open for e in self.g.out[s.id] for x in e.get("alt_gates", []))
            if s.mass > s.residual_t(side) + 0.5:
                return False, "шнек вмикають після самопливу: зерно ще йде самопливом"
            s.sweep = "run"
        else:
            s.sweep = "off"
        return True, ""

    def _cmd_feed(self, c):
        """Throttle a store outlet (the feed gate under the pit, a silo outlet): t/h, or null for fully open."""
        st = self.sim.stores[c["id"]]
        v = c.get("t_h")
        if v is not None and float(v) <= 0:
            return False, "подача > 0 т/год або null"
        st.feed_t_h = None if v is None else float(v)
        return True, ""

    def _cmd_fans(self, c):
        self.sim.stores[c["id"]].fans = "run" if c["action"] == "start" else "off"
        return True, ""

    def _cmd_truck_in(self, c):
        n = int(c.get("count", 1))
        for _ in range(n):
            self.sim.trucks_in.append({"mass": float(c.get("mass", self.sim.truck_cfg["payload_t"])),
                                       "moisture": float(c.get("moisture",
                                                               self.sim.P["grain"]["default_moisture_pct"]["value"]))})
        return True, ""

    def _cmd_truck_out(self, c):
        self.sim.trucks_out += int(c.get("count", 1))
        return True, ""

    def _cmd_store(self, c):
        self.sim.set_store(c["id"], float(c["mass"]), c.get("moisture"), c.get("temp_c"))
        return True, ""

    def _cmd_set(self, c):
        """Disturbances for scenarios: belt speed %, bearing temperature, silo temperature."""
        what, i, v = c["what"], c["id"], c["value"]
        if what == "speed_pct":
            self.mover(i).speed_pct = float(v)
        elif what == "bearing_c":
            self.mover(i).bearing_c = float(v)
        elif what == "temp_c":
            self.sim.stores[i].temp_c = float(v)
        else:
            return False, f"невідомий параметр {what}"
        return True, ""

    def _cmd_speed(self, c):
        v = float(c["value"])
        if v <= 0:
            return False, "швидкість > 0"
        self.speed = v
        return True, ""

    def _cmd_pause(self, c):
        self.paused = bool(c["value"])
        return True, ""

    # ============================================================== routes
    def route_start(self, rid, r):
        if rid in self.active:
            return False, "маршрут уже працює"
        need, close = set(self.g.route_gates(r)), self.diverters(r)
        for other, a in self.active.items():
            clash = (need & a["close"]) | (close & a["need"])
            if clash:
                return False, f"конфлікт з маршрутом {other}: засувки {', '.join(sorted(clash))}"
        stuck = [m for m in self.route_units(r) if m in self.latched]
        if stuck:
            return False, f"аварійно зупинені {', '.join(stuck)} — спершу скинути тривогу"
        src = self.source_gates(self.g, r)
        self.active[rid] = {"route": r, "state": "starting", "phase": "gates", "need": need, "close": close,
                            "source": src, "queue": list(reversed(self.route_units(r))), "tripped": False,
                            "dry": DRYER in self.g.route_nodes(r)}
        for x in close:
            self.sim.gates[x].target = 0.0
        for x in need - set(src):
            self.sim.gates[x].target = 1.0
        self.log("route", f"пуск маршруту {rid}")
        return True, ""

    def route_stop(self, rid, tripped=False):
        a = self.active[rid]
        a["state"], a["phase"], a["tripped"] = "stopping", "drain", a["tripped"] or tripped
        first = a["route"][0]                        # the source outlet: all its gates, the silo side gates too
        for x in set(a["source"]) | (set(first["gates"] + first.get("alt_gates", [])) if first["from"] in self.sim.stores else set()):
            self.sim.gates[x].target = 0.0
        self.log("route", f"{'аварійна ' if tripped else ''}зупинка маршруту {rid}")

    def _gates_at(self, ids, target):
        return all(abs(self.sim.gates[x].pos - target) < EPS and self.sim.gates[x].target == target for x in ids)

    def _route_tick(self, rid, a):
        s = self.sim
        if a["state"] == "starting":
            if a["phase"] == "gates":
                if self._gates_at(a["need"] - set(a["source"]), 1.0) and self._gates_at(a["close"], 0.0):
                    a["phase"], a["siren_until"] = "siren", s.t + self.siren_s
                    self.log("siren", f"сирена перед пуском маршруту ({self.siren_s:.0f} с)")
            if a["phase"] == "siren" and s.t >= a["siren_until"] - EPS:
                a["phase"] = "motors"
            if a["phase"] == "motors":
                while a["queue"]:
                    u = a["queue"][0]
                    if u == DRYER:
                        s.dryer["state"] = "run"
                        a["queue"].pop(0)
                        continue
                    mv = self.mover(u)
                    if mv.state == "run":
                        a["queue"].pop(0)
                        continue
                    if mv.state == "off":
                        ok, why = self.can_start(u)
                        if not ok:
                            self.log("route", f"маршрут {rid}: {why}")
                            self.route_stop(rid, tripped=True)
                            return
                        mv.command(True)
                    break
                if not a["queue"]:
                    a["phase"] = "source"
                    for x in a["source"]:
                        s.gates[x].target = 1.0
            if a["phase"] == "source" and self._gates_at(a["source"], 1.0):
                a["state"], a["phase"] = "run", "run"
                self.log("route", f"маршрут працює: {rid}")
            return
        if a["state"] == "run":
            if a["dry"]:                                 # T3 keeps the bin over the dryer between lo and hi
                d = s.dryer
                if d["bin"][0] >= self.bin_hi * d["bin_cap"]:
                    for x in a["source"]:
                        s.gates[x].target = 0.0
                elif d["bin"][0] <= self.bin_lo * d["bin_cap"]:
                    for x in a["source"]:
                        s.gates[x].target = 1.0
            return
        # stopping: each unit stops once everything above it on the route is stopped and it has run empty
        units = self.route_units(a["route"])
        for k, u in enumerate(units):
            above_off = all(self._unit_off(x) for x in units[:k])
            if not above_off or self._unit_off(u):
                continue
            if u == DRYER:
                d = s.dryer
                if d["bin"][0] <= EPS and d["csum"][0] <= EPS and d["backlog"][0] <= EPS:
                    d["state"] = "off"
                continue
            mv = self.mover(u)
            if mv.state == "run" and mv.transit <= 1e-6 and not self._fed(u):
                mv.command(False)
        if all(s.dryer["state"] == "off" if u == DRYER else self.mover(u).state == "off" for u in units):
            del self.active[rid]
            self.log("route", f"маршрут зупинено: {rid}")

    def _unit_off(self, u):
        if u == DRYER:
            return self.sim.dryer["state"] == "off"
        return self.mover(u).state in ("off", "stopping")

    def _fed(self, m):
        """Grain still coming into `m` by gravity from a store or the dryer above it (open path, grain there)."""
        s, seen = self.sim, set()

        def walk(x):
            for e in self.g.inn[x]:
                y = e["from"]
                if y in seen or not s.edge_open(e):
                    continue
                seen.add(y)
                if y in s.stores and s.stores[y].mass > EPS:
                    return True
                if y == DRYER and s.dryer["state"] == "run" and (s.dryer["bin"][0] > EPS or s.dryer["backlog"][0] > EPS
                                                                 or s.dryer["csum"][0] > EPS):
                    return True
                if y in s.pass_nodes and walk(y):
                    return True
            return False
        return walk(m)

    # ============================================================== trips and sensors
    def trip(self, m, text, sensor=None):
        stop = {m} | set(self.upstream(m))
        for rid, a in list(self.active.items()):
            r = a["route"]
            if m in self.g.route_motors(r):
                stop |= set(self.g.trip(r, m)[0])
                if a["state"] != "stopping" or not a["tripped"]:
                    self.route_stop(rid, tripped=True)
        for x in sorted(stop):
            self.mover(x).command(False)
        self.latched.add(m)
        if sensor:
            self.sensors[sensor] = "trip"
        self.alarm(sensor or f"{m}.estop", "trip", text + " — зупинено: " + ", ".join(sorted(stop)))

    def sensors_tick(self):
        s = self.sim
        for m, mv in s.movers.items():
            # plug: grain the mover cannot discharge
            if mv.backlog[0] > self.plug_t:
                sid = f"{m}.plug"
                if sid in self.sensors:
                    if self.sensors[sid] != "trip":
                        self.trip(m, f"підпір {m}: зерно не йде далі ({mv.backlog[0]:.2f} т)", sid)
                else:
                    self.alarm(f"{m}.overflow", "alarm", f"{m}: зерно не йде далі ({mv.backlog[0]:.2f} т), датчика підпору немає")
            # speed relay
            sid = f"{m}.speed"
            if sid in self.sensors and mv.state == "run" and mv.run_s >= self.speed_delay:
                drop = 100.0 - mv.speed_pct
                if drop >= self.speed_trip:
                    self.low_speed_s[m] += s.dt
                    if self.low_speed_s[m] >= self.speed_delay and self.sensors[sid] != "trip":
                        self.trip(m, f"реле швидкості {m}: швидкість {mv.speed_pct:.0f} %", sid)
                elif drop >= self.speed_alarm:
                    self.low_speed_s[m] = 0.0
                    if self.sensors[sid] == "ok":
                        self.sensors[sid] = "alarm"
                        self.alarm(sid, "alarm", f"реле швидкості {m}: швидкість {mv.speed_pct:.0f} %")
                else:
                    self.low_speed_s[m] = 0.0
            # bearings
            sid = f"{m}.bearing"
            if sid in self.sensors and mv.bearing_c is not None and mv.bearing_c >= self.bearing_trip \
                    and self.sensors[sid] != "trip" and mv.state in ("starting", "run"):
                self.trip(m, f"гарячий підшипник {m}: {mv.bearing_c:.0f} °C", sid)
        # upper level of the silos and the wet silos: trip what feeds them
        for sid_store, st in s.stores.items():
            sid = f"{sid_store}.{LEVEL}"
            full = st.mass >= self.level_frac * st.cap - 1e-6 or st.refused > 1e-9     # grain up to the switch
            if sid in self.sensors and full and self.sensors[sid] != "trip":
                for f in self.feeders(sid_store):
                    if self.mover(f).state in ("starting", "run"):
                        self.trip(f, f"верхній рівень {sid_store}: {st.mass:.0f} т", sid)
                        break
                else:
                    self.sensors[sid] = "trip"
                    self.alarm(sid, "trip", f"верхній рівень {sid_store}: {st.mass:.0f} т")
        # dryer bin levels (the level loop is in _route_tick)
        d = s.dryer
        for sid, on in (("DRYER.level_hi", d["bin"][0] >= self.bin_hi * d["bin_cap"]),
                        ("DRYER.level_lo", d["bin"][0] <= self.bin_lo * d["bin_cap"])):
            if sid in self.sensors:
                self.sensors[sid] = "alarm" if on else "ok"

    # ============================================================== time
    def tick(self):
        for rid in list(self.active):
            if rid in self.active:
                self._route_tick(rid, self.active[rid])
        self.sim.step()
        self.sensors_tick()

    def run_until(self, t_s):
        while self.sim.t < t_s - EPS:
            self.tick()

    def journal_hash(self):
        return hashlib.sha256(json.dumps(self.sim.events, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    # ============================================================== state (world/sim/STATE_SCHEMA.json)
    def state(self, events=60):
        s = self.sim
        k = 3600.0 / s.dt
        motors = {m: {"state": mv.state, "load_t_h": round(mv.out_t * k, 3), "transit_t": round(mv.transit, 4),
                      "backlog_t": round(mv.backlog[0], 4), "kw": mv.kw} for m, mv in s.movers.items()}
        gates = {gid: {"state": x.state, "pos": round(x.pos, 4)} for gid, x in s.gates.items()}
        edges = {e: {"t_h": round(v * k, 3)} for e, v in s.edge_t.items() if v > EPS}
        stores = {}
        for sid, st in s.stores.items():
            stores[sid] = {"mass_t": round(st.mass, 4), "cap_t": round(st.cap, 3), "fill": round(min(1.0, st.mass / st.cap), 5),
                           "moisture_pct": None if st.mass <= EPS else round(100 * st.lot[1] / st.lot[0], 3),
                           "temp_c": st.temp_c}
            if st.residual is not None:
                stores[sid].update({"sweep": st.sweep, "fans": st.fans})
            if st.feed_t_h is not None:
                stores[sid]["feed_t_h"] = st.feed_t_h
        if s.truck_out is not None:
            to = s.truck_out
            stores["TRUCK_OUT"] = {"mass_t": round(to["lot"][0], 4), "cap_t": to["cap"], "fill": round(to["lot"][0] / to["cap"], 5),
                                   "moisture_pct": None if to["lot"][0] <= EPS else round(100 * to["lot"][1] / to["lot"][0], 3),
                                   "temp_c": None}
        d = s.dryer
        dryer = {"state": d["state"], "in_t_h": round(d["in_t"] * k, 3), "out_t_h": round(d["out_t"] * k, 3),
                 "water_t_h": round(d["water_t"] * k, 4), "bin_t": round(d["bin"][0], 4),
                 "column_t": round(d["csum"][0], 4), "w_in": None if d["w_in"] is None else round(d["w_in"], 3),
                 "w_out": d["w_out"],
                 "gas_m3_h": None if d["state"] != "run" or d["w_in"] is None else
                 round(self.gas_per * max(0.0, d["w_in"] - d["w_out"]) * d["in_t"] * k, 2)}
        T = s.totals
        power = sum(mv.kw for mv in s.movers.values() if mv.kw and mv.state in ("starting", "run"))
        reg = s.registry
        for sid, st in s.stores.items():
            if st.fans == "run" and f"{sid}.fan" in reg:
                power += reg[f"{sid}.fan"]["kw"] * reg[f"{sid}.fan"]["qty"]
            if st.sweep == "run":
                power += sum(reg[f"{sid}.{p}"]["kw"] for p in ("sweep", "tractor") if f"{sid}.{p}" in reg)
        if d["state"] == "run":
            power += reg["DRYER"]["kw"] or 0.0
        return {
            "t_s": round(s.t, 3), "speed": self.speed, "paused": self.paused, "scenario": self.scenario,
            "motors": motors, "gates": gates, "edges": edges, "stores": stores, "dryer": dryer,
            "sensors": dict(self.sensors), "alarms": list(self.alarms.values()), "events": s.events[-events:],
            "routes": [{"id": rid, "nodes": self.g.route_nodes(a["route"]), "state": a["state"]} for rid, a in self.active.items()],
            "totals": {"received_t": round(T["received_t"], 4), "shipped_t": round(T["shipped_t"], 4),
                       "evaporated_t": round(T["evaporated_t"], 4), "stored_t": round(s.stored(), 4),
                       "transit_t": round(s.transit(), 4)},
            "power_kw": round(power, 2),
            "trucks": {"in_queue": len(s.trucks_in),
                       "in_now": None if s.truck_in is None else {"phase": s.truck_in["phase"], "left_t": round(s.truck_in["lot"][0], 3)},
                       "out_queue": s.trucks_out,
                       "out_now": None if s.truck_out is None else {"load_t": round(s.truck_out["lot"][0], 3), "cap_t": s.truck_out["cap"]}},
            "dryer_bin_cap_t": s.dryer["bin_cap"],
        }
