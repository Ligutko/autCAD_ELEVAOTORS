"""Check of the live scene (CONTROL_CENTER_SPEC.md §6.2): the Blender model follows the simulator state.

    blender --background --python world/build/check_live.py

Builds the site once (quick), adds the live layer (kit/live.py) and checks it against numbers taken here
independently of it: SITE positions, the process graph, the heap volume of the mass, the derived geometry.
Every rule is a function of its inputs, so each broken variant feeds a broken input without a rebuild.
Gate blades (C4): the ТЗА blade of every tunnel opening, moved by Live.apply from the gate "pos", against the bore
square of SITE and the blade the gate kit draws at that open fraction; what one pos change adds to apply().
Motion (kit/live_motion.py, phase 8 minimum): the grain packets are checked as the frames of a 30 Hz redraw show them —
speed of the pattern against the source of each mover, which owners move for which state, the vertices against the
paths, the cost of one step. The viewport drawing itself needs a window: build/live_probe.py and
build/live_motion_shots.py (two screenshots, the shift of the pattern measured on the pixels).
"""

import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy  # noqa: I001
import numpy as np

WORLD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORLD))

from kit import live as lv  # noqa: E402
from kit import live_motion as mo  # noqa: E402
from kit import noria_n100 as nn  # noqa: E402
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


PARTS_PER = {"tunnel": 5, "dist": 3, "gallery": 2}   # objects per opening / branch / drop, as the kits build them:
                                                    # tunnel: BODY + BLADE + MOTOR + HANDWHEELS + DARK groups (ТЗА over ТЗР);
                                                    # splitter: gate + housing + motor; gallery: gate + housing


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
            places = len(pts) // lv.PTS_PER_PLACE[f.split(":")[0]]
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
                f"{len(by_gate)} gates cut out whole ({sum(got.values())} parts = 5 groups per tunnel opening, 3 per splitter branch, "
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


# ------------------------------------------------------------------ the ТЗА blades of the tunnels

def blade_openings(scene, site):
    """{blade object name: (bore x0, x1, y0, y1, kit, pocket end)}: the bore square from SITE (tunnel row, gate
    positions and sizes), not from live.py; kit(pos) = the 3D box (x0, x1, y0, y1, z0, z1) of the blade gates.gate_tza
    draws at open fraction pos, set where tunnel.gate_stack_parts sets the gate (opening x, row y, SITE stack_z of the
    ТЗА); the pocket end = the -X end of the kit's ТЗА body (the pocket end wall)."""
    from kit import gates as gk
    out = {}
    z = site["silo_gates"]["stack_z"]["tza"][0]
    for t in site.get("tunnels", []):
        y = t["row_y"]
        side = lv.tun.walkway_side(site, t)
        for i, (x, s) in enumerate(lv.tun._gate_positions(site, t)):
            name = f"{t['id']}_GATE_{i:02d}_BLADE"
            if name not in scene.objects:
                continue
            mm = int(round(s * 1000))

            def kit(pos, mm=mm, side=side, x=x, y=y):
                v = np.asarray(gk.gate_tza(mm, pos, side)["parts"]["blade"][0], float) + (x, y, z)
                return tuple(float(q) for k in range(3) for q in (v[:, k].min(), v[:, k].max()))
            pocket_end = x + float(np.asarray(gk.gate_tza(mm, 0.0, side)["parts"]["body"][0])[:, 0].min())
            out[name] = (x - s / 2, x + s / 2, y - s / 2, y + s / 2, kit, pocket_end)
    return out


def world_box(o):
    mw = o.matrix_world
    vs = [mw @ v.co for v in o.data.vertices]
    return tuple(f(getattr(v, a) for v in vs) for a in "xyz" for f in (min, max))


def gate_state(base, gid, pos):
    st = json.loads(json.dumps(base))
    st["gates"][gid] = {"state": "closed" if pos <= 0 else ("open" if pos >= 1 else "opening"), "pos": pos}
    return st


def r_blades(live, scene, site, tol=0.001):
    """Every tunnel gate with a ТЗА blade, set alone through Live.apply: pos 0 -> the blade covers the bore whole;
    pos 1 -> the bore is free; pos 0.5 -> it covers half of the bore (±2 %); at every pos the blade is where the gate
    kit draws it at that open fraction (±1 mm in 3D: direction and stroke of gates.py). A repeated state moves nothing;
    a pos change of one gate moves only that gate's blades."""
    opening = blade_openings(scene, site)
    base = Plant().state()
    live.last.clear()
    live.apply(base)
    bad, n_bl, over = [], 0, 0.0
    gids = sorted(g for g in live.gates if any(o.name in opening for o in live.gates[g]))
    for gid in gids:
        blades = [o for o in live.gates[gid] if o.name in opening]
        n_bl += len(blades)
        for pos in (0.0, 1.0, 0.5):
            live.apply(gate_state(base, gid, pos))
            bpy.context.view_layer.update()
            for o in blades:
                x0, x1, y0, y1, kit, pocket_end = opening[o.name]
                box = world_box(o)
                bx0, bx1, by0, by1 = box[:4]
                cover = max(0.0, min(bx1, x1) - max(bx0, x0)) / (x1 - x0)
                off = max(abs(p - q) for p, q in zip(box, kit(pos)))
                if off > tol:
                    bad.append((gid, o.name, f"pos {pos}: {off * 1000:.0f} mm off the kit blade"))
                if pos == 0.0 and not (bx0 <= x0 + tol and bx1 >= x1 - tol and by0 <= y0 + tol and by1 >= y1 - tol):
                    bad.append((gid, o.name, "pos 0: bore not covered", round(cover, 3)))
                if pos == 1.0:
                    over = max(over, pocket_end - bx0)
                    if cover > tol / (x1 - x0):
                        bad.append((gid, o.name, "pos 1: bore not free", round(cover, 3)))
                if pos == 0.5 and abs(cover - 0.5) > 0.02:
                    bad.append((gid, o.name, "pos 0.5: not half", round(cover, 3)))
        live.apply(gate_state(base, gid, 0.0))
    gid = gids[0] if gids else None
    k_same = k_one = None
    if gid:
        live.apply(gate_state(base, gid, 0.3))
        k_same = live.apply(gate_state(base, gid, 0.3))
        k_one = live.apply(gate_state(base, gid, 0.4))
        live.apply(gate_state(base, gid, 0.0))
        want_one = sum(o.name in opening for o in live.gates[gid])
        if k_same != 0 or k_one != want_one:
            bad.append((gid, "touched", k_same, k_one, "expected 0 and", want_one))
    ok = not bad and len(gids) >= 2 and n_bl > 10
    finding = (f"; FINDING: at open 1 the kit's blade reaches {over * 1000:.0f} mm past the pocket end wall (gates.py "
               f"gate_tza: pocket end -w - travel + 0.03, blade end -s/2 - 0.01 - travel)" if over > tol else "")
    return ok, (bad[:4] if bad else f"{len(gids)} gates, {n_bl} ТЗА blades: pos 0 covers the bore, 1 frees it, 0.5 covers half, "
                f"each where the kit draws it (≤ 1 mm); repeated state touches {k_same}, a pos change of {gid} touches {k_one} "
                f"(its blades)" + finding)


def r_blade_cost(live, budget_ms=1.0, n=300):
    """What one gate's pos change adds to apply(): the same state applied again vs a state that moves one gate (the
    gate with the most blades: a side-opening gate of a silo moves all its openings)."""
    gid = max(sorted(live.blades), key=lambda g: len(live.blades[g]))
    base = Plant().state()
    live.last.clear()
    live.apply(base)
    same, moved = [], []
    for k in range(n):
        st = gate_state(base, gid, 0.25 + 0.5 * (k % 2))
        t = time.perf_counter()
        live.apply(st)
        moved.append(time.perf_counter() - t)
        t = time.perf_counter()
        live.apply(st)
        same.append(time.perf_counter() - t)
    live.apply(base)
    add = 1000 * (sorted(moved)[n // 2] - sorted(same)[n // 2])
    return add < budget_ms, (f"gate {gid} ({len(live.blades[gid])} blades): apply {1000 * sorted(moved)[n // 2]:.3f} ms with the move, "
                             f"{1000 * sorted(same)[n // 2]:.3f} ms without (medians of {n}); a pos change adds {add:.3f} ms (≤ {budget_ms})")


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


# ------------------------------------------------------------------ motion: grain packets along the flow lines

def expected_speed(site, n):
    """m/s of mover n from its sources, not from the simulator: the LUB table of the two detailed norias
    (noria_n100.MODELS), params.json belt_speed_m_s by kind for the others."""
    kind, layer = G.nodes[n]["kind"], G.nodes[n].get("layer")
    b = P["belt_speed_m_s"]
    if kind == "noria":
        t = next((t for t in site["noria_towers"] if t["id"] == n), None)
        return nn.MODELS[t["noria_model"]]["belt_speed"] if t else b["noria_existing"]["value"]
    if kind in ("conveyor_belt", "conveyor_chain"):
        return b[kind]["value"]
    return (b["conveyor_designed"] if layer == "designed" else b["conveyor_existing"])["value"]


def nearest_arc(pts, s, x):
    """(arc length of the point of the polyline nearest to x, its distance): plain vector geometry, none of Motion's code."""
    a, b = pts[:-1], pts[1:]
    ab = b - a
    t = np.clip(((x - a) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-12), 0.0, 1.0)
    d = np.linalg.norm(a + ab * t[:, None] - x, axis=1)
    i = int(d.argmin())
    return float(s[i] + t[i] * np.linalg.norm(ab[i])), float(d[i])


def measured_speed(motion, owner, hz=30.0, frames=31, t0=0.37):
    """Speed of the drawn pattern of `owner` in frames: follow one packet head over `frames` frames at `hz` (a
    viewport redraw rate) through the 3D points motion.dashes() returns, project them on the path, fit arc against time."""
    leg = max((i for i, lg in enumerate(motion.legs) if lg[0] == owner), key=lambda i: motion.legs[i][3])
    _, pts, s, L, _ = motion.legs[leg]
    motion.set_active({owner})
    ts = t0 + np.arange(frames) / hz
    heads = []
    for t in ts:
        li, _, _, p = motion.dashes(t)
        heads.append(sorted(nearest_arc(pts, s, x)[0] for x in p[li == leg][:, -1, :]))
    motion.set_active(())
    cur = min(heads[0], key=lambda a: abs(a - 0.3 * L))
    arcs = [cur]
    for h in heads[1:]:
        step = [a - arcs[-1] for a in h if -1e-6 <= a - arcs[-1] < 0.5]
        if not step:
            return None
        arcs.append(arcs[-1] + min(step))
    return float(np.polyfit(ts, arcs, 1)[0])


def r_motion_speed(live, site, motion=None, tol=0.015):
    """Every mover's packets run at the speed of its source (H5 2.87, H6 2.40 m/s of the LUB table, belts 2.4, chains
    0.6-0.75), seen in the frames of a 30 Hz redraw, within 1.5 %; the edges run at the EST picture speed."""
    motion = motion or live.motion
    bad, rows = [], []
    for n in sorted(x for x, v in G.nodes.items() if v["kind"] in pr.MOVERS and x in motion.owners):
        want, got = expected_speed(site, n), measured_speed(motion, n)
        rows.append(f"{n} {got:.3f}" if got else f"{n} lost")
        if got is None or abs(got - want) > tol * want:
            bad.append((n, want, None if got is None else round(got, 3)))
    e = next(o for o in sorted(motion.owners) if "->" in o)
    got_e = measured_speed(motion, e)
    if got_e is None or abs(got_e - mo.EDGE_SPEED["value"]) > tol * mo.EDGE_SPEED["value"]:
        bad.append((e, mo.EDGE_SPEED["value"], got_e))
    detail = ", ".join(rows)
    return not bad, (f"off the source: {bad}" if bad else f"measured in 30 Hz frames, m/s: {detail}; edges {got_e:.2f} = the "
                     f"{mo.EDGE_SPEED['basis']} picture speed {mo.EDGE_SPEED['value']} (no source); H5 2.87 / H6 2.40 = noria_n100.MODELS")


def st_with(base, run=(), load=100.0, edges=(), state="run", alarms=()):
    st = json.loads(json.dumps(base))
    for m in run:
        st["motors"][m]["state"] = state
        st["motors"][m]["load_t_h"] = load
    for e in edges:
        st["edges"][e] = {"t_h": 100.0}
    st["alarms"] = [{"id": a, "level": "trip", "t_s": 0.0, "text": "test"} for a in alarms]
    return st


def r_motion_state(live, moving=lv.moving_owners):
    """Only a mover that RUNS and carries grain, and an edge with t/h > 0, has moving packets; off / starting / stopping /
    faulted / tripped / unloaded movers and edges without flow stand; a truck lane is not grain."""
    base = Plant().state()
    route = ("S1->T9", "T9->H5", "H5->T10")
    inter = live.motion.owners
    fails = []

    def active_for(st):
        live.motion.set_active(moving(st))
        return set(live.motion.active)

    def drawn(t=0.5):
        li = live.motion.dashes(t)[0]
        return {live.motion.owner_of_leg[i] for i in set(li.tolist())}

    want = ({"H5", "T9", "T10"} | set(route)) & inter
    got = active_for(st_with(base, run=("H5", "T9", "T10"), edges=route))
    if got != want or drawn() != want:
        fails.append(("route running", sorted(got ^ want)))
    for state in ("off", "starting", "stopping", "fault"):
        got = active_for(st_with(base, run=("H5", "T9", "T10"), edges=route, state=state))
        if got & {"H5", "T9", "T10"} or drawn() & {"H5", "T9", "T10"}:
            fails.append((f"motors {state}", sorted(got & {"H5", "T9", "T10"})))
    if "H5" in active_for(st_with(base, run=("H5",), edges=route, alarms=("H5.plug",))):
        fails.append(("H5 running with its own trip alarm", "moves"))
    got = active_for(st_with(base, run=("H5", "T9"), load=0.0))
    if got & {"H5", "T9"}:
        fails.append(("running without grain", sorted(got)))
    got = active_for(st_with(base))
    if got or drawn():
        fails.append(("nothing runs", sorted(got)))
    lane = "TRUCK_IN->SCALES_IN"
    active_for(st_with(base, edges=(lane,)))
    if lane in inter:
        fails.append(("a truck lane has packets", lane))
    live.motion.set_active(())
    return not fails, (fails if fails else f"route H5/T9/T10 + 3 edges move ({len(want)} owners); off, starting, stopping, fault, "
                       f"a trip alarm, no load, no flow and a truck lane stand still")


def r_motion_pause(live, clock=mo.Overlay.clock):
    """A paused simulator stops the packets where they are (the motion clock stands still, the set of moving owners stays)
    and they go on from there when it resumes."""
    ov = mo.Overlay(live.motion)
    base = Plant().state()
    running = st_with(base, run=("H5", "T9"), edges=("S1->T9",))
    paused = dict(running, paused=True)
    live.apply(running)
    t1 = clock(ov, 10.0)
    t2 = clock(ov, 10.5)
    live.apply(paused)
    frozen = clock(ov, 11.5)
    still_moving = set(live.motion.active) == {"H5", "T9", "S1->T9"} & live.motion.owners
    live.apply(dict(running, paused=False))
    t4 = clock(ov, 12.0)
    ok = abs((t2 - t1) - 0.5) < 1e-9 and abs(frozen - t2) < 1e-9 and abs((t4 - frozen) - 0.5) < 1e-9 and still_moving         and live.motion.paused is False
    live.motion.set_active(())
    live.last.clear()
    return ok, (f"running 0.5 s -> {t2 - t1:.2f} s of motion; paused 1.0 s -> {frozen - t2:.2f} s (packets stay, the moving set is kept: "
                f"{still_moving}); resumed 0.5 s -> {t4 - frozen:.2f} s")


def r_motion_path(live, motion=None, times=(0.0, 0.31, 1.7, 5.03, 100.3), tol=0.002):
    """Every drawn vertex lies on its own owner's path (2 mm), on every frame, and every long-enough path carries packets."""
    motion = motion or live.motion
    motion.set_active(set(motion.owners))
    worst, n_pts, bare = 0.0, 0, set()
    for t in times:
        li, tail, head, p = motion.dashes(t)
        n_pts += p.shape[0] * p.shape[1]
        for i, ptl in zip(li, p):
            _, pts, s, _, _ = live.motion.legs[i]                # the truth: the model's paths
            for x in ptl:
                worst = max(worst, nearest_arc(pts, s, x)[1])
        seen = {int(i) for i in li}
        bare |= {live.motion.owner_of_leg[i] for i, lg in enumerate(live.motion.legs) if lg[3] > mo.SPACING_M and i not in seen}
    motion.set_active(())
    ok = worst <= tol and not bare and n_pts > 1000
    return ok, (f"{n_pts} vertices, worst distance to the own path {worst * 1000:.1f} mm (≤ {tol * 1000:.0f}); paths longer than "
                f"{mo.SPACING_M} m with no packet: {sorted(bare)[:4]}")


def r_motion_cost(live, motion=None, budget_ms=3.0):
    """One animation step (every dash of every moving owner) is a small part of a 30 Hz frame."""
    motion = motion or live.motion
    motion.set_active(set(motion.owners))
    times = []
    for k in range(300):
        c = time.perf_counter()
        motion.points(0.37 + 0.01 * k)
        times.append((time.perf_counter() - c) * 1000)
    n = len(motion.points(1.0))
    motion.set_active(())
    avg = sum(times) / len(times)
    return avg < budget_ms and max(times) < 5 * budget_ms, (f"all {len(motion.owners)} owners moving: {avg:.2f} ms per step "
            f"(≤ {budget_ms}), worst {max(times):.1f} ms, {n // 2} segments; one 30 Hz frame is 33 ms")


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
        ("ТЗА blades follow the gate pos: 0 covers the bore, 1 frees it, 0.5 half", lambda: r_blades(live, scene, site)),
        ("one gate's pos change is cheap", lambda: r_blade_cost(live)),
        ("flow tubes exactly where grain moves", lambda: r_flow(live)),
        ("heap volume = mass / density", lambda: r_heap(live)),
        ("state updates are cheap", lambda: r_speed(live)),
        ("after a whole scenario the glow still follows the state", lambda: r_glow(live, scene)),
        ("trees merged for the viewport, none lost", lambda: r_trees(scene, MERGED, LOCS)),
        ("grain packets run at the speed of their source", lambda: r_motion_speed(live, site)),
        ("packets move only for running loaded movers and flowing edges", lambda: r_motion_state(live)),
        ("a paused simulator stops the packets in place", lambda: r_motion_pause(live)),
        ("packets stay on their own paths, every frame", lambda: r_motion_path(live)),
        ("one animation step is cheap", lambda: r_motion_cost(live)),
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

    # ---- motion: each broken variant feeds a wrong input to its own rule
    def variant(name, fn):
        nonlocal ok_v
        try:
            ok, info = fn()
        except Exception as e:                           # noqa: BLE001
            ok, info = False, f"crash {type(e).__name__}: {e}"
        ok_v &= not ok
        print(f"{'PASS' if not ok else 'FAIL'}  broken variant must be rejected — {name} -> {'failed' if not ok else 'passed'} ({str(info)[:140]})", flush=True)

    sp = dict(live.motion.speeds)
    fast = {k: v * 1.1 for k, v in sp.items()}
    wrong_h5 = dict(sp, H5=sp["H6"])
    chain_as_belt = {k: (2.4 if G.nodes[k]["kind"] == "conveyor_chain" else v) for k, v in sp.items()}
    variant("H5 packets at the H6 speed (2.40 instead of 2.87)", lambda: r_motion_speed(live, site, motion=mo.Motion(live.paths, wrong_h5, live.static)))
    variant("every packet 10 % too fast", lambda: r_motion_speed(live, site, motion=mo.Motion(live.paths, fast, live.static)))
    variant("chain conveyors at the belt speed", lambda: r_motion_speed(live, site, motion=mo.Motion(live.paths, chain_as_belt, live.static)))

    def by_load_only(st):                                # the tube rule: any load moves, whatever the motor does
        return {m for m, v in st["motors"].items() if v["load_t_h"] > 0} | {e for e, v in st["edges"].items() if v["t_h"] > 0}

    def by_state_only(st):                               # a trip alarm of its own is not looked at
        return {m for m, v in st["motors"].items() if v["state"] == "run" and v["load_t_h"] > 0} | {e for e, v in st["edges"].items() if v["t_h"] > 0}

    def no_load_check(st):                               # a running empty belt shows grain (the rest of the rule as it is)
        trip = {a["id"].split(".")[0] for a in st.get("alarms", []) if a["level"] == "trip"}
        return {m for m, v in st["motors"].items() if lv.motor_key(m, v, trip) == "run"} | {e for e, v in st["edges"].items() if v["t_h"] > 0}

    variant("packets by load only (a stopped motor still moves)", lambda: r_motion_state(live, moving=by_load_only))
    variant("packets ignore the trip alarm", lambda: r_motion_state(live, moving=by_state_only))
    variant("packets on a running empty belt", lambda: r_motion_state(live, moving=no_load_check))
    variant("every line moves, flow or not", lambda: r_motion_state(live, moving=lambda st: set(live.motion.owners)))
    lifted = {o: [p + np.array([0.0, 0.0, 0.5]) for p in pl] for o, pl in live.paths.items()}
    variant("the motion clock ignores the pause", lambda: r_motion_pause(live, clock=lambda ov, now: (setattr(ov, "_t", ov._t + (now - ov._prev if ov._prev is not None else 0.0)), setattr(ov, "_prev", now), ov._t)[2]))
    variant("packets 0.5 m off their paths", lambda: r_motion_path(live, motion=mo.Motion(lifted, sp, live.static)))
    slow = mo.Motion(live.paths, sp, live.static)
    real_points = slow.points

    def slow_points(t):
        time.sleep(0.006)
        return real_points(t)
    slow.points = slow_points
    variant("6 ms extra per animation step", lambda: r_motion_cost(live, motion=slow))
    live.motion.set_active(())

    # ---- ТЗА blades: a wrong travel, a scene that moves every blade on every state, a slow move
    real_blades = live.blades
    for name, k in (("blades slide the opposite way (+X, out of the pocket side)", -1.0), ("blades slide a double stroke", 2.0)):
        live.blades = {g: [(o, r, t * k) for o, r, t in bl] for g, bl in real_blades.items()}
        variant(name, lambda: r_blades(live, scene, site))
    live.blades = real_blades

    def apply_moves_all(st):                             # forgets "only what changed": every blade moves on every state
        n = orig_apply(st)
        for gid, bl in live.blades.items():
            n += lv.set_blades(bl, st["gates"].get(gid, {}).get("pos", 0.0))
        return n
    live.apply = apply_moves_all
    variant("every blade moved on every state", lambda: r_blades(live, scene, site))
    live.apply = orig_apply
    real_set = lv.set_blades

    def slow_set(bl, pos):
        time.sleep(0.002)
        return real_set(bl, pos)
    lv.set_blades = slow_set
    variant("2 ms extra per blade move", lambda: r_blade_cost(live))
    lv.set_blades = real_set
    live.last.clear()
    live.apply(Plant().state())

    print("RESULT", "ALL PASS" if ok_all and ok_v else "FAILED", flush=True)
    sys.exit(0 if ok_all and ok_v else 1)


if __name__ == "__main__":
    main()
