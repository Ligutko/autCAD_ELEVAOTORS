"""Control center, phase 8 minimum: grain packets running along the flow lines of the live scene.

Why an overlay and not the flow tubes of kit/live.py, and not the buckets themselves. Measured (build/live_visibility.py,
results in world/out/control_center/motion/recon_visibility.json): every grain path of the model (conveyor casings, noria
legs, spouts, tunnels) lies inside a casing or under the ground; of the four recording cameras only the truck lane and a
metre of the gravity pipe are seen, none of the conveyors and norias, with the head covers of H5 / H6 removed as well. The
buckets are inside the leg casings; they are seen only in a close cutaway of the head (cover removed). Turning them was
tried: 8 prebuilt phases of the bucket mesh swapped at 30 Hz. Any change of the scene makes EEVEE render the frame again
from scratch, 59-107 ms per frame instead of the 5-15 ms of a static one (also when the swapped buckets are out of view),
so the belts of the norias are shown by the packets on their path at the belt speed instead (numbers and the cutaway
frames: world/out/control_center/motion/bucket_swap_probe.json, head_cutaway_*.png). The motion is therefore an
«x-ray» layer over the viewport — dashes of grain along each path, the idea of the FlowOverlay of the 7C reel — and not
scene geometry: nothing here touches the depsgraph, the shaders or the scene, and a redraw costs what a static frame costs.

  Motion    pure numpy, no bpy: the paths (kit/live.py flow_paths), the speed of each mover from the simulator
            itself (sim.core Mover.v = params.json belt_speed_m_s, the noria_n100.MODELS speeds of H5 / H6), the set
            of moving owners, and points(t): the vertices of every dash at time t. A dash head sits at
            arc = (v t) mod SPACING + k SPACING, so the pattern shifts by v dt between two frames.
  Overlay   the viewport part (gpu draw handler + one light timer that only asks the 3D views for a redraw).

Motion is drawn only for movers in state «run» that carry grain (load > 0) and for edges with t/h > 0
(kit/live.py Live.apply decides); a stopped, faulted, tripped or idle line shows no dashes, and a paused simulator
freezes them. Time is real time, not simulated time: a belt turns at its real speed at any panel speed (×1 ... ×600).
There is no occlusion: the scene depth is not readable in a POST_VIEW callback (probed: LESS_EQUAL draws nowhere,
GREATER_EQUAL everywhere), so a packet behind a wall is drawn as bright as one in front: an x-ray on purpose.
"""

import math
import time

import numpy as np

# ---- look (judgment: a screen convention, no source)
DASH_M = 0.8            # length of a packet along the path
SPACING_M = 2.4         # distance between the heads of two packets
SAMPLES = 5             # vertices per packet (a packet follows a bend)
OUTLINE_PX = 8.0
CORE_PX = 4.0
# A dark edge and a light core read on the amber glow of a running casing, on grey steel and on the ground alike.
LOOK = {"outline": (0.16, 0.07, 0.0, 0.60), "core": (1.0, 0.88, 0.42, 0.95)}
REDRAW_S = 0.030        # the 3D views are redrawn this often while something moves (Windows timers tick every 15.6 ms: 2 ticks)
IDLE_S = 0.25           # ... and this often when nothing moves (the timer only waits)

# Grain in a spout or a fall is not carried by a belt; the simulator has no transit time on edges, and no source for
# the speed of grain in the model's spouts was found: this number is for the picture only.
EDGE_SPEED = {"value": 2.0, "unit": "m/s", "basis": "EST",
              "src": "no source: the simulator has no delay on edges; a drawing convention for gravity spouts and falls"}


def mover_speeds():
    """{mover id: m/s} exactly as the simulator moves the grain (Sim.movers[n].v)."""
    from sim import core                         # not at import time: the kits do not depend on the simulator
    return {n: m.v for n, m in core.Sim().movers.items()}


class Motion:
    """paths: {owner: [ (N, 3) arrays ]} (Live.flow_paths); speeds: {mover id: m/s}; static: owners that do not move
    (a truck on its lane is not grain); edge_speed: m/s of an owner 'A->B' that is not a mover."""

    def __init__(self, paths, speeds, static=(), edge_speed=None):
        self.speeds = dict(speeds)
        self.edge_speed = float((edge_speed or EDGE_SPEED)["value"])
        self.legs = []                                       # [(owner, pts, s, length, speed)]
        for owner, plist in paths.items():
            v = self.speeds.get(owner, self.edge_speed if "->" in owner else None)
            if v is None or owner in static:
                continue
            for pts in plist:
                pts = np.asarray(pts, float)
                if len(pts) < 2:
                    continue
                s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
                if s[-1] > 0.05:
                    self.legs.append((owner, pts, s, float(s[-1]), float(v)))
        # one global polyline: leg i occupies the arc range [base_i, base_i + L_i]; np.interp is never asked between legs
        base, off = [], 0.0
        for _, _, _, L, _ in self.legs:
            base.append(off)
            off += L + 1.0
        self.base = np.array(base)
        self.L = np.array([lg[3] for lg in self.legs])
        self.v = np.array([lg[4] for lg in self.legs])
        self.g_s = np.concatenate([b + lg[2] for b, lg in zip(self.base, self.legs)]) if self.legs else np.zeros(0)
        self.g_p = np.concatenate([lg[1] for lg in self.legs]) if self.legs else np.zeros((0, 3))
        # dash slots: k = -1 ... n per leg; which slots exist at time t is decided by the head position
        slots = [int(math.ceil((L + DASH_M) / SPACING_M)) + 2 for L in self.L]
        self.slot_leg = np.repeat(np.arange(len(self.legs)), slots)
        self.slot_k = np.concatenate([np.arange(n) - 1 for n in slots]) if self.legs else np.zeros(0)
        self.owner_of_leg = [lg[0] for lg in self.legs]
        self.leg_active = np.zeros(len(self.legs), bool)
        self.owners = set(self.owner_of_leg)
        self.active = frozenset()
        self.paused = False                                  # the simulator is paused: the packets stand where they are
        self._w = np.linspace(0.0, 1.0, SAMPLES)

    # ---------------------------------------------------------------- what moves
    def set_active(self, owners):
        """The owners whose grain moves now. Returns True when the set changed."""
        owners = frozenset(o for o in owners if o in self.owners)
        if owners == self.active:
            return False
        self.active = owners
        self.leg_active = np.array([o in owners for o in self.owner_of_leg], bool)
        return True

    def set_paused(self, paused):
        self.paused = bool(paused)

    def speed_of(self, owner):
        """m/s the pattern of `owner` runs at when it moves (None: this owner has no drawn path)."""
        for lg in self.legs:
            if lg[0] == owner:
                return lg[4]
        return None

    # ---------------------------------------------------------------- one frame
    def dashes(self, t):
        """(leg index (n,), tail arc (n,), head arc (n,), points (n, SAMPLES, 3)) of every dash of the active legs at
        time t (s). A head at (v t) mod SPACING + k SPACING; the part of a dash outside its leg is cut off."""
        if not self.legs or not self.leg_active.any():
            return np.zeros(0, int), np.zeros(0), np.zeros(0), np.zeros((0, SAMPLES, 3))
        li = self.slot_leg
        head = (self.v * t) % SPACING_M
        head = head[li] + self.slot_k * SPACING_M
        tail = head - DASH_M
        keep = self.leg_active[li] & (head > 0.0) & (tail < self.L[li])
        li, head, tail = li[keep], np.minimum(head[keep], self.L[li[keep]]), np.maximum(tail[keep], 0.0)
        arcs = self.base[li][:, None] + tail[:, None] + (head - tail)[:, None] * self._w[None, :]      # (n, SAMPLES)
        flat = arcs.reshape(-1)
        pts = np.stack([np.interp(flat, self.g_s, self.g_p[:, i]) for i in range(3)], axis=1).reshape(len(li), SAMPLES, 3)
        return li, tail, head, pts

    def points(self, t):
        """float32 (2 m, 3) for a LINES batch: every dash as SAMPLES-1 segments."""
        _, _, _, p = self.dashes(t)
        if not len(p):
            return np.zeros((0, 3), np.float32)
        return np.stack([p[:, :-1], p[:, 1:]], axis=2).reshape(-1, 3).astype(np.float32)


# ---------------------------------------------------------------------- the viewport part

class Overlay:
    """gpu draw handler + a light redraw timer. Only drawing; no scene data is touched."""

    def __init__(self, motion, redraw_s=REDRAW_S):
        self.m, self.redraw_s = motion, redraw_s
        self._t, self._prev = 0.0, None          # the motion clock: real time, but it stands still while the simulator is paused
        self.handle = None
        self.shader = None
        self.last_t = None                       # motion time of the last drawn frame
        self.draws, self.ticks = 0, 0
        self.draw_ms = []                        # python cost of the draw handler (the last ones)
        self.tick_gap_ms = []
        self.draw_gap_ms = []                    # time between two drawn frames
        self._tick_prev = None
        self._draw_prev = None
        self.look = dict(LOOK)

    def clock(self, now):
        """Motion time (s) at the real time `now`: runs with the wall clock, stands still while the simulator is paused."""
        if self._prev is not None and not self.m.paused:
            self._t += now - self._prev
        self._prev = now
        return self._t

    def install(self):
        import bpy
        import gpu
        self.gpu = gpu
        self.shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
        self.handle = bpy.types.SpaceView3D.draw_handler_add(self._draw, (), "WINDOW", "POST_VIEW")
        bpy.app.timers.register(self._tick, first_interval=0.1, persistent=True)

    def remove(self):
        import bpy
        if self.handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self.handle, "WINDOW")
            self.handle = None
        if bpy.app.timers.is_registered(self._tick):
            bpy.app.timers.unregister(self._tick)

    def _draw(self):
        c0 = time.perf_counter()
        t = self.clock(c0)
        if self._draw_prev is not None:
            self.draw_gap_ms.append((c0 - self._draw_prev) * 1000)
            del self.draw_gap_ms[:-600]
        self._draw_prev = c0
        pts = self.m.points(t)
        self.last_t = t
        if not len(pts):
            return
        from gpu_extras.batch import batch_for_shader
        gpu, sh = self.gpu, self.shader
        batch = batch_for_shader(sh, "LINES", {"pos": pts})
        vp = gpu.state.viewport_get()
        gpu.state.blend_set("ALPHA")
        sh.bind()
        sh.uniform_float("viewportSize", (vp[2], vp[3]))
        gpu.state.depth_test_set("NONE")     # x-ray: the scene depth is not readable in POST_VIEW (probed 2026-09-29:
        lk = self.look                       # LESS_EQUAL draws nowhere, GREATER_EQUAL everywhere), so no occlusion
        for width, col in ((OUTLINE_PX, lk["outline"]), (CORE_PX, lk["core"])):
            sh.uniform_float("lineWidth", width)
            sh.uniform_float("color", col)
            batch.draw(sh)
        gpu.state.blend_set("NONE")
        self.draws += 1
        self.draw_ms.append((time.perf_counter() - c0) * 1000)
        del self.draw_ms[:-300]

    def _tick(self):
        import bpy
        now = time.perf_counter()
        self.clock(now)                           # keeps the clock's last reading fresh while nothing is drawn (idle, paused)
        if self._tick_prev is not None:
            self.tick_gap_ms.append((now - self._tick_prev) * 1000)
            del self.tick_gap_ms[:-300]
        self._tick_prev = now
        self.ticks += 1
        if self.m.paused or not self.m.active:
            return IDLE_S
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()
        return self.redraw_s
