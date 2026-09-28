"""Phase 7C check: the grain path of the reel cycle (kit/routes.py) against the process graph and the
geometry the model is built from. Constants are independent of routes.py where they can be.

FAIL:
  every route of the cycle is a route of the process graph, and the routes meet at the silo;
  every node and every edge of a route owns a leg, in route order;
  conveyors: grain runs tail -> head (SITE tail / head, not the route), it is fed inside the run and
  leaves before the drum plus the discharge hood, the spouts land on / leave from the casing axis
  (0 ... 0.6 m over the top, 0 ... 1.5 m under the bottom);
  gravity legs never go up; legs from drawn / designed geometry fall at >= 45° (distribution.MIN_SLOPE_DEG);
  norias lift from boot to head; H5 / H6 discharge from the kit = the drawn head outlet (SITE distribution);
  legs meet: a gap between two legs from drawn / designed geometry is at most 5 cm.
FAIL in the assembled scene (stage B, routes.NODE_OBJECTS / EDGE_OBJECTS):
  every object pattern of the cycle finds objects;
  the path runs inside its own equipment (nearest surface of the owner's meshes <= 0.5 m; hoppers 1.6);
  H5: the path goes up the leg where the kit draws grain in the buckets (<= 0.25 m of H5_NORIA_GRAIN);
  every highlighted object is on the path, or bolted to a part of its node that is;
  rays along drawn / designed legs cross nothing but the cycle's own equipment and pierced slabs.
FINDING (the existing simplified block and judgment connectors, not model errors):
  gaps and gentle falls where one side is existing or judgment geometry; the judgment legs by length;
  existing / judgment legs through foreign objects.

Broken variants that must fail, each on its own rule: no SH1 -> TOWER_PIT edge (route gone), T8
running the other way, T9 outlet 3 m past the H5 boot, the H5 head outlet 0.3 m higher on the drawing,
the T7 -> T8 spout made flat, the gravity pipe drawn uphill; T7 mapped to the T11 conveyor, H3 mapped to
the H2 noria, a Ш1 pattern with a typo, the H5 path up the empty leg, the T8 -> S1 drop on the edge beam.

Run:
    blender --background --python world/build/check_routes.py
"""

import copy
import json
import sys
from pathlib import Path

import bpy  # noqa: F401  bpy first: the pip module registers bmesh and mathutils
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import distribution as dist  # noqa: E402
from kit import process as pr  # noqa: E402
from kit import routes as R  # noqa: E402

CYCLE = "full_cycle"
MIN_FALL = dist.MIN_SLOPE_DEG            # 45°, EST rule of thumb used by check_distribution too
JOINT_TOL = 0.05                        # m, two drawn / designed legs must meet
OUTLET_TOL = 0.03                       # m, kit discharge vs drawn head outlet
HOOD_M = 0.7                            # m past the head drum still inside the discharge hood
FEED_OVER_TOP = (-0.10, 0.60)           # spout end over the casing top (check_process.lands_on)
OUT_UNDER_BOTTOM = (-0.05, 1.50)        # outlet spout start under the casing bottom (check_process.leaves)
SOLID = ("drawn", "designed")


def owners(nodes, route):
    out = []
    for i, n in enumerate(nodes):
        out.append(n)
        if i < len(route):
            out.append(f"{route[i]['from']}->{route[i]['to']}")
    return out


def checks(site):
    out = []
    g = pr.Graph(site)
    try:
        cyc = [(nodes, route, R.route_legs(site, nodes, route)) for nodes, route in R.cycle(CYCLE, site)]
    except KeyError as e:
        return [(f"every route of {CYCLE} is a route of the process graph", False, str(e))]
    out.append((f"every route of {CYCLE} is a route of the process graph", True,
                "; ".join(" -> ".join(n) for n, _, _ in cyc)))
    joined = all(cyc[i][0][-1] == cyc[i + 1][0][0] and g.is_silo(cyc[i][0][-1]) for i in range(len(cyc) - 1))
    out.append(("the routes of the cycle meet at a silo", joined, " | ".join(f"{n[0]}..{n[-1]}" for n, _, _ in cyc)))

    findings = []
    for nodes, route, legs in cyc:
        tag = f"{nodes[0]}->{nodes[-1]}"
        seq = []
        for lg in legs:
            o = lg.owner.split(" (")[0]
            if not seq or seq[-1] != o:
                seq.append(o)
        want = owners(nodes, route)
        out.append((f"{tag}: every node and edge owns a leg, in route order", seq == want,
                    f"{len(want)} owners" if seq == want else f"legs {seq} vs route {want}"))

        # ---- conveyors
        bad = []
        for lg in legs:
            if lg.kind != "convey":
                continue
            m = lg.meta
            lo, hi = -0.3 / m["run_m"], 1 + HOOD_M / m["run_m"]
            fwd = m["t_out"] > m["t_in"]
            inside = lo <= m["t_in"] <= 1 and 0 <= m["t_out"] <= hi
            on_axis = max(m["off_in"], m["off_out"]) <= m["half_w"] + 0.05
            if not (fwd and inside and on_axis):
                bad.append(f"{lg.owner}: t {m['t_in']:.3f} -> {m['t_out']:.3f}, off {m['off_in']:.2f}/{m['off_out']:.2f}")
        out.append((f"{tag}: conveyors carry tail -> head, fed and emptied inside the run on the axis", not bad,
                    "; ".join(bad) or ", ".join(f"{lg.owner} {lg.meta['t_in']:.2f}->{lg.meta['t_out']:.2f}" for lg in legs if lg.kind == "convey")))

        # ---- joints: spouts over / under conveyor casings, other legs end to end
        bad, gaps = [], []
        for i in range(len(legs) - 1):
            a, b = legs[i], legs[i + 1]
            if b.kind == "convey":                       # spout end -> casing top
                top = b.pts[0][2] + b.meta["half_h"]
                dz = a.pts[-1][2] - top
                ok = FEED_OVER_TOP[0] <= dz <= FEED_OVER_TOP[1]
                (gaps if ok else bad).append(f"{a.owner} lands {dz:+.2f} over the {b.owner} top")
                continue
            if a.kind == "convey":                       # casing bottom -> outlet spout start
                bot = a.pts[-1][2] - a.meta["half_h"]
                dz = bot - b.pts[0][2]
                ok = OUT_UNDER_BOTTOM[0] <= dz <= OUT_UNDER_BOTTOM[1]
                (gaps if ok else bad).append(f"{b.owner} starts {dz:.2f} under the {a.owner} bottom")
                continue
            gap = float(np.linalg.norm(b.pts[0] - a.pts[-1]))
            if gap <= JOINT_TOL:
                continue
            if a.basis in SOLID and b.basis in SOLID:
                bad.append(f"{a.owner} -> {b.owner} gap {gap:.3f}")
            else:
                findings.append((f"{tag}: legs do not meet ({a.basis} / {b.basis}): FINDING, not a model error",
                                 f"{a.owner} ends {np.round(a.pts[-1], 2)}, {b.owner} starts {np.round(b.pts[0], 2)}: {gap:.2f} m"))
        out.append((f"{tag}: legs meet (drawn / designed gaps <= {JOINT_TOL} m, spouts over / under the casings)", not bad,
                    "; ".join(bad) or f"{len(legs) - 1} joints"))

        # ---- gravity legs
        up, flat = [], []
        for lg in legs:
            if lg.kind != "fall":
                continue
            for p, q in zip(lg.pts[:-1], lg.pts[1:]):
                if q[2] > p[2] + 1e-6:
                    up.append(f"{lg.owner} rises {q[2] - p[2]:.2f} m")
                s = R.slope_deg(p, q)
                if s < MIN_FALL - 1e-6:
                    if lg.basis in SOLID:
                        flat.append(f"{lg.owner} {s:.1f}°")
                    else:
                        findings.append((f"{tag}: {lg.basis} fall under {MIN_FALL:.0f}°: FINDING, not a model error",
                                         f"{lg.owner} {s:.1f}° over {np.linalg.norm(q - p):.2f} m"))
        out.append((f"{tag}: grain never goes up by gravity", not up, "; ".join(up) or "all gravity legs descend"))
        out.append((f"{tag}: drawn / designed falls >= {MIN_FALL:.0f}°", not flat, "; ".join(flat) or "ok"))

        # ---- norias
        bad = []
        for lg in legs:
            if lg.kind != "lift":
                continue
            if not lg.pts[-1][2] - lg.pts[0][2] > 20.0:
                bad.append(f"{lg.owner} lifts only {lg.pts[-1][2] - lg.pts[0][2]:.1f} m")
            d = next((d for d in site["distribution"] if d["tower"] == lg.owner), None)
            if d is not None:
                gap = float(np.linalg.norm(lg.pts[-1] - np.asarray(d["head_outlet"], float)))
                if gap > OUTLET_TOL:
                    bad.append(f"{lg.owner} kit outlet {np.round(lg.pts[-1], 3)} vs drawn {d['head_outlet']}: {gap:.3f} m")
        out.append((f"{tag}: norias lift boot -> head; H5 / H6 kit outlet = drawn head outlet (<= {OUTLET_TOL} m)", not bad,
                    "; ".join(bad) or ", ".join(f"{lg.owner} {lg.pts[0][2]:+.2f} -> {lg.pts[-1][2]:+.2f}" for lg in legs if lg.kind == "lift")))

        jl = [lg for lg in legs if lg.basis == "judgment" and lg.length > 1e-3]
        findings.append((f"{tag}: judgment legs (no model geometry): FINDING",
                         f"{len(jl)} legs, {sum(lg.length for lg in jl):.1f} m of {sum(lg.length for lg in legs):.1f} m: "
                         + ", ".join(f"{lg.owner} {lg.length:.1f}" for lg in jl)))
    out += [(n, True, i) for n, i in findings]
    return out


# ================================================================== stage B: the path in the real scene
SCENE = {}
IN_TOL = 0.5                           # m, path point to the nearest surface of its own equipment
IN_TOL_WIDE = {"PIT->T1": 1.6, "SH1": 1.6}   # hoppers and Ш1: the centreline is up to 1.5 m from the walls
GRAIN_TOL = 0.25                       # m, lift path to the grain the kit draws in the loaded buckets
NEAR_BOX = 0.5                         # m, a highlighted object's box must hold a path point
PASS_THROUGH = ("DECK", "PLATFORM", "SLAB", "COVER", "ROOF", "GRATING", "FLOOR", "CIVIL", "TOES", "RAILS")


def scene():
    """Assemble the site scene once (quick materials), world BVH per mesh object on demand."""
    if not SCENE:
        import importlib.util
        spec = importlib.util.spec_from_file_location("site_scene", ROOT / "build" / "site.py")
        S = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(S)
        sc, *_ = S.assemble(quick=True)
        bpy.context.view_layer.update()
        SCENE["scene"] = sc
        SCENE["objs"] = {o.name: o for o in sc.objects if o.type in ("MESH", "EMPTY") and rendered(o)}
        SCENE["bvh"] = {}
    return SCENE


def rendered(ob):
    """Visible in the frames: labels hide by collection (site.py LABELS_*), not by object."""
    ob = ob.original
    return not ob.hide_render and not any(col.hide_render for col in ob.users_collection)


def bvh(name):
    from mathutils.bvhtree import BVHTree
    S = scene()
    if name not in S["bvh"]:
        o = S["objs"][name]
        mw = o.matrix_world
        S["bvh"][name] = BVHTree.FromPolygons([mw @ v.co for v in o.data.vertices], [p.vertices[:] for p in o.data.polygons])
    return S["bvh"][name]


def samples(pts, step=0.5):
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(1, int(np.linalg.norm(b - a) / step))
        out += [a + (b - a) * k / n for k in range(n)]
    return out + [pts[-1]]


def world_box(o):
    from mathutils import Vector
    if o.type == "EMPTY" and o.instance_collection:
        pts = [o.matrix_world @ Vector(c) for ob in o.instance_collection.objects if ob.type == "MESH" for c in ob.bound_box]
    else:
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return np.min(pts, axis=0), np.max(pts, axis=0)


def mirror_h5(site, legs):
    """Broken variant: the H5 path up the empty (down) leg."""
    spec = next(t for t in site["noria_towers"] if t["id"] == "H5")
    for lg in legs:
        if lg.owner == "H5":
            for arr in (lg.pts, lg.meta["up_leg"]):
                arr[:, 1] = 2 * spec["noria_axis"][1] - arr[:, 1]


def drop_on_beam(site, legs):
    """Broken variant: the T8 -> S1 drop 0.28 m off the axis, onto the edge beam of the gallery."""
    for lg in legs:
        if lg.owner == "T8->S1":
            lg.pts[:, 1] -= 0.28


def scene_checks(site, nmap=None, emap=None, leg_patch=None):
    from fnmatch import fnmatchcase
    from mathutils import Vector
    nmap = R.NODE_OBJECTS if nmap is None else nmap
    emap = R.EDGE_OBJECTS if emap is None else emap
    S = scene()
    names = sorted(S["objs"])

    def objs_of(owner):
        o = owner.split(" (")[0]
        pats = nmap.get(o) or emap.get(o) or []
        return sorted({n for n in names for p in pats if fnmatchcase(n, p)}), pats

    out, findings = [], []
    legs_all = [lg for _, lgs in R.cycle_legs(CYCLE, site) for lg in lgs]
    if leg_patch:
        leg_patch(site, legs_all)

    owners = sorted({lg.owner.split(" (")[0] for lg in legs_all})
    empty = [(o, p) for o in owners for p in (nmap.get(o) or emap.get(o) or []) if not any(fnmatchcase(n, p) for n in names)]
    out.append(("every object pattern of the cycle's nodes and edges finds objects", not empty,
                f"no object for {empty}" if empty else f"{len(owners)} owners"))

    bad, worst = [], {}
    for lg in legs_all:
        mine, _ = objs_of(lg.owner)
        mine = [n for n in mine if S["objs"][n].type == "MESH"]
        if not mine or lg.basis == "judgment" or lg.kind not in ("convey", "lift", "fall"):
            continue
        tol = IN_TOL_WIDE.get(lg.owner, IN_TOL)
        trees = [bvh(n) for n in mine]
        d = max(min(t.find_nearest(Vector(p))[3] for t in trees) for p in samples(lg.pts))
        worst[lg.owner] = max(worst.get(lg.owner, 0.0), d)
        if d > tol:
            bad.append(f"{lg.owner} {d:.2f} m > {tol}")
    out.append((f"the path runs inside its own equipment (nearest surface <= {IN_TOL} m, hoppers {IN_TOL_WIDE['SH1']})", not bad,
                "; ".join(bad) or ", ".join(f"{k} {v:.2f}" for k, v in sorted(worst.items()))))

    lift = next(lg for lg in legs_all if lg.owner == "H5")
    a, b = (np.asarray(p, float) for p in lift.meta["up_leg"])
    up = [p for p in samples(np.array([a, b])) if a[2] + 1.0 < p[2] < b[2] - 1.0]   # the straight loaded leg
    g = bvh("H5_NORIA_GRAIN")
    d = max(g.find_nearest(Vector(p))[3] for p in up) if up else 99.0
    out.append((f"H5: the path goes up the leg where the kit's buckets carry grain (<= {GRAIN_TOL} m)", d <= GRAIN_TOL,
                f"{len(up)} points, farthest {d:.2f} m from H5_NORIA_GRAIN"))

    pts = [p for lg in legs_all for p in samples(lg.pts, 1.0)]
    pts += [np.array([p[0], p[1], site["ground_z"]]) for lg in legs_all if lg.kind == "drive" for p in samples(lg.pts, 1.0)]
    P = np.array(pts)
    far, n_lit = [], 0
    for o in owners:                                   # per owner: on the path, or bolted to a part that is
        mine = objs_of(o)[0]
        n_lit += len(mine)
        box = {n: world_box(S["objs"][n]) for n in mine}
        reached = {n for n, (lo, hi) in box.items() if np.any(np.all((P >= lo - NEAR_BOX) & (P <= hi + NEAR_BOX), axis=1))}
        grow = True
        while grow:
            grow = False
            for n, (lo, hi) in box.items():
                if n in reached:
                    continue
                if any(np.all(lo - NEAR_BOX <= box[m][1]) and np.all(box[m][0] <= hi + NEAR_BOX) for m in reached):
                    reached.add(n)
                    grow = True
        far += [f"{n} ({o})" for n in mine if n not in reached]
    out.append((f"every highlighted object is on the path or bolted to a part of its node that is (box +{NEAR_BOX} m)", not far,
                f"off the path: {sorted(set(far))}" if far else f"{n_lit} object links"))

    # rays along the path: what it passes through besides the cycle's own equipment and slabs it pierces
    depsgraph = bpy.context.evaluated_depsgraph_get()
    ok_names = {n for o in owners for n in objs_of(o)[0]}
    inst_at = {tuple(np.round(o.matrix_world.translation, 2)): o.name     # a silo is an instance: rays report the
               for o in S["objs"].values() if o.type == "EMPTY" and o.instance_collection}   # prototype part, the matrix says which silo
    crossed = {}
    for lg in legs_all:
        if lg.basis == "judgment" or lg.kind not in ("convey", "lift", "fall"):
            continue
        for a, b in zip(lg.pts[:-1], lg.pts[1:]):
            o, dvec = Vector(a), Vector(b - a)
            left = dvec.length
            dvec.normalize()
            while left > 1e-3:
                hit, loc, _, _, ob, mat = S["scene"].ray_cast(depsgraph, o, dvec, distance=left)
                if not hit:
                    break
                name = inst_at.get(tuple(np.round(mat.translation, 2)), ob.name)
                if name not in ok_names and (name in inst_at.values() or rendered(ob)) and not any(k in name for k in PASS_THROUGH):
                    crossed.setdefault((lg.basis in SOLID), {}).setdefault(name, set()).add(lg.owner)
                step = (loc - o).length + 0.01
                o, left = o + dvec * step, left - step

    def fmt(d):
        return "; ".join(f"{n} by {sorted(v)}" for n, v in sorted(d.items())) or "nothing"
    out.append(("drawn / designed path legs cross no foreign object (rays; decks, slabs, roofs, gratings are pierced)",
                not crossed.get(True), fmt(crossed.get(True, {}))))
    findings.append(("existing / judgment path legs through foreign objects: FINDING, not a model error", fmt(crossed.get(False, {}))))
    return out + [(n, True, i) for n, i in findings]


def main():
    run(json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8")))


def run(site):
    ok_all = True
    for name, ok, info in checks(site) + scene_checks(site):
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)

    def edge(s, a, b):
        return next(e for e in s["process"]["edges"] if e["from"] == a and e["to"] == b)

    def v_no_edge(s):
        s["process"]["edges"].remove(edge(s, "SH1", "TOWER_PIT"))
    def v_t8_back(s):
        ln = next(ln for ln in s["silo_top_galleries"]["lines"] if ln["id"] == "T8")
        ln["tail_x"], ln["head_x"] = ln["head_x"], ln["tail_x"]
    def v_t9_out(s):
        next(t for t in s["tunnels"] if t["id"] == "T9")["conveyor"]["outlet_xz"][0] = 3.0
    def v_head(s):
        next(d for d in s["distribution"] if d["tower"] == "H5")["head_outlet"][2] += 0.3
    def v_flat(s):
        sp = next(x for x in next(d for d in s["distribution"] if d["tower"] == "H5")["spouts"] if x.get("from_conveyor") == "T7")
        sp["path"][-1][1] = 23.0                          # same drop over 3.9 m: about 23°
    def v_uphill(s):
        gp = s["receiving"]["cleaning_tower"]["gravity_pipe"]
        gp["to"][1] = 23.8                                # pipe end above its start

    variants = [("no SH1 -> TOWER_PIT edge", v_no_edge, "route of the process graph"),
                ("T8 runs the other way", v_t8_back, "tail -> head"),
                ("T9 outlet 3 m past the H5 boot", v_t9_out, "tail -> head"),
                ("H5 head outlet 0.3 m higher on the drawing", v_head, "kit outlet"),
                ("T7 -> T8 spout made flat", v_flat, "falls >="),
                ("gravity pipe drawn uphill", v_uphill, "never goes up")]
    for name, patch, rule in variants:
        bad = copy.deepcopy(site)
        patch(bad)
        failed = [n for n, ok, _ in checks(bad) if not ok]
        hit = any(rule in n for n in failed)
        ok_all &= hit
        print(f"{'PASS' if hit else 'FAIL'}  broken variant must be rejected by its own rule — {name}: failed {failed}", flush=True)

    def nmap_with(**kw):
        m = copy.deepcopy(R.NODE_OBJECTS)
        m.update(kw)
        return m
    scene_variants = [("T7 mapped to the T11 conveyor", dict(nmap=nmap_with(T7=["G_H5_H6_T11_CONV_*"])), "inside its own equipment"),
                      ("H3 mapped to the H2 noria", dict(nmap=nmap_with(H3=["RECEIVING_NORIA_*_H2"])), "on the path"),
                      ("Ш1 pattern with a typo", dict(nmap=nmap_with(SH1=["RECEIVING_CT_BIN_SH2"])), "finds objects"),
                      ("H5 path up the empty leg", dict(leg_patch=mirror_h5), "buckets carry grain"),
                      ("T8 -> S1 drop onto the gallery edge beam", dict(leg_patch=drop_on_beam), "cross no foreign object")]
    for name, kw, rule in scene_variants:
        failed = [n for n, ok, _ in scene_checks(site, **kw) if not ok]
        hit = any(rule in n for n in failed)
        ok_all &= hit
        print(f"{'PASS' if hit else 'FAIL'}  broken variant must be rejected by its own rule — {name}: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
