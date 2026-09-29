"""Control center, module P: a local server that runs the simulator in real time and serves the operator panel
(CONTROL_CENTER_SPEC.md §4). Standard library only, 127.0.0.1.

Run:
    python world/sim/server.py [--port 8765] [--scenario receive_s1]
    then open http://127.0.0.1:8765/

API (JSON):
    GET  /state          the state contract (world/sim/STATE_SCHEMA.json); live Blender reads the same
    GET  /graph          nodes, edges, gates, routes, capacities with their basis: what the panel draws
    GET  /mnemo.svg      the process schematic (world/panel/mnemo.py from world/panel/layout.json)
    GET  /scenarios      [{id, title, description}]
    POST /cmd            a command of control.Plant.cmd -> {"ok", "reason"}
    POST /scenario       {"id": name | null} -> a fresh plant, the scenario's timed commands run as time goes
    GET  /               the panel (world/panel/index.html and its files)
Simulated time runs `speed` times faster than the wall clock; the physics does not depend on `speed`
(check_sim: time step independence).
"""

import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
if str(WORLD) not in sys.path:
    sys.path.insert(0, str(WORLD))

from panel import mnemo  # noqa: E402
from sim import scenario as scn  # noqa: E402
from sim.control import Plant  # noqa: E402

PANEL = WORLD / "panel"
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".svg": "image/svg+xml; charset=utf-8", ".json": "application/json; charset=utf-8", ".png": "image/png"}
MAX_STEPS_PER_LOOP = 4000          # at ×600 and dt 1 s a loop of 20 ms needs 12 steps; this only bounds a catch-up


class Engine:
    """The plant plus the clock that advances it; every access under one lock."""

    def __init__(self, scenario=None):
        self.lock = threading.RLock()
        self.load(scenario)
        self.stop = False

    def load(self, scenario=None):
        with self.lock:
            self.plant = Plant()
            self.runner = scn.Runner(scn.load(scenario), plant=self.plant) if scenario else None
            if self.runner is None:
                self.plant.scenario = None
            self.t_wall = time.perf_counter()
            self.t_sim0 = 0.0

    def tick_loop(self):
        while not self.stop:
            time.sleep(0.02)
            with self.lock:
                p = self.plant
                now = time.perf_counter()
                if p.paused:
                    self.t_wall, self.t_sim0 = now, p.sim.t
                    continue
                target = self.t_sim0 + (now - self.t_wall) * p.speed
                n = 0
                while p.sim.t + p.sim.dt <= target + 1e-9 and n < MAX_STEPS_PER_LOOP:
                    (self.runner.tick if self.runner else p.tick)()
                    n += 1
                if n >= MAX_STEPS_PER_LOOP:          # cannot keep up: drop the lag instead of spiralling
                    self.t_wall, self.t_sim0 = now, p.sim.t

    def cmd(self, c):
        with self.lock:
            if c.get("op") == "speed":               # keep the simulated clock continuous across a speed change
                self.t_wall, self.t_sim0 = time.perf_counter(), self.plant.sim.t
            return self.plant.cmd(c)

    def state(self):
        with self.lock:
            return self.plant.state()


def graph_info(plant):
    s, g = plant.sim, plant.g
    nodes = []
    for n, v in g.nodes.items():
        d = {"id": n, "kind": v["kind"], "layer": v.get("layer"), "model": v.get("model"), "note": v.get("note")}
        if n in s.movers:
            mv = s.movers[n]
            d.update({"t_h": mv.t_h, "t_h_basis": mv.t_h_basis, "kw": mv.kw, "v": mv.v, "length_m": mv.length})
        if n in s.stores:
            d["cap_t"] = s.stores[n].cap
        nodes.append(d)
    edges = [{"id": f"{e['from']}->{e['to']}", "from": e["from"], "to": e["to"], "gates": e["gates"],
              "alt_gates": e.get("alt_gates", []), "order": e["order"], "logic": e.get("gate_logic", "all")} for e in g.edges]
    routes = [{"index": i, "id": g.describe(r), "category": g.category(r), "nodes": g.route_nodes(r)}
              for i, r in enumerate(plant.routes_all)]
    P = s.P
    est = {n: {"value": d["value"], "basis": d["basis"], "src": d["src"]} for n, d in P["t_h_missing"]["nodes"].items()}
    return {"nodes": nodes, "edges": edges, "gates": sorted(s.gates), "routes": routes, "t_h_estimates": est,
            "separator": {"nodes": P["separator"]["nodes"], "base": P["separator"]["base_moisture_pct"]["value"],
                          "derate": P["separator"]["derate_pct_per_pct"]["value"]},
            "speed_presets": P["sim"]["speed_presets"]["value"], "dt": s.dt}


def make_handler(engine):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else body.encode("utf-8")
            try:
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                pass                                   # the page was closed mid-answer: nothing to answer to

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False))

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/state":
                return self._json(engine.state())
            if path == "/graph":
                with engine.lock:
                    return self._json(graph_info(engine.plant))
            if path == "/mnemo.svg":
                with engine.lock:
                    return self._send(200, mnemo.build_svg(engine.plant.g), TYPES[".svg"])
            if path == "/scenarios":
                out = []
                for n in scn.all_scenarios():
                    sc = scn.load(n)
                    out.append({"id": n, "title": sc["title"], "description": sc["description"], "until_s": sc["until_s"]})
                return self._json(out)
            name = "index.html" if path in ("/", "") else path.lstrip("/")
            f = (PANEL / name).resolve()
            if PANEL.resolve() not in f.parents or not f.is_file():
                return self._send(404, "not found", "text/plain; charset=utf-8")
            return self._send(200, f.read_bytes(), TYPES.get(f.suffix, "application/octet-stream"))

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                return self._json({"ok": False, "reason": "не JSON"}, 400)
            if self.path == "/cmd":
                return self._json(engine.cmd(body))
            if self.path == "/scenario":
                sid = body.get("id")
                if sid and sid not in scn.all_scenarios():
                    return self._json({"ok": False, "reason": f"немає сценарію {sid}"}, 404)
                engine.load(sid)
                return self._json({"ok": True, "reason": ""})
            return self._json({"ok": False, "reason": "невідомий шлях"}, 404)
    return H


def serve(port=8765, scenario=None, block=True):
    engine = Engine(scenario)
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(engine))
    threading.Thread(target=engine.tick_loop, daemon=True).start()
    if not block:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv, engine
    print(f"пульт: http://127.0.0.1:{srv.server_address[1]}/", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop = True
    return srv, engine


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--scenario", default=None)
    a = ap.parse_args()
    serve(a.port, a.scenario)


if __name__ == "__main__":
    main()
