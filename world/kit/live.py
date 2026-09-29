"""Control center, module L: the live scene — the Blender model follows the simulator state
(CONTROL_CENTER_SPEC.md §6). The kits are not changed: everything here works on the assembled scene.

  split_gates(scene, site)  tunnel gate objects by opening, and the merged gate meshes (H5_DIST_GATES, T8_GATES, ...) cut into their loose
                            parts; each part gets the id of its gate by plan position, looked up only among the
                            gates of its own family (tunnel openings, splitter branches, gallery drops — SITE)
  split_old_silos           the old silos «2», «3» share one merged mesh per part kind: cut into OS2 / OS3 parts
  object_map(scene, site)   process node -> Blender objects, all 42 nodes (routes.NODE_OBJECTS extended); nodes
                            with no body of their own are in NO_BODY with the reason
  wrap_materials()          LIVE_FX before every material output: the surface mixed towards the emission of the
                            object's `live_rgb` by the share `live_on` (object attributes, so one material serves every object)
  flow_curves(scene, site)  a thin tube along the grain path of every edge (routes.edge_legs) and every mover,
                            hidden until grain moves there; owners the kits give no path for are reported
  grain_heaps(scene, site)  per silo a level body and the repose cone, sized from the mass
  trees_merge(scene)        the 55 k tree instances as a few merged low-poly meshes (viewport speed)
  Live.apply(state)         the state contract (world/sim/STATE_SCHEMA.json) onto the objects, only what changed
  Live.motion               the grain packets along the flow lines (live_motion.py), drawn as a viewport overlay

The real gate plate is inside its casing, so an open gate is shown by the colour of its body, not by motion.
Colours follow the panel: running = amber (the route colour of 7C), starting / stopping = light blue,
trip / fault = red (alarm colour, research R7), open gate = amber.
"""

import fnmatch
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from . import process as pr
from . import routes as R
from . import silo_interior as si
from . import silo_msvu220 as silo
from . import tunnel as tun

GROUP = "LIVE_FX"
ON, RGB = "live_on", "live_rgb"
AMBER = (1.0, 0.38, 0.02)
BLUE = (0.15, 0.45, 1.0)
RED = (1.0, 0.03, 0.03)
# object attribute live_on = share of the colour in the surface (0..1); emission strength inside the group is fixed.
# 2026-09-29: emission added at strength 6-10 washed amber to peach on galvanised steel under AgX.
EM_STRENGTH = 2.0
GLOW = {"run": (AMBER, 0.75), "starting": (BLUE, 0.75), "stopping": (BLUE, 0.75), "fault": (RED, 0.85), "trip": (RED, 0.85),
        "open": (AMBER, 0.8), "opening": (BLUE, 0.8), "closing": (BLUE, 0.8)}

# Nodes with no body of their own in the model (the flow line shows them) — the reason is part of the contract.
NO_BODY = {
    "TRUCK_IN": "a truck on the lane: the trucks of FIGURES are for scale, not per process node",
    "TRUCK_OUT": "the truck under Ш1: as TRUCK_IN",
    "TRUCK_EXIT": "a lane end",
    "NODE_1": "a point of the drawing (вузол «1»)",
}
# Patterns for the nodes routes.NODE_OBJECTS does not cover (site.py object names).
MORE_OBJECTS = {
    "H2": ["RECEIVING_NORIA_*_H2"], "H4": ["RECEIVING_NORIA_*_H4"],
    "T2": ["RECEIVING_CONVEYOR_T2"], "T4": ["RECEIVING_CONVEYOR_T4"], "T6": ["RECEIVING_CONVEYOR_T6"],
    "T7": ["G_H14_H5_T7_CONV_*"], "T10": ["G_H14_H5_T10_CONV_*"],
    "T11": ["G_H5_H6_T11_CONV_*"], "T14": ["G_H5_H6_T14_CONV_*"],
    "T12": ["T12_CONV_*"], "T15": ["T15_CONV_*"], "T13": ["T13_CONV_*"], "T16": ["T16_CONV_*"],
    "H6": ["H6_NORIA_*", "H6_DIST_*"],
    "S2": ["S2", "S2_FOUNDATION_*"], "S3": ["S3", "S3_FOUNDATION_*"], "S4": ["S4", "S4_FOUNDATION_*"],
    "S5": ["S5", "S5_FOUNDATION_*"], "S6": ["S6", "S6_FOUNDATION_*"],
    "OS2": ["LIVE_PART_OS2_*"], "OS3": ["LIVE_PART_OS3_*"],
    "DRYER": ["RECEIVING_DRYER*"], "T3": ["RECEIVING_T3_*"], "T5": ["RECEIVING_T5_*"],
}
# merged mesh -> the family of gates it may hold (a gallery drop over a silo centre is never the silo gate)
MERGED_GATES = {
    "H5_DIST_GATES": "dist:H5", "H6_DIST_GATES": "dist:H6", "H5_DIST_GATE_MOTORS": "dist:H5", "H6_DIST_GATE_MOTORS": "dist:H6",
    "T8_GATES": "gallery:T8", "T12_GATES": "gallery:T12", "T15_GATES": "gallery:T15",
}
MERGED_OLD_SILOS = ("RECEIVING_OLD_SILO_WALLS", "RECEIVING_OLD_SILO_ROOFS", "RECEIVING_OLD_SILO_PLINTHS", "RECEIVING_OLD_SILO_CHAIRS")
MAX_D = 0.05         # m in plan: every part must lie on an expected centre of a part of its gate (kit geometry)
TUNNEL_GATE_D = 0.9  # m in plan: a tunnel gate object (tunnel.build: <T>_GATE_<nn>_<group>) belongs to the opening
                     # whose centre is this close; the drive and handwheel reach ~0.7 m out, the openings are 3.25 m apart
PTS_PER_PLACE = {"tunnel": 1, "dist": 2, "gallery": 2}   # gate_points centres per opening / branch / drop


# ------------------------------------------------------------------ splitting merged meshes

def gate_points(site):
    """{family: {"gates" | "motors": {gate id: [(x, y) plan centres]}}} (family = the values of MERGED_GATES).
    The centres are where the kits put each loose part of a gate (the offsets below are the kits' own sizes, so
    a kit change shows up as unassigned parts in check_live):
      tunnel   the opening centre (x, row) only: tunnel.build makes one object per group and opening
               (<T>_GATE_<nn>_BODY / _MOTOR / _HANDWHEELS / _DARK), assigned by plan distance (TUNNEL_GATE_D);
               the opening under the silo centre is <silo>.c, the others <silo>.s (SITE silo_gates);
      splitter distribution.build: the gate box on the branch, the housing at +0.425 in x, the motor at
               (+0.52, +0.17); the gate is the one of the edge whose spout starts at that branch (SITE distribution);
      gallery  gallery.silo_row_gallery: the gate box on the drop over the silo, the housing at +0.425 in x."""
    g = pr.Graph(site)
    by_edge = {(e["from"], e["to"]): e for e in g.edges}
    silos = {s["id"]: s for s in site["silos"]}
    out = {}

    def put(fam, kind, gid, xy):
        out.setdefault(fam, {"gates": {}, "motors": {}})[kind].setdefault(gid, []).append(xy)

    for t in site.get("tunnels", []):
        fam, y = f"tunnel:{t['conveyor']['id']}", t["row_y"]
        feeders = [e for e in g.edges if e["to"] == t["conveyor"]["id"] and e["from"] in silos]
        for x, size in tun._gate_positions(site, t):
            sid = min(feeders, key=lambda e: abs(silos[e["from"]]["x"] - x))["from"]
            e = by_edge[(sid, t["conveyor"]["id"])]
            gid = e["gates"][0] if abs(silos[sid]["x"] - x) < 0.3 else e["alt_gates"][0]
            put(fam, "gates", gid, (x, y))
    for d in site.get("distribution", []):
        fam = f"dist:{d['tower']}"
        for spl in d["splitters"]:
            for b in spl["branches"]:
                sp = next((x for x in d["spouts"] if math.dist(x["path"][0], b) < 0.02), None)
                if sp is None:
                    continue
                to = sp["to"].split()[0]                    # "T11 head" -> T11
                e = by_edge.get((sp.get("from_conveyor") or d["tower"], to))
                if e is None or not e["gates"]:
                    continue
                gid = e["gates"][-1]
                put(fam, "gates", gid, (b[0], b[1]))
                put(fam, "gates", gid, (b[0] + 0.425, b[1]))
                put(fam, "motors", gid, (b[0] + 0.52, b[1] + 0.17))
    for line in site["silo_top_galleries"]["lines"]:
        fam = f"gallery:{line['id']}"
        for dx in line["drops_x"]:
            sid = min(silos, key=lambda s: math.hypot(silos[s]["x"] - dx, silos[s]["y"] - line["row_y"]))
            e = by_edge.get((line["id"], sid))
            if e is not None:
                put(fam, "gates", e["gates"][0], (dx, line["row_y"]))
                put(fam, "gates", e["gates"][0], (dx + 0.425, line["row_y"]))
    return out


def _islands(bm):
    bm.verts.ensure_lookup_table()
    seen, out = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        seen.add(v.index)
        while stack:
            a = stack.pop()
            isl.append(a.index)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index)
                    stack.append(b)
        out.append(sorted(isl))
    return out


def split_by_points(ob, points, prefix, max_d=MAX_D):
    """Cut `ob` into its loose parts; each part gets the id of the nearest plan point of `points` ({id: [(x, y)]})
    within max_d. The parts are linked next to `ob`, `ob` is hidden. Returns ([(id or None, part, distance)],
    vertices before, vertices after)."""
    flat = [(i, np.array(p)) for i, ps in points.items() for p in ps]
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    mw = ob.matrix_world
    bm.verts.ensure_lookup_table()
    co = np.array([tuple(mw @ v.co) for v in bm.verts])
    out, total = [], 0
    for k, isl in enumerate(_islands(bm)):
        c = co[isl].mean(axis=0)
        gid, dist = None, None
        if flat:
            i, p = min(flat, key=lambda ip: float(np.hypot(*(c[:2] - ip[1]))))
            dist = float(np.hypot(*(c[:2] - p)))
            if dist <= max_d:
                gid = i
        b2 = bm.copy()
        keep = set(isl)
        b2.verts.ensure_lookup_table()
        bmesh.ops.delete(b2, geom=[v for v in b2.verts if v.index not in keep], context="VERTS")
        me = bpy.data.meshes.new(f"{prefix}_{gid or 'NONE'}_{ob.name}_{k}")
        b2.to_mesh(me)
        b2.free()
        total += len(me.vertices)
        for m in ob.data.materials:
            me.materials.append(m)
        o = bpy.data.objects.new(me.name, me)
        o.matrix_world = mw.copy()
        for col in ob.users_collection:
            col.objects.link(o)
        o["part_of"] = gid or ""
        out.append((gid, o, dist))
    n0 = len(ob.data.vertices)
    bm.free()
    ob.hide_viewport = ob.hide_render = True
    ob["split_into_parts"] = True
    return out, n0, total


def split_gates(scene, site):
    """({gate id: [part objects]}, [(name, distance to the nearest expected centre) of parts of no gate],
    {merged mesh: (vertices before, after)})."""
    fam = gate_points(site)
    by_gate, loose, count = {}, [], {}
    for name, f in MERGED_GATES.items():
        ob = scene.objects.get(name)
        if ob is None:
            continue
        kind = "motors" if name.endswith("MOTORS") else "gates"
        parts, n0, n1 = split_by_points(ob, fam.get(f, {}).get(kind, {}), "GATE")
        count[name] = (n0, n1)
        for gid, o, dist in parts:
            if gid:
                by_gate.setdefault(gid, []).append(o)
            else:
                loose.append((o.name, dist))
    for t in site.get("tunnels", []):                    # tunnel gates are already one object per group and opening
        pts = [(gid, np.array(p)) for gid, ps in fam.get(f"tunnel:{t['conveyor']['id']}", {}).get("gates", {}).items() for p in ps]
        objs = [o for o in scene.objects if o.name.startswith(f"{t['id']}_GATE_") and o.type == "MESH"]
        for o in objs:
            mw = o.matrix_world
            bb = [mw @ Vector(v) for v in o.bound_box]
            cxy = np.array([sum(v.x for v in bb) / 8, sum(v.y for v in bb) / 8])
            gid, d = min(((g, float(np.hypot(*(cxy - p)))) for g, p in pts), key=lambda gd: gd[1], default=(None, None))
            if gid and d <= TUNNEL_GATE_D:
                by_gate.setdefault(gid, []).append(o)
                o["part_of"] = gid
            else:
                loose.append((o.name, d))
        count[f"{t['id']}_GATE_*"] = (len(objs), len(objs))
    return by_gate, loose, count


def split_old_silos(scene, site):
    """The old silos «2», «3» are one merged mesh per part kind: cut them into LIVE_PART_OS2_* / LIVE_PART_OS3_*."""
    pts = {s["id"]: [(s["x"], s["y"])] for s in site["receiving"]["old_silos"]}
    count = {}
    for name in MERGED_OLD_SILOS:
        ob = scene.objects.get(name)
        if ob is None:
            continue
        parts, n0, n1 = split_by_points(ob, pts, "LIVE_PART", max_d=8.0)
        for gid, o, _ in parts:
            if gid:
                o.name = f"LIVE_PART_{gid}_{name}_{o.name.rsplit('_', 1)[-1]}"
        count[name] = (n0, n1)
    return count


# ------------------------------------------------------------------ node -> objects

def object_map(scene, site=None):
    names = [o.name for o in scene.objects if not o.get("split_into_parts")]
    g = pr.Graph(site)
    pats = dict(R.NODE_OBJECTS)
    pats.update({k: v for k, v in MORE_OBJECTS.items() if k not in pats})
    return {n: sorted({x for p in pats.get(n, []) for x in fnmatch.filter(names, p)}) for n in g.nodes}


# ------------------------------------------------------------------ LIVE_FX

def _group():
    g = bpy.data.node_groups.get(GROUP)
    if g:
        return g
    g = bpy.data.node_groups.new(GROUP, "ShaderNodeTree")
    g.interface.new_socket("Shader", in_out="INPUT", socket_type="NodeSocketShader")
    g.interface.new_socket("Shader", in_out="OUTPUT", socket_type="NodeSocketShader")
    n, ln = g.nodes, g.links.new
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    on = n.new("ShaderNodeAttribute")
    on.attribute_type, on.attribute_name = "OBJECT", ON
    col = n.new("ShaderNodeAttribute")
    col.attribute_type, col.attribute_name = "OBJECT", RGB
    em = n.new("ShaderNodeEmission")
    ln(col.outputs["Color"], em.inputs["Color"])
    em.inputs["Strength"].default_value = EM_STRENGTH
    mix = n.new("ShaderNodeMixShader")                 # mix towards the colour, not add: adding to a bright surface goes white under AgX
    ln(on.outputs["Fac"], mix.inputs["Fac"])
    ln(gi.outputs["Shader"], mix.inputs[1])
    ln(em.outputs[0], mix.inputs[2])
    ln(mix.outputs[0], go.inputs["Shader"])
    return g


def wrap_materials():
    """Put LIVE_FX before the output of every opaque node material (cut-out materials keep their holes)."""
    from . import route_fx as fx
    g = _group()
    k = 0
    for mat in bpy.data.materials:
        if not mat.use_nodes or mat.get("live_fx"):
            continue
        out = next((nd for nd in mat.node_tree.nodes if nd.type == "OUTPUT_MATERIAL" and nd.is_active_output), None)
        if out is None or not out.inputs["Surface"].is_linked:
            continue
        sp = fx._splice_point(mat, out)
        if sp is None:
            continue
        src, dst = sp
        node = mat.node_tree.nodes.new("ShaderNodeGroup")
        node.node_tree = g
        mat.node_tree.links.new(src, node.inputs[0])
        mat.node_tree.links.new(node.outputs[0], dst)
        mat["live_fx"] = True
        k += 1
    return k


def set_glow(objs, key):
    """key: a state name of GLOW, or None for off. Returns how many objects changed."""
    col, s = GLOW[key] if key in GLOW else ((0.0, 0.0, 0.0), 0.0)
    k = 0
    for o in objs:
        if o.get(ON) != s or tuple(o.get(RGB, (0, 0, 0))) != tuple(col):
            o[ON] = s
            o[RGB] = col
            o.update_tag()
            k += 1
    return k


# ------------------------------------------------------------------ flow lines

def flow_material():
    m = bpy.data.materials.get("LIVE_FLOW")
    if m:
        return m
    m = bpy.data.materials.new("LIVE_FLOW")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*AMBER, 1.0)
    em.inputs["Strength"].default_value = 2.5            # brighter goes white under the AgX / Filmic view transform
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    m["live_fx"] = True
    return m


def _tube(name, pts, radius, mat, collection):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 2
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (float(q[0]), float(q[1]), float(q[2]), 1.0)
    ob = bpy.data.objects.new(name, cu)
    ob.data.materials.append(mat)
    collection.objects.link(ob)
    return ob


def mover_path(site, n):
    """Grain path along a mover: the conveyor casing centreline, or the noria lift (kit geometry)."""
    from . import drying as dr
    if pr.Graph(site).nodes[n]["kind"] == "noria":
        return np.asarray(R.noria_leg(site, n, None)[0].pts, float)
    if n in ("T3", "T5"):
        a, b = dr.conv_axis(n, site)
    else:
        a, b, _, _ = R.conveyor_axis(site, n)
    return np.array([a, b], float)


def flow_paths(site, with_kinds=False):
    """({owner: [point arrays]}, {owner: reason}) — edges by routes.edge_legs, movers by mover_path.
    with_kinds: also {owner: [leg kind]} (routes.Leg.kind: drive | fall | ...; a mover is "mover")."""
    g = pr.Graph(site)
    paths, fails, kinds = {}, {}, {}
    for e in g.edges:
        key = f"{e['from']}->{e['to']}"
        try:
            legs = R.edge_legs(site, e, None)
            paths[key] = [np.asarray(lg.pts, float) for lg in legs]
            kinds[key] = [lg.kind for lg in legs]
        except Exception as ex:                                  # noqa: BLE001  reported by check_live
            fails[key] = f"{type(ex).__name__}: {ex}"
    for n, v in g.nodes.items():
        if v["kind"] in pr.MOVERS:
            try:
                paths[n] = [mover_path(site, n)]
                kinds[n] = ["mover"]
            except Exception as ex:                              # noqa: BLE001
                fails[n] = f"{type(ex).__name__}: {ex}"
    return (paths, fails, kinds) if with_kinds else (paths, fails)


def flow_curves(scene, site, radius=0.09, paths=None, fails=None):
    col = bpy.data.collections.get("LIVE_FLOW") or bpy.data.collections.new("LIVE_FLOW")
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    mat = flow_material()
    if paths is None:
        paths, fails = flow_paths(site)
    out = {}
    for owner, plist in paths.items():
        objs = []
        for pts in plist:
            if len(pts) < 2:
                continue
            ob = _tube(f"LIVE_FLOW_{owner}_{len(objs)}", pts, radius, mat, col)
            ob.hide_viewport = ob.hide_render = True
            objs.append(ob)
        out[owner] = objs
    return out, fails


# ------------------------------------------------------------------ grain in the silos

def heap_top(mass_t, rho):
    """(top, level at the wall) over the silo floor for `mass_t`: the silo_interior heap, a level body plus the
    repose cone under the roof spout; while the grain is under one full cone, a cone alone."""
    r, tan = si.R_IN, math.tan(si.REPOSE)
    v = mass_t / rho
    cone = math.pi * r * r * r * tan / 3
    if v <= cone:
        rr = (3 * v / (math.pi * tan)) ** (1 / 3)
        return rr * tan, 0.0
    h_wall = (v - cone) / (math.pi * r * r)
    return h_wall + r * tan, h_wall


def grain_heaps(scene, site):
    """{silo: (body, cone)}: a unit cylinder and a unit cone (base at z 0, top at z 1), hidden until there is grain."""
    col = bpy.data.collections.get("LIVE_GRAIN") or bpy.data.collections.new("LIVE_GRAIN")
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    mat = bpy.data.materials.get("WHEAT") or si.mat_grain()
    out = {}
    for s in site["silos"]:
        pair = []
        for part, r2 in (("BODY", si.R_IN), ("CONE", 0.0)):
            me = bpy.data.meshes.new(f"LIVE_GRAIN_{s['id']}_{part}")
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=96, radius1=si.R_IN, radius2=r2, depth=1.0)
            bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.5))
            bm.to_mesh(me)
            bm.free()
            me.materials.append(mat)
            o = bpy.data.objects.new(me.name, me)
            o.location = (s["x"], s["y"], s["z"] + silo.FLOOR_Z)
            o.hide_viewport = o.hide_render = True
            col.objects.link(o)
            pair.append(o)
        out[s["id"]] = tuple(pair)
    return out


def set_heap(pair, mass_t, rho, base_z):
    """Body up to the level at the wall and the repose cone on it; a cone alone while under one full cone.
    Returns the height of the heap top over the floor."""
    body, cone = pair
    if mass_t <= 1e-6:
        for o in pair:
            o.hide_viewport = o.hide_render = True
        return 0.0
    top, h_wall = heap_top(mass_t, rho)
    r, tan = si.R_IN, math.tan(si.REPOSE)
    if h_wall <= 0:
        k = (top / tan) / r
        cone.scale = (k, k, top)
        cone.location.z = base_z
        body.hide_viewport = body.hide_render = True
    else:
        body.scale = (1.0, 1.0, h_wall)
        body.location.z = base_z
        body.hide_viewport = body.hide_render = False
        cone.scale = (1.0, 1.0, r * tan)
        cone.location.z = base_z + h_wall
    cone.hide_viewport = cone.hide_render = False
    return top


# ------------------------------------------------------------------ trees

def trees_merge(scene, ratio=0.06, chunks=16):
    """The viewport cost of the shelterbelts is the 55 k tree objects, not their faces (a decimated prototype
    alone left the frame at ~170 ms). Replace the instances by `chunks` merged meshes of the decimated
    prototypes, split along x so that off-screen chunks are culled; the TREES collection is excluded, the
    rendered look of the belts stays (same prototypes, same materials). Returns (trees, faces)."""
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    protos = {}
    for col in bpy.data.collections:
        if not col.name.startswith("KIT_TREE_"):
            continue
        parts = []
        for o in col.objects:
            if o.type != "MESH":
                continue
            m = o.modifiers.get("LIVE_LOD") or o.modifiers.new("LIVE_LOD", "DECIMATE")
            m.ratio = ratio
            bpy.context.view_layer.update()
            ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
            me = ev.to_mesh()
            v = np.empty(len(me.vertices) * 3)
            me.vertices.foreach_get("co", v)
            v = v.reshape(-1, 3)
            mw = np.array(o.matrix_world)
            v = v @ mw[:3, :3].T + mw[:3, 3]
            me.calc_loop_triangles()
            t = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
            me.loop_triangles.foreach_get("vertices", t)
            parts.append((v, t.reshape(-1, 3), o.active_material))
            ev.to_mesh_clear()
        protos[col.name] = parts
    inst = [o for o in scene.objects if o.instance_type == "COLLECTION" and o.instance_collection
            and o.instance_collection.name in protos]
    if not inst:
        return 0, 0
    out_col = bpy.data.collections.get("LIVE_TREES") or bpy.data.collections.new("LIVE_TREES")
    if out_col.name not in scene.collection.children:
        scene.collection.children.link(out_col)
    xs = np.array([o.matrix_world.translation.x for o in inst])
    edges = np.quantile(xs, np.linspace(0, 1, chunks + 1))
    faces_total = 0
    for c in range(chunks):
        sel = [o for o, x in zip(inst, xs) if edges[c] <= x <= edges[c + 1] and (c == chunks - 1 or x < edges[c + 1])]
        by_part = {}
        for o in sel:
            for k, (v, t, mat) in enumerate(protos[o.instance_collection.name]):
                by_part.setdefault((mat.name if mat else "", len(v), len(t), o.instance_collection.name, k), []).append(np.array(o.matrix_world))
        for (mname, _, _, cname, k), mats in by_part.items():
            v, t, mat = protos[cname][k]
            M = np.stack(mats)                                   # (n, 4, 4)
            V = np.einsum("nij,vj->nvi", M[:, :3, :3], v) + M[:, None, :3, 3]
            n, nv = V.shape[0], v.shape[0]
            F = (t[None, :, :] + (np.arange(n) * nv)[:, None, None]).reshape(-1, 3)
            me = bpy.data.meshes.new(f"LIVE_TREES_{c}_{cname}_{k}")
            me.vertices.add(n * nv)
            me.vertices.foreach_set("co", V.reshape(-1).astype(np.float32))
            me.loops.add(len(F) * 3)
            me.loops.foreach_set("vertex_index", F.reshape(-1).astype(np.int32))
            me.polygons.add(len(F))
            me.polygons.foreach_set("loop_start", np.arange(0, len(F) * 3, 3, dtype=np.int32))
            me.polygons.foreach_set("loop_total", np.full(len(F), 3, dtype=np.int32))
            me.update()
            if mat:
                me.materials.append(mat)
            ob = bpy.data.objects.new(me.name, me)
            out_col.objects.link(ob)
            faces_total += len(F)
    lc = bpy.context.view_layer.layer_collection.children.get("TREES")
    if lc is not None:
        lc.exclude = True          # out of the view layer: hidden objects still cost every depsgraph update
    return len(inst), faces_total


# ------------------------------------------------------------------ state -> scene

NEVER = object()          # "not applied yet": differs from every state, also from None (= off)


def motor_key(m, v, trip):
    """The look of a motor: fault (state or a trip alarm of its own), else its state, None when off."""
    return "fault" if m in trip or v["state"] == "fault" else (v["state"] if v["state"] != "off" else None)


def moving_owners(st):
    """Owners whose grain moves in state `st`: a mover that RUNS (not starting, stopping, off, faulted or tripped)
    and carries grain, and every edge with t/h > 0. Everything else stands."""
    trip = {a["id"].split(".")[0] for a in st.get("alarms", []) if a["level"] == "trip"}
    out = {m for m, v in st["motors"].items() if motor_key(m, v, trip) == "run" and v["load_t_h"] > 0}
    out |= {e for e, v in st["edges"].items() if v["t_h"] > 0}
    return out


class Live:
    def __init__(self, scene, site, rho, speeds=None):
        self.scene, self.site, self.rho = scene, site, rho
        bpy.context.view_layer.update()               # once: matrix_world of objects moved by .location (the towers)
        self.gates, self.gate_loose, self.gate_count = split_gates(scene, site)
        self.old_silo_count = split_old_silos(scene, site)
        self.nodes = object_map(scene, site)
        from . import live_motion as mo
        paths, fails, kinds = flow_paths(site, with_kinds=True)
        self.flows, self.flow_fails = flow_curves(scene, site, paths=paths, fails=fails)
        # grain packets along the flow lines (live_motion.py): a truck on its lane is not grain, it does not move
        self.paths, self.static = paths, {o for o, ks in kinds.items() if ks and all(k == "drive" for k in ks)}
        self.motion = mo.Motion(paths, speeds if speeds is not None else mo.mover_speeds(), self.static)
        self.heaps = grain_heaps(scene, site)
        self.base_z = {s["id"]: s["z"] + silo.FLOOR_Z for s in site["silos"]}
        self.wrapped = wrap_materials()
        self.last = {}

    def objs(self, node):
        return [self.scene.objects[n] for n in self.nodes.get(node, []) if n in self.scene.objects]

    def apply(self, st):
        """Apply a state dict; returns the number of objects touched (0 when nothing changed)."""
        k = 0
        trip = {a["id"].split(".")[0] for a in st.get("alarms", []) if a["level"] == "trip"}
        for m, v in st["motors"].items():
            key = motor_key(m, v, trip)
            if self.last.get(("m", m), NEVER) != key:
                k += set_glow(self.objs(m), key)
                self.last[("m", m)] = key
        for gid, v in st["gates"].items():
            key = v["state"] if v["state"] != "closed" else None
            if self.last.get(("g", gid), NEVER) != key:
                k += set_glow(self.gates.get(gid, []), key)
                self.last[("g", gid)] = key
        dk = "run" if st["dryer"]["state"] == "run" else None
        if self.last.get(("d",), NEVER) != dk:
            k += set_glow(self.objs("DRYER"), dk)
            self.last[("d",)] = dk
        moving = {e for e, v in st["edges"].items() if v["t_h"] > 0}
        moving |= {m for m, v in st["motors"].items() if v["load_t_h"] > 0}
        for owner, objs in self.flows.items():
            show = owner in moving
            if self.last.get(("f", owner), NEVER) != show:
                for o in objs:
                    o.hide_viewport = o.hide_render = not show
                k += len(objs)
                self.last[("f", owner)] = show
        self.motion.set_active(moving_owners(st))
        self.motion.set_paused(st.get("paused", False))
        for sid, pair in self.heaps.items():
            m = round(st["stores"].get(sid, {}).get("mass_t", 0.0), 1)
            if self.last.get(("s", sid), NEVER) != m:
                set_heap(pair, m, self.rho, self.base_z[sid])
                self.last[("s", sid)] = m
                k += 1
        return k
