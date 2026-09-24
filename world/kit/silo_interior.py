"""K5. Silo МСВУ 220 interior: aeration floor, discharge gates, sweep auger, temperature
cables, roof rafters, level sensors, roof hatch and ladder, grain heap, light shaft.

Local frame as silo_msvu220.py: axis at (0, 0), Z = 0 on the floor (site +0.600).
Tunnel and gates run along X (PDF p.2, p.6). Source tags as in silo_msvu220.py plus
`research` = research/PARTS_DIMENSIONS.md.
"""

import math

import numpy as np

from . import common as c
from . import silo_msvu220 as silo
from . import steel as st

R_IN = silo.R - 0.5 * silo.WAVE_DEPTH - silo.SHEET_T_BOTTOM      # inner face of the wall

# ------------------------------------------------------------------ aeration floor (PDF p.2, research B9)
CHANNEL_W = 0.505                  # research: Symaga SBH channel 505 mm
CHANNEL_CLEAR_WALL = 0.6           # PDF p.2: channels stop short of the wall
TUNNEL_BAND = (-1.2, 1.0)          # PDF p.2: 1200 / 1000 from the tunnel axis, no channels
AXIS_CLEAR = 0.45                  # PDF p.2: channels stop at the vertical centreline
BRANCH_T = [2.2, 4.0, 5.8, 7.6, 9.4]   # PDF p.2: 5 branches per quadrant; spacing EST 1.8 m
FAN_ANGLES = silo.FAN_ANGLES       # collectors run from the four fans at 45 deg

# ------------------------------------------------------------------ gates (PDF p.2, p.6, p.7; research/tunnel_k4.md)
# openings are symmetric at 3250 on all three sheets; the "2750" chain on p.6 misses the openings
GATE_STEP = 3.25
GATE_OFFSETS = [k * GATE_STEP for k in range(-3, 4)]
GATE_SIZES = [0.35, 0.35, 0.35, 0.40, 0.35, 0.35, 0.35]

# ------------------------------------------------------------------ temperature cables (research B8)
CABLES = [(0.0, 0.0)] + [(4.5, a) for a in (45, 135, 225, 315)] + [(8.5, a) for a in range(0, 360, 45)]
CABLE_R = 0.006                    # research: Ø10.8-13 mm
SENSOR_STEP = 2.0                  # research: Lubnymash, sensors every 2 m
FLOOR_TIE = 0.4                    # research: bottom end tied to the floor in large silos

# ------------------------------------------------------------------ sweep auger (research B10)
SWEEP_ANGLE = 200.0                # EST: parked position
SWEEP_R = 0.15                     # research: Ø250-600; EST Ø300
SWEEP_LEN = 10.4                   # centre to wall clearance

# ------------------------------------------------------------------ roof structure (EST)
RAFTERS = 40                       # every second roof rib carries a rafter
PURLIN_R = [3.0, 6.0, 9.0]
REPOSE = math.radians(27.0)        # STD: wheat angle of repose 25-28 deg


def roof_underside_z(r):
    return silo.WALL_TOP + (silo.R - r) * math.tan(silo.ROOF_SLOPE) - silo.ROOF_T - 0.01


# ================================================================== floor

def _clip_segment(p, d, half_len=12.0, steps=400):
    """Longest run of p + s*d (s in [-half_len, half_len]) inside the channel area."""
    s = np.linspace(-half_len, half_len, steps)
    pts = p[None, :] + s[:, None] * d[None, :]
    r = np.linalg.norm(pts, axis=1)
    ok = (r < R_IN - CHANNEL_CLEAR_WALL - CHANNEL_W / 2) & \
         ((pts[:, 1] > TUNNEL_BAND[1] + 0.3) | (pts[:, 1] < TUNNEL_BAND[0] - 0.3)) & \
         (np.abs(pts[:, 0]) > AXIS_CLEAR)
    same_side = np.sign(pts[:, 0]) == np.sign(p[0])
    ok &= same_side & (np.sign(pts[:, 1]) == np.sign(p[1]))
    if not ok.any():
        return None
    idx = np.where(ok)[0]
    runs = np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)
    run = max(runs, key=len)
    return pts[run[0]], pts[run[-1]]


def channel_layout():
    """Aeration channels as (a, b) plan segments: 4 collectors + 5 branches per quadrant."""
    segs = []
    for deg in FAN_ANGLES:
        u = np.array([math.cos(math.radians(deg)), math.sin(math.radians(deg))])   # collector direction
        w = np.array([-u[1], u[0]])                                              # branch direction
        a = u * (R_IN + 0.05)
        b = u * 1.9
        segs.append(("collector", a, b))
        for t in BRANCH_T:
            seg = _clip_segment(u * t, w)
            if seg is not None and np.linalg.norm(seg[1] - seg[0]) > 0.8:
                segs.append(("branch", seg[0], seg[1]))
    return segs


def build_floor(segs):
    """Perforated channel covers flush with the floor, with angle edge frames."""
    covers, frames = [], []
    for _, a, b in segs:
        a3 = np.array([a[0], a[1], 0.006])
        b3 = np.array([b[0], b[1], 0.006])
        covers.append(st.member(a3, b3, np.array([(-CHANNEL_W / 2, -0.003), (CHANNEL_W / 2, -0.003),
                                                  (CHANNEL_W / 2, 0.003), (-CHANNEL_W / 2, 0.003)])))
        for side in (-1, 1):
            off = np.array([0, 0, 0.0])
            d = (b3 - a3) / np.linalg.norm(b3 - a3)
            n = np.array([-d[1], d[0], 0.0]) * side * (CHANNEL_W / 2 + 0.02)
            frames.append(st.member(a3 + n + off, b3 + n + off, np.array([(-0.02, -0.004), (0.02, -0.004),
                                                                          (0.02, 0.006), (-0.02, 0.006)])))
    slab = c.cylinder(R_IN - 0.005, -0.05, 0.001, steps=256)
    return c.merge_parts(covers), c.merge_parts(frames), slab


def build_gates():
    """Discharge openings over the tunnel: dark well, gate frame, grating on top."""
    wells, frames, gratings = [], [], []
    for x, size in zip(GATE_OFFSETS, GATE_SIZES):
        h = size / 2
        wells.append(c.box((x - h, -h, 0.0015), (x + h, h, 0.003)))                  # dark opening under grating
        for p0, p1 in (((x - h - 0.06, -h - 0.06, -0.01), (x + h + 0.06, -h, 0.02)),
                       ((x - h - 0.06, h, -0.01), (x + h + 0.06, h + 0.06, 0.02)),
                       ((x - h - 0.06, -h, -0.01), (x - h, h, 0.02)),
                       ((x + h, -h, -0.01), (x + h + 0.06, h, 0.02))):
            frames.append(c.box(p0, p1))
        gratings.append(c.box((x - h, -h, 0.004), (x + h, h, 0.016)))
    return c.merge_parts(wells), c.merge_parts(frames), c.merge_parts(gratings)


# ================================================================== sweep auger

def build_sweep():
    """Sweep auger parked on the floor: tube, helical flight, back shield, centre pivot,
    intermediate support wheel and a tractor drive wheel at the wall end."""
    ang = math.radians(SWEEP_ANGLE)
    d = np.array([math.cos(ang), math.sin(ang), 0.0])
    n = np.array([-d[1], d[0], 0.0])
    z = SWEEP_R + 0.02
    steel_parts, flight, rubber = [], [], []
    steel_parts.append(st.rod(d * 0.5 + [0, 0, z], d * SWEEP_LEN + [0, 0, z], 0.06, 20))           # core tube
    # helical flight: pitch = diameter, thickness 6 mm
    turns = int((SWEEP_LEN - 0.6) / (2 * SWEEP_R))
    k = 24
    tt = np.linspace(0, turns * 2 * math.pi, turns * k)
    s = 0.6 + (tt / (2 * math.pi)) * 2 * SWEEP_R
    inner, outer = 0.06, SWEEP_R
    rows = []
    for rr in (inner, outer):
        rows.append(d[None, :] * s[:, None] + n[None, :] * (rr * np.cos(tt))[:, None]
                    + np.array([0, 0, 1.0])[None, :] * (z + rr * np.sin(tt))[:, None])
    v = np.concatenate([rows[0], rows[1], rows[0] + d * 0.006, rows[1] + d * 0.006])
    m = len(tt)
    faces = []
    for i in range(m - 1):
        for a0, a1 in ((0, m), (2 * m, 3 * m), (0, 2 * m), (m, 3 * m)):
            faces.append((a0 + i, a0 + i + 1, a1 + i + 1, a1 + i))
    flight.append((v, np.array(faces)))
    # back shield (angle plate behind the flight)
    steel_parts.append(st.member(d * 0.6 - n * (SWEEP_R + 0.03) + [0, 0, 0.02],
                                 d * SWEEP_LEN - n * (SWEEP_R + 0.03) + [0, 0, 0.02],
                                 np.array([(-0.003, 0.0), (0.003, 0.0), (0.003, 0.38), (-0.003, 0.38)])))
    # centre pivot and gearbox over the central gate
    steel_parts.append(st.rod((0, 0, 0.0), (0, 0, 0.55), 0.28, 32))
    steel_parts.append(c.box((-0.2, -0.2, 0.55), (0.2, 0.2, 0.85)))
    # intermediate support and drive wheel at the wall
    for sw, rr in ((SWEEP_LEN * 0.5, 0.18), (SWEEP_LEN + 0.15, 0.28)):
        p = d * sw
        rubber.append(st.rod(p - n * 0.07 + [0, 0, rr], p + n * 0.07 + [0, 0, rr], rr, 32))
        steel_parts.append(c.box(tuple(p - n * 0.12 + [-0.05, 0, rr]), tuple(p + n * 0.12 + [0.05, 0, rr + 0.25])))
    p = d * (SWEEP_LEN + 0.15)
    steel_parts.append(st.rod(p + n * 0.15 + [0, 0, 0.45], p + n * 0.75 + [0, 0, 0.45], 0.13, 24))   # drive motor
    return c.merge_parts(steel_parts), c.merge_parts(flight), c.merge_parts(rubber)


# ================================================================== roof structure, cables, sensors

def build_roof_structure():
    rafters, rings = [], []
    for k in range(RAFTERS):
        a = 2 * math.pi * k / RAFTERS + math.pi / silo.ROOF_RIBS
        u = np.array([math.cos(a), math.sin(a), 0.0])
        r0, r1 = R_IN - 0.05, silo.COLLAR_R + 0.05
        p0 = u * r0 + [0, 0, roof_underside_z(r0) - 0.08]
        p1 = u * r1 + [0, 0, roof_underside_z(r1) - 0.08]
        rafters.append(st.member(p0, p1, st.channel(0.16, 0.06, 0.004, 0.006), up=(0, 0, 1)))
    for rr in PURLIN_R:
        n = 96
        z = roof_underside_z(rr) - 0.2
        a = np.linspace(0, 2 * math.pi, n + 1)
        for a0, a1 in zip(a, a[1:]):
            rings.append(st.member((rr * math.cos(a0), rr * math.sin(a0), z), (rr * math.cos(a1), rr * math.sin(a1), z),
                                   st.angle(0.063, 0.005)))
    z = roof_underside_z(silo.COLLAR_R) - 0.1
    rings.append(c.cylinder(silo.COLLAR_R + 0.08, z - 0.2, z, steps=48, capped=False))
    return c.merge_parts(rafters), c.merge_parts(rings)


def cable_positions():
    return [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), r) for r, a in CABLES]


def build_cables(positions=None, sensor_step=SENSOR_STEP):
    """Temperature cables hung from the rafters: cable, sensor capsules, top shackle, floor tie."""
    cables, sensors, hardware = [], [], []
    for x, y, r in positions or cable_positions():
        top = roof_underside_z(max(r, silo.COLLAR_R + 0.3)) - 0.25
        bottom = FLOOR_TIE
        cables.append(st.rod((x, y, bottom), (x, y, top), CABLE_R, 8))
        z = top - 1.0
        while z > bottom + 0.3:
            sensors.append(st.rod((x, y, z - 0.05), (x, y, z + 0.05), 0.016, 12))
            z -= sensor_step
        hardware.append(c.box((x - 0.05, y - 0.02, top), (x + 0.05, y + 0.02, top + 0.2)))        # shackle plate
        hardware.append(st.rod((x, y, 0.0), (x, y, bottom), 0.002, 6))                           # tie cord
        hardware.append(c.box((x - 0.04, y - 0.04, 0.0), (x + 0.04, y + 0.04, 0.02)))            # floor eye
    return c.merge_parts(cables), c.merge_parts(sensors), c.merge_parts(hardware)


def build_level_sensors():
    """Rotary paddle level switches through the roof (research B10: E+H FTE20, paddles 75-300 mm)."""
    parts = []
    for deg, r in ((30.0, 9.6), (150.0, 9.6), (270.0, 5.0)):
        a = math.radians(deg)
        x, y = r * math.cos(a), r * math.sin(a)
        zr = roof_underside_z(r)
        parts.append(st.rod((x, y, zr - 0.6), (x, y, zr + 0.25), 0.012, 8))                     # shaft
        parts.append(c.box((x - 0.1, y - 0.004, zr - 0.75), (x + 0.1, y + 0.004, zr - 0.6)))    # paddle
        parts.append(st.rod((x, y, zr + 0.05), (x, y, zr + 0.25), 0.06, 16))                    # housing
    return c.merge_parts(parts)


def build_hatch_and_ladder():
    """Roof hatch near the eave over the outside ladder, and a straight inside ladder down the wall."""
    a = math.radians(silo.LADDER_ANGLE)
    u = np.array([math.cos(a), math.sin(a), 0.0])
    t = np.array([-u[1], u[0], 0.0])
    r_h = silo.R - 1.4
    zh = roof_underside_z(r_h)
    frame = [c.box(tuple(u * r_h - t * 0.35 + [0, 0, zh - 0.05]), tuple(u * r_h + t * 0.35 + [0, 0, zh + 0.12]))]
    ladder = []
    r_l = R_IN - 0.25
    for s in (-0.22, 0.22):
        ladder.append(st.member(u * r_l + t * s + [0, 0, 0.0], u * r_l + t * s + [0, 0, silo.WALL_TOP - 0.3],
                                st.FLAT_60x10, up=tuple(u)))
    for z in np.arange(0.3, silo.WALL_TOP - 0.4, 0.3):
        ladder.append(st.rod(u * r_l - t * 0.22 + [0, 0, z], u * r_l + t * 0.22 + [0, 0, z], 0.011, 6))
    for z in np.arange(1.0, silo.WALL_TOP, 3.0):                                             # wall brackets
        ladder.append(st.member(u * r_l + [0, 0, z], u * (R_IN - 0.01) + [0, 0, z], st.flat(0.05, 0.008)))
    hatch_pos = u * r_h + [0, 0, zh]
    return c.merge_parts(frame), c.merge_parts(ladder), hatch_pos


# ================================================================== grain

def build_grain(fill=0.3, draw=False, n_r=90, n_a=256):
    """Grain surface: cone under the centre spout at the angle of repose, level `fill` of the wall
    height at the wall; `draw` sinks a funnel over the centre gate. Returns (verts, faces) or None."""
    if fill <= 0:
        return None
    h_wall = fill * silo.WALL_TOP
    rr = np.linspace(0.0, R_IN - 0.01, n_r)
    z = h_wall + (R_IN - rr) * math.tan(REPOSE)
    if draw:
        z = np.minimum(z, h_wall - 1.2 + rr * math.tan(math.radians(35)))
    a = np.linspace(0, 2 * math.pi, n_a, endpoint=False)
    x = rr[:, None] * np.cos(a)[None, :]
    y = rr[:, None] * np.sin(a)[None, :]
    ripple = (0.035 * np.sin(1.7 * x + 0.4) * np.cos(1.3 * y) + 0.02 * np.sin(4.1 * x - 2.3 * y)
              + 0.012 * np.cos(7.3 * y + 1.1 * x))                                # EST: loose surface
    top = np.stack([x, y, z[:, None] + ripple * (rr[:, None] / R_IN)], axis=-1).reshape(-1, 3)
    wall = np.column_stack([(R_IN - 0.01) * np.cos(a), (R_IN - 0.01) * np.sin(a), np.full(n_a, 0.01)])
    verts = np.concatenate([top, wall])
    faces = [c.grid_faces(n_r, n_a, wrap_cols=True)[:, ::-1]]
    i = np.arange(n_a)
    j = (i + 1) % n_a
    last = (n_r - 1) * n_a
    faces.append(np.stack([last + i, last + j, len(top) + j, len(top) + i], axis=-1))
    return verts, faces


def grain_section(fill=0.3, normal=(1.0, 0.0), n=120):
    """Vertical section face of the grain heap on the cut plane (for cutaways and heat maps)."""
    if fill <= 0:
        return None
    nx, ny = normal
    t = np.array([-ny, nx])                                                     # direction along the cut
    h_wall = fill * silo.WALL_TOP
    s = np.linspace(-(R_IN - 0.01), R_IN - 0.01, n)
    z = h_wall + (R_IN - np.abs(s)) * math.tan(REPOSE)
    top = np.column_stack([t[0] * s, t[1] * s, z])
    bot = np.column_stack([t[0] * s, t[1] * s, np.full(n, 0.01)])
    v = np.concatenate([bot, top])
    f = np.array([(i, i + 1, n + i + 1, n + i) for i in range(n - 1)])
    return v, f


def mat_grain(name="WHEAT"):
    """Wheat in bulk: warm golden base, grain-sized voronoi bump, darker hollows."""
    import bpy

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tex = nodes.new("ShaderNodeTexCoord")
    vor = nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 180.0
    links.new(tex.outputs["Object"], vor.inputs["Vector"])
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 2.0
    links.new(tex.outputs["Object"], noise.inputs["Vector"])
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = (0.55, 0.38, 0.16, 1.0)
    mix.inputs[7].default_value = (0.36, 0.23, 0.09, 1.0)
    links.new(vor.outputs["Distance"], mix.inputs["Factor"])
    links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.65
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.8
    bump.inputs["Distance"].default_value = 0.004
    links.new(vor.outputs["Distance"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def mat_perforated(name="PERFORATED"):
    """Perforated channel cover: galvanised plate with a dense dark hole pattern (23 % open)."""
    mat = c.mat_galvanized(name, age=0.55, spangle_scale=40.0)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tex = nodes.new("ShaderNodeTexCoord")
    holes = nodes.new("ShaderNodeTexVoronoi")
    holes.voronoi_dimensions = "2D"
    holes.inputs["Scale"].default_value = 90.0
    holes.inputs["Randomness"].default_value = 0.0
    links.new(tex.outputs["Object"], holes.inputs["Vector"])
    thr = nodes.new("ShaderNodeMath")
    thr.operation = "LESS_THAN"
    thr.inputs[1].default_value = 0.27
    links.new(holes.outputs["Distance"], thr.inputs[0])
    dark = nodes.new("ShaderNodeMix")
    dark.data_type = "RGBA"
    dark.inputs[7].default_value = (0.01, 0.01, 0.01, 1.0)
    links.new(thr.outputs[0], dark.inputs["Factor"])
    base_link = next(lk for lk in links if lk.to_socket == bsdf.inputs["Base Color"])
    links.new(base_link.from_socket, dark.inputs[6])
    links.new(dark.outputs[2], bsdf.inputs["Base Color"])
    return mat


# ================================================================== assembly

def build(collection=None, fill=0.3, draw=False, cable_positions_override=None, sensor_step=SENSOR_STEP, cut=None):
    import bpy

    m = {
        "galv": bpy.data.materials.get("SILO_GALV") or c.mat_galvanized("SILO_GALV_IN", age=0.4),
        "perf": mat_perforated("AERATION_COVER"),
        "dark": c.mat_painted("GATE_WELL", (0.015, 0.015, 0.015), 0.9, grime=0.0),
        "grating": st.mat_grating("GATE_GRATING"),
        "concrete": c.mat_concrete("SILO_FLOOR_CONCRETE", tint=(0.36, 0.35, 0.33)),
        "cable": c.mat_painted("THERMO_CABLE", (0.02, 0.02, 0.02), 0.5, grime=0.0),
        "sensor": c.mat_painted("THERMO_SENSOR", (0.55, 0.57, 0.6), 0.35, grime=0.1),
        "auger": c.mat_painted("SWEEP_PAINT", (0.62, 0.64, 0.66), 0.4, grime=0.4),
        "rubber": c.mat_rubber("SWEEP_TYRE"),
        "motor": c.mat_painted("SWEEP_MOTOR", (0.05, 0.16, 0.35), 0.35),
        "grain": mat_grain(),
        "yellow": c.mat_painted("LEVEL_SENSOR", (0.9, 0.7, 0.05), 0.4, grime=0.1),
    }
    objs, labels = {}, []

    def add(key, data, mat, smooth=False):
        if data is None:
            return
        v, f = data
        if cut is not None:
            v, f = c.cut_mesh(v, f, cut)
            if not f:
                return
        objs[key] = c.mesh_from_arrays(f"SILO_IN_{key.upper()}", v, f, m[mat], smooth=smooth, collection=collection)

    segs = channel_layout()
    covers, frames, slab = build_floor(segs)
    add("floor", slab, "concrete")
    add("aeration_covers", covers, "perf")
    add("aeration_frames", frames, "galv")
    labels.append(("Аераційний канал 505 мм, перфорований настил", tuple(np.append(segs[1][1], 0.0))))
    wells, gframes, gratings = build_gates()
    add("gate_wells", wells, "dark")
    add("gate_frames", gframes, "galv")
    add("gate_gratings", gratings, "grating")
    labels.append(("Засувка вивантаження 400×400 (над тунелем)", (0.0, 0.0, 0.02)))
    s_steel, s_flight, s_rubber = build_sweep()
    add("sweep", s_steel, "auger", "quads")
    add("sweep_flight", s_flight, "auger", True)
    add("sweep_wheels", s_rubber, "rubber", "quads")
    ang = math.radians(SWEEP_ANGLE)
    labels.append(("Зачисний шнек (до стіни 10.4 м)", (5.0 * math.cos(ang), 5.0 * math.sin(ang), 0.35)))
    rafters, rings = build_roof_structure()
    add("rafters", rafters, "galv")
    add("purlins", rings, "galv")
    cables, sensors, hardware = build_cables(cable_positions_override, sensor_step)
    add("thermo_cables", cables, "cable", "quads")
    add("thermo_sensors", sensors, "sensor", "quads")
    add("thermo_hardware", hardware, "galv")
    x, y, r = cable_positions()[5]
    labels.append(("Термопідвіска: датчики через 2 м", (x, y, 4.0)))
    labels.append(("Датчик температури", (x, y, roof_underside_z(r) - 1.25)))
    add("level_sensors", build_level_sensors(), "yellow", "quads")
    labels.append(("Датчик рівня (роторний)", (9.6 * math.cos(math.radians(30)), 9.6 * math.sin(math.radians(30)),
                                                roof_underside_z(9.6) - 0.7)))
    hframe, ladder, hatch = build_hatch_and_ladder()
    add("hatch_frame", hframe, "galv")
    add("inside_ladder", ladder, "galv", "quads")
    labels.append(("Люк даху", tuple(hatch)))
    add("grain", build_grain(fill, draw), "grain", True)
    measure = {
        "channels": len(segs),
        "channel_width_m": CHANNEL_W,
        "gates": len(GATE_OFFSETS),
        "cables": len(cable_positions_override or cable_positions()),
        "sensor_step_m": sensor_step,
        "sweep_length_m": SWEEP_LEN,
        "rafters": RAFTERS,
        "fill": fill,
        "grain_repose_deg": 27.0,
        "grain_mass_t_full": round(6381 * 0.75),
        "aeration_required_m3h": 10 * round(6381 * 0.75),
    }
    return objs, labels, measure, hatch
