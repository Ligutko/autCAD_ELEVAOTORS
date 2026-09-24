"""D3. Reel builder: one JSON -> MP4 in the "process -> final" format (CANON_WORLD).

Each shot names a scene, a render state and a camera move:
  state "clay"  - everything plain grey, like a viewport greybox
  state "wire"  - dark background, glowing mesh edges
  state "final" - full materials, sky, fog
A hook text sits on top of the first seconds, a caption on each shot.

Run:
    python world/build/reel.py world/reels/reel_01_site.json [--preview]
--preview renders at half size, 12 fps, 8 samples: to check the motion before a final render.
"""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import bpy  # noqa: I001  bpy first: the pip module registers bmesh and mathutils

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import cameras as cm  # noqa: E402
from kit import common as c  # noqa: E402

FONT_CANDIDATES = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"]


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
    raise ValueError(f"unknown move {move}")


# ------------------------------------------------------------------ text

def _font(size):
    from PIL import ImageFont

    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def overlay(png, text, sub=None):
    """Bold hook / caption on a dark band near the top (vertical-video safe area)."""
    from PIL import Image, ImageDraw

    im = Image.open(png).convert("RGB")
    w, h = im.size
    draw = ImageDraw.Draw(im, "RGBA")
    y = int(h * 0.12)
    for line, size, fill in ((text, int(w * 0.058), (255, 255, 255, 255)), (sub, int(w * 0.036), (255, 210, 90, 255))):
        if not line:
            continue
        font = _font(size)
        box = draw.textbbox((0, 0), line, font=font)
        tw, th = box[2] - box[0], box[3] - box[1]
        x = (w - tw) // 2
        draw.rectangle((x - 18, y - 12, x + tw + 18, y + th + 20), fill=(0, 0, 0, 150))
        draw.text((x, y), line, font=font, fill=fill)
        y += th + 40
    im.save(png)


# ------------------------------------------------------------------ main

def main():
    spec_path = Path(sys.argv[1])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    preview = "--preview" in sys.argv
    fps = 12 if preview else spec.get("fps", 24)
    out_dir = ROOT / "out" / "reels" / (spec["name"] + ("_preview" if preview else ""))
    frames_dir = out_dir / "frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)

    built = {}
    index = 0
    t_all = time.time()
    for s_i, shot in enumerate(spec["shots"]):
        if shot["scene"] not in built:
            built.clear()
            built[shot["scene"]] = SCENES[shot["scene"]](preview)
        scene = built[shot["scene"]]
        cm.set_format(scene, spec.get("format", "9:16"), 0.5 if preview else 1.0)
        scene.cycles.samples = 8 if preview else spec.get("samples", 96)
        apply_state(scene, shot.get("state", "final"))
        cam = bpy.data.objects.get("REEL_CAM") or c.camera("REEL_CAM", (0, 0, 10), (0, 1, 10), lens=shot.get("lens", 24))
        cam.data.lens = shot.get("lens", 24)
        path = make_path(shot, fps)
        scene.camera = cam
        for k, (loc, look) in enumerate(path):
            from mathutils import Vector
            cam.location = Vector(loc)
            cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
            png = frames_dir / f"f_{index:05d}.png"
            c.render(scene, cam, png)
            t_sec = index / fps
            hook = spec.get("hook") if t_sec < spec.get("hook_seconds", 2.5) else None
            overlay(str(png), hook or shot.get("caption", ""), shot.get("sub") if not hook else None)
            index += 1
        print(f"shot {s_i + 1}/{len(spec['shots'])}: {len(path)} frames, {round(time.time() - t_all)} s total", flush=True)

    import imageio_ffmpeg

    mp4 = out_dir / (spec["name"] + ".mp4")
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-framerate", str(fps),
           "-i", str(frames_dir / "f_%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(mp4)]
    subprocess.run(cmd, check=True)
    print("reel", mp4, index, "frames", round(time.time() - t_all), "s", flush=True)


if __name__ == "__main__":
    main()
