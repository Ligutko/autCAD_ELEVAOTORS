"""Control center: scenarios (world/sim/scenarios/*.json) — timed commands for a repeatable demonstration.

    {"id", "title", "description", "until_s",
     "events": [{"t_s": 0, "cmd": {...}}, ...],          # commands of control.Plant.cmd
     "expect": [{"what": ..., ...}, ...]}                 # checked by check_sim.py

Run:  python world/sim/scenario.py world/sim/scenarios/receive_s1.json      # prints the journal and the result
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim.control import Plant  # noqa: E402

SCEN = Path(__file__).resolve().parent / "scenarios"


def load(name_or_path):
    p = Path(name_or_path)
    if not p.exists():
        p = SCEN / f"{name_or_path}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def all_scenarios():
    return sorted(p.stem for p in SCEN.glob("*.json"))


class Runner:
    """Feeds the timed commands of a scenario into a Plant as time goes."""

    def __init__(self, sc, plant=None, **kw):
        self.sc = sc
        self.plant = plant or Plant(**kw)
        self.plant.scenario = sc["id"]
        self.queue = sorted(sc["events"], key=lambda e: e["t_s"])
        self.answers = []

    def due(self):
        t = self.plant.sim.t
        while self.queue and self.queue[0]["t_s"] <= t + 1e-9:
            ev = self.queue.pop(0)
            self.answers.append((ev["t_s"], ev["cmd"], self.plant.cmd(ev["cmd"])))

    def tick(self):
        self.due()
        self.plant.tick()

    def run(self, until_s=None):
        until_s = self.sc["until_s"] if until_s is None else until_s
        while self.plant.sim.t < until_s - 1e-9:
            self.tick()
        self.due()
        return self.plant


def run(name_or_path, **kw):
    sc = load(name_or_path)
    r = Runner(sc, **kw)
    r.run()
    return sc, r


def main():
    sc, r = run(sys.argv[1])
    p = r.plant
    for e in p.sim.events:
        print(f"{e['t_s'] / 3600:7.3f} h  {e['kind']:6s} {e['text']}")
    st = p.state()
    print("stores", {k: v["mass_t"] for k, v in st["stores"].items() if v["mass_t"] > 0})
    print("totals", st["totals"], "balance", p.sim.balance())
    print("journal", p.journal_hash()[:16])


if __name__ == "__main__":
    main()
