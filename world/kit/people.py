"""Real people for the scenes: Microsoft Rocketbox avatars (MIT, Copyright (c) 2020 Microsoft; world/assets/people/
LICENSE.txt and SOURCE.txt per avatar; research by Grok T10a). Construction workers in helmets, overalls and hi-vis.

The FBX come in a T-pose; stand_pose() lowers the arms along the body by aiming the upper arm and forearm bones in
armature space (the target direction is taken from the world, so the import rotation does not matter). Textures are
the Rocketbox TGA shrunk to 1024 px JPG (world/assets/people/<name>/), relinked by file name.

    place(site, collection) -> [armature objects]   one avatar per SITE designed.environment.scale.people entry
"""

import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from . import common as c

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "people"
AVATARS = ["Construction_Male_03", "Construction_Female_01", "Construction_Male_04", "Construction_Male_01", "Delivery_Male_01"]
ARM_OUT = 0.10       # judgment: hands 0.10 m out from the thigh line per metre down (a relaxed stance)


def _relink(mats, folder):
    for m in mats:
        if not m or not m.use_nodes:
            continue
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image:
                stem = Path(n.image.filepath.replace("\\", "/")).stem
                jpg = folder / f"{stem}.jpg"
                if jpg.exists():
                    n.image = bpy.data.images.load(str(jpg), check_existing=True)
                    if "normal" in stem or "specular" in stem or "opacity" in stem:
                        n.image.colorspace_settings.name = "Non-Color"
                else:                                          # a map left out of the download (a specular): drop it
                    for link in list(n.outputs[0].links):
                        m.node_tree.links.remove(link)


def _aim(arm, name, world_dir):
    """Rotate pose bone `name` so its head->tail points along world_dir (armature space math)."""
    pb = arm.pose.bones.get(name)
    if pb is None:
        return False
    bpy.context.view_layer.update()
    M = pb.matrix.copy()
    nxt = next((ch for ch in pb.children if (ch.head - pb.head).length > 1e-6), None)
    cur = ((nxt.head if nxt else pb.tail) - pb.head).normalized()     # Biped bone tails do not follow the limb
    target = (arm.matrix_world.inverted().to_3x3() @ Vector(world_dir)).normalized()
    q = cur.rotation_difference(target)
    pb.matrix = Matrix.Translation(M.translation) @ q.to_matrix().to_4x4() @ Matrix(M.to_3x3()).to_4x4()
    bpy.context.view_layer.update()
    return True


def stand_pose(arm, facing):
    """Arms down along the body, forearms slightly forward. facing: world unit vector the person looks along."""
    fx, fy = facing
    right = (fy, -fx)                                   # the person's right side in plan
    for side, s in (("L", -1), ("R", 1)):
        out = (right[0] * s * ARM_OUT, right[1] * s * ARM_OUT)
        _aim(arm, f"Bip01 {side} UpperArm", (out[0], out[1], -1.0))
        _aim(arm, f"Bip01 {side} Forearm", (out[0] + 0.25 * fx, out[1] + 0.25 * fy, -1.0))


def load(name, collection, tag):
    """Import one avatar; returns its armature. Objects are renamed FIG_PERSON_<tag>_*."""
    folder = ASSETS / name
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(folder / f"{name}.fbx"), use_anim=False)   # the bind-pose keys would reset
    new = [o for o in bpy.data.objects if o not in before]                            # the pose and place at render
    arm = next(o for o in new if o.type == "ARMATURE")
    arm.animation_data_clear()
    arm.data.pose_position = "POSE"
    for o in new:
        for col in list(o.users_collection):
            col.objects.unlink(o)
        collection.objects.link(o)
        o.name = f"FIG_PERSON_{tag}_{o.type}"
        if o.type == "MESH":
            _relink(o.data.materials, folder)
            for p in o.data.polygons:
                p.use_smooth = True
    return arm


def place(site, collection):
    """One avatar per people entry [x, y, heading deg], cycling through AVATARS, feet on the ground."""
    people = site["designed"]["environment"]["scale"]["people"]
    out = []
    g = c.ground_z()
    for i, (x, y, heading) in enumerate(people):
        arm = load(AVATARS[i % len(AVATARS)], collection, f"{i:02d}")
        a = math.radians(heading)
        facing = (math.cos(a - math.pi / 2), math.sin(a - math.pi / 2))    # heading 0 = the person looks to -Y
        arm.rotation_euler = (0.0, 0.0, arm.rotation_euler[2] + a)
        arm.location = (x, y, g + arm.location.z)                          # the FBX origin is the pelvis, keep its height
        bpy.context.view_layer.update()
        stand_pose(arm, facing)
        out.append(arm)
    return out
