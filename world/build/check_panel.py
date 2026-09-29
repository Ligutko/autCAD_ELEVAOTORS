"""Check of the control center panel: the schematic, the server API, the browser (CONTROL_CENTER_SPEC.md §4.2).

Plain Python; check_all runs it in Blender. The browser part runs world/panel/browser_check.py with the system
Python (Playwright); if there is none, that rule is a WARN, not a pass.
    python world/build/check_panel.py
Each rule has a broken variant that must fail on it.
"""

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from contextlib import ExitStack, contextmanager
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORLD))

from kit import process as pr  # noqa: E402
from panel import mnemo  # noqa: E402
from sim import schema  # noqa: E402
from sim import server  # noqa: E402
from sim.control import Plant  # noqa: E402
from sim.core import Sim  # noqa: E402

G = pr.Graph()
STORES = sorted(Sim().stores)
SVGNS = "{http://www.w3.org/2000/svg}"
TOL = 3.0


@contextmanager
def patched(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def svg_ids(svg):
    root = ET.fromstring(svg)
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    return root, ids


def all_gates():
    return sorted({g for e in G.edges for g in e["gates"] + e.get("alt_gates", [])})


# ------------------------------------------------------------------ schematic

def r_coverage(lay=None):
    try:
        svg = mnemo.build_svg(G, lay)
    except KeyError as e:
        return False, f"schematic not built: no layout for {e}"
    _, ids = svg_ids(svg)
    want = [f"n-{n}" for n in G.nodes] + [f"e-{e['from']}->{e['to']}" for e in G.edges] + [f"g-{g}" for g in all_gates()]
    want += [f"lvl-{n}" for n in STORES]                   # every store of the simulator shows its level
    want += [f"e-{e['from']}->{e['to']}~alt" for e in G.edges if e.get("alt_gates")]
    missing = [i for i in want if i not in ids]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    stray = [i for i in ids if i.startswith(("n-", "g-")) and i not in want]
    ok = not missing and not dup and not stray
    return ok, (f"missing {missing[:5]} dup {dup[:5]} stray {stray[:5]}" if not ok else
                f"{len(G.nodes)} nodes, {len(G.edges)} lines, {len(all_gates())} gates, levels of every store: each once")


def _inside(p, box, tol=TOL):
    x0, y0, x1, y1 = box
    return x0 - tol <= p[0] <= x1 + tol and y0 - tol <= p[1] <= y1 + tol


def r_lines_connect(lay=None):
    lay = lay or mnemo.load_layout()
    bad = []
    for e in G.edges:
        pts = mnemo.edge_points(lay, e)
        if not _inside(pts[0], mnemo.bbox(lay["nodes"][e["from"]])) or not _inside(pts[-1], mnemo.bbox(lay["nodes"][e["to"]])):
            bad.append(f"{e['from']}->{e['to']} {pts[0]}..{pts[-1]}")
        if e.get("alt_gates"):                      # the side branch leaves the silo and joins the main line
            alt = mnemo.alt_points(lay, e)
            joins = min(_dist_seg(alt[-1], a, b) for a, b in zip(pts, pts[1:]))
            if not _inside(alt[0], mnemo.bbox(lay["nodes"][e["from"]])) or joins > TOL:
                bad.append(f"{e['from']}->{e['to']} side branch {alt[0]}..{alt[-1]}")
    return not bad, bad[:4] or f"every grain line starts on its source symbol and ends on its target ({len(G.edges)})"


def _dist_seg(p, a, b):
    ax, ay = a
    bx, by = b
    L2 = (bx - ax) ** 2 + (by - ay) ** 2
    t = 0 if L2 == 0 else max(0, min(1, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / L2))
    return math.dist(p, (ax + t * (bx - ax), ay + t * (by - ay)))


def r_gates_on_lines(lay=None):
    lay = lay or mnemo.load_layout()
    root, _ = svg_ids(mnemo.build_svg(G, lay))
    bad = []
    for gid in all_gates():
        el = next(x for x in root.iter() if x.get("id") == f"g-{gid}")
        c = next(x for x in el.iter() if x.tag == SVGNS + "circle")
        p = (float(c.get("cx")), float(c.get("cy")))
        lines = [mnemo.edge_points(lay, e) for e in G.edges if gid in e["gates"]]
        lines += [mnemo.alt_points(lay, e) for e in G.edges if gid in e.get("alt_gates", [])]
        d = min(min(_dist_seg(p, a, b) for a, b in zip(pts, pts[1:])) for pts in lines)
        if d > TOL:
            bad.append(f"{gid} {d:.0f} px off")
    return not bad, bad[:4] or f"every gate symbol sits on a line that carries it ({len(all_gates())})"


# ------------------------------------------------------------------ server

class Srv:
    def __init__(self, scenario=None):
        self.srv, self.eng = server.serve(0, scenario, block=False)
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            return r.status, r.read()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def state(self):
        return json.loads(self.get("/state")[1])

    def close(self):
        self.eng.stop = True
        self.srv.shutdown()
        self.srv.server_close()


def r_api():
    s = Srv()
    try:
        st = s.state()
        errs = schema.validate(st)
        gr = json.loads(s.get("/graph")[1])
        g_ok = {n["id"] for n in gr["nodes"]} == set(G.nodes) and len(gr["edges"]) == len(G.edges) and len(gr["routes"]) == len(G.routes())
        a = s.post("/cmd", {"op": "gate", "id": "6.9", "action": "open"})
        s.post("/cmd", {"op": "speed", "value": 60})
        t0 = time.time()
        while time.time() - t0 < 5 and s.state()["gates"]["6.9"]["state"] != "open":
            time.sleep(0.1)
        g69 = s.state()["gates"]["6.9"]["state"]
        rej = s.post("/cmd", {"op": "motor", "id": "H5", "action": "start"})
        sc = s.post("/scenario", {"id": "receive_s1"})
        st2 = s.state()
        ok = not errs and g_ok and a["ok"] and g69 == "open" and not rej["ok"] and rej["reason"] and sc["ok"] and st2["scenario"] == "receive_s1"
        return ok, (f"schema errors {errs[:2]}; /graph complete {g_ok}; gate 6.9 -> {g69}; H5 start rejected: {rej['reason'][:60]!r}; "
                    f"scenario loaded {st2['scenario']}")
    finally:
        s.close()


def r_clock():
    s = Srv()
    try:
        s.post("/cmd", {"op": "speed", "value": 600})
        a, t0 = s.state()["t_s"], time.time()
        time.sleep(1.5)
        b, t1 = s.state()["t_s"], time.time()
        rate = (b - a) / (t1 - t0)
        s.post("/cmd", {"op": "pause", "value": True})
        time.sleep(0.2)
        c = s.state()["t_s"]
        time.sleep(0.8)
        d = s.state()["t_s"]
        ok = 0.8 * 600 <= rate <= 1.2 * 600 and d == c
        return ok, f"×600: {rate:.0f} simulated s per wall s (±20 %); paused: {c} -> {d}"
    finally:
        s.close()


def r_static_only():
    s = Srv()
    try:
        bad = []
        for path in ("/../sim/params.json", "/%2e%2e/sim/params.json", "/..%2fsim%2fparams.json", "/nope.js"):
            try:
                code, _ = s.get(path)
                bad.append(f"{path} -> {code}")
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    bad.append(f"{path} -> {e.code}")
        code, body = s.get("/panel.js")
        return not bad and code == 200, bad or "only files of world/panel are served (4 escapes -> 404)"
    finally:
        s.close()


def r_browser():
    py = shutil.which("python") or shutil.which("py")
    if not py:
        return True, "WARN: no system Python for the browser check"
    probe = subprocess.run([py, "-c", "import playwright"], capture_output=True)
    if probe.returncode:
        return True, "WARN: no Playwright in the system Python"
    s = Srv()
    try:
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        p = subprocess.run([py, str(WORLD / "panel" / "browser_check.py"), s.base], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120, env=env)
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("{")), None)
        if line is None:
            return False, f"browser check crashed: {(p.stderr or p.stdout)[-300:]}"
        r = json.loads(line)
        ok = (set(r["nodes"]) == set(G.nodes) and set(r["gates"]) == set(all_gates()) and " open" in f" {r['gate_after_click']}"
              and "Відмова" in r["toast"] and not r["page_errors"])
        return ok, (f"page rendered {len(r['nodes'])} nodes, {len(r['gates'])} gates; click on 6.9 -> {r['gate_after_click']!r}; "
                    f"rejected start shows {r['toast'][:60]!r}; page errors {r['page_errors'][:2]}")
    finally:
        s.close()


RULES = {
    "every node, line and gate on the schematic once": r_coverage,
    "lines start and end on their symbols": r_lines_connect,
    "gates sit on their lines": r_gates_on_lines,
    "API: state contract, graph, commands, rejection, scenario": r_api,
    "clock: speed ×600 and pause": r_clock,
    "server serves world/panel only": r_static_only,
    "browser: schematic, gate click, rejection shown": r_browser,
}


def broken():
    lay = mnemo.load_layout()

    def lay_without(node):
        q = json.loads(json.dumps(lay))
        q["nodes"].pop(node)
        return q

    def lay_edge(key, **kw):
        q = json.loads(json.dumps(lay))
        q["edges"].setdefault(key, {}).update(kw)
        return q

    def lay_gate(key, gid, pos):
        q = json.loads(json.dumps(lay))
        q["edges"][key].setdefault("gate_pos", {})[gid] = pos
        return q

    orig_build = mnemo.build_svg

    def no_alt(graph, lay_=None):
        class NoAlt:
            nodes = graph.nodes
            edges = [dict(e, alt_gates=[]) for e in graph.edges]
        return orig_build(NoAlt, lay_)

    def state_without_stores(orig):
        def f(self, events=60):
            st = orig(self, events)
            del st["stores"]
            return st
        return f

    def slow_loop(orig):
        def f(self):
            p = self.plant
            real = p.speed
            while not self.stop:
                p.speed = 1.0                        # ignores the chosen speed
                time.sleep(0.02)
                with self.lock:
                    p.tick()
                p.speed = real
        return f

    def leaky_handler(orig):
        def make(engine):
            H = orig(engine)

            class Leaky(H):
                def do_GET(self):
                    path = self.path.split("?")[0]
                    if ".." in path or "%2e" in path.lower() or "%2f" in path.lower():
                        f = (server.PANEL / urllib.request.unquote(path.lstrip("/"))).resolve()
                        if f.is_file():
                            return self._send(200, f.read_bytes(), "text/plain")
                    return super().do_GET()
            return Leaky
        return make

    tmp = Path(tempfile.mkdtemp(prefix="panel_broken_"))
    for f in (WORLD / "panel").iterdir():
        if f.is_file():
            shutil.copy(f, tmp / f.name)
    js = (tmp / "panel.js").read_text(encoding="utf-8")
    (tmp / "panel.js").write_text(js.replace('e.classList.add(v.state);', '/* broken: gates never repainted */'), encoding="utf-8")

    variants = [
        ("layout without separator 5", "every node, line and gate on the schematic once",
         lambda: [], lambda: r_coverage(lay_without("SEP5"))),
        ("silo side gates not drawn", "every node, line and gate on the schematic once",
         lambda: [patched(mnemo, "build_svg", no_alt)], None),
        ("T8 -> S1 line starts off T8", "lines start and end on their symbols",
         lambda: [], lambda: r_lines_connect(lay_edge("T8->S1", from_x=1300))),
        ("gate 6.6 drawn away from its line", "gates sit on their lines",
         lambda: [], lambda: r_gates_on_lines(lay_gate("H5->T8", "6.6", [1200, 300, "v"]))),
        ("state without stores", "API: state contract, graph, commands, rejection, scenario",
         lambda: [patched(Plant, "state", state_without_stores(Plant.state))], None),
        ("server ignores the speed", "clock: speed ×600 and pause",
         lambda: [patched(server.Engine, "tick_loop", slow_loop(server.Engine.tick_loop))], None),
        ("server serves files outside world/panel", "server serves world/panel only",
         lambda: [patched(server, "make_handler", leaky_handler(server.make_handler))], None),
        ("panel.js never repaints gates", "browser: schematic, gate click, rejection shown",
         lambda: [patched(server, "PANEL", tmp)], None),
    ]
    ok_all = True
    for name, rule, patches, call in variants:
        with ExitStack() as es:
            for cm in patches():
                es.enter_context(cm)
            try:
                ok, info = (call or RULES[rule])()
                failed = not ok or str(info).startswith("WARN")
                if str(info).startswith("WARN"):
                    info = "— WARN browser unavailable, variant not tested: " + str(info)
            except Exception as e:                   # noqa: BLE001
                failed, info = True, f"crash {type(e).__name__}: {e}"
        ok_all &= failed
        print(f"{'PASS' if failed else 'FAIL'}  broken variant must be rejected — {name}: {rule} -> "
              f"{'failed' if failed else 'passed'} ({str(info)[:150]})", flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return ok_all


def main():
    ok_all = True
    for name, fn in RULES.items():
        try:
            ok, info = fn()
        except Exception as e:                       # noqa: BLE001
            ok, info = False, f"crash {type(e).__name__}: {e}"
        ok_all &= ok
        warn = str(info).startswith("WARN")
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {'— WARN ' if warn else ''}{info}", flush=True)
    ok_all &= broken()
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
