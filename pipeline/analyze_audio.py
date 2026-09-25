"""Measure Pursuit's tempo and the drop that the lock is timed to.

usage: python3 analyze_audio.py [../assets/source/Pursuit.mp3]
Prints the tempo, the beat grid around the drop, and the strongest full-spectrum
hit between 52 and 53.5 s (the drop the lock lands on: 0:52.725).
"""
import sys

import librosa
import numpy as np
import scipy.signal as ss

path = sys.argv[1] if len(sys.argv) > 1 else "../assets/source/Pursuit.mp3"
y, sr = librosa.load(path, sr=22050, mono=True)

oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
_, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=512, units="time", start_bpm=108, tightness=400)
b = beats[(beats > 40) & (beats < 62)]
ibi = (b[-1] - b[0]) / (len(b) - 1)
print(f"tempo {60 / ibi:.2f} BPM (beat {ibi:.4f} s)")

S = np.abs(librosa.stft(y, n_fft=1024, hop_length=64))
t = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=64)[1:]
flux = np.maximum(0, np.diff(np.log1p(S), axis=1)).sum(0)
m = (t > 52.0) & (t < 53.5)
print(f"drop hit (strongest full-spectrum onset 52-53.5 s): {t[m][np.argmax(flux[m])]:.3f} s")

S2 = np.abs(librosa.stft(y, n_fft=2048, hop_length=128))
f2 = librosa.fft_frequencies(sr=sr, n_fft=2048)
t2 = librosa.frames_to_time(np.arange(S2.shape[1]), sr=sr, hop_length=128)
low = np.log1p(S2[(f2 > 30) & (f2 < 120)].sum(0))
lf = np.maximum(0, np.diff(low, prepend=low[0]))
m2 = (t2 > 52.5) & (t2 < 58)
pk, _ = ss.find_peaks(lf[m2], height=np.percentile(lf[m2], 97), distance=int(0.12 * sr / 128))
print("kicks after the drop (every two beats):", np.round(t2[m2][pk], 3))
