"""D3. Reel builder: one JSON -> MP4 in the "process -> final" format (CANON_WORLD).

Each shot names a scene, a render state and a camera move:
  state "clay"  - everything plain grey, like a viewport greybox
  state "wire"  - dark background, glowing mesh edges
  state "final" - full materials, sky, fog
  state "route" - full materials; the reel's grain cycle (spec "cycle", kit/routes.py) glows amber, the
                  rest is mixed towards grey by "fx": {"dim": [from, to], "glow": [from, to]} (phase 7C)
A hook text sits on top of the first seconds, a caption on each shot.

Phase 7C additions (all optional in the JSON):
  "device": "GPU"         OptiX on the RTX, persistent data (the scene syncs once, not per frame)
  "cycle": "full_cycle"   highlight + the flow overlay (kit/route_fx.py): each shot's "flow" moves the
                          grain front of each route between anchors "START", "END", "<node or edge>:start|end"
                          or metres, e.g. "flow": {"A": ["SCALES_IN:end", "T1:end"]}; fronts keep their
                          place between shots
  "props"                 [{"kind": "truck", "lane": "in", "over": "pit"}, {"kind": "tunnel_lights"}]
  "caption_pos": "bottom" lower-third captions (16:9)
  move "keys"             {"points": [...], "looks": [...]}: spline through key positions

Run:
    python world/build/reel.py world/reels/reel_02_grain_path.json [--preview] [--board] [--shots 3,4]
--preview renders at half size, 12 fps, 8 samples: to check the motion before a final render.
--board renders only the middle frame of each shot (a storyboard) into out/reels/<name>_board/.
"""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import bpy  # noqa: I001  bpy first: the pip module registers bmesh and mathutils
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import cameras as cm  # noqa: E402
from kit import common as c  # noqa: E402

FONT_CANDIDATES = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"]
FLOW_SPEED = 2.0            # m/s of the running chevrons (a look, not the conveyor speed)
TUNNEL_LAMP_W = 120.0       # as k4_tunnel
PATHS = "AB"                # the routes of a cycle, in order


# ------------------------------------------------------------------ scenes

def _load(name):
    """Load a build script by path (world/build/site.py would clash with Python's own `site`)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(f"world_build_{name}", ROOT / "build" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scene_site(quick):
    scene, *_ = _load("site").assemble(quick)
    return scene


SCENES = {"site": scene_site}


def use_gpu(scene):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        prefs.get_devices()
        if any(d.type == kind for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == kind
            scene.cycles.device = "GPU"
            scene.render.use_persistent_data = True
            if kind == "OPTIX":                     # measured 2026-09-28: default denoiser (OIDN, CPU)
                scene.cycles.denoiser = "OPTIX"      # costs ~5-6 s/frame more than the OptiX GPU denoiser
                scene.cycles.denoising_use_gpu = True
            return kind
    return "CPU"


# ------------------------------------------------------------------ 7C: cycle, props

def cycle_setup(scene, name):
    """Legs, highlight, overlay and anchors of a grain cycle."""
    from kit import process as pr
    from kit import route_fx as fx
    from kit import routes as R
    site = pr._site()
    cyc = R.cycle_legs(name, site)
    legs = [lg for _, ls in cyc for lg in ls]
    names = R.highlight_names([o.name for o in scene.objects], legs)
    fx.wrap_materials()
    fx.highlight(scene, names)
    ov = fx.FlowOverlay(scene, [R.polyline(ls)[0] for _, ls in cyc])
    return {"overlay": ov, "anchors": [anchors(ls) for _, ls in cyc], "lit": names}


def anchors(legs):
    """{owner: [start m, end m]} along one route's polyline (joint gaps bridged, as routes.polyline)."""
    s, prev, out = 0.0, None, {}
    for lg in legs:
        if prev is not None:
            s += float(np.linalg.norm(lg.pts[0] - prev))
        a = s
        s += lg.length
        prev = lg.pts[-1]
        o = lg.owner.split(" (")[0]
        out.setdefault(o, [a, s])[1] = s
    out["START"], out["END"] = [0.0, 0.0], [s, s]
    return out


def resolve(v, anc):
    if isinstance(v, (int, float)):
        return float(v)
    key, _, end = v.partition(":")
    a, b = anc[key]
    return a if end == "start" else b


def add_props(scene, props):
    from kit import figures as fg
    from kit import process as pr
    site = pr._site()
    made = []
    for p in props:
        if p["kind"] == "truck":
            src = {k: scene.objects[f"FIG_TRUCK_{k.upper()}"].data.materials[0] for k in ("cab", "glass", "trailer", "tarp", "wheels", "chassis")}
            t = {"lane": p["lane"], "x_front": p.get("x_front", 0.0)}
            dz = 0.0
            if p.get("over") == "pit":                         # trailer centre over the pit outlet, on the +0.100 drive
                pit = site["receiving"]["pit"]
                t0 = fg.TRACTOR_L - 1.6
                _, _, sgn, z = fg.truck_pose(site, t)
                t["x_front"] = pit["outlets"][0][0] + sgn * (t0 + fg.TRAILER_L / 2)
                dz = pit["deck_z"] - fg.truck_pose(site, t)[3]
            for k, (v, f) in fg.build_truck(site, t).items():
                v = np.asarray(v, float) + (0.0, 0.0, dz)
                made.append(c.mesh_from_arrays(f"PROP_TRUCK_{k.upper()}", v, f, src[k]))
        elif p["kind"] == "tunnel_lights":
            from kit import tunnel as tun
            for t in site["tunnels"]:
                for k, q in enumerate(tun.build_services(site, t)[2]):
                    made.append(_point_light(f"PROP_{t['id']}_LAMP_{k}", q, TUNNEL_LAMP_W))
            for s in site["noria_towers"]:
                made.append(_point_light(f"PROP_{s['id']}_PIT_LAMP", (s["x"] + 1.3, s["y"] + 1.2, s["pit_z"] + 1.1), 150.0))
    return made


def _point_light(name, loc, energy):
    data = bpy.data.lights.new(name, type="POINT")
    data.energy, data.shadow_soft_size, data.color = energy, 0.2, (1.0, 0.93, 0.82)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    return obj


# ------------------------------------------------------------------ states

def _override(name, kind):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
    if kind == "clay":
        bsdf.inputs["Base Color"].default_value = (0.30, 0.30, 0.30, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.6
    else:                                          # wire: emissive edges over near-black
        wire = nodes.new("ShaderNodeWireframe")
        wire.use_pixel_size = True
        wire.inputs["Size"].default_value = 1.2
        emit = nodes.new("ShaderNodeEmission")
        emit.inputs["Color"].default_value = (0.35, 0.75, 1.0, 1.0)
        emit.inputs["Strength"].default_value = 3.0
        dark = nodes.new("ShaderNodeBsdfDiffuse")
        dark.inputs["Color"].default_value = (0.01, 0.012, 0.015, 1.0)
        mix = nodes.new("ShaderNodeMixShader")
        links.new(wire.outputs[0], mix.inputs["Fac"])
        links.new(dark.outputs[0], mix.inputs[1])
        links.new(emit.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def apply_state(scene, state):
    layer = bpy.context.view_layer
    world_bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    if not hasattr(apply_state, "sky_strength"):
        apply_state.sky_strength = world_bg.inputs["Strength"].default_value
    layer.material_override = None
    world_bg.inputs["Strength"].default_value = apply_state.sky_strength
    sun = bpy.data.objects.get("SUN")
    if sun:
        sun.hide_render = False
    if bpy.data.node_groups.get("ROUTE_FX") and state != "route":
        from kit import route_fx as fx
        fx.set_fx(0.0, 0.0)
    if state == "clay":
        layer.material_override = _override("REEL_CLAY", "clay")
    elif state == "wire":
        layer.material_override = _override("REEL_WIRE", "wire")
        world_bg.inputs["Strength"].default_value = 0.0
        if sun:
            sun.hide_render = True


# ------------------------------------------------------------------ moves

def make_path(shot, fps):
    frames = max(2, int(shot["seconds"] * fps))
    a = shot["args"]
    move = shot["move"]
    if move == "orbit":
        return cm.orbit(a["target"], a["radius"], a["height"], a["start_deg"], a["sweep_deg"], frames)
    if move == "dolly":
        return cm.dolly(a["from"], a["to"], a["look_from"], a["look_to"], frames)
    if move == "push_in":
        return cm.push_in(a["from"], a["target"], a["fraction"], frames)
    if move == "crane":
        return cm.crane(a["xy"], a["z0"], a["z1"], a["look"], frames)
    if move == "walk":
        return cm.walk(a["points"], fps)
    if move == "keys":
        return cm.keys(a["points"], a["looks"], frames)
    raise ValueError(f"unknown move {move}")


def shot_frames(spec, fps):
    """[(shot index, location, look_at)] of every frame: what the renderer and the camera check use."""
    return [(i, loc, look) for i, shot in enumerate(spec["shots"]) for loc, look in make_path(shot, fps)]


# ------------------------------------------------------------------ text

def _font(size):
    from PIL import ImageFont

    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def overlay(png, text, sub=None, pos="top"):
    """Bold hook / caption on a dark band: near the top (vertical-video safe area) or a lower third."""
    from PIL import Image, ImageDraw

    im = Image.open(png).convert("RGB")
    w, h = im.size
    base = min(w, h)
    draw = ImageDraw.Draw(im, "RGBA")
    lines = [(t, s, f) for t, s, f in ((text, int(base * 0.058), (255, 255, 255, 255)), (sub, int(base * 0.036), (255, 210, 90, 255))) if t]
    if pos == "bottom":
        y = int(h * 0.74)
        x0 = int(w * 0.05)
        for line, size, fill in lines:
            font = _font(size)
            box = draw.textbbox((0, 0), line, font=font)
            tw, th = box[2] - box[0], box[3] - box[1]
            draw.rectangle((x0 - 18, y - 12, x0 + tw + 18, y + th + 20), fill=(0, 0, 0, 150))
            draw.text((x0, y), line, font=font, fill=fill)
            y += th + 34
    else:
        y = int(h * 0.12)
        for line, size, fill in lines:
            font = _font(size)
            box = draw.textbbox((0, 0), line, font=font)
            tw, th = box[2] - box[0], box[3] - box[1]
            x = (w - tw) // 2
            draw.rectangle((x - 18, y - 12, x + tw + 18, y + th + 20), fill=(0, 0, 0, 150))
            draw.text((x, y), line, font=font, fill=fill)
            y += th + 40
    im.save(png)


# ------------------------------------------------------------------ main

def _lerp(v, u):
    if isinstance(v, (list, tuple)):
        return v[0] + (v[1] - v[0]) * cm.ease(u)
    return v


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]   # blender ... -- args, or pip bpy
    spec_path = Path(argv[0])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    preview = "--preview" in argv
    board = "--board" in argv
    only = None
    if "--shots" in argv:
        only = {int(x) - 1 for x in argv[argv.index("--shots") + 1].split(",")}
    fps = 12 if preview else spec.get("fps", 24)
    suffix = "_board" if board else ("_preview" if preview else "")
    out_dir = ROOT / "out" / "reels" / (spec["name"] + suffix)
    frames_dir = out_dir / "frames"
    if frames_dir.exists() and not board:
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)

    built, cyc, device = {}, None, "CPU"
    fronts = [0.0] * len(PATHS)
    index = 0
    t_all = time.time()
    t_sec = 0.0
    for s_i, shot in enumerate(spec["shots"]):
        if shot["scene"] not in built:
            built.clear()
            built[shot["scene"]] = SCENES[shot["scene"]](preview)
            scene = built[shot["scene"]]
            if spec.get("device") == "GPU":
                device = use_gpu(scene)
            if spec.get("props"):
                add_props(scene, spec["props"])
            if spec.get("cycle"):
                cyc = cycle_setup(scene, spec["cycle"])
            bpy.context.view_layer.update()
            print(f"scene {shot['scene']} on {device}, {round(time.time() - t_all)} s", flush=True)
        scene = built[shot["scene"]]
        cm.set_format(scene, spec.get("format", "9:16"), 0.5 if preview else 1.0)
        scene.cycles.samples = 8 if preview else spec.get("samples", 96)
        state = shot.get("state", "final")
        apply_state(scene, state)
        cam = bpy.data.objects.get("REEL_CAM") or c.camera("REEL_CAM", (0, 0, 10), (0, 1, 10), lens=shot.get("lens", 24))
        cam.data.lens = shot.get("lens", 24)
        path = make_path(shot, fps)
        scene.camera = cam
        flow = shot.get("flow") or {}
        spans = []
        for p_i, key in enumerate(PATHS):
            if cyc and key in flow and flow[key] is not None:
                a, b = (resolve(v, cyc["anchors"][p_i]) for v in flow[key])
            else:
                a = b = fronts[p_i]
            spans.append((a, b))
        fx_ = shot.get("fx", {})
        picks = range(len(path)) if not board else [len(path) // 2]
        for k in range(len(path)):
            u = k / max(len(path) - 1, 1)
            t_here = t_sec + k / fps
            if (only is not None and s_i not in only) or k not in picks:
                continue
            from mathutils import Vector
            loc, look = path[k]
            cam.location = Vector(loc)
            cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
            if state == "route":
                from kit import route_fx as fx
                fx.set_fx(_lerp(fx_.get("dim", 0.33), u), _lerp(fx_.get("glow", 2.5), u))
            png = frames_dir / (f"shot_{s_i + 1:02d}.png" if board else f"f_{index:05d}.png")
            t0 = time.time()
            c.render(scene, cam, png)
            t1 = time.time()
            if cyc and state == "route" and shot.get("flow") is not None:
                prog = [a + (b - a) * cm.ease(u) for a, b in spans]
                cyc["overlay"].draw(str(png), cam, prog, phase=t_here * FLOW_SPEED)
            t2 = time.time()
            hook = spec.get("hook") if t_here < spec.get("hook_seconds", 2.5) else None
            overlay(str(png), hook or shot.get("caption", ""), (spec.get("hook_sub") if hook else shot.get("sub")),
                    spec.get("caption_pos", "top"))
            if k < 2:
                print(f"  frame {index}: render {t1 - t0:.1f} s, flow {t2 - t1:.1f} s, text {time.time() - t2:.1f} s", flush=True)
            index += 1
        fronts = [b for _, b in spans]
        t_sec += len(path) / fps
        print(f"shot {s_i + 1}/{len(spec['shots'])}: {len(path)} frames, {round(time.time() - t_all)} s total", flush=True)

    if board or only is not None:
        print("frames", frames_dir, round(time.time() - t_all), "s", flush=True)
        return
    import imageio_ffmpeg

    mp4 = out_dir / (spec["name"] + ".mp4")
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-framerate", str(fps),
           "-i", str(frames_dir / "f_%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(mp4)]
    subprocess.run(cmd, check=True)
    print("reel", mp4, index, "frames", round(time.time() - t_all), "s", flush=True)


if __name__ == "__main__":
    main()
