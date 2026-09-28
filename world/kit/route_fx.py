"""Phase 7C: route highlighting in the scene and the grain-flow overlay of the «шлях зерна» reel.

highlight(scene, names)   objects of the route get the custom property `route_on` = 1 (an instanced
                          silo: on its empty). One node group ROUTE_FX is spliced before every material
                          output: route objects get an amber rim (Fresnel facing) and a faint glow, the
                          rest of the scene is mixed towards a flat grey by `dim`. set_fx(dim, glow) drives
                          all materials at once through the group's two value nodes.
FlowOverlay               the cycle path (routes.polyline) resampled by arc length, projected into the
                          camera; a ray from the camera to each sample says whether it is seen or behind
                          something. Drawn with PIL over the rendered frame: seen parts as a bright amber
                          line with running chevrons, hidden parts faint and dashed («x-ray»), a bright
                          dot at the grain front. Nothing is rendered twice.
"""

import math

import bpy
import numpy as np
from mathutils import Vector

AMBER = (1.0, 0.50, 0.06, 1.0)
AMBER_RGB = (255, 150, 30)
PROP = "route_on"
GROUP = "ROUTE_FX"


# ------------------------------------------------------------------ highlight

def _group():
    g = bpy.data.node_groups.get(GROUP)
    if g:
        return g
    g = bpy.data.node_groups.new(GROUP, "ShaderNodeTree")
    g.interface.new_socket("Shader", in_out="INPUT", socket_type="NodeSocketShader")
    g.interface.new_socket("On", in_out="INPUT", socket_type="NodeSocketFloat")
    g.interface.new_socket("Shader", in_out="OUTPUT", socket_type="NodeSocketShader")
    n, ln = g.nodes, g.links.new
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    dim = n.new("ShaderNodeValue")
    dim.name = dim.label = "DIM"
    glow = n.new("ShaderNodeValue")
    glow.name = glow.label = "GLOW"
    dim.outputs[0].default_value = 0.0
    glow.outputs[0].default_value = 0.0
    off = n.new("ShaderNodeMath")
    off.operation = "SUBTRACT"
    off.inputs[0].default_value = 1.0
    ln(gi.outputs["On"], off.inputs[1])
    fac = n.new("ShaderNodeMath")
    fac.operation = "MULTIPLY"
    ln(dim.outputs[0], fac.inputs[0])
    ln(off.outputs[0], fac.inputs[1])
    grey = n.new("ShaderNodeBsdfDiffuse")
    grey.inputs["Color"].default_value = (0.30, 0.31, 0.32, 1.0)
    mix = n.new("ShaderNodeMixShader")
    ln(fac.outputs[0], mix.inputs["Fac"])
    ln(gi.outputs["Shader"], mix.inputs[1])
    ln(grey.outputs[0], mix.inputs[2])
    lw = n.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    rim = n.new("ShaderNodeMath")
    rim.operation = "POWER"
    ln(lw.outputs["Facing"], rim.inputs[0])
    rim.inputs[1].default_value = 2.0
    base = n.new("ShaderNodeMath")                  # rim + a faint body glow
    base.operation = "MULTIPLY_ADD"
    ln(rim.outputs[0], base.inputs[0])
    base.inputs[1].default_value = 1.0
    base.inputs[2].default_value = 0.05
    s1 = n.new("ShaderNodeMath")
    s1.operation = "MULTIPLY"
    ln(base.outputs[0], s1.inputs[0])
    ln(glow.outputs[0], s1.inputs[1])
    s2 = n.new("ShaderNodeMath")
    s2.operation = "MULTIPLY"
    ln(s1.outputs[0], s2.inputs[0])
    ln(gi.outputs["On"], s2.inputs[1])
    em = n.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = AMBER
    ln(s2.outputs[0], em.inputs["Strength"])
    add = n.new("ShaderNodeAddShader")
    ln(mix.outputs[0], add.inputs[0])
    ln(em.outputs[0], add.inputs[1])
    ln(add.outputs[0], go.inputs["Shader"])
    return g


def _transparent(mat):
    return any(nd.type in ("BSDF_TRANSPARENT", "HOLDOUT") for nd in mat.node_tree.nodes)


def _splice_point(mat, out):
    """(source socket, target socket) to put ROUTE_FX between: the surface output, or for a cut-out
    material (grating: Mix(Transparent, BSDF)) the opaque branch only, so the holes stay holes."""
    dst = out.inputs["Surface"]
    src = dst.links[0].from_socket
    nd = src.node
    if nd.type == "MIX_SHADER":
        ins = [nd.inputs[1], nd.inputs[2]]
        clear = [s for s in ins if s.is_linked and s.links[0].from_node.type == "BSDF_TRANSPARENT"]
        other = [s for s in ins if s not in clear and s.is_linked]
        if len(clear) == 1 and len(other) == 1:
            return other[0].links[0].from_socket, other[0]
    if _transparent(mat):
        return None
    return src, dst


def wrap_materials():
    """Splice ROUTE_FX into every node material (once). Returns the count."""
    g = _group()
    k = 0
    for mat in bpy.data.materials:
        if not mat.use_nodes or mat.get("route_fx"):
            continue
        nt = mat.node_tree
        out = next((nd for nd in nt.nodes if nd.type == "OUTPUT_MATERIAL" and nd.is_active_output), None)
        if out is None or not out.inputs["Surface"].is_linked:
            continue
        sp = _splice_point(mat, out)
        if sp is None:
            continue
        src, dst = sp
        a_obj = nt.nodes.new("ShaderNodeAttribute")
        a_obj.attribute_type, a_obj.attribute_name = "OBJECT", PROP
        a_ins = nt.nodes.new("ShaderNodeAttribute")
        a_ins.attribute_type, a_ins.attribute_name = "INSTANCER", PROP
        on = nt.nodes.new("ShaderNodeMath")
        on.operation = "MAXIMUM"
        nt.links.new(a_obj.outputs["Fac"], on.inputs[0])
        nt.links.new(a_ins.outputs["Fac"], on.inputs[1])
        grp = nt.nodes.new("ShaderNodeGroup")
        grp.node_tree = g
        nt.links.new(src, grp.inputs["Shader"])
        nt.links.new(on.outputs[0], grp.inputs["On"])
        nt.links.new(grp.outputs["Shader"], dst)
        mat["route_fx"] = 1
        k += 1
    return k


def highlight(scene, names):
    """Mark the route objects (and nothing else)."""
    names = set(names)
    for o in scene.objects:
        if PROP in o.keys():
            del o[PROP]
    for n in names:
        o = scene.objects.get(n)
        if o is not None:
            o[PROP] = 1.0
    return len(names)


def set_fx(dim, glow):
    g = _group()
    g.nodes["DIM"].outputs[0].default_value = float(dim)
    g.nodes["GLOW"].outputs[0].default_value = float(glow)


# ------------------------------------------------------------------ flow overlay

SEEN_IN_CASING = 0.45       # m: a path this close behind the first surface is inside a casing, drawn as seen
SILO_PROXY = (11.0, 15.0, 21.4)   # m, wall radius, eave z, peak z over the silo base (SILO_WALL / SILO_ROOF boxes)
# thin members do not hide a conveyor or a pipe behind them (and would chop the line into flicker)
THIN = ("RAILS", "RUNGS", "STILES", "CAGE", "TOES", "TOE_BOARDS", "BRACING", "LADDER", "FENCE", "HANDWHEELS",
        "LIGHT_", "HYDRANTS", "BARRIERS")


def rendered(ob):
    return not ob.hide_render and not any(col.hide_render for col in ob.users_collection)


def occluder(scene, segments=48):
    """BVH of what hides the path, built once per reel: scene_bvh without thin members and owners."""
    return scene_bvh(scene, segments, all_parts=False)[0]


def scene_bvh(scene, segments=48, all_parts=True):
    """(BVH, owner name per face): every rendered mesh except trees and labels (and thin members unless
    all_parts); a silo instance as a cylinder with its cone roof, owned by the instance empty (the real
    wall is 2.4 M faces)."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    V, F, owner, base = [], [], [], 0
    for o in scene.objects:
        if o.type == "EMPTY" and o.instance_collection and o.instance_collection.name.startswith("KIT_SILO"):
            r, ze, zp = SILO_PROXY
            x, y, z = o.matrix_world.translation
            a = np.linspace(0, 2 * math.pi, segments, endpoint=False)
            ring = lambda zz: np.stack([x + r * np.cos(a), y + r * np.sin(a), np.full(segments, z + zz)], axis=1)
            v = np.vstack([ring(0.0), ring(ze), [(x, y, z + zp)]])
            f = [(i, (i + 1) % segments, segments + (i + 1) % segments, segments + i) for i in range(segments)]
            f += [(segments + i, segments + (i + 1) % segments, 2 * segments) for i in range(segments)]
        elif o.type == "MESH" and rendered(o) and not o.name.startswith(("TREE", "LBL_")) and \
                (all_parts or not any(k in o.name for k in THIN)):
            me = o.evaluated_get(dg).to_mesh()
            mw = np.array(o.matrix_world)
            co = np.empty(len(me.vertices) * 3)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
            v = co
            f = [tuple(p.vertices) for p in me.polygons]
            o.evaluated_get(dg).to_mesh_clear()
        else:
            continue
        V.append(np.asarray(v, float))
        F += [tuple(i + base for i in q) for q in f]
        owner += [o.name] * len(f)
        base += len(v)
    return BVHTree.FromPolygons(np.vstack(V).tolist(), F), owner


class FlowOverlay:
    """The cycle path resampled every `step` m; each route of the cycle keeps its own arc length."""

    def __init__(self, scene, paths, step=0.25):
        self.scene = scene
        self.tree = occluder(scene)
        self.paths = []
        for pts in paths:
            pts = np.asarray(pts, float)
            seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
            s = np.concatenate([[0.0], np.cumsum(seg)])
            ss = np.arange(0.0, s[-1] + 1e-9, step)
            xyz = np.stack([np.interp(ss, s, pts[:, i]) for i in range(3)], axis=1)
            self.paths.append((ss, xyz))

    @property
    def lengths(self):
        return [p[0][-1] for p in self.paths]

    def project(self, cam, xyz):
        """Pixel (x, y), in front of the camera, seen (a ray from the camera reaches the point)."""
        from bpy_extras.object_utils import world_to_camera_view
        sc = self.scene
        r = sc.render
        w, h = r.resolution_x * r.resolution_percentage / 100, r.resolution_y * r.resolution_percentage / 100
        eye = cam.matrix_world.translation
        out = []
        for p in xyz:
            v = Vector(p)
            co = world_to_camera_view(sc, cam, v)
            front = co.z > 0.05
            seen = False
            if front and -0.1 <= co.x <= 1.1 and -0.1 <= co.y <= 1.1:
                d = v - eye
                dist = d.length
                loc, *_ = self.tree.ray_cast(eye, d.normalized(), max(dist - SEEN_IN_CASING, 0.01))
                seen = loc is None
            out.append((co.x * w, (1.0 - co.y) * h, front, seen))
        return out

    def draw(self, png, cam, progress, phase=0.0, alpha=1.0, spacing=2.4):
        """progress: metres shown of each path (list, None = all). phase: chevron offset in metres."""
        from PIL import Image, ImageDraw, ImageFilter

        im = Image.open(png).convert("RGBA")
        W, H = im.size
        k = 2                                                       # supersample the line layer
        glow = Image.new("RGBA", (W * k, H * k), (0, 0, 0, 0))
        line = Image.new("RGBA", (W * k, H * k), (0, 0, 0, 0))
        dg, dl = ImageDraw.Draw(glow), ImageDraw.Draw(line)
        lw = max(2, int(W / 480))
        a = int(255 * alpha)
        for (ss, xyz), prog in zip(self.paths, progress):
            if prog is not None and prog <= 0:
                continue
            n = len(ss) if prog is None else int(np.searchsorted(ss, prog))
            if n < 2:
                continue
            pr = self.project(cam, xyz[:n])
            for i in range(n - 1):
                x0, y0, f0, s0 = pr[i]
                x1, y1, f1, s1 = pr[i + 1]
                if not (f0 and f1):
                    continue
                p0, p1 = (x0 * k, y0 * k), (x1 * k, y1 * k)
                if s0 and s1:
                    dg.line([p0, p1], fill=AMBER_RGB + (int(a * 0.8),), width=lw * k * 4)
                    dl.line([p0, p1], fill=(255, 214, 120, a), width=lw * k)
                elif (i // 2) % 2 == 0:                             # hidden: faint dashes
                    dl.line([p0, p1], fill=AMBER_RGB + (int(a * 0.45),), width=max(1, lw * k // 2))
            for s_c in np.arange((phase % spacing), ss[n - 1], spacing):   # chevrons on the seen line
                i = int(np.searchsorted(ss, s_c))
                if i < 1 or i >= n - 1:
                    continue
                x0, y0, f0, s0 = pr[i - 1]
                x1, y1, f1, s1 = pr[i + 1]
                if not (f0 and f1 and s0 and s1):
                    continue
                dx, dy = x1 - x0, y1 - y0
                L = math.hypot(dx, dy)
                if L < 1e-3:
                    continue
                ux, uy = dx / L, dy / L
                cx, cy = pr[i][0] * k, pr[i][1] * k
                size = lw * k * 3.2
                tip = (cx + ux * size, cy + uy * size)
                wing = [(cx - ux * size * 0.2 + uy * size * 0.8, cy - uy * size * 0.2 - ux * size * 0.8),
                        (cx - ux * size * 0.2 - uy * size * 0.8, cy - uy * size * 0.2 + ux * size * 0.8)]
                dl.line([wing[0], tip, wing[1]], fill=(255, 245, 210, a), width=max(2, lw * k))
            if prog is not None and n < len(ss):                    # the grain front
                x, y, f, s = pr[n - 1]
                if f:
                    r_ = lw * k * (4 if s else 2.5)
                    dg.ellipse([x * k - 3 * r_, y * k - 3 * r_, x * k + 3 * r_, y * k + 3 * r_], fill=AMBER_RGB + (int(a * 0.7),))
                    dl.ellipse([x * k - r_, y * k - r_, x * k + r_, y * k + r_], fill=(255, 250, 230, a))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=lw * k * 3)).resize((W, H), Image.LANCZOS)
        line = line.resize((W, H), Image.LANCZOS)
        im = Image.alpha_composite(Image.alpha_composite(im, glow), line)
        im.convert("RGB").save(png)
