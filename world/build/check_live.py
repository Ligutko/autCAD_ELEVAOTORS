"""Check of the live scene (CONTROL_CENTER_SPEC.md §6.2): the Blender model follows the simulator state.

    blender --background --python world/build/check_live.py

Builds the site once (quick), adds the live layer (kit/live.py) and checks it against numbers taken here
independently of it: SITE positions, the process graph, the heap volume of the mass, the derived geometry.
Every rule is a function of its inputs, so each broken variant feeds a broken input without a rebuild.
"""

import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy  # noqa: I001

WORLD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORLD))

from kit import live as lv  # noqa: E402
from kit import process as pr  # noqa: E402
from sim import core  # noqa: E402
from sim.control import Plant  # noqa: E402
from sim.derive_geometry import derive  # noqa: E402
from sim.scenario import Runner, load  # noqa: E402

G = pr.Graph()
P = core.load_params()
RHO = P["grain"]["bulk_density_t_m3"]["value"]


def build():
    spec = importlib.util.spec_from_file_location("site_scene", str(WORLD / "build" / "site.py"))
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    scene, site, _, _, _ = S.assemble(quick=True)
    return scene, site


# ------------------------------------------------------------------ rules

def r_geometry(file_data, now):
    bad = []
    for n, m in now["movers"].items():
        f = file_data["movers"].get(n)
        key = "lift_m" if "lift_m" in m else "run_m"
        if f is None or abs(f.get(key, -1) - m[key]) > 1e-3:
            bad.append((n, f and f.get(key), m[key]))
    for k in ("r_in_m", "wall_top_m", "repose_deg"):
        if abs(file_data["silo"][k] - now["silo"][k]) > 1e-4:
            bad.append((k, file_data["silo"][k], now["silo"][k]))
    return not bad, bad[:4] or f"world/sim/geometry.json = the kits now ({len(now['movers'])} movers, silo)"


def r_nodes(node_map):
    bare = [n for n in G.nodes if not node_map.get(n) and n not in lv.NO_BODY]
    claimed = [n for n in lv.NO_BODY if node_map.get(n)]
    owners = {}
    for n, objs in node_map.items():
        for o in objs:
            owners.setdefault(o, []).append(n)
    shared = {o: ns for o, ns in owners.items() if len(ns) > 1 and set(ns) != {"SCALES_IN", "SCALES_OUT"}}
    ok = not bare and not claimed and not shared
    return ok, (f"no objects {bare}; NO_BODY with objects {claimed}; shared {list(shared.items())[:3]}" if not ok else
                f"{len(G.nodes) - len(lv.NO_BODY)} nodes have their objects, {len(lv.NO_BODY)} have none by reason "
                f"({', '.join(lv.NO_BODY)}); only the two scales share the scale decks")


PARTS_PER = {"tunnel": 4, "dist": 3, "gallery": 2}   # loose parts per opening / branch / drop, as the kits build them:
                                                    # ТЗА + ТЗР + rack housing + motor; gate + housing + motor; gate + housing


def _centre(o):
    mw = o.matrix_world
    vs = [mw @ v.co for v in o.data.vertices]
    return sum(vs, vs[0] * 0) / len(vs)


def r_gates(scene, site, by_gate, loose, count):
    """Every gate the model has is cut out whole: the expected number of parts, each silo gate under its silo."""
    fam = lv.gate_points(site)
    expect = {}
    for f, kinds in fam.items():
        per = PARTS_PER[f.split(":")[0]]
        for g, pts in kinds["gates"].items():
            places = len(pts) // 2                        # two centres per place: the gate box and its housing
            expect[g] = expect.get(g, 0) + per * places
    got = {g: len(v) for g, v in by_gate.items()}
    counts = {g: (got.get(g, 0), n) for g, n in expect.items() if got.get(g, 0) != n}
    lost = {k: v for k, v in count.items() if v[0] != v[1]}
    silos = {s["id"]: s for s in site["silos"]}
    wrong = []
    for gid, objs in by_gate.items():
        sid = gid.split(".")[0]
        if sid not in silos:
            continue
        for o in objs:
            dx = abs(_centre(o).x - silos[sid]["x"])
            if (gid.endswith(".c") and dx > 0.7) or (gid.endswith(".s") and not 0.7 < dx < 11.0):
                wrong.append((gid, round(dx, 2)))
    unmod = sorted(set(G.gates()) - set(expect))
    ok = not counts and not loose and not lost and not wrong
    return ok, (f"parts {list(counts.items())[:4]} loose {loose[:3]} lost {lost} wrong {wrong[:3]}" if not ok else
                f"{len(by_gate)} gates cut out whole ({sum(got.values())} parts = 4 per tunnel opening, 3 per splitter branch, "
                f"2 per gallery drop; vertices kept); silo gates under their silos; {len(unmod)} gates of the graph have no "
                f"body in the model: {', '.join(unmod)}")


def glow_set(scene):
    return {o.name for o in scene.objects if (o.get(lv.ON) or 0) > 0}


def r_glow(live, scene):
    """Only H5 runs and gate 6.6 is open: exactly their objects glow; then all off: nothing glows."""
    p = Plant()
    st = p.state()
    st["motors"]["H5"]["state"] = "run"
    st["gates"]["6.6"]["state"] = "open"
    live.last.clear()
    live.apply(st)
    got = glow_set(scene)
    want = {o.name for o in live.objs("H5")} | {o.name for o in live.gates.get("6.6", [])}
    st["motors"]["H5"]["state"] = "off"
    st["gates"]["6.6"]["state"] = "closed"
    live.apply(st)
    after = glow_set(scene)
    ok = got == want and not after and len(want) > 3
    return ok, (f"H5 run + 6.6 open: {len(got)} objects glow, expected {len(want)}; extra {sorted(got - want)[:3]}, "
                f"missing {sorted(want - got)[:3]}; after stop {len(after)} glow")


def visible_flows(live):
    return {owner for owner, objs in live.flows.items() if objs and not objs[0].hide_viewport}


def r_flow(live):
    """Grain from S1 through T9 into H5 and on to T8: the tubes shown are exactly the moving edges and movers."""
    p = Plant()
    st = p.state()
    st["edges"] = {"S1->T9": {"t_h": 100.0}, "T9->H5": {"t_h": 100.0}, "H5->T8": {"t_h": 100.0}}
    for m in ("T9", "H5"):
        st["motors"][m]["load_t_h"] = 100.0
    live.last.clear()
    live.apply(st)
    got = visible_flows(live)
    want = {k for k in ("S1->T9", "T9->H5", "H5->T8", "T9", "H5") if live.flows.get(k)}
    ok = got == want and len(want) == 5
    no_path = sorted(live.flow_fails)
    return ok, (f"shown {sorted(got)}, expected {sorted(want)}; " + (f"— WARN {len(no_path)} edges have no grain path in "
                f"routes.py (not drawn, not invented): {', '.join(no_path)}" if no_path else "every edge has a path"))


def mesh_volume(o):
    bm = bmesh.new()
    bm.from_object(o, bpy.context.evaluated_depsgraph_get())
    bm.transform(o.matrix_world)
    v = bm.calc_volume(signed=False)
    bm.free()
    return v


def r_heap(live, set_heap=lv.set_heap, rho_used=None):
    """S1 at a third and at full: the heap volume = mass / 0.75 t/m3 (±1 %), the top where the heap model puts it."""
    bad = []
    for mass in (300.0, 1600.0, 4700.0):
        pair = live.heaps["S1"]
        top = set_heap(pair, mass, rho_used or RHO, live.base_z["S1"])
        bpy.context.view_layer.update()
        vol = sum(mesh_volume(o) for o in pair if not o.hide_viewport)
        want = mass / RHO
        if abs(vol - want) > 0.01 * want:
            bad.append((mass, round(vol, 1), round(want, 1)))
        if top > GEOM_SILO["wall_top_m"] + GEOM_SILO["r_in_m"] * math.tan(math.radians(GEOM_SILO["repose_deg"])) + 0.05:
            bad.append((mass, "top over the roof", round(top, 2)))
    return not bad, bad or "heap volume = mass / 0.75 at 300, 1600, 4700 t (±1 %), top under the roof"


def r_speed(live):
    """Applying the states of a running scenario costs little: a panel update every 0.2 s must not stall Blender."""
    r = Runner(load("wet_season"))
    times, touched = [], 0
    live.last.clear()
    for k in range(240):
        for _ in range(60):
            r.tick()
        t = time.perf_counter()
        touched += live.apply(r.plant.state())
        times.append(time.perf_counter() - t)
    avg, worst = 1000 * sum(times) / len(times), 1000 * max(times)
    return avg < 20 and worst < 200, f"240 states of wet_season: {avg:.1f} ms average, {worst:.0f} ms worst (≤ 20 / 200), {touched} object updates"


def r_trees(scene, merged, locs):
    """Every tree of the belts sits inside a merged chunk (bounding box + 6 m of crown) and the 55 k instances are
    out of the view layer."""
    boxes = []
    for o in merged:
        bb = [o.matrix_world @ __import__("mathutils").Vector(c) for c in o.bound_box]
        boxes.append((min(v.x for v in bb) - 6, min(v.y for v in bb) - 6, max(v.x for v in bb) + 6, max(v.y for v in bb) + 6))
    out = [p for p in locs if not any(b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3] for b in boxes)]
    lc = bpy.context.view_layer.layer_collection.children.get("TREES")
    hidden = lc is not None and lc.exclude
    ok = not out and hidden and len(locs) > 50000
    return ok, (f"{len(locs)} trees, {len(out)} outside every merged chunk, instances excluded {hidden}, "
                f"{len(merged)} merged meshes, {sum(len(o.data.polygons) for o in merged)} faces")


GEOM_SILO = None
MERGED, LOCS = [], []


def main():
    global GEOM_SILO
    t = time.time()
    scene, site = build()
    file_data = json.loads((WORLD / "sim" / "geometry.json").read_text(encoding="utf-8"))
    now = derive(site)
    GEOM_SILO = now["silo"]
    live = lv.Live(scene, site, RHO)
    global MERGED, LOCS
    LOCS = [tuple(o.matrix_world.translation)[:2] for o in scene.objects if o.name.startswith("TREE.")]
    lv.trees_merge(scene)
    MERGED = [o for o in scene.objects if o.name.startswith("LIVE_TREES_")]
    print(f"built in {time.time() - t:.0f} s", flush=True)
    rules = [
        ("geometry.json matches the kits", lambda: r_geometry(file_data, now)),
        ("every node has its objects or a reason", lambda: r_nodes(live.nodes)),
        ("gates cut out whole, each under its silo / on its branch", lambda: r_gates(scene, site, live.gates, live.gate_loose, live.gate_count)),
        ("exactly the running and open glow", lambda: r_glow(live, scene)),
        ("flow tubes exactly where grain moves", lambda: r_flow(live)),
        ("heap volume = mass / density", lambda: r_heap(live)),
        ("state updates are cheap", lambda: r_speed(live)),
        ("after a whole scenario the glow still follows the state", lambda: r_glow(live, scene)),
        ("trees merged for the viewport, none lost", lambda: r_trees(scene, MERGED, LOCS)),
    ]
    ok_all = True
    for name, fn in rules:
        try:
            ok, info = fn()
        except Exception as e:                           # noqa: BLE001
            ok, info = False, f"crash {type(e).__name__}: {e}"
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)

    # ---- broken variants: each must fail on its own rule
    tampered = json.loads(json.dumps(file_data))
    tampered["movers"]["T8"]["run_m"] += 1.0
    no_h6 = {k: (v if k != "H6" else []) for k, v in live.nodes.items()}
    swapped = dict(live.gates)
    swapped["S1.c"], swapped["S2.c"] = live.gates["S2.c"], live.gates["S1.c"]

    def glow_all_norias(orig):
        def objs(node):
            return orig("H5") + orig("H6") if node == "H5" else orig(node)
        return objs

    def show_everything(owner_set):
        return set(live.flows)

    variants = [
        ("geometry.json edited by hand (T8 +1 m)", lambda: r_geometry(tampered, now)),
        ("H6 lost its objects", lambda: r_nodes(no_h6)),
        ("S1.c and S2.c parts swapped", lambda: r_gates(scene, site, swapped, live.gate_loose, live.gate_count)),
        ("a part left without a gate", lambda: r_gates(scene, site, live.gates, live.gate_loose + [("GATE_NONE_x", 0.3)], live.gate_count)),
    ]
    orig_objs = live.objs
    live.objs = glow_all_norias(orig_objs)
    variants_glow = [("H5 glow spills to H6", lambda: r_glow(live, scene))]
    ok_v = True
    for name, fn in variants + variants_glow:
        try:
            ok, info = fn()
        except Exception as e:                           # noqa: BLE001
            ok, info = False, f"crash {type(e).__name__}: {e}"
        ok_v &= not ok
        print(f"{'PASS' if not ok else 'FAIL'}  broken variant must be rejected — {name} -> {'failed' if not ok else 'passed'} ({str(info)[:140]})", flush=True)
    live.objs = orig_objs
    live.apply(Plant().state())

    # flows shown for idle edges
    orig_apply = live.apply

    def apply_all_flows(st):
        k = orig_apply(st)
        for objs in live.flows.values():
            for o in objs:
                o.hide_viewport = False
        return k
    live.apply = apply_all_flows
    ok, info = r_flow(live)
    ok_v &= not ok
    print(f"{'PASS' if not ok else 'FAIL'}  broken variant must be rejected — tubes shown on idle edges -> {'failed' if not ok else 'passed'} ({str(info)[:140]})", flush=True)
    live.apply = orig_apply
    live.last.clear()
    live.apply(Plant().state())

    ok, info = r_heap(live, rho_used=0.8)
    ok_v &= not ok
    print(f"{'PASS' if not ok else 'FAIL'}  broken variant must be rejected — heap sized with 0.8 t/m3 -> {'failed' if not ok else 'passed'} ({str(info)[:140]})", flush=True)

    def slow_apply(st):
        time.sleep(0.03)
        return orig_apply(st)
    live.apply = slow_apply
    ok, info = r_speed(live)
    ok_v &= not ok
    print(f"{'PASS' if not ok else 'FAIL'}  broken variant must be rejected — 30 ms per state -> {'failed' if not ok else 'passed'} ({str(info)[:140]})", flush=True)
    live.apply = orig_apply

    last_x = max(MERGED, key=lambda o: max((o.matrix_world @ __import__("mathutils").Vector(c)).x for c in o.bound_box))
    lost = [o for o in MERGED if o.name.split("_")[2] != last_x.name.split("_")[2]]
    ok, info = r_trees(scene, lost, LOCS)
    ok_v &= not ok
    print(f"{'PASS' if not ok else 'FAIL'}  broken variant must be rejected — the easternmost chunk of trees lost -> {'failed' if not ok else 'passed'} ({str(info)[:140]})", flush=True)

    print("RESULT", "ALL PASS" if ok_all and ok_v else "FAILED", flush=True)
    sys.exit(0 if ok_all and ok_v else 1)


if __name__ == "__main__":
    main()
