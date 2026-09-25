""""Assembly" reel: timeline, cameras and render jobs.

Times below are on the animation clock t. The reel itself starts LEAD (0.25 s,
6 frames) earlier, so reel time = t + 0.25. The reel is cut to Gesaffelstein -
Pursuit starting at 0:44.00 of the track: the build cuts out at 0:52.47 and the
drop hits at 0:52.725, which lands on the lock (t = 8.47, reel 8.72 s). Tempo is
108.95 BPM (0.5507 s per beat, 2.203 s per bar), measured from Pursuit.mp3.

Shot list (animation clock, from the approved plan):
  0.00-1.86   blueprint   cyan lines plot beam 1, 2, 3 over a faint grid floor, low steep camera
  1.86-4.06   frame       slow orbit; lines thicken into glowing edges, faces fill with indigo metal edge-inward
  4.06-7.37   detail      three shallow-focus close-ups: circuits etch, network nodes switch on, dot grid fills
  7.37-8.47   lock        camera pulls out and whips to the one angle where the beams line up
  8.47        LOCK        beams lock on the drop, pink core ignites
  8.47-10.67  reveal      skin grows out from the core, camera eases round to the hero pose,
                          glow rises to full, one light sweep; then a still hold with no text
  10.67-end   lockup      ENGINEER'26 lockup fades in below
"""
import hashlib
import json
import math
import os

import numpy as np

from trickcam import RIGHT, UP, qaxis, qmul, qnorm, qslerp

FPS = 24
DROP = 52.725                       # Pursuit: full-spectrum hit + first kick of the drop
BPM = 108.95
BEAT = 60.0 / BPM
BAR = 4 * BEAT
T_LOCK = 8.47                       # animation clock: beams lock, core ignites
LEAD_FRAMES = 6                     # pen-ignition frames before the animation clock starts
LEAD = LEAD_FRAMES / FPS
SONG_START = DROP - T_LOCK - LEAD   # 44.005 -> start the track at 0:44
DUR = T_LOCK + 3 * BAR              # animation clock end, on a bar line
NFRAMES = LEAD_FRAMES + int(round(DUR * FPS))   # 368 frames = 15.33 s
W, H = 1080, 1920


def frame_time(i):
    """animation-clock time of reel frame i."""
    return i / FPS - LEAD


def beat(n):
    return T_LOCK + n * BEAT


T_BEAM = [beat(-15), beat(-14), beat(-13)]      # 0.209 0.760 1.311  blueprint traces
T_FRAME = beat(-12)                              # 1.861  lines thicken
T_FILL = [beat(-11), beat(-10), beat(-9)]        # 2.412 2.962 3.513  metal fills, one beam per beat
T_C1, T_C2, T_C3 = beat(-8), beat(-6), beat(-4)  # 4.064 5.166 6.267  close-ups
T_SWING = beat(-2)                               # 7.369
T_SKIN = (T_LOCK + 0.5 * BEAT, T_LOCK + 1.75 * BEAT)    # 8.745 -> 9.434
T_EASE = (T_LOCK + 1.25 * BEAT, T_LOCK + 3.5 * BEAT)   # 9.158 -> 10.397
T_SWEEP = (T_LOCK + 2.75 * BEAT, T_LOCK + 3.75 * BEAT)  # 9.984 -> 10.535
T_LOCKUP = T_LOCK + BAR                          # 10.673
CAPTION = (T_FRAME, T_C1 - 0.12)

# ---------------------------------------------------------------- easing
clamp = lambda v, a=0.0, b=1.0: max(a, min(b, v))
lerp = lambda a, b, u: a + (b - a) * u


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def e_io(u):  # ease in-out cubic
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def e_out(u):
    return 1 - (1 - u) ** 3


def e_sine(u):
    return 0.5 - 0.5 * math.cos(math.pi * u)


def e_whip(u):  # slow start, very fast middle, hard settle into the lock
    return 1 - (1 - u ** 2.2) ** 3.2 if u < 1 else 1.0


# ---------------------------------------------------------------- beam camera
BEAM_H = 0.5
LOCK_ORTHO = 3.35
LOCK_PAN = [0.00026, 0.0844]


BUILD_SEP = 0.85
BUILD_TARGET = (540.0, 860.0)   # where the middle of the beams sits in the 1080x1920 frame


def build_cam(t):
    """low camera slowly orbiting the beams for blueprint + frame (0 -> T_C1), auto-centred."""
    from trickcam import Cam, boxes, box_edges
    u = e_sine(clamp(t / T_C1))
    yaw = lerp(3.05, 2.62, u)
    pitch = lerp(-0.40, -0.56, u)
    q = qnorm(qmul(qaxis(UP, yaw), qaxis(RIGHT, pitch)))
    ortho = lerp(4.15, 3.75, u)
    cam = Cam(q, ortho, (0.0, 0.0), W, H)
    pts = np.concatenate([cam.project(e)[0] for c, h in boxes(BEAM_H, BUILD_SEP) for _, e in box_edges(c, h)])
    mid = (pts.min(0) + pts.max(0)) / 2
    pan = [(BUILD_TARGET[0] - mid[0]) / H, (mid[1] - BUILD_TARGET[1]) / H]
    return dict(q=list(map(float, q)), ortho=ortho, pan=[float(v) for v in pan], sep=BUILD_SEP)


SWING_Q0 = qnorm(qmul(qaxis(UP, 1.3), qaxis(RIGHT, -0.6)))


def swing_cam(t):
    """pull out + whip into the lock (T_SWING -> T_LOCK)."""
    u = clamp((t - T_SWING) / (T_LOCK - T_SWING))
    k = e_whip(u)
    q = qslerp(SWING_Q0, [0, 0, 0, 1], k)
    if u >= 1:
        q = np.array([0, 0, 0, 1.0])
    ortho = lerp(4.6, LOCK_ORTHO, e_out(k))
    pan = [lerp(0.0, LOCK_PAN[0], k), lerp(0.02, LOCK_PAN[1], k)]
    return dict(q=list(map(float, q)), ortho=ortho, pan=pan, sep=lerp(1.25, 0.0, k))


# ---------------------------------------------------------------- relief poses
P0 = dict(depth=0.3, yaw=0.0, pitch=0.0, center=[0.0, 0.1357], scale=0.269)       # matches the locked beams
P1 = dict(depth=0.45, yaw=-0.22, pitch=0.1, center=[-0.00858, 0.12807], scale=0.2820)  # v2 hero pose
CORE_OFF = dict(coreCol=[0, 0, 0], coreGlow=0)
# darker anodised indigo, matched to the v2 end frame (Mind circuit, fading dots)
KEY = [0.672, 0.724, 1.0]
MAT = dict(famR=[0.104, 0.084, 0.392], envInt=0.4, keyCol=[v * 0.9 for v in KEY], coreGlow=2.3)
TRICK_MAT = dict(famR=[0.104, 0.084, 0.392])
FLASH_K = 0.4
HERO_GLOW = 0.92

CLOSEUPS = [
    # (start, end, focus q, yaw a->b, pitch a->b, scale a->b, boot key, light)
    dict(t0=T_C1, t1=T_C2, focus=(-0.10, -0.42), yaw=(0.36, 0.30), pitch=(0.30, 0.25), scale=(0.62, 0.67), boot="bootTrace", light=(-0.2, 0.9), spark=0.16, ease="sine"),
    dict(t0=T_C2, t1=T_C3, focus=(-0.50, 0.42), yaw=(-0.30, -0.25), pitch=(0.32, 0.27), scale=(0.64, 0.69), boot="bootNet", light=(-0.5, 0.55), spark=0.8),
    dict(t0=T_C3, t1=T_SWING, focus=(0.25, 0.42), yaw=(-0.40, -0.34), pitch=(0.16, 0.11), scale=(0.64, 0.69), boot="bootDots", light=(0.1, 0.7), spark=0.8),
]


def flash(t):
    return FLASH_K * math.exp(-(t - T_LOCK) * 2.2) if t >= T_LOCK else 0.0


def relief_job(t, pose, over=None, **kw):
    o = dict(kind="relief", w=W, h=H, t=round(t, 5), center=[round(v, 6) for v in pose["center"]],
             scale=round(pose["scale"], 6), light=list(kw.get("light", (-0.55, 0.6))),
             full=kw.get("full", True), glow=round(kw.get("glow", 1.0), 4),
             over={**MAT, "depth": round(pose["depth"], 6), "yaw": round(pose["yaw"], 6), "pitch": round(pose["pitch"], 6), "persp": 4, **(over or {})})
    return o


def trick_job(t, cam, core=0.0, fl=0.0, lit=1.0):
    return dict(kind="trick", w=W, h=H, t=round(t, 5), q=[round(v, 7) for v in cam["q"]], sep=round(cam["sep"], 6),
                ortho=round(cam["ortho"], 6), pan=[round(v, 6) for v in cam["pan"]], beamH=BEAM_H, lit=lit,
                coreK=round(core, 4), coreGlow=2.2 if core > 0 else 0.0, flash=round(fl, 5), over=TRICK_MAT)


def pose_lerp(a, b, u):
    return {k: ([lerp(x, y, u) for x, y in zip(a[k], b[k])] if isinstance(a[k], list) else lerp(a[k], b[k], u)) for k in a}


def closeup_pose(c, t):
    u = e_sine(seg(t, c["t0"], c["t1"]))
    s = lerp(*c["scale"], u)
    fx, fy = c["focus"]
    return dict(depth=0.3, yaw=lerp(*c["yaw"], u), pitch=lerp(*c["pitch"], u), center=[-fx * s, -fy * s], scale=s)


def spec(t):
    """Everything the compositor needs for reel time t."""
    s = dict(t=t, jobs=[], shot=None)
    if t < T_C1:
        s["shot"] = "build"
        s["cam"] = build_cam(t)
        if t >= T_FILL[0] - 0.05:
            s["jobs"] = [trick_job(t, s["cam"])]
    elif t < T_SWING:
        c = next(c for c in CLOSEUPS if c["t0"] <= t < c["t1"])
        s["shot"] = "close"
        s["close"] = c
        u = seg(t, c["t0"] + 0.04, c["t1"] - 0.16)
        # layers boot in order: circuits, then network, then dots; earlier ones stay on
        order = ["bootTrace", "bootNet", "bootDots"]
        i = order.index(c["boot"])
        over = dict(CORE_OFF, spark=c["spark"])
        for j, k in enumerate(order):
            ue = e_sine(u) if c.get("ease") == "sine" else e_out(u)
            over[k] = 1.0 if j < i else (round(ue, 5) if j == i else 0.0)
        pose = closeup_pose(c, t)
        s["pose"] = pose
        s["jobs"] = [relief_job(t, pose, over, light=c["light"], glow=1.0)]
    elif t < T_LOCK:
        s["shot"] = "swing"
        # 180-degree shutter: blend sub-frames across half a frame
        n = 7
        sub = [t + (k / (n - 1) - 0.5) * (0.5 / FPS) for k in range(n)]
        sub = [min(x, T_LOCK - 1e-4) for x in sub]
        s["jobs"] = [trick_job(x, swing_cam(x), lit=1.25) for x in sub]
        s["cam"] = swing_cam(t)
    else:
        s["shot"] = "reveal" if t < T_LOCKUP else "end"
        lock = dict(q=[0, 0, 0, 1.0], ortho=LOCK_ORTHO, pan=LOCK_PAN, sep=0.0)
        fl = flash(t)
        grow = e_io(seg(t, *T_SKIN))
        s["grow"] = grow
        ease_u = e_io(seg(t, *T_EASE))
        pose = pose_lerp(P0, P1, ease_u)
        s["pose"] = pose
        glow = lerp(0.66, HERO_GLOW, e_sine(seg(t, T_SKIN[0], T_EASE[1])))
        full = lerp(1.0, 0.82, e_sine(seg(t, T_LOCKUP + 0.6, T_LOCKUP + 1.8)))
        sw = seg(t, *T_SWEEP)
        over = dict(coreFlash=round(fl * 0.7, 5), spark=0.0,
                    sweepPos=round(lerp(-1.5, 1.5, sw), 5), sweepAmt=round(math.sin(math.pi * sw) * 1.1, 5) if 0 < sw < 1 else 0.0)
        jobs = []
        if grow < 0.999:
            jobs.append(trick_job(t, lock, core=1.0, fl=fl))
        if grow > 0.0:
            jobs.append(relief_job(t, pose, over, glow=glow, full=round(full, 4)))
        s["jobs"] = jobs
    return s


def job_path(job, root="renders"):
    key = json.dumps({k: v for k, v in job.items() if k != "out"}, sort_keys=True)
    h = hashlib.md5(key.encode()).hexdigest()[:14]
    return os.path.join(root, f"{job['kind']}_{h}.png")


def write_jobs(frames, path, root="renders"):
    seen = set()
    out = []
    for i in frames:
        for j in spec(frame_time(i))["jobs"]:
            p = job_path(j, root)
            if p in seen:
                continue
            seen.add(p)
            out.append({**j, "out": os.path.abspath(p)})
    with open(path, "w") as f:
        for j in out:
            f.write(json.dumps(j) + "\n")
    return out


if __name__ == "__main__":
    import sys
    frames = range(NFRAMES)
    if len(sys.argv) > 2:
        frames = [int(x) for x in sys.argv[2].split(",")]
    jobs = write_jobs(frames, sys.argv[1] if len(sys.argv) > 1 else "jobs.jsonl")
    print(f"{NFRAMES} frames ({NFRAMES / FPS:.3f} s), song from {SONG_START:.3f} s, lock at reel {T_LOCK + LEAD:.3f} s; {len(jobs)} render jobs")
    for name in ["T_BEAM", "T_FRAME", "T_FILL", "T_C1", "T_C2", "T_C3", "T_SWING", "T_LOCK", "T_SKIN", "T_EASE", "T_SWEEP", "T_LOCKUP", "DUR"]:
        v = globals()[name]
        print(f"  {name:9s}", [round(x, 3) for x in v] if isinstance(v, (list, tuple)) else round(v, 3))
