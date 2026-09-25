"""Python mirror of the TrickView camera and beam geometry in the renderer.

The WebGL TRICK shader ray-marches three rounded boxes seen through an
orthographic camera looking down the (1,1,1) diagonal. Rotating the object by a
quaternion q breaks the illusion; q = identity with sep = 0 is the "lock".
Everything here reproduces that projection exactly so the compositor can draw
blueprint lines and edge-inward fills that sit on the rendered beams.
"""
import numpy as np

L = 2.0
RND = 0.075
DIR = np.array([1.0, 1.0, 1.0]) / np.sqrt(3)
RIGHT = np.array([-2.0, 1.0, 1.0]) / np.sqrt(6)
UP = np.array([0.0, -1.0, 1.0]) / np.sqrt(2)
PIVOT = np.array([5 * L / 6, L / 2, L / 6])
DG = np.full(3, 0.57735)


def qnorm(q):
    q = np.asarray(q, float)
    return q / np.linalg.norm(q)


def qaxis(ax, ang):
    ax = np.asarray(ax, float) / np.linalg.norm(ax)
    s = np.sin(ang / 2)
    return np.array([ax[0] * s, ax[1] * s, ax[2] * s, np.cos(ang / 2)])


def qmul(a, b):
    return np.array([
        a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1],
        a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0],
        a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3],
        a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2]])


def qslerp(a, b, t):
    a, b = qnorm(a), qnorm(b)
    d = float(np.dot(a, b))
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        return qnorm(a + (b - a) * t)
    th = np.arccos(d)
    return (a * np.sin((1 - t) * th) + b * np.sin(t * th)) / np.sin(th)


def qmat(q):
    x, y, z, w = qnorm(q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def boxes(H, sep):
    """(centre, half-size) of beams A, B, C in object space."""
    return [
        (np.array([L * 0.5, 0.0, 0.0]), np.array([L * 0.5 + H, H, H])),
        (np.array([L, L * 0.5, 0.0]) + DG * sep * 0.7, np.array([H, L * 0.5 + H, H])),
        (np.array([L, L, L * 0.5]) + DG * sep * 1.6, np.array([H, H, L * 0.5 + H])),
    ]


class Cam:
    def __init__(self, q, ortho, pan=(0.0, 0.0), W=1080, Hpx=1920):
        self.R = qmat(q)
        self.ortho, self.pan, self.W, self.H = ortho, np.asarray(pan, float), W, Hpx

    def project(self, X):
        """object-space points (..., 3) -> pixel xy (..., 2) (image rows down) and depth (bigger = nearer)."""
        X = np.asarray(X, float)
        Xc = (X - PIVOT) @ self.R.T
        px = Xc @ RIGHT / (2 * self.ortho) + self.pan[0]
        py = Xc @ UP / (2 * self.ortho) + 0.086 + self.pan[1]
        xy = np.stack([px * self.H + self.W / 2, self.H / 2 - py * self.H], -1)
        return xy, Xc @ DIR

    def rays(self, ss=1):
        """object-space ray origins/dirs for every pixel centre (GL convention)."""
        W, H = self.W * ss, self.H * ss
        fx = (np.arange(W) + 0.5) / ss
        fy = (np.arange(H) + 0.5) / ss
        FX, FY = np.meshgrid(fx, fy)
        FYgl = self.H - FY
        px = (FX - 0.5 * self.W) / self.H
        py = (FYgl - 0.5 * self.H) / self.H
        roW = (PIVOT + RIGHT * ((px - self.pan[0]) * 2 * self.ortho)[..., None]
               + UP * ((py - 0.086 - self.pan[1]) * 2 * self.ortho)[..., None] + DIR * 14.0)
        ro = PIVOT + (roW - PIVOT) @ self.R          # R^T applied to row vectors
        rd = (-DIR) @ self.R
        return ro, rd

    def labels(self, H, sep, ss=1):
        """per-pixel (beam id 0..2 or -1, face id 0..5, depth t) by analytic slab intersection."""
        ro, rd = self.rays(ss)
        best_t = np.full(ro.shape[:2], np.inf)
        beam = np.full(ro.shape[:2], -1, np.int8)
        face = np.full(ro.shape[:2], -1, np.int8)
        inv = 1.0 / np.where(np.abs(rd) < 1e-9, 1e-9, rd)
        for bi, (c, h) in enumerate(boxes(H, sep)):
            t1 = (c - h - ro) * inv
            t2 = (c + h - ro) * inv
            tmin = np.minimum(t1, t2)
            tmax = np.maximum(t1, t2)
            tn = tmin.max(-1)
            tf = tmax.min(-1)
            hit = (tn <= tf) & (tf > 0) & (tn < best_t)
            ax = tmin.argmax(-1)
            sgn = (rd[ax] > 0).astype(np.int8)
            best_t = np.where(hit, tn, best_t)
            beam = np.where(hit, bi, beam)
            face = np.where(hit, ax * 2 + sgn, face)
        return beam, face, best_t


def box_edges(c, h, inset=0.3 * RND):
    """12 edges of a box as (2, 3) segments, pulled onto the rounded bevel."""
    hh = h - inset
    corners = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)], float) * hh + c
    idx = lambda sx, sy, sz: (sx > 0) * 4 + (sy > 0) * 2 + (sz > 0)
    edges = []
    for a in range(3):
        o = [i for i in range(3) if i != a]
        for s1 in (-1, 1):
            for s2 in (-1, 1):
                s = [0, 0, 0]
                s[o[0]], s[o[1]] = s1, s2
                s[a] = -1
                p0 = idx(*s)
                s[a] = 1
                p1 = idx(*s)
                edges.append((a, np.array([corners[p0], corners[p1]])))
    return edges
