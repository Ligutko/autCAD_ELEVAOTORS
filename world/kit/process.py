"""Phase 7A: process graph of the drawn facility (SITE.json `process`, `equipment`).

Plain Python, no bpy: the simulator and the Blender scenes read the same graph.

Nodes are SITE ids (T7, H5, S1, ...). An edge carries the gates that must be open for grain to pass
(`gate_logic` "any": one of them is enough) and `order`, its place along the source conveyor:
a chain conveyor drops everything into the first open outlet along its run (1 = intermediate gate,
2 = drive section), a 45° splitter (`via` SPL*) shares the grain between its open gates.

Routes: every simple path from a source (a node nobody feeds, or a silo) to a sink (a node that feeds
nothing, or a silo). A silo is both: grain leaves it through the tunnel and can come back to it.
"""

import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

SITE_JSON = Path(__file__).resolve().parents[1] / "site" / "SITE.json"
MOVERS = ("noria", "conveyor", "conveyor_chain", "conveyor_belt")
UNITS = ("dryer",)                       # process units with a capacity but no place in the start order


@lru_cache(maxsize=1)
def _site():
    return json.loads(SITE_JSON.read_text(encoding="utf-8"))


class Graph:
    def __init__(self, site=None):
        site = site or _site()
        self.site = site
        p = site["process"]
        self.nodes = {n["id"]: n for n in p["nodes"]}
        self.edges = p["edges"]
        self.out = defaultdict(list)
        self.inn = defaultdict(list)
        for e in self.edges:
            self.out[e["from"]].append(e)
            self.inn[e["to"]].append(e)
        self.equipment = {m["id"]: m for m in site["equipment"]["items"]}

    # ------------------------------------------------------------ structure
    def is_silo(self, n):
        return self.nodes[n]["kind"] == "silo"

    def sources(self):
        return [n for n in self.nodes if not self.inn[n] or self.is_silo(n)]

    def sinks(self):
        return [n for n in self.nodes if not self.out[n] or self.is_silo(n)]

    def gates(self):
        return sorted({g for e in self.edges for g in e["gates"] + e.get("alt_gates", [])})

    # ------------------------------------------------------------ flow
    @staticmethod
    def passable(e, open_gates):
        if not e["gates"]:
            return True
        test = any if e.get("gate_logic") == "any" else all
        return test(g in open_gates for g in e["gates"])

    def flow(self, source, open_gates, q=1.0):
        """Share of the grain from `source` arriving at each sink; 'blocked:<node>' where it has
        nowhere to go. Grain that reaches a silo stays there (unless the silo is the source)."""
        got = defaultdict(float)

        def push(n, q, seen):
            live = [e for e in self.out[n] if self.passable(e, open_gates)]
            if not live:
                got[f"blocked:{n}"] += q
                return
            first = min(e["order"] for e in live)
            live = [e for e in live if e["order"] == first]
            for e in live:
                m, share = e["to"], q / len(live)
                if self.is_silo(m) or not self.out[m]:
                    got[m] += share                 # a silo keeps what it gets, also its own grain back
                elif m in seen:
                    got[f"loop:{m}"] += share
                else:
                    push(m, share, seen | {m})

        push(source, q, {source})
        return dict(got)

    # ------------------------------------------------------------ routes
    def routes(self):
        """All simple paths source -> sink as lists of edges."""
        out = []

        def walk(n, path, seen):
            for e in self.out[n]:
                m = e["to"]
                if self.is_silo(m) or not self.out[m]:
                    out.append(path + [e])
                elif m not in seen:
                    walk(m, path + [e], seen | {m})

        for s in self.sources():
            walk(s, [], {s})
        return out

    @staticmethod
    def route_nodes(route):
        return [route[0]["from"]] + [e["to"] for e in route]

    @staticmethod
    def route_gates(route):
        """Gates to open. `any` edges need just their first gate."""
        g = []
        for e in route:
            g += e["gates"][:1] if e.get("gate_logic") == "any" else e["gates"]
        return g

    def route_motors(self, route):
        """Motors along the grain flow. Start = reversed (downstream first, against the grain);
        stop = this order (upstream first, each one runs empty before the next stops)."""
        return [n for n in self.route_nodes(route) if self.nodes[n]["kind"] in MOVERS]

    def start_order(self, route):
        return list(reversed(self.route_motors(route)))

    def trip(self, route, motor):
        """Emergency stop of `motor` on `route`: (stop now = it and everything feeding it,
        run empty = everything downstream, which clears the grain it already carries)."""
        m = self.route_motors(route)
        k = m.index(motor)
        return m[:k + 1], m[k + 1:]

    def bottleneck(self, route, caps=None):
        """(t/h, node) of the smallest known capacity (movers and process units), and the movers
        with no number."""
        caps = caps or {}
        known, unknown = [], []
        for n in self.route_nodes(route):
            if self.nodes[n]["kind"] not in MOVERS + UNITS:
                continue
            t = caps.get(n, self.nodes[n].get("t_h"))
            (known if t is not None else unknown).append((t, n))
        return (min(known) if known else (None, None)), [n for _, n in unknown]

    def category(self, route):
        a, b = route[0]["from"], route[-1]["to"]
        if any(self.nodes[n]["kind"] == "dryer" for n in self.route_nodes(route)):
            return "dry"
        if self.is_silo(a) and a == b:
            return "recirculate"
        if self.is_silo(a) and self.is_silo(b):
            return "transfer"
        if self.is_silo(a):
            return "unload"
        return "receive" if self.is_silo(b) else "pass"

    def describe(self, route):
        return " -> ".join(self.route_nodes(route))
