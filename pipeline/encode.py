"""Encode every cut from composited frames, with Pursuit laid in at the right offset.

usage: python3 encode.py        (expects frames/9x16 and frames/1x1 to be complete)

Outputs (../renders/):
  cognitrixx-assembly-reel-15s.mp4          1080x1920, full reel with audio
  cognitrixx-assembly-reel-15s-silent.mp4   same, no audio (add Pursuit in the app)
  cognitrixx-assembly-story-11s.mp4         1080x1920, from the close-ups to the end
  cognitrixx-assembly-sting-2s.mp4          1080x1920, whip + lock + end card
  cognitrixx-assembly-feed-1x1-15s.mp4      1080x1080 reframe of the full reel
  cognitrixx-assembly-cover.jpg             settled logo + lockup, 9:16
  cognitrixx-assembly-cover-1x1.jpg         settled logo + lockup, 1:1
"""
import math
import os
import shutil
import subprocess
import tempfile

import cv2
import numpy as np

import plan as P

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, "..", "assets", "source", "Pursuit.mp3")
OUT = os.path.join(HERE, "..", "renders")
FR = os.path.join(HERE, "frames")
FF = shutil.which("ffmpeg") or "ffmpeg"

VIDEO = ["-c:v", "libx264", "-preset", "slow", "-crf", "15", "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-movflags", "+faststart"]


def run(cmd):
    print(" ".join(cmd[:6]), "...", cmd[-1])
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def encode(fmt, first, count, name, audio_start=None, fade_out=0.35, frame_list=None):
    """frames [first, first+count) of fmt; audio from Pursuit at audio_start seconds."""
    dur = count / P.FPS
    with tempfile.TemporaryDirectory() as tmp:
        src = frame_list or [os.path.join(FR, fmt, f"{i:04d}.png") for i in range(first, first + count)]
        for k, p in enumerate(src):
            os.symlink(os.path.abspath(p), os.path.join(tmp, f"{k:04d}.png"))
        cmd = [FF, "-y", "-v", "error", "-framerate", str(P.FPS), "-i", os.path.join(tmp, "%04d.png")]
        if audio_start is not None:
            af = f"afade=t=in:st=0:d=0.02,afade=t=out:st={dur - fade_out:.3f}:d={fade_out:.3f}"
            cmd += ["-ss", f"{audio_start:.3f}", "-t", f"{dur:.3f}", "-i", AUDIO, "-map", "0:v", "-map", "1:a",
                    "-af", af, "-c:a", "aac", "-b:a", "256k", "-ar", "48000"]
        cmd += VIDEO + ["-r", str(P.FPS), "-t", f"{dur:.3f}", os.path.join(OUT, name)]
        run(cmd)


def sting():
    """one bar (2.2 s): the whip's last beat, the lock on the drop, then the end card."""
    fmt = "9x16"
    t0 = P.T_LOCK - P.BEAT + P.LEAD             # reel time one beat before the lock
    n = int(round(P.BAR * P.FPS))               # 53 frames
    a = int(round(t0 * P.FPS))
    cut = int(round((P.T_LOCK + P.LEAD + 0.55) * P.FPS)) - a   # hold the flare ~0.55 s
    end0 = int(round((12.6 + P.LEAD) * P.FPS))
    tmpd = tempfile.mkdtemp()
    frames = []
    for k in range(n):
        if k < cut:
            frames.append(os.path.join(FR, fmt, f"{a + k:04d}.png"))
            continue
        e = cv2.imread(os.path.join(FR, fmt, f"{end0 + (k - cut):04d}.png")).astype(np.float32)
        x = (k - cut) / 4.0
        if x < 1:   # 4-frame dissolve out of the flare
            f = cv2.imread(os.path.join(FR, fmt, f"{a + k:04d}.png")).astype(np.float32)
            e = f * (1 - x) + e * x
        p = os.path.join(tmpd, f"s{k:04d}.png")
        cv2.imwrite(p, np.clip(e, 0, 255).astype(np.uint8))
        frames.append(p)
    encode(fmt, 0, n, "cognitrixx-assembly-sting-2s.mp4", audio_start=P.SONG_START + a / P.FPS, fade_out=0.3, frame_list=frames)
    shutil.rmtree(tmpd)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    N = P.NFRAMES
    encode("9x16", 0, N, "cognitrixx-assembly-reel-15s.mp4", audio_start=P.SONG_START)
    encode("9x16", 0, N, "cognitrixx-assembly-reel-15s-silent.mp4")
    s0 = int(math.ceil((P.T_C1 + P.LEAD) * P.FPS))
    encode("9x16", s0, N - s0, "cognitrixx-assembly-story-11s.mp4", audio_start=P.SONG_START + s0 / P.FPS)
    encode("1x1", 0, N, "cognitrixx-assembly-feed-1x1-15s.mp4", audio_start=P.SONG_START)
    sting()
    cover = int(round((13.5 + P.LEAD) * P.FPS))
    for fmt, name in (("9x16", "cognitrixx-assembly-cover.jpg"), ("1x1", "cognitrixx-assembly-cover-1x1.jpg")):
        im = cv2.imread(os.path.join(FR, fmt, f"{cover:04d}.png"))
        cv2.imwrite(os.path.join(OUT, name), im, [cv2.IMWRITE_JPEG_QUALITY, 94])
    print("done ->", OUT)
