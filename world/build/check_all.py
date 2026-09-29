"""Run every world/build/check_*.py in Blender and print one summary. Required before every commit.

Run (plain Python, not inside Blender):
    python world/build/check_all.py [--jobs 3] [--only noria,tower]
Blender: $BLENDER or the default Windows install path. Exit code 1 when any check fails or crashes.
"""

import argparse
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLENDER = os.environ.get("BLENDER", r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe")


def run(path):
    t = time.time()
    p = subprocess.run([BLENDER, "--background", "--python", str(path)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=HERE.parents[1])
    lines = p.stdout.splitlines()
    fails = [ln for ln in lines if ln.startswith("FAIL")]
    result = next((ln for ln in lines if ln.startswith("RESULT")), None)
    crash = [ln for ln in (p.stdout + p.stderr).splitlines() if "Traceback" in ln or "Error" in ln][:3]
    ok = p.returncode == 0 and result == "RESULT ALL PASS"
    warns = [ln for ln in lines if ln.startswith("PASS") and re.search(r": WARN|— WARN", ln)]
    return path.stem, ok, time.time() - t, sum(ln.startswith(("PASS", "FAIL")) for ln in lines), fails, warns, crash


def main():
    sys.stdout.reconfigure(errors="replace")     # a FAIL line with a symbol the console code page lacks must not crash the summary
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    only = {f"check_{n.strip()}" for n in a.only.split(",") if n.strip()}
    checks = [p for p in sorted(HERE.glob("check_*.py")) if p.stem != "check_all" and (not only or p.stem in only)]
    with ThreadPoolExecutor(a.jobs) as ex:
        results = list(ex.map(run, checks))
    bad = 0
    for name, ok, sec, n, fails, warns, crash in results:
        bad += not ok
        print(f"{'ALL PASS' if ok else 'FAILED  '}  {name:<24} {n:>3} cases  {sec:6.1f} s" + (f"  {len(warns)} WARN" if warns else ""))
        for ln in fails + crash:
            print(f"          {ln[:160]}")
    print(f"\n{len(results) - bad}/{len(results)} checks pass")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
