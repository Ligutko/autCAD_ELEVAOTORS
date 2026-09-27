"""IES LM-63 photometry (Type C): read a luminaire file, look up its luminous intensity in any direction,
integrate its flux. Plain Python + numpy, no Blender.

Frame of a Type C luminaire (LM-63): gamma (vertical angle) 0 = nadir, 90 = horizontal, 180 = zenith;
C (horizontal angle) 0 = the luminaire's reference direction, counting anticlockwise seen from above.
"""

import math
from pathlib import Path

import numpy as np


class Photometry:
    def __init__(self, path):
        self.path = Path(path)
        lines = self.path.read_text(encoding="latin-1").replace("\r", "").split("\n")
        k = next(i for i, ln in enumerate(lines) if ln.strip().upper().startswith("TILT="))
        self.keywords = {}
        for ln in lines[:k]:
            if ln.startswith("[") and "]" in ln:
                key, val = ln[1:].split("]", 1)
                self.keywords[key.strip().upper()] = val.strip()
        nums = [float(t) for t in " ".join(lines[k + 1:]).split()]
        n_lamps, lm_per_lamp, mult, n_v, n_h, ptype, _units, w, l, h = nums[:10]
        _ballast, _future, self.watts = nums[10:13]
        n_v, n_h = int(n_v), int(n_h)
        i = 13
        self.v = np.array(nums[i:i + n_v]); i += n_v
        self.h = np.array(nums[i:i + n_h]); i += n_h
        self.cd = np.array(nums[i:i + n_v * n_h]).reshape(n_h, n_v) * mult     # [C index, gamma index]
        self.lumens_lamp = n_lamps * lm_per_lamp
        self.photometric_type = int(ptype)
        self.size = (w, l, h)
        assert self.photometric_type == 1, "only Type C photometry"

    def _c_fold(self, c):
        """Map any C angle onto the measured range using the file's symmetry."""
        c = np.mod(c, 360.0)
        h_max = self.h[-1]
        if h_max == 0:                                    # rotationally symmetric
            return np.zeros_like(c)
        if h_max == 90:                                   # quadrant symmetry
            c = np.where(c > 180, 360 - c, c)
            return np.where(c > 90, 180 - c, c)
        if h_max == 180:                                  # bilateral symmetry about the 0-180 plane
            return np.where(c > 180, 360 - c, c)
        return c

    def intensity(self, c, gamma):
        """cd at C, gamma in degrees (arrays broadcast). Zero outside the measured gamma range."""
        c, gamma = np.broadcast_arrays(np.asarray(c, float), np.asarray(gamma, float))
        cf = self._c_fold(c)
        hs, vs = self.h, self.v
        if len(hs) == 1:
            ci0 = np.zeros(cf.shape, int); ci1 = ci0; tc = np.zeros(cf.shape)
        else:
            ci1 = np.clip(np.searchsorted(hs, cf, side="right"), 1, len(hs) - 1)
            ci0 = ci1 - 1
            tc = (cf - hs[ci0]) / (hs[ci1] - hs[ci0])
        gi1 = np.clip(np.searchsorted(vs, gamma, side="right"), 1, len(vs) - 1)
        gi0 = gi1 - 1
        tg = np.clip((gamma - vs[gi0]) / (vs[gi1] - vs[gi0]), 0.0, 1.0)
        i00, i01 = self.cd[ci0, gi0], self.cd[ci0, gi1]
        i10, i11 = self.cd[ci1, gi0], self.cd[ci1, gi1]
        val = (1 - tc) * ((1 - tg) * i00 + tg * i01) + tc * ((1 - tg) * i10 + tg * i11)
        return np.where((gamma < vs[0] - 1e-9) | (gamma > vs[-1] + 1e-9), 0.0, val)

    def flux(self, n_gamma=720, n_c=720, lower_only=False):
        """Luminous flux of the luminaire, lm: integral of I dOmega over the sphere (midpoint rule)."""
        g = (np.arange(n_gamma) + 0.5) * (180.0 / n_gamma)
        if lower_only:
            g = g[g < 90]
        c = (np.arange(n_c) + 0.5) * (360.0 / n_c)
        G, C = np.meshgrid(g, c)
        dom = np.sin(np.radians(G)) * math.radians(180.0 / n_gamma) * math.radians(360.0 / n_c)
        return float(np.sum(self.intensity(C, G) * dom))

    def peak(self):
        """(cd, C, gamma) of the highest measured intensity."""
        k = np.unravel_index(np.argmax(self.cd), self.cd.shape)
        return float(self.cd[k]), float(self.h[k[0]]), float(self.v[k[1]])


def direction_to_cg(d_local):
    """Unit vectors in the luminaire frame (x = C 0, y = C 90, z up) -> (C, gamma) degrees."""
    d = np.asarray(d_local, float)
    gamma = np.degrees(np.arccos(np.clip(-d[..., 2], -1.0, 1.0)))
    c = np.degrees(np.arctan2(d[..., 1], d[..., 0]))
    return np.mod(c, 360.0), gamma
