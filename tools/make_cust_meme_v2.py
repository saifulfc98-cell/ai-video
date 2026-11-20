"""v2 of the 'cust datang semalam dengan awek lain' meme: harder effects + phonk/DJ music.

Usage (from repo root):  python3 tools/make_cust_meme_v2.py
Writes cust-awek-lain/output/cust-awek-lain-v2.mp4 (1080x1920, 30 s).
Everything is timed in beats of a 128 BPM synthesized phonk track:
  intro cowbell -> beat -> record-stop freeze 'KANTOI!' -> beat -> snare roll -> DROP -> end card.
Effects: zoom-blur whip transitions, RGB split glitch, beat strobe, camera shake, freeze frame,
caption slam with tilt, emoji rain.  Reuses the text helpers of make_cust_meme.py.
"""
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from make_cust_meme import ROOT, W, H, FPS, SR, YELLOW, WHITE, HOOK, emoji_img, text_img, ease_out  # noqa: E402

BPM = 128
B = 60 / BPM                 # one beat = 0.469 s
RED = (255, 40, 60)

# (clip, start s, length in beats, words [(text, colour, beat)], fx)
SEGMENTS = [
    ("klip1-kaunter-air.mp4", 0.4, 12,
     [("EH", WHITE, 0), ("ABANG", WHITE, 1), ("DATANG", WHITE, 2), ("LAGI 😏", YELLOW, 3),
      ("TAPI", WHITE, 6), ("KAKAK", WHITE, 7), ("NI", WHITE, 8), ("BARU 👀", YELLOW, 9)], "intro"),
    ("klip2-kaunter-air-lebar.mp4", 0.8, 10,
     [("SEMALAM", WHITE, 0), ("BUKAN", WHITE, 1), ("YANG", WHITE, 2), ("NI…", YELLOW, 3),
      ("🤐", WHITE, 8)], "freeze"),
    ("klip3-kafe.mp4", 4.2, 10,
     [("SATU", WHITE, 0), ("KEDAI", WHITE, 1), ("DAH", WHITE, 2), ("TAHU 🤭", YELLOW, 3),
      ("HAHAHA", WHITE, 6)], "beat"),
    ("klip4-kedai.mp4", 2.4, 10,
     [("ABANG", WHITE, 0), ("KAUNTER", WHITE, 1), ("PUN", WHITE, 2), ("PERASAN 👀", YELLOW, 3),
      ("TUNGGU…", RED, 6)], "build"),
    ("klip5-juruwang.mp4", 0.15, 16,
     [("SELAMAT", YELLOW, 3), ("DATANG", YELLOW, 4), ("KAKAK", WHITE, 5), ("BARU!! 🙌", YELLOW, 6),
      ("ESOK", WHITE, 9), ("SIAPA", WHITE, 10), ("PULA", WHITE, 11), ("BANG? 😂", YELLOW, 12)], "drop"),
]
END_BEATS = 6
END_LINES = [("Tag kawan yang", WHITE), ("macam ni 😂", YELLOW), ("", WHITE), ("Part 2? 👀", WHITE)]
FREEZE = (4, 8)              # beats inside clip 2: hold frame, 'KANTOI!' stamp, music stops
FREEZE_CENTER = (0.55, 0.45)  # where the side-eye is, as fraction of the frame

STARTS = np.cumsum([0] + [s[2] for s in SEGMENTS])  # segment starts in beats
DROP = STARTS[4]
TOTAL_BEATS = STARTS[-1] + END_BEATS
TOTAL = TOTAL_BEATS * B


# ============================================================ video

def read_clip(name, start, length):
    vf = ("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
          "eq=contrast=1.12:saturation=1.3:brightness=0.02,unsharp=5:5:0.7")
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(length + 0.1),
         "-i", f"{ROOT}/assets/{name}", "-vf", vf, "-r", str(FPS),
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    n = int(round(length * FPS))
    if len(fr) < n:
        fr = np.concatenate([fr, np.repeat(fr[-1:], n - len(fr), 0)])
    return fr


def zoom(im, z, cx=0.5, cy=0.5, dx=0.0, dy=0.0):
    z = max(z, 1.0)
    cw, ch = W / z, H / z
    x0 = min(max(cx * W - cw / 2 + dx, 0), W - cw)
    y0 = min(max(cy * H - ch / 2 + dy, 0), H - ch)
    return im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))


def zoom_blur(im, z, amount):
    """Radial (zoom) blur: average several zoom levels."""
    acc = np.zeros((H, W, 3), np.float32)
    k = 5
    for i in range(k):
        acc += np.asarray(zoom(im, z * (1 + amount * i / k)), np.float32)
    return Image.fromarray((acc / k).astype(np.uint8))


def rgb_split(arr, px):
    px = int(px)
    if px <= 0:
        return arr
    out = arr.copy()
    out[..., 0] = np.roll(arr[..., 0], -px, axis=1)
    out[..., 2] = np.roll(arr[..., 2], px, axis=1)
    return out


def make_vignette(strength=0.55):
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
    return (1 - strength * np.clip(r - 0.35, 0, 1) ** 1.5 / 0.65 ** 1.5)[..., None].astype(np.float32)


class EmojiRain:
    def __init__(self, t0, seed=7):
        rng = np.random.default_rng(seed)
        chars = ["😂", "🔥", "💀", "🙌", "😭", "👀"]
        self.t0 = t0
        self.p = []
        for i in range(34):
            self.p.append(dict(
                img=emoji_img(chars[i % len(chars)], int(rng.uniform(90, 160))),
                x=rng.uniform(0, W), t=rng.uniform(0, 3.2), v=rng.uniform(900, 1500),
                rot=rng.uniform(-40, 40), spin=rng.uniform(-200, 200)))

    def draw(self, im, t):
        for p in self.p:
            dt = t - self.t0 - p["t"]
            if dt < 0:
                continue
            y = -160 + p["v"] * dt
            if y > H:
                continue
            e = p["img"].rotate(p["rot"] + p["spin"] * dt, expand=True, resample=Image.BICUBIC)
            im.alpha_composite(e, (int(p["x"] - e.width / 2), int(y)))


def slam(img, age, tilt):
    """Caption pop: overshoot scale 1.6 -> 0.94 -> 1.0, with a small tilt."""
    if age < 0.08:
        s = 1.6 - 0.66 * age / 0.08
    elif age < 0.16:
        s = 0.94 + 0.06 * (age - 0.08) / 0.08
    else:
        s = 1.0
    out = img.resize((int(img.width * s), int(img.height * s)), Image.BICUBIC)
    return out.rotate(tilt, expand=True, resample=Image.BICUBIC) if tilt else out


def render_video(path):
    hook = [text_img(line, 74, WHITE, 7) for line in HOOK]
    kantoi = text_img("KANTOI!", 190, RED, 16).rotate(-9, expand=True, resample=Image.BICUBIC)
    camera = emoji_img("📸", 150)
    vign = make_vignette()
    rain = EmojiRain((DROP + 12) * B)
    rng = np.random.default_rng(3)
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)

    def overlay_common(im, gt):
        y = 170
        for h in hook:
            im.alpha_composite(h, ((W - h.width) // 2, y))
            y += h.height - 14

    last_frame = None
    for si, (name, start, beats, words, fx) in enumerate(SEGMENTS):
        length = beats * B
        frames = read_clip(name, start, length)
        size = 124 if fx == "drop" else 108
        caps = [(wb * B, text_img(w, size, c), (-4 if k % 2 else 4)) for k, (w, c, wb) in enumerate(words)]
        n = int(round(length * FPS))
        seg_t0 = STARTS[si] * B
        for fi in range(n):
            t = fi / FPS
            gt = seg_t0 + t
            bt = t / B                      # beats into the segment
            ph = bt % 1                     # phase inside the beat
            src = fi
            frozen = fx == "freeze" and FREEZE[0] <= bt < FREEZE[1]
            if frozen:
                src = int(FREEZE[0] * B * FPS)
            elif fx == "freeze" and bt >= FREEZE[1]:
                src = int(FREEZE[0] * B * FPS) + (fi - int(FREEZE[1] * B * FPS))
            im = Image.fromarray(frames[min(src, len(frames) - 1)])

            z, cx, cy, dx, dy = 1.04, 0.5, 0.5, 0.0, 0.0
            if fx == "intro":
                z = 1.04 + 0.08 * t / length
                if bt >= 4:  # beat kicks in: pulse
                    z += 0.035 * (1 - ease_out(ph * 3))
            elif fx == "freeze":
                if frozen:
                    fz = ease_out((bt - FREEZE[0]) / 0.5)
                    z = 1.04 + 0.5 * fz
                    cx = 0.5 + (FREEZE_CENTER[0] - 0.5) * fz
                    cy = 0.5 + (FREEZE_CENTER[1] - 0.5) * fz
                    sh = 22 * np.exp(-(bt - FREEZE[0]) * 3)
                    dx, dy = rng.normal(0, sh, 2)
                else:
                    z = 1.04 + 0.03 * ph
            elif fx == "beat":
                z = 1.05 + 0.045 * (1 - ease_out(ph * 3)) + 0.04 * t / length
                dx, dy = rng.normal(0, 3, 2)
            elif fx == "build":  # creep in harder as the snare roll builds
                z = 1.04 + 0.35 * (t / length) ** 2
                sh = 2 + 14 * (t / length) ** 3
                dx, dy = rng.normal(0, sh, 2)
            elif fx == "drop":
                z = 1.08 + 0.09 * (1 - ease_out(ph * 2.5))
                sh = 16 * (1 - ph) + 4
                dx, dy = rng.normal(0, sh, 2)

            # whip-zoom out of the clip (last 3 frames) and into the next (first 4 frames)
            if si < len(SEGMENTS) - 1 and fi >= n - 3:
                k = (fi - (n - 3) + 1) / 3
                im = zoom_blur(zoom(im, z, cx, cy, dx, dy), 1 + 0.35 * k, 0.12 * k)
            elif si > 0 and fi < 4:
                k = 1 - fi / 4
                im = zoom_blur(zoom(im, z, cx, cy, dx, dy), 1 + 0.35 * k, 0.12 * k)
            else:
                im = zoom(im, z, cx, cy, dx, dy)

            arr = np.asarray(im).astype(np.float32)
            if frozen:  # desaturate + red tint
                g = arr.mean(axis=2, keepdims=True)
                arr = 0.35 * arr + 0.65 * g
                arr[..., 0] *= 1.25
                arr[..., 1:] *= 0.85
            arr *= vign
            # flash on cuts, strobe on drop beats, invert on the drop hit
            flash = 0.0
            if si > 0 and fi < 3:
                flash = [0.6, 0.3, 0.1][fi]
            if fx == "drop" and ph < 0.1 and bt >= 1:
                flash = max(flash, 0.35)
            if frozen and bt - FREEZE[0] < 0.1:
                flash = 0.9
            arr = arr * (1 - flash) + 255 * flash
            arr = np.clip(arr, 0, 255).astype(np.uint8)
            if fx == "drop" and fi < 2:
                arr = 255 - arr
            split = 0
            if si > 0 and fi < 5:
                split = 34 * (1 - fi / 5)
            if fx == "drop":
                split = max(split, 22 * (1 - ease_out(ph * 2)))
            if fx == "build" and t / length > 0.7:
                split = max(split, rng.uniform(0, 18))
            if frozen:
                split = max(split, 10 * np.exp(-(bt - FREEZE[0]) * 4))
            arr = rgb_split(arr, split)
            # black out the half beat of silence before the drop
            if fx == "build" and bt >= beats - 0.5:
                arr = (arr * 0.08).astype(np.uint8)

            im = Image.fromarray(arr).convert("RGBA")
            overlay_common(im, gt)
            if frozen:
                age = (bt - FREEZE[0]) * B
                k = slam(kantoi, age, 0)
                im.alpha_composite(k, ((W - k.width) // 2, int(H * 0.60) - k.height // 2))
                if age > 0.25:
                    im.alpha_composite(camera, (W - 260, int(H * 0.47)))
            else:
                cur = [(wt, img, tilt) for wt, img, tilt in caps if wt <= t]
                if cur and not (fx == "build" and bt >= beats - 0.5):
                    wt, img, tilt = cur[-1]
                    c = slam(img, t - wt, tilt)
                    im.alpha_composite(c, ((W - c.width) // 2, int(H * 0.70) - c.height // 2))
            if fx == "drop":
                rain.draw(im, gt)
            enc.stdin.write(im.convert("RGB").tobytes())
            last_frame = Image.fromarray(frames[min(src, len(frames) - 1)])

    # end card
    bg = last_frame.filter(ImageFilter.GaussianBlur(30))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.55)
    lines = [(text_img(t, 108, c) if t else None) for t, c in END_LINES]
    t0 = STARTS[-1] * B
    for fi in range(int(round(END_BEATS * B * FPS))):
        t = fi / FPS
        ph = (t / B) % 1
        im = zoom(bg, 1.03 + 0.04 * (1 - ease_out(ph * 3))).convert("RGBA")
        y = 680
        for li, l in enumerate(lines):
            if l is None:
                y += 60
                continue
            age = t - li * 0.12
            if age >= 0:
                c = slam(l, age, 0)
                im.alpha_composite(c, ((W - c.width) // 2, y - (c.height - l.height) // 2))
            y += l.height
        rain.draw(im, t0 + t)
        arr = np.asarray(im.convert("RGB"))
        if fi < 3:
            arr = rgb_split((arr * (1 - [0.7, 0.35, 0.1][fi]) + 255 * [0.7, 0.35, 0.1][fi]).astype(np.uint8), 30 - fi * 10)
        enc.stdin.write(np.ascontiguousarray(arr).tobytes())
    enc.stdin.close()
    enc.wait()


# ============================================================ music (stereo phonk / DJ)

def note(n):
    return 440 * 2 ** ((n - 69) / 12)


def ns(n, seed):
    return np.random.default_rng(seed).uniform(-1, 1, n)


def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, "same")


def cowbell(f, dur=0.22):
    t = np.arange(int(dur * SR)) / SR
    x = np.sign(np.sin(2 * np.pi * f * t)) + np.sign(np.sin(2 * np.pi * f * 1.48 * t))
    x = x - lowpass(x, 40)                    # crude band-pass: remove lows
    x = lowpass(x, 3)
    return x * np.exp(-t * 14) * np.minimum(t / 0.001, 1) * 0.35


def kick(dur=0.45):
    t = np.arange(int(dur * SR)) / SR
    f = 48 + 160 * np.exp(-t * 35)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)
    x[:int(0.004 * SR)] += ns(int(0.004 * SR), 1) * 0.6   # click
    return np.tanh(2.5 * x)


def snare(dur=0.22, seed=2):
    t = np.arange(int(dur * SR)) / SR
    nz = np.diff(ns(len(t) + 1, seed)) * np.exp(-t * 18)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    clap = sum(np.roll(np.diff(ns(len(t) + 1, seed + i)) * np.exp(-t * 60), int(i * 0.011 * SR)) for i in range(3))
    return np.tanh(1.5 * (0.6 * nz + 0.5 * tone + 0.4 * clap))


def hat(dur=0.05, seed=1, open_=False):
    t = np.arange(int((0.3 if open_ else dur) * SR)) / SR
    x = np.diff(np.diff(ns(len(t) + 2, seed)))
    return x * np.exp(-t * (12 if open_ else 80)) * 0.22


def crash(dur=2.5):
    t = np.arange(int(dur * SR)) / SR
    x = np.diff(ns(len(t) + 1, 11)) * np.exp(-t * 1.6)
    return x * 0.45


def bass808(f0, dur, glide_to=None, drive=3.0):
    t = np.arange(int(dur * SR)) / SR
    f = np.full_like(t, f0)
    if glide_to:
        f = f0 + (glide_to - f0) * np.clip((t - dur * 0.55) / (dur * 0.3), 0, 1)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 1.2) * np.minimum(t / 0.003, 1)
    x[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))
    return np.tanh(drive * x) * 0.8


def riser(dur):
    n = int(dur * SR)
    x = ns(n, 9)
    out = np.zeros(n)
    # sweep from dark to bright
    for i, k in enumerate(np.linspace(40, 2, 12)):
        a, b = i * n // 12, (i + 1) * n // 12
        out[a:b] = x[a:b] - lowpass(x, int(max(k, 2)))[a:b] * 0.5
    return out * np.linspace(0, 1, n) ** 2 * 0.5


def boom(dur=1.6):
    t = np.arange(int(dur * SR)) / SR
    x = np.sin(2 * np.pi * (32 + 70 * np.exp(-t * 18)) * t) * np.exp(-t * 2.2)
    return np.tanh(2.5 * x)


def shutter():
    a = np.diff(ns(int(0.03 * SR) + 1, 21)) * np.exp(-np.arange(int(0.03 * SR)) / SR * 120)
    out = np.zeros(int(0.12 * SR))
    out[:len(a)] += a
    out[int(0.07 * SR):int(0.07 * SR) + len(a)] += a * 0.8
    return out * 0.9


def whoosh(dur=0.4, seed=3):
    n = int(dur * SR)
    return lowpass(ns(n, seed), 8) * np.sin(np.linspace(0, np.pi, n)) ** 3 * 0.7


class Mix:
    def __init__(self, total):
        self.buf = np.zeros((int(total * SR) + SR, 2))

    def add(self, x, t, g=1.0, pan=0.0, haas=0.0):
        i = int(t * SR)
        if i < 0:
            x, i = x[-i:], 0
        if i >= len(self.buf):
            return
        x = x[: len(self.buf) - i] * g
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        self.buf[i:i + len(x), 0] += x * l * 1.414
        j = i + int(haas * SR)
        xr = x[: max(0, len(self.buf) - j)]
        self.buf[j:j + len(xr), 1] += xr * r * 1.414


MEL = [66, None, None, 66, None, None, 66, None, 69, None, None, 68, None, None, 64, None,
       66, None, None, 66, None, None, 66, None, 61, None, None, 64, None, None, 66, None]
ROOTS = [30, 30, 26, 28]   # F#1 F#1 D1 E1


def make_music():
    m = Mix(TOTAL)
    s16 = B / 4
    fz0, fz1 = STARTS[1] + FREEZE[0], STARTS[1] + FREEZE[1]
    build0 = STARTS[4] - 4

    def silent(b):  # record stop during the freeze and half a beat before the drop
        return fz0 <= b < fz1 or DROP - 0.5 <= b < DROP

    for step in range(int(TOTAL_BEATS * 4)):
        b = step / 4
        t = b * B
        if b >= TOTAL_BEATS - END_BEATS or silent(b):
            continue
        drop = b >= DROP
        bar = int(b // 4)
        # cowbell melody (octave up on the drop)
        n = MEL[step % 32]
        if n:
            m.add(cowbell(note(n + (12 if drop else 0))), t, 0.55 if drop else 0.5, pan=0.15, haas=0.012)
        if b < 4:
            continue
        # drums
        if drop:
            if step % 4 == 0:
                m.add(kick(), t, 1.0)
            if step % 8 == 4:
                m.add(snare(), t, 0.85)
        else:
            if step % 16 in (0, 10):  # half-time phonk kick
                m.add(kick(), t, 0.95)
            if step % 16 == 8:
                m.add(snare(), t, 0.8)
        if b >= build0 and not drop:  # snare roll: 8ths -> 16ths -> 32nds
            pr = (b - build0) / 4
            div = 2 if pr < 0.5 else 4
            if step % (4 // div) == 0:
                m.add(snare(0.12, step), t, 0.3 + 0.6 * pr)
                if pr >= 0.75:
                    m.add(snare(0.08, step + 99), t + s16 / 2, 0.3 + 0.6 * pr)
        # hats: 16ths, triplet roll every 2nd bar end
        if not (b >= build0 and not drop):
            if step % 32 == 28 and drop:
                for k in range(6):
                    m.add(hat(seed=step * 7 + k), t + k * B / 6, 0.9, pan=-0.3)
            elif not (drop and 28 <= step % 32 < 32):
                m.add(hat(seed=step), t, 0.9 if step % 2 else 0.55, pan=-0.3)
            if step % 8 == 6:
                m.add(hat(seed=step, open_=True), t, 0.5, pan=0.3)
        # 808: on every bar, dotted pattern, from beat 22 on (after the freeze) and harder on the drop
        if b >= STARTS[2] or (STARTS[0] + 4 <= b < fz0):
            bs = step % 16
            r = note(ROOTS[bar % 4])
            if bs == 0:
                m.add(bass808(r, 1.5 * B, drive=4 if drop else 2.5), t, 0.75)
            elif bs == 6:
                m.add(bass808(r * 1.5, 1.2 * B, glide_to=r * 2, drive=4 if drop else 2.5), t, 0.6)
            elif bs == 12:
                m.add(bass808(r, B, drive=4 if drop else 2.5), t, 0.65)
    # transitions
    for si in range(1, len(SEGMENTS)):
        m.add(whoosh(seed=si), STARTS[si] * B - 0.3, 0.9, pan=(-0.5 if si % 2 else 0.5))
    m.add(boom(), fz0 * B, 1.0)
    m.add(shutter(), fz0 * B, 0.8)
    m.add(riser(4 * B), (DROP - 4.5) * B, 0.8)
    m.add(boom(1.2), DROP * B, 0.8)
    m.add(crash(), DROP * B, 1.0, pan=0.2, haas=0.015)
    # end card: final hit
    end = (TOTAL_BEATS - END_BEATS) * B
    m.add(kick(0.8), end, 1.0)
    m.add(bass808(note(30), 2.6, drive=4), end, 0.8)
    m.add(crash(2.8), end, 0.8, haas=0.015)
    m.add(cowbell(note(78), 0.6), end, 0.5, haas=0.02)
    return m.buf[: int(TOTAL * SR)]


def clip_audio():
    parts = []
    for name, start, beats, *_ in SEGMENTS:
        length = beats * B
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(length), "-i",
             f"{ROOT}/assets/{name}", "-vn", "-ac", "1", "-ar", str(SR),
             "-af", "highpass=f=150,lowpass=f=8000", "-f", "f32le", "-"],
            capture_output=True, check=True).stdout
        a = np.frombuffer(raw, np.float32).astype(np.float64)
        n = int(length * SR)
        a = np.pad(a, (0, max(0, n - len(a))))[:n]
        parts.append(a)
    a = np.concatenate(parts)
    # mute phone audio during the freeze and the drop (music carries those)
    fz0, fz1 = (STARTS[1] + FREEZE[0]) * B, (STARTS[1] + FREEZE[1]) * B
    a[int(fz0 * SR):int(fz1 * SR)] = 0
    a[int(DROP * B * SR):] *= 0.3
    return np.pad(a, (0, int(TOTAL * SR) - len(a)))


def write_wav(path, x):
    x = np.tanh(1.3 * x / (np.max(np.abs(x)) + 1e-9)) / np.tanh(1.3) * 0.95   # soft clip master
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def main():
    out = f"{ROOT}/output"
    os.makedirs(out, exist_ok=True)
    music = make_music()
    write_wav(f"{out}/muzik-v2.wav", music)
    voice = clip_audio()
    mix = music / np.max(np.abs(music)) * 0.85 + np.stack([voice, voice], 1) * 1.4
    write_wav(f"{out}/audio-mix-v2.wav", mix)
    render_video(f"{out}/_video.mp4")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", f"{out}/_video.mp4", "-i", f"{out}/audio-mix-v2.wav",
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
         "-af", "loudnorm=I=-12:TP=-1:LRA=9", "-shortest", "-movflags", "+faststart",
         f"{out}/cust-awek-lain-v2.mp4"], check=True)
    os.remove(f"{out}/_video.mp4")
    print("done", round(TOTAL, 2), "s")


if __name__ == "__main__":
    main()
