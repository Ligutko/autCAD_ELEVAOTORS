"""Phase W1c check: site lighting (world/kit/lighting.py, research/design/environment.md).

Point-by-point maintained horizontal illuminance from the real photometry file (IES LM-63) with shadows cast by the
built scene (rays from each calculation point to each lamp through a BVH of every mesh above the ground).

FAIL (norms, values typed here, not read from the data):
  each photometry file integrates to its datasheet flux within 1 % (200 W 26 400 lm, LEDVANCE datasheet p. 3; 50 W
  6 300 lm, any-lamp listing) and its measured peak lies in the throw direction set in the data (15°);
  drives (every lane stretch outside the zones below): E_avg >= 10 lx, U0 >= 0.4 (ДБН В.2.5-28 табл. 8.12);
  U-turn, the drawn pit drive, the loading lane under Ш1, the trailer spot under each dust bin: E_avg >= 50 lx,
  U0 >= 0.4 (табл. 8.12 loading areas, 8.18);
  both scales platforms: E_avg >= 200 lx (ДБН В.2.2-8-98 табл. 6, discharge-lamp column: LED judged with it);
  the 12 m straights before and after each scales: E_avg >= 50 lx (ДБН В.2.5-28 табл. 8.8, surrounding zone of a
  200 lx object; U0 not normed there);
  all with the maintenance factor 0.67 (ДБН В.2.5-28 п. 8.3.7);
  mast height >= табл. 8.9 for the flux on the pole (the 'wide' row, the stricter one);
  I_max / H^2 of every floodlight <= табл. 8.10 for the norm it serves (3500 for 50 lx and over, 700 for 10 lx);
  upward light ratio ULR <= 5 % and intensity toward the horizon (0..-10 degrees) <= 7500 cd (табл. 8.11, zone A2,
  rural, before curfew);
  masts stand inside the fence, off every road and shoulder (>= 0.5 m) and clear of every structure footprint;
  every head whose housing reaches over a carriageway hangs >= 4.5 m over it (cab + 0.5, as in check_site_plan);
  every photometry file is symmetric about its throw plane (Cycles counts C the other way round);
  Blender lamps reproduce the calculation: one turned, tilted head of each type rendered over a Lambert plane from
  above, pixels turned back into lux, render / calc median 0.9-1.1, p10-p90 within 0.8-1.2, peak within 1 m.
WARN: scales U0 under 0.4 (no U0 in the scales norm); E_avg over 3 x the norm on drives (glare, waste).

Broken variants that must fail: Blender lamps turned 180 degrees, the lamp under Ш1 lowered to 3.9 m, the mast by scales in removed, a 13 m mast cut to 8 m, heads tilted 35 degrees up,
maintenance factor 1.0 in the data (the check keeps 0.67), a mast on the in lane.

Run:
    blender --background --python world/build/check_lighting.py
"""

import copy
import json
import math
import sys
import time
from pathlib import Path

import bpy  # noqa: I001  bpy first: the pip module registers mathutils
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import common as c  # noqa: E402
from kit import environment as env  # noqa: E402
from kit import lighting as lt  # noqa: E402
from kit import site_plan as spl  # noqa: E402

E_DRIVE, E_TURN, E_SCALES, U0 = 10.0, 50.0, 200.0, 0.4
E_SURROUND, SURROUND = 50.0, 12.0   # ДБН В.2.5-28 табл. 8.8: round a 200 lx object 50 lx; band = the 12 m straights (NIST, rec_7f0c2c19)
MF = 0.67
DATASHEET = {"F200": 26400.0, "F50": 6300.0}   # LEDVANCE datasheet p. 3 (200 W); any-lamp listing «50W 6300lm» (50 W)
H_MIN_WIDE = [(6000, 7.5), (10000, 8.5), (20000, 9.5), (30000, 10.5), (40000, 11.5), (1e12, 13.0)]   # табл. 8.9
IMAX_H2 = [(0.5, 100), (1, 150), (2, 250), (3, 300), (5, 400), (10, 700), (20, 1400), (30, 2100), (50, 3500)]  # табл. 8.10
ULR_MAX, I_HORIZON_MAX = 0.05, 7500.0
HEADROOM = 4.5


# ---------------------------------------------------------------- zones

def zones(site):
    """{zone id: (norm lx, points (n, 3))} on the running surfaces."""
    sp = spl.spec(site)
    g = c.ground_z()
    road = g + sp["road_z_over_ground"]
    r = site["receiving"]
    sh1x = spl.lane(sp, "out")["narrow"]["x"]
    scales = {k: spl.scales_box(sp, k) for k in ("scales_in", "scales_out")}
    ramps = {k: sp[k]["ramp"] for k in scales}

    def in_scales(x, y):
        return any(b[0] - ramps[k] <= x <= b[2] + ramps[k] and b[1] - 0.5 <= y <= b[3] + 0.5 for k, b in scales.items())

    def near_scales(x, y):                                                 # the straights before and after (table 8.8 band)
        return next((k for k, b in scales.items() if b[0] - ramps[k] - SURROUND <= x <= b[2] + ramps[k] + SURROUND
                     and b[1] - 2.0 <= y <= b[3] + 2.0), None)

    out = {}
    for ln in sp["lanes"]:
        pts, nrm, hw = env.lane_frame(ln, 1.0)
        rows = []
        for i in range(len(pts)):
            for f in (-0.7, 0.0, 0.7):
                q = pts[i] + nrm[i] * hw[i] * f
                rows.append((q[0], q[1]))
        rows = np.array(rows)
        if ln["id"] == "uturn":
            out["turn:uturn"] = (E_TURN, rows)
            continue
        keep = np.array([not in_scales(x, y) for x, y in rows])
        rows = rows[keep]
        if ln.get("to_bin"):                                              # the spot under the dust bin is a loading point
            b = next(bb for bb in site["aspiration"]["dust_bins"] if bb["id"] == ln["to_bin"])
            (cx, cy), (fx, fy) = b["center"], b["frame"]
            under = (np.abs(rows[:, 0] - cx) <= fx / 2) & (np.abs(rows[:, 1] - cy) <= fy / 2)
            gx, gy = np.meshgrid(np.linspace(cx - fx / 2 + 0.3, cx + fx / 2 - 0.3, 5), np.linspace(cy - fy / 2 + 0.3, cy + fy / 2 - 0.3, 4))
            out[f"turn:bin_{b['id']}"] = (E_TURN, np.column_stack([gx.ravel(), gy.ravel()]))
            rows = rows[~under]
        band = np.array([near_scales(x, y) for x, y in rows], dtype=object)
        for k in scales:
            if (band == k).any():
                prev = out.get(f"surround:{k}", (E_SURROUND, np.zeros((0, 2))))[1]
                out[f"surround:{k}"] = (E_SURROUND, np.concatenate([prev, rows[band == k]]))
        rows = rows[band == None]                                         # noqa: E711
        if ln["id"] == "out":                                              # the Ш1 loading lane splits the out lane in two
            under = (rows[:, 0] >= sh1x[0]) & (rows[:, 0] <= sh1x[1])
            out["turn:under_Sh1"] = (E_TURN, rows[under])
            out["drive:out_west"] = (E_DRIVE, rows[rows[:, 0] < sh1x[0]])
            out["drive:out_east"] = (E_DRIVE, rows[rows[:, 0] > sh1x[1]])
            continue
        out[f"drive:{ln['id']}"] = (E_DRIVE, rows)
    d = r["pit"]["drive"]
    xs, ys = np.arange(d["x"][0] + 0.5, d["x"][1], 1.0), np.linspace(d["y"][0] + 0.5, d["y"][1] - 0.5, 4)
    out["turn:pit_drive"] = (E_TURN, np.array([(x, y) for x in xs for y in ys]))
    for k, (x0, y0, x1, y1) in scales.items():
        xs, ys = np.arange(x0 + 0.5, x1, 1.0), np.linspace(y0 + 0.4, y1 - 0.4, 4)
        out[f"scales:{k}"] = (E_SCALES, np.array([(x, y) for x in xs for y in ys]))

    def z_at(key, x):
        if key == "turn:pit_drive":                                        # ramps down to the deck at its flat part
            fx0, fx1 = d["flat_x"]
            deck = d["deck_z"]
            if x < fx0:
                return road + (deck - road) * (x - d["x"][0]) / (fx0 - d["x"][0])
            if x > fx1:
                return deck + (road - deck) * (x - fx1) / (d["x"][1] - fx1)
            return deck
        if key.startswith("scales:"):
            return road + 0.35
        return road
    return {k: (n, np.column_stack([p, [z_at(k, x) for x in p[:, 0]]])) for k, (n, p) in out.items()}


# ---------------------------------------------------------------- shadows

def scene_blocker(site):
    """Build the site scene and return blocked(p0, p1) casting rays through every mesh standing above the ground
    (silos as instances, towers, galleries, buildings, the fence); lamps, their housings and the ground layers skipped."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("site_scene", str(ROOT / "build" / "site.py"))
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    S.assemble(quick=True)
    dg = bpy.context.evaluated_depsgraph_get()
    g = c.ground_z()
    verts, polys, base = [], [], 0
    for inst in dg.object_instances:
        ob = inst.object
        if ob.type != "MESH" or ob.name.startswith(("ENV_", "SITE_PLAN_ROADS", "GROUND", "LIGHT_", "TREE_", "FIG_")):   # trees >= 31 m off; figures are for scale: norms hold on the empty surface
            continue
        me = ob.to_mesh()
        mw = np.array(inst.matrix_world)
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        if co[:, 2].max() < g + 0.1:
            ob.to_mesh_clear()
            continue
        verts.append(co)
        polys += [tuple(base + i for i in p.vertices) for p in me.polygons]
        base += len(co)
        ob.to_mesh_clear()
    v = np.concatenate(verts)
    bvh = BVHTree.FromPolygons([Vector(p) for p in v], polys)

    def blocked(p0, p1):
        res = np.zeros(len(p0), bool)
        for i, (a, b) in enumerate(zip(p0, p1)):
            d = b - a
            dist = float(np.linalg.norm(d))
            hit = bvh.ray_cast(Vector(a + [0, 0, 0.05]), Vector(d / dist), dist - 0.6)   # stop short of the lamp head
            res[i] = hit[0] is not None
        return res
    return blocked, len(polys)


# ---------------------------------------------------------------- checks

def stats(e):
    avg = float(e.mean())
    return avg, (float(e.min()) / avg if avg > 0 else 0.0)


def light_checks(site, blocked):
    out = []
    ls = lt.spec(site)
    fl_bad, fl_info = [], {}
    for key, lu in ls["luminaires"].items():
        ph = lt.photometry(lu["ies"])
        fl = ph.flux()
        _, c_peak, _ = ph.peak()
        dc = (c_peak - lu["throw_c"] + 180) % 360 - 180
        fl_info[key] = (round(fl), c_peak)
        if key not in DATASHEET or abs(fl - DATASHEET[key]) > 0.01 * DATASHEET[key] or abs(dc) > 15.0:
            fl_bad.append(key)
    out.append(("each photometry file integrates to its datasheet flux (1 %) and peaks in its throw direction (15°)", not fl_bad,
                f"(lm, peak C) {fl_info}, bad {fl_bad}"))
    zs = zones(site)
    res, bad, warn = {}, [], []
    for k, (norm, pts) in zs.items():
        e = lt.illuminance(site, pts, blocked=blocked, mf=MF)
        avg, u0 = stats(e)
        res[k] = (round(avg, 1), round(u0, 2), round(float(e.min()), 1))
        if avg < norm - 1e-6 or (not k.startswith(("scales", "surround")) and u0 < U0 - 1e-6):
            bad.append((k, res[k]))
        if k.startswith("scales") and u0 < U0:
            warn.append((k, "U0", round(u0, 2)))
        if k.startswith("drive") and avg > 3 * norm:
            warn.append((k, "E_avg", round(avg, 1)))
    for group, label in (("drive", "drives E_avg >= 10 lx, U0 >= 0.4 (ДБН В.2.5-28 табл. 8.12)"),
                         ("surround", "12 m straights at the scales E_avg >= 50 lx (табл. 8.8 for a 200 lx object)"),
                         ("turn", "U-turn, pit drive, under Ш1, under the dust bins: E_avg >= 50 lx, U0 >= 0.4 (табл. 8.12, 8.18)"),
                         ("scales", "scales platforms E_avg >= 200 lx (ДБН В.2.2-8-98 табл. 6)")):
        mine = {k: v for k, v in res.items() if k.startswith(group)}
        out.append((label + ", MF 0.67", not [b for b in bad if b[0].startswith(group)], f"(avg, U0, min) {mine}"))
    if warn:
        out.append(("scales U0 under 0.4 / drives over 3 x the norm: WARN", True, f"{warn}"))

    hs = lt.heads(site)
    g = c.ground_z()
    low = []
    for m in ls["masts"]:
        flux = DATASHEET[m.get("lum", ls["default_lum"])] * len(m["heads"])
        need = next(h for lim, h in H_MIN_WIDE if flux <= lim)
        if m["h"] < need - 1e-6:
            low.append((m["id"], m["h"], need))
    out.append(("mast height >= ДБН В.2.5-28 табл. 8.9 for the flux on the pole ('wide' row)", not low, f"low {low}"))

    zone_of = {}
    for k, (norm, pts) in zs.items():                                      # which norm each head serves: its brightest zone
        _, parts = lt.illuminance(site, pts, mf=MF, per_head=True)
        for hid, e in parts.items():
            if e.size and e.max() > 0:
                prev = zone_of.get(hid, (0.0, 0.0))
                if e.mean() > prev[0]:
                    zone_of[hid] = (float(e.mean()), norm)
    ratio_bad = []
    for h in hs:
        i_max = float(lt.head_photometry(site, h)[0].cd.max())
        norm = zone_of.get(h["id"], (0, E_DRIVE))[1]
        lim = next((v for lx, v in IMAX_H2 if norm <= lx), IMAX_H2[-1][1])
        H = h["pos"][2] - g
        if i_max / H ** 2 > lim:
            ratio_bad.append((h["id"], round(i_max / H ** 2), lim))
    out.append(("I_max / H² of every floodlight <= ДБН В.2.5-28 табл. 8.10", not ratio_bad, f"bad {ratio_bad[:5]}"))

    ulr = lt.upward_ratio(site)
    ih, hid = lt.near_horizontal_peak(site)
    out.append(("ULR <= 5 %, <= 7500 cd toward the horizon (ДБН В.2.5-28 табл. 8.11, zone A2)", ulr <= ULR_MAX and ih <= I_HORIZON_MAX,
                f"ULR {100 * ulr:.2f} %, horizon peak {ih:.0f} cd ({hid})"))

    fe = env.spec(site)["fence"]
    x0, y0, x1, y1 = fe["rect"]
    sp = spl.spec(site)
    frames = [(ln["id"], *env.lane_frame(ln, 0.25)) for ln in sp["lanes"]]
    ob = env.obstacles(site)
    misplaced = []
    for m in ls["masts"]:
        x, y = m["xy"]
        if not (x0 + 0.5 < x < x1 - 0.5 and y0 + 0.5 < y < y1 - 0.5):
            misplaced.append((m["id"], "outside the fence"))
        for lid, pts, _, hw in frames:
            d = np.min(np.hypot(pts[:, 0] - x, pts[:, 1] - y) - hw) - env.spec(site)["shoulder"]["w"]
            if d < 0.5:
                misplaced.append((m["id"], lid, round(float(d), 2)))
        for name, k, gm in ob:
            if spl.footprint_dist((x, y), k, gm) < 0.45 + 0.1:
                misplaced.append((m["id"], name))
    out.append(("masts inside the fence, >= 0.5 m off roads and shoulders, clear of structures", not misplaced, f"{misplaced[:5]}"))

    road = g + sp["road_z_over_ground"]
    low_heads = []
    for h in hs:                                                          # a head hanging over a carriageway clears the cab
        L, W, H = lt.luminaire(site, h["lum"])["size"]
        reach = 0.5 * math.hypot(L, W)                                     # housing overhang round the head point
        for lid, pts, _, hw in frames:
            over = np.min(np.hypot(pts[:, 0] - h["pos"][0], pts[:, 1] - h["pos"][1]) - hw) < reach
            if over and h["pos"][2] - road < HEADROOM:
                low_heads.append((h["id"], lid, round(float(h["pos"][2] - road), 2)))
    out.append(("every head over a carriageway hangs >= 4.5 m over it (cab + 0.5, as in check_site_plan)", not low_heads, f"{low_heads}"))
    return out, res


def symmetry_checks(site):
    """Cycles counts C the other way round: a file must be symmetric about its throw plane, I(throw+a) = I(throw-a)."""
    bad = []
    for key, lu in lt.spec(site)["luminaires"].items():
        ph = lt.photometry(lu["ies"])
        a = np.arange(0, 181, 15.0)
        gg = np.arange(0, 91, 5.0)
        A, G = np.meshgrid(a, gg)
        i1, i2 = ph.intensity(lu["throw_c"] + A, G), ph.intensity(lu["throw_c"] - A, G)
        dev = float(np.max(np.abs(i1 - i2)) / ph.cd.max())
        if dev > 0.01:
            bad.append((key, round(dev, 3)))
    return [("every photometry file is symmetric about its throw plane (Cycles mirrors C)", not bad, f"bad {bad}")]


def render_test(site, lum, az=30.0, tilt=-10.0, h=10.0, res=120, size=60.0):
    """Render one head of type lum over a white Lambert plane from straight above and turn the pixels back into lux;
    returns (median, p10, p90 of render / calculation over the lit area, peak offset in m)."""
    import math as m
    s = copy.deepcopy(site)
    ls = s["designed"]["environment"]["lighting"]
    ls["masts"] = []
    ls["mounts"] = [{"id": "T", "xy": [0.0, 0.0], "z": h, "heads": [[az, tilt]], "lum": lum}]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 128
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 0
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    world = bpy.data.worlds.new("W")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    mat = bpy.data.materials.new("WHITE")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1)
    b.inputs["Roughness"].default_value = 1.0
    b.inputs["Specular IOR Level"].default_value = 0.0
    g = c.ground_z()
    q = size / 2
    c.mesh_from_arrays("PLANE", np.array([(-q, -q, g), (q, -q, g), (q, q, g), (-q, q, g)]), np.array([(0, 1, 2, 3)]), mat)
    lt.add_lamps(s)
    cam = bpy.data.cameras.new("C")
    cam.type = "ORTHO"
    cam.ortho_scale = size
    co = bpy.data.objects.new("CAM", cam)
    scene.collection.objects.link(co)
    co.location = (0, 0, g + 50)
    scene.camera = co
    scene.render.image_settings.file_format = "OPEN_EXR"
    path = str(Path(bpy.app.tempdir or ".") / f"lighting_test_{lum}.exr")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    px = np.array(img.pixels[:]).reshape(res, res, 4)[:, :, 0]
    xs = -q + (np.arange(res) + 0.5) * size / res
    X, Y = np.meshgrid(xs, xs)
    e_calc = lt.illuminance(s, np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, g)]), mf=1.0).reshape(res, res)
    e_px = px * m.pi / 0.8 * 683.0
    lit = e_calc > 0.2 * e_calc.max()
    r = e_px[lit] / e_calc[lit]
    k1, k2 = np.unravel_index(np.argmax(e_calc), e_calc.shape), np.unravel_index(np.argmax(e_px), e_px.shape)
    off = float(np.hypot(X[k1] - X[k2], Y[k1] - Y[k2]))
    return float(np.median(r)), float(np.percentile(r, 10)), float(np.percentile(r, 90)), off


def render_checks(site):
    res = {}
    ok = True
    for key in lt.spec(site)["luminaires"]:
        med, p10, p90, off = render_test(site, key)
        res[key] = (round(med, 3), round(p10, 3), round(p90, 3), round(off, 2))
        ok &= 0.9 <= med <= 1.1 and p10 >= 0.8 and p90 <= 1.2 and off <= 1.0
    return [("Blender lamps reproduce the calculation: a turned, tilted head over a Lambert plane, render / calc median 0.9-1.1,"
             " p10-p90 in 0.8-1.2, peak within 1 m", ok, f"(median, p10, p90, peak offset m) {res}")]


def main():
    run(json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8")))


def run(site):
    t = time.time()
    blocked, n = scene_blocker(site)
    print(f"INFO  shadow scene: {n} polygons, {time.time() - t:.1f} s", flush=True)
    ok_all = True
    results, _ = light_checks(site, blocked)
    for name, ok, info in results:
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)

    def v_remove(s):
        s["designed"]["environment"]["lighting"]["masts"] = [m for m in s["designed"]["environment"]["lighting"]["masts"] if m["id"] != "L2"]
    def v_short(s):
        next(m for m in s["designed"]["environment"]["lighting"]["masts"] if m["id"] == "L2")["h"] = 8.0
    def v_tilt(s):
        for m in s["designed"]["environment"]["lighting"]["masts"]:
            m["heads"] = [[az, 35.0] for az, _ in m["heads"]]
    def v_mf(s):
        s["designed"]["environment"]["lighting"]["mf"] = 1.0
        for m in s["designed"]["environment"]["lighting"]["masts"]:        # a designer who counts on MF 1.0 thins the heads out
            if len(m["heads"]) > 1:
                m["heads"] = m["heads"][:1]
    def v_on_lane(s):
        next(m for m in s["designed"]["environment"]["lighting"]["masts"] if m["id"] == "L2")["xy"] = [36.0, 63.25]

    def v_low(s):
        next(m for m in s["designed"]["environment"]["lighting"]["mounts"] if m["id"] == "S1")["z"] = 3.9

    variants = [("the lamp under Ш1 lowered to 3.9 m", v_low, "over a carriageway"), ("mast L2 by scales in removed", v_remove, "scales"), ("mast L2 cut to 8 m", v_short, "табл. 8.9"),
                ("heads tilted 35 degrees up", v_tilt, "ULR"), ("MF 1.0 in the data, heads thinned", v_mf, "MF 0.67"),
                ("mast L2 on the in lane", v_on_lane, "off roads")]
    for name, patch, expect in variants:
        bad = copy.deepcopy(site)
        patch(bad)
        failed = [n for n, ok, _ in light_checks(bad, blocked)[0] if not ok]
        hit = any(expect in n for n in failed)
        ok_all &= hit
        print(f"{'PASS' if hit else 'FAIL'}  broken variant must be rejected — {name}: failed {failed}", flush=True)
    for name, ok, info in symmetry_checks(site) + render_checks(site):  # the render tests reset the scene: last
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)
    c0 = lt.CYCLES_C0_ANGLE
    lt.CYCLES_C0_ANGLE = c0 + 180.0                                        # the lamp turned the wrong way round
    failed = [n for n, ok, _ in render_checks(site) if not ok]
    lt.CYCLES_C0_ANGLE = c0
    ok_all &= bool(failed)
    print(f"{'PASS' if failed else 'FAIL'}  broken variant must be rejected — Blender lamps turned 180 degrees: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
