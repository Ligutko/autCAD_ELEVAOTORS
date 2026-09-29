"""Screenshots of the panel for looking at it (Playwright, system Python): starts the server in-process,
runs a scenario at a speed, captures 1920x1080 frames.

Run:  python world/panel/shot.py <out_dir> [scenario] [speed] [seconds...]
      e.g. python world/panel/shot.py shots receive_s1 600 5 20
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

WORLD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORLD))

from playwright.sync_api import sync_playwright  # noqa: E402

from sim import server  # noqa: E402


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    scenario = sys.argv[2] if len(sys.argv) > 2 else None
    speed = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    moments = [float(x) for x in sys.argv[4:]] or [3.0]
    srv, eng = server.serve(0, scenario, block=False)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    post(base + "/cmd", {"op": "speed", "value": speed})
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto(base + "/")
        t0 = time.time()
        for k, t in enumerate(moments):
            time.sleep(max(0.0, t - (time.time() - t0)))
            st = json.loads(urllib.request.urlopen(base + "/state").read())
            f = out / f"panel_{scenario or 'free'}_{k}_{int(st['t_s'])}s.png"
            pg.screenshot(path=str(f))
            print("shot", f, "sim t", st["t_s"], flush=True)
        b.close()
    srv.shutdown()


if __name__ == "__main__":
    main()
