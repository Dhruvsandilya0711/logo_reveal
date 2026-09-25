"""Lift the approved end-card lockup out of the v2 reel.

The lockup (NITK Surathkal's / ENGINEER'26 wordmark / pixel COGNITRIXX /
Rewire reality) was approved in cognitrixx-reel-v2-12s.mp4. It is light on a
dark ground, so it is recovered as an additive (screen-like) light layer:
layer = frame - smooth background, where the background under the type is
reconstructed by inpainting. Output: assets/derived/lockup_add.png (RGB, add
it onto the new frame) plus the crop box it came from.
"""
import json
import subprocess
import sys

import cv2
import numpy as np

src = sys.argv[1] if len(sys.argv) > 1 else "../assets/source/cognitrixx-reel-v2-12s.mp4"
out = "../assets/derived/"
Y0, Y1 = 1320, 1820

raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "11.4", "-i", src, "-frames:v", "12",
                      "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, 1920, 1080, 3).astype(np.float32)
frame = frames.mean(0)
reg = frame[Y0:Y1]

lum = reg.max(2)
floor = cv2.GaussianBlur(cv2.erode(lum, np.ones((61, 61), np.uint8)), (0, 0), 30)
bright = (lum - floor) > 9
# only keep crisp structures (type, rules, sparkles), not the soft reflection haze
sharp = np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 2.0)) > 5
near_sharp = cv2.dilate(sharp.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (51, 51))) > 0
mask = (bright & near_sharp).astype(np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
# normalised convolution: smooth the background using only pixels outside the type
keep = (1 - mask).astype(np.float32)
num = cv2.GaussianBlur(reg * keep[..., None], (0, 0), 28)
den = cv2.GaussianBlur(keep, (0, 0), 28)[..., None]
bg_far = num / np.maximum(den, 1e-3)
num = cv2.GaussianBlur(reg * keep[..., None], (0, 0), 7)
den = cv2.GaussianBlur(keep, (0, 0), 7)[..., None]
bg_near = num / np.maximum(den, 1e-3)
wnear = np.clip(den * 3.0 - 1.2, 0, 1)
bg = bg_near * wnear + bg_far * (1 - wnear)
layer = np.clip(reg - bg, 0, 255)
# kill compression noise floor outside the type
soft = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 4)
layer *= np.clip(soft * 1.4, 0, 1)[..., None]
layer = np.where(layer < 2.0, 0, layer)
cv2.imwrite(out + "lockup_add.png", np.clip(layer + 0.5, 0, 255).astype(np.uint8))
ys, xs = np.where(layer.max(2) > 6)
box = {"y0": Y0, "y1": Y1, "content_x": [int(xs.min()), int(xs.max())], "content_y": [int(ys.min() + Y0), int(ys.max() + Y0)]}
json.dump(box, open(out + "lockup_box.json", "w"), indent=1)
print(box)
