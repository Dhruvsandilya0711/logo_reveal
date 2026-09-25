"""Composite reel frames from the rendered layers.

usage: python3 compose.py <9x16|1x1> <outdir> [frame,frame,...|a-b]

Each frame is built in a 1080x1920 "world" canvas as three layers:
  rgb  premultiplied colour of the object      (renders, metal fill)
  a    coverage of the object
  add  additive light (blueprint lines, grid, welding front, skin ring)
then warped into the output format and laid over a procedural background with a
floor reflection, the caption and the lockup.
"""
import math
import os
import sys
from multiprocessing import Pool

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import plan as P
from trickcam import DIR, PIVOT, RIGHT, RND, UP, Cam, boxes

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
W, H = P.W, P.H

CYAN = np.array([0.21, 0.78, 1.0], np.float32)        # #35C6FF, blueprint lines
CYAN_HOT = np.array([0.80, 0.97, 1.0], np.float32)
VIOLET = np.array([0.55, 0.36, 1.0], np.float32)
PINK = np.array([1.0, 0.36, 0.78], np.float32)        # #FF5CC8, core only


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ renders
_cache = {}


def load(job):
    p = P.job_path(job, os.path.join(HERE, "renders"))
    if p in _cache:
        return _cache[p]
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im is None:
        raise FileNotFoundError(p)
    im = im.astype(np.float32) / 255.0
    a = im[..., 3]
    rgb = im[..., 2::-1] * a[..., None]
    if len(_cache) > 24:
        _cache.clear()
    _cache[p] = (rgb, a)
    return rgb, a


# ------------------------------------------------------------------ blueprint
def draw_poly(canvas, pts, val, width):
    pts = np.round(np.asarray(pts) * 16).astype(np.int32)
    for i in range(len(pts) - 1):
        cv2.line(canvas, tuple(pts[i]), tuple(pts[i + 1]), float(val), int(width), cv2.LINE_AA, shift=4)


def edge_samples(p0, p1, frac, n=48):
    if frac <= 0:
        return None
    s = np.linspace(0, frac, max(2, int(n * frac) + 2))
    return p0[None] + (p1 - p0)[None] * s[:, None]


def beam_paths(b, c, h, pb):
    """segments of beam b drawn so far (progress pb 0..1) + pen-tip points."""
    a = b
    o1, o2 = [i for i in range(3) if i != a]
    hh = h - 0.3 * RND
    rect = [(-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1)]

    def corner(sa, s1, s2):
        v = c.copy()
        v[a] += sa * hh[a]
        v[o1] += s1 * hh[o1]
        v[o2] += s2 * hh[o2]
        return v

    segs, tips = [], []
    pc = min(1.0, pb / 0.3)
    pl = min(1.0, max(0.0, (pb - 0.22) / 0.55))
    pe = min(1.0, max(0.0, (pb - 0.75) / 0.25))
    for cap_sa, prog in ((-1, pc), (1, pe)):
        done = prog * 4
        for k in range(4):
            f = min(1.0, max(0.0, done - k))
            if f <= 0:
                break
            p0, p1 = corner(cap_sa, *rect[k]), corner(cap_sa, *rect[k + 1])
            segs.append(edge_samples(p0, p1, f))
            if f < 1:
                tips.append(p0 + (p1 - p0) * f)
    if pl > 0:
        for k in range(4):
            p0, p1 = corner(-1, *rect[k]), corner(1, *rect[k])
            segs.append(edge_samples(p0, p1, pl, 96))
            if pl < 1:
                tips.append(p0 + (p1 - p0) * pl)
    return [s for s in segs if s is not None], tips


def grid_layer(cam, t, amt):
    g = np.zeros((H, W), np.float32)
    if amt <= 0:
        return g
    base = PIVOT - 2.25 * UP
    e1, e2 = RIGHT, DIR
    span, step = 9.0, 0.5
    for v in np.arange(-span, span + 1e-6, step):
        for a, bvec in ((e1, e2), (e2, e1)):
            p0 = base + a * v - bvec * span
            p1 = base + a * v + bvec * span
            xy, _ = cam.project(np.array([p0, p1]))
            major = abs((v / step) % 4) < 1e-6
            draw_poly(g, xy, 0.55 if major else 0.28, 1)
    cxy, _ = cam.project(base[None])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r2 = ((xx - cxy[0, 0]) ** 2 + (yy - cxy[0, 1]) ** 2) / (620.0 ** 2)
    return g * np.exp(-r2) * amt


def build_layers(s):
    t, c = s["t"], s["cam"]
    cam = Cam(c["q"], c["ortho"], c["pan"], W, H)
    beam, face, tdep = cam.labels(P.BEAM_H, c["sep"])
    bx = boxes(P.BEAM_H, c["sep"])

    rgb = np.zeros((H, W, 3), np.float32)
    a = np.zeros((H, W), np.float32)
    add = np.zeros((H, W, 3), np.float32)

    # ---- metal fill, edge-inward, one beam per beat
    fills = [P.e_out(P.seg(t, tf, tf + 0.72)) for tf in P.T_FILL]
    if s["jobs"]:
        mrgb, ma = load(s["jobs"][0])
        lab = np.where(beam >= 0, beam.astype(np.int16) * 8 + face, -1)
        M = np.zeros((H, W), np.float32)
        front = np.zeros((H, W), np.float32)
        for code in np.unique(lab):
            if code < 0:
                continue
            b = code // 8
            fb = fills[b]
            if fb <= 0:
                continue
            reg = (lab == code).astype(np.uint8)
            d = cv2.distanceTransform(np.pad(reg, 1), cv2.DIST_L2, 5)[1:-1, 1:-1]
            dn = d / max(d.max(), 1.0)
            m = smooth(fb + 0.03, fb - 0.03, dn) if fb < 1 else np.ones_like(dn)
            M = np.maximum(M, m * reg)
            if fb < 1:
                front = np.maximum(front, np.exp(-((dn - fb) / 0.035) ** 2) * reg * (1 - fb) ** 0.5)
        sil = (beam >= 0).astype(np.float32)
        Ms = cv2.GaussianBlur(M, (0, 0), 1.0)
        halo = cv2.GaussianBlur(cv2.dilate(M, np.ones((31, 31), np.uint8)), (0, 0), 12)
        k = np.where(sil > 0, Ms, halo)
        rgb += mrgb * k[..., None]
        a = np.maximum(a, ma * k)
        add += (VIOLET * 0.9 + CYAN * 0.5)[None, None] * cv2.GaussianBlur(front, (0, 0), 1.2)[..., None] * 1.3

    # ---- blueprint lines
    thick = P.e_out(P.seg(t, P.T_FRAME, P.T_FRAME + 0.5))
    width = 2 + int(round(2 * thick))
    line = np.zeros((H, W), np.float32)
    tip = np.zeros((H, W), np.float32)
    if t < P.T_BEAM[0]:
        # the pen ignites before the first line is drawn, so something moves from the first frame
        c0, h0 = bx[0]
        start = c0 - (h0 - 0.3 * RND)
        xy, _ = cam.project(start[None])
        k = P.e_out(P.clamp((t + P.LEAD) / (P.T_BEAM[0] + P.LEAD)))
        cv2.circle(tip, tuple(np.round(xy[0] * 16).astype(int)), 5 * 16, k, -1, cv2.LINE_AA, shift=4)
    for b in range(3):
        pb = P.clamp((t - P.T_BEAM[b]) / 0.55)
        if pb <= 0:
            continue
        done = fills[b]
        vis_k = 1.0 + 0.7 * thick - 0.6 * P.e_out(done)
        hid_k = 0.3 * (1 - P.e_out(done))
        segs, tips = beam_paths(b, bx[b][0], bx[b][1], pb)
        for sp in segs:
            xy, dep = cam.project(sp)
            tX = 14.0 - dep
            xi = np.clip(xy[:, 0].astype(int), 0, W - 1)
            yi = np.clip(xy[:, 1].astype(int), 0, H - 1)
            vis = tX <= tdep[yi, xi] + 0.09
            for i in range(len(sp) - 1):
                v = vis_k if (vis[i] and vis[i + 1]) else hid_k
                if v > 0.01:
                    draw_poly(line, xy[i:i + 2], v, width)
        for tp in tips:
            xy, _ = cam.project(tp[None])
            cv2.circle(tip, tuple(np.round(xy[0] * 16).astype(int)), 5 * 16, 1.0, -1, cv2.LINE_AA, shift=4)
    glow = cv2.GaussianBlur(line, (0, 0), 3.5) * 0.9 + cv2.GaussianBlur(line, (0, 0), 12) * 0.55
    tipg = cv2.GaussianBlur(tip, (0, 0), 3) * 1.6 + cv2.GaussianBlur(tip, (0, 0), 16) * 1.2
    add += CYAN_HOT[None, None] * line[..., None] * 0.9 + CYAN[None, None] * glow[..., None] + CYAN_HOT[None, None] * tipg[..., None]

    # ---- grid floor
    gamt = P.e_out(P.seg(t, -P.LEAD, 0.6)) * (1 - P.seg(t, P.T_FILL[2], P.T_C1)) * 0.7
    g = grid_layer(cam, t, gamt)
    add += (CYAN * 0.8 + VIOLET * 0.2)[None, None] * g[..., None] * (1 - a[..., None])
    return rgb, a, add


# ------------------------------------------------------------------ close-ups
def dof(rgb, a, angle_deg=-10, band=170, ramp=260, maxs=11.0):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    th = math.radians(angle_deg)
    d = np.abs((yy - H * 0.5) * math.cos(th) - (xx - W * 0.5) * math.sin(th))
    r = np.clip((d - band) / ramp, 0, 1) * maxs
    stack = [np.dstack([rgb, a])]
    sig = [0.0, 3.0, 6.5, 11.0]
    for sgm in sig[1:]:
        stack.append(cv2.GaussianBlur(stack[0], (0, 0), sgm))
    out = np.zeros_like(stack[0])
    for i in range(len(sig) - 1):
        w = np.clip((r - sig[i]) / (sig[i + 1] - sig[i]), 0, 1)
        if i == 0:
            out = stack[0] * (1 - w[..., None]) + stack[1] * w[..., None]
        else:
            out = out * (1 - w[..., None]) + stack[i + 1] * w[..., None]
    return out[..., :3], out[..., 3]


def close_layers(s):
    rgb, a = load(s["jobs"][0])
    rgb, a = dof(rgb, a)
    return rgb, a, np.zeros_like(rgb)


def swing_layers(s):
    acc_rgb = np.zeros((H, W, 3), np.float32)
    acc_a = np.zeros((H, W), np.float32)
    for j in s["jobs"]:
        r, al = load(j)
        acc_rgb += r
        acc_a += al
    n = len(s["jobs"])
    return acc_rgb / n, acc_a / n, np.zeros((H, W, 3), np.float32)


def core_px(pose):
    q = np.array([0.485 * 2 - 1, (0.5 - 0.4304) * 2])
    p = np.array(pose["center"]) + pose["scale"] * q
    return np.array([W / 2 + p[0] * H, H / 2 - p[1] * H])


def reveal_layers(s):
    t, grow = s["t"], s["grow"]
    jobs = list(s["jobs"])
    add = np.zeros((H, W, 3), np.float32)
    if grow <= 0:
        rgb, a = load(jobs[0])
        return rgb, a, add
    if grow >= 0.999:
        rgb, a = load(jobs[-1])
        return rgb, a, add
    trgb, ta = load(jobs[0])
    rrgb, ra = load(jobs[1])
    c = core_px(P.P0)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot(xx - c[0], yy - c[1])
    r = grow * 780.0
    m = smooth(r + 10, r - 10, d)
    rgb = rrgb * m[..., None] + trgb * (1 - m[..., None])
    a = ra * m + ta * (1 - m)
    body = cv2.GaussianBlur(np.maximum(ra, ta), (0, 0), 2) > 0.3
    ring = np.exp(-((d - r) / 7.0) ** 2) * body
    col = PINK * (1 - grow) + CYAN * grow
    add += col[None, None] * (cv2.GaussianBlur(ring.astype(np.float32), (0, 0), 1.5) * 2.2 + cv2.GaussianBlur(ring.astype(np.float32), (0, 0), 9) * 1.4)[..., None]
    return rgb, a, add


# ------------------------------------------------------------------ overlays
FONT = os.path.join(ASSETS, "fonts", "Orbitron.ttf")


def caption_img(text, size, track):
    f = ImageFont.truetype(FONT, size)
    try:
        f.set_variation_by_name("Medium")
    except Exception:
        pass
    widths = [f.getlength(ch) for ch in text]
    total = sum(widths) + track * size * (len(text) - 1)
    rule, gap = int(size * 2.2), int(size * 1.1)
    Wc = int(total + 2 * (rule + gap) + 40)
    Hc = int(size * 2.4)
    im = Image.new("L", (Wc, Hc), 0)
    dr = ImageDraw.Draw(im)
    x = 20 + rule + gap
    for ch, w in zip(text, widths):
        dr.text((x, Hc / 2), ch, font=f, fill=255, anchor="lm")
        x += w + track * size
    yl = Hc // 2
    dr.line([(20, yl), (20 + rule, yl)], fill=150, width=1)
    dr.line([(Wc - 20 - rule, yl), (Wc - 20, yl)], fill=150, width=1)
    return np.asarray(im, np.float32) / 255.0


_cap = {}


def caption_layer(fmt, alpha):
    key = fmt
    if key not in _cap:
        _cap[key] = caption_img("SOMETHING IS BEING WIRED", 26 if fmt == "9x16" else 22, 0.62)
    c = _cap[key]
    glow = cv2.GaussianBlur(c, (0, 0), 6) * 0.9
    col = np.array([0.86, 0.94, 0.96], np.float32)
    teal = np.array([0.43, 0.86, 0.82], np.float32)
    return (c[..., None] * col + glow[..., None] * teal * 0.6) * alpha


_lock = None


def lockup_layer():
    global _lock
    if _lock is None:
        _lock = cv2.imread(os.path.join(ASSETS, "derived", "lockup_add.png"))[..., ::-1].astype(np.float32) / 255.0
    return _lock


def paste_add(dst, src, x0, y0, k=1.0):
    h, w = src.shape[:2]
    X0, Y0 = max(0, x0), max(0, y0)
    X1, Y1 = min(dst.shape[1], x0 + w), min(dst.shape[0], y0 + h)
    if X1 <= X0 or Y1 <= Y0:
        return
    dst[Y0:Y1, X0:X1] += src[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * k


# ------------------------------------------------------------------ formats
FMT = {"9x16": (1080, 1920), "1x1": (1080, 1080)}


def view(fmt, t):
    """world -> output affine (scale, world anchor y, output anchor y)."""
    if fmt == "9x16":
        return 1.0, 0.0, 0.0
    if t < P.T_C1:
        s0, yw, yo = 0.8, 850.0, 492.0
    elif t < P.T_SWING:
        s0, yw, yo = 1.0, 960.0, 540.0
    else:
        u = P.e_io(P.seg(t, P.T_SWING, P.T_LOCK))
        s0 = P.lerp(0.86, 0.64, u)
        yw = P.lerp(760.0, 700.0, u)
        yo = P.lerp(540.0, 368.0, u)
    return s0, yw, yo


def warp(img, fmt, t):
    if fmt == "9x16":
        return img
    Wo, Ho = FMT[fmt]
    s0, yw, yo = view(fmt, t)
    M = np.float32([[s0, 0, Wo / 2 - s0 * W / 2], [0, s0, yo - s0 * yw]])
    return cv2.warpAffine(img, M, (Wo, Ho), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)


def background(fmt, t, center_y):
    Wo, Ho = FMT[fmt]
    yy, xx = np.mgrid[0:Ho, 0:Wo].astype(np.float32)
    # sampled from the v2 end frame: navy-violet, brightest behind the logo
    v = (yy / Ho)[..., None]
    stops = [(0.0, (0.031, 0.035, 0.125)), (0.36, (0.059, 0.043, 0.184)), (0.65, (0.039, 0.035, 0.137)),
             (0.78, (0.024, 0.031, 0.094)), (1.0, (0.010, 0.020, 0.055))]
    bg = np.zeros((Ho, Wo, 3), np.float32)
    for (a0, c0), (a1, c1) in zip(stops[:-1], stops[1:]):
        k = np.clip((v - a0) / (a1 - a0), 0, 1)
        inside = (v >= a0) & (v <= a1)
        bg = np.where(inside, np.array(c0, np.float32) * (1 - k) + np.array(c1, np.float32) * k, bg)
    if fmt == "1x1":
        bg = cv2.resize(bg, (Wo, Ho))
    lift = P.e_out(P.seg(t, P.T_FRAME, P.T_C1)) * 0.4 + 0.6 * P.e_out(P.seg(t, P.T_SWING, P.T_LOCK + 0.4))
    bg = bg * (0.3 + 0.7 * lift)
    r2 = ((xx - Wo / 2) / 520.0) ** 2 + ((yy - center_y) / 600.0) ** 2
    halo = np.exp(-r2)[..., None] * np.array([0.42, 0.30, 1.0], np.float32) * 0.05 * lift
    return bg + halo


def reflection(rgb, a, add, strength):
    if strength <= 0.001:
        return None
    cov = a > 0.5
    rows = np.where(cov.any(1))[0]
    if len(rows) == 0:
        return None
    fy = int(rows.max()) + 3
    Ho = rgb.shape[0]
    n = min(fy, Ho - fy)
    if n <= 4:
        return None
    src = (rgb + add * 0.5)[fy - n:fy][::-1]
    src = cv2.GaussianBlur(src, (0, 0), 1.5) * 0.5 + cv2.GaussianBlur(src, (0, 0), 7) * 0.5
    dy = np.arange(n, dtype=np.float32)[:, None, None]
    fall = np.exp(-dy / 170.0) * strength
    out = np.zeros_like(rgb)
    out[fy:fy + n] = src * fall
    return out


def frame(fmt, i):
    t = P.frame_time(i)
    s = P.spec(t)
    if s["shot"] == "build":
        rgb, a, add = build_layers(s)
    elif s["shot"] == "close":
        rgb, a, add = close_layers(s)
    elif s["shot"] == "swing":
        rgb, a, add = swing_layers(s)
    else:
        rgb, a, add = reveal_layers(s)
    rgb, a, add = warp(rgb, fmt, t), warp(a, fmt, t), warp(add, fmt, t)
    Wo, Ho = FMT[fmt]
    s0, yw, yo = view(fmt, t)
    cy = yo + s0 * (700.0 - yw) if fmt == "1x1" else (700.0 if t >= P.T_SWING else P.BUILD_TARGET[1])
    bg = background(fmt, t, cy)
    ref = reflection(rgb, a, add, 0.32 * P.e_out(P.seg(t, P.T_LOCK - 0.05, P.T_LOCK + 0.5)))
    if ref is not None:
        bg = bg + ref * (1 - a[..., None])
    out = bg * (1 - a[..., None]) + rgb + add

    # caption, one line during the build
    ca = P.e_out(P.seg(t, P.CAPTION[0], P.CAPTION[0] + 0.3)) * (1 - P.seg(t, P.CAPTION[1] - 0.25, P.CAPTION[1]))
    if ca > 0.001:
        cl = caption_layer(fmt, ca)
        y = int(Ho * (0.80 if fmt == "9x16" else 0.905)) - cl.shape[0] // 2
        paste_add(out, cl, (Wo - cl.shape[1]) // 2, y)

    # lockup
    la = P.e_out(P.seg(t, P.T_LOCKUP, P.T_LOCKUP + 0.75))
    if la > 0.001:
        L = lockup_layer()
        rise = int((1 - la) * 22)
        if fmt == "9x16":
            paste_add(out, L, 0, 1320 + rise, la)
        else:
            Ls = cv2.resize(L, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA)
            paste_add(out, Ls, (Wo - Ls.shape[1]) // 2, 752 + rise, la)

    # grain against banding, gentle vignette
    yy, xx = np.mgrid[0:Ho, 0:Wo].astype(np.float32)
    vig = 1 - 0.18 * np.clip(((xx - Wo / 2) / (Wo * 0.75)) ** 2 + ((yy - Ho / 2) / (Ho * 0.7)) ** 2, 0, 1)
    out = out * vig[..., None]
    rng = np.random.default_rng(i * 7 + (0 if fmt == "9x16" else 1))
    out = out + (rng.random(out.shape[:2], np.float32)[..., None] - 0.5) / 255.0 * 1.5
    return np.clip(out, 0, 1)


def run(args):
    fmt, outdir, i = args
    p = os.path.join(outdir, f"{i:04d}.png")
    img = frame(fmt, i)
    cv2.imwrite(p, (img[..., ::-1] * 255 + 0.5).astype(np.uint8))
    return i


def parse_frames(arg):
    if arg is None:
        return list(range(P.NFRAMES))
    out = []
    for part in arg.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


if __name__ == "__main__":
    fmt, outdir = sys.argv[1], sys.argv[2]
    frames = parse_frames(sys.argv[3] if len(sys.argv) > 3 else None)
    os.makedirs(outdir, exist_ok=True)
    procs = int(os.environ.get("PROCS", "4"))
    with Pool(procs) as pool:
        for n, _ in enumerate(pool.imap_unordered(run, [(fmt, outdir, i) for i in frames]), 1):
            if n % 24 == 0:
                print(f"{fmt}: {n}/{len(frames)}", flush=True)
    print("composited", len(frames), "frames ->", outdir)
