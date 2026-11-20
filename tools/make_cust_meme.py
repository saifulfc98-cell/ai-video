"""Edit 'Bila cust datang semalam dengan awek lain' meme video from five phone clips.

Usage (from repo root):  python3 tools/make_cust_meme.py
Reads cust-awek-lain/assets/klip*.mp4, writes cust-awek-lain/output/cust-awek-lain.mp4.
Cuts land on the beat of a synthesized 100 BPM 'sneaky' track that drops on the last clip.
Needs: ffmpeg, numpy, Pillow, fonts Inter Black + Noto Color Emoji.
"""
import os
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = "cust-awek-lain"
W, H, FPS, SR = 1080, 1920, 30, 44100
BPM = 100
BEAT = 60 / BPM          # 0.6 s
BAR = 4 * BEAT           # 2.4 s
FONT = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
YELLOW = (255, 221, 0)
WHITE = (255, 255, 255)

HOOK = ["Bila cust datang semalam", "dengan awek lain 😭"]

# (file, start in clip, length, words [(text, colour, beat offset)], effect)
SEGMENTS = [
    ("klip1-kaunter-air.mp4", 0.4, 6.0,
     [("EH", WHITE, 0), ("ABANG", WHITE, 1), ("DATANG", WHITE, 2), ("LAGI 😏", YELLOW, 3),
      ("TAPI", WHITE, 5), ("KAKAK", WHITE, 6), ("NI", WHITE, 7), ("BARU 👀", YELLOW, 8)], "slowzoom"),
    ("klip2-kaunter-air-lebar.mp4", 0.8, 4.8,
     [("SEMALAM", WHITE, 0), ("BUKAN", WHITE, 1), ("YANG", WHITE, 2), ("NI…", YELLOW, 3),
      ("🤐", WHITE, 5)], "punch"),
    ("klip3-kafe.mp4", 4.2, 4.8,
     [("SATU", WHITE, 0), ("KEDAI", WHITE, 1), ("DAH", WHITE, 2), ("TAHU 🤭", YELLOW, 3),
      ("HAHAHA", WHITE, 5)], "slowzoom"),
    ("klip4-kedai.mp4", 2.4, 4.8,
     [("ABANG", WHITE, 0), ("KAUNTER", WHITE, 1), ("PUN", WHITE, 2), ("PERASAN 👀", YELLOW, 3),
      ("…", WHITE, 6)], "punch"),
    ("klip5-juruwang.mp4", 0.3, 7.2,
     [("SELAMAT", YELLOW, 2), ("DATANG", YELLOW, 3), ("KAKAK", WHITE, 4), ("BARU!! 🙌", YELLOW, 5),
      ("ESOK", WHITE, 7), ("SIAPA", WHITE, 8), ("PULA", WHITE, 9), ("BANG? 😂", YELLOW, 10)], "drop"),
]
END_LEN = BAR
END_LINES = [("Tag kawan yang", WHITE), ("macam ni 😂", YELLOW), ("", WHITE), ("Part 2? 👀", WHITE)]


# ---------------------------------------------------------------- text rendering

_emoji_font = ImageFont.truetype(EMOJI, 109)


def emoji_img(ch, h):
    im = Image.new("RGBA", (140, 140))
    ImageDraw.Draw(im).text((4, 4), ch, font=_emoji_font, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)


def is_emoji(tok):
    return any(ord(c) > 0x2600 and c != "…" for c in tok)


def text_img(text, size, colour, stroke=None):
    """Render text (may contain emoji tokens) with a thick black outline and soft shadow."""
    font = ImageFont.truetype(FONT, size)
    stroke = stroke or max(4, size // 9)
    parts = []
    for tok in text.split(" "):
        if is_emoji(tok):
            parts.append(emoji_img(tok, int(size * 1.05)))
        else:
            box = font.getbbox(tok, stroke_width=stroke)
            im = Image.new("RGBA", (box[2] - box[0], box[3] - box[1] + stroke))
            ImageDraw.Draw(im).text((-box[0], -box[1]), tok, font=font, fill=colour,
                                    stroke_width=stroke, stroke_fill=(0, 0, 0))
            parts.append(im)
    gap = size // 4
    w = sum(p.width for p in parts) + gap * (len(parts) - 1)
    h = max(p.height for p in parts)
    out = Image.new("RGBA", (w + 24, h + 24))
    x = 12
    for p in parts:
        out.alpha_composite(p, (x, 12 + (h - p.height) // 2))
        x += p.width + gap
    shadow = Image.new("RGBA", out.size, (0, 0, 0, 0))
    shadow.putalpha(out.getchannel("A").point(lambda a: a * 0.55))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    final = Image.new("RGBA", out.size)
    final.alpha_composite(shadow, (0, 6))
    final.alpha_composite(out)
    return final


# ---------------------------------------------------------------- video

def read_clip(name, start, length):
    vf = ("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
          "eq=contrast=1.08:saturation=1.22:brightness=0.02,unsharp=5:5:0.6")
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(length),
           "-i", f"{ROOT}/assets/{name}", "-vf", vf, "-r", str(FPS),
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    n = int(round(length * FPS))
    if len(frames) < n:  # pad with last frame
        frames = np.concatenate([frames, np.repeat(frames[-1:], n - len(frames), 0)])
    return frames[:n]


def zoom(im, z, dx=0, dy=0):
    if abs(z - 1) < 1e-3 and not dx and not dy:
        return im
    cw, ch = W / z, H / z
    x0 = (W - cw) / 2 + dx
    y0 = (H - ch) / 2 + dy
    return im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


def ease_out(t):
    return 1 - (1 - min(max(t, 0), 1)) ** 3


def render_video(path):
    hook = [text_img(line, 74, WHITE, 7) for line in HOOK]
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    rng = np.random.default_rng(3)
    last = None
    for si, (name, start, length, words, fx) in enumerate(SEGMENTS):
        frames = read_clip(name, start, length)
        imgs = [(w_t * BEAT, text_img(w, 118 if fx == "drop" else 104, c)) for w, c, w_t in words]
        for fi, fr in enumerate(frames):
            t = fi / FPS
            im = Image.fromarray(fr)
            z, dx, dy = 1.0, 0, 0
            if fx == "slowzoom":
                z = 1.0 + 0.10 * t / length
            elif fx == "punch":  # snap zoom on the 2nd beat, like a side-eye
                z = 1.0 + 0.22 * ease_out((t - BEAT) / 0.12) if t >= BEAT else 1.0
                z += 0.03 * t / length
            elif fx == "drop":   # bounce on every beat + shake on the wave
                ph = (t % BEAT) / BEAT
                z = 1.06 + 0.05 * (1 - ease_out(ph * 2.5))
                if t >= 5 * BEAT:
                    dx, dy = rng.normal(0, 9, 2)
            im = zoom(im, z, dx, dy)
            # flash at the start of every cut
            if fi < 3 and si > 0:
                im = Image.blend(im, Image.new("RGB", (W, H), WHITE), [0.75, 0.4, 0.15][fi])
            im = im.convert("RGBA")
            y = 170
            for h in hook:
                im.alpha_composite(h, ((W - h.width) // 2, y))
                y += h.height - 14
            # current word, popping in
            cur = [(wt, wi) for wt, wi in imgs if wt <= t]
            if cur:
                wt, wi = cur[-1]
                p = ease_out((t - wt) / 0.13)
                s = 1.35 - 0.35 * p
                wi2 = wi.resize((int(wi.width * s), int(wi.height * s)), Image.BICUBIC)
                im.alpha_composite(wi2, ((W - wi2.width) // 2, int(H * 0.70) - wi2.height // 2))
            out = im.convert("RGB")
            enc.stdin.write(out.tobytes())
            last = Image.fromarray(fr)
    # end card on a blurred freeze of the last frame
    bg = last.filter(ImageFilter.GaussianBlur(28))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.55).convert("RGBA")
    lines = [(text_img(t, 104, c) if t else None) for t, c in END_LINES]
    for fi in range(int(END_LEN * FPS)):
        t = fi / FPS
        im = bg.copy()
        y = 700
        for li, l in enumerate(lines):
            if l is None:
                y += 60
                continue
            p = ease_out((t - li * 0.15) / 0.2)
            if p > 0:
                s = 1.4 - 0.4 * p
                l2 = l.resize((int(l.width * s), int(l.height * s)), Image.BICUBIC)
                im.alpha_composite(l2, ((W - l2.width) // 2, y - (l2.height - l.height) // 2))
            y += l.height
        if fi < 3:
            im = Image.blend(im.convert("RGB"), Image.new("RGB", (W, H), WHITE),
                             [0.75, 0.4, 0.15][fi]).convert("RGBA")
        enc.stdin.write(im.convert("RGB").tobytes())
    enc.stdin.close()
    enc.wait()


# ---------------------------------------------------------------- music + sfx

def note(n):  # MIDI -> Hz
    return 440 * 2 ** ((n - 69) / 12)


def env(n, a=0.003, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / d)


_pluck_cache = {}


def pluck(f, dur):
    """Karplus-Strong plucked string (pizzicato)."""
    key = (round(f, 2), dur)
    if key in _pluck_cache:
        return _pluck_cache[key]
    n = int(dur * SR)
    p = max(2, int(SR / f))
    buf = list(np.random.default_rng(int(f)).uniform(-1, 1, p))
    out = np.empty(n)
    for i in range(n):
        j = i % p
        out[i] = buf[j]
        buf[j] = 0.497 * (buf[j] + buf[(j + 1) % p])
    out = out * env(n, 0.002, dur / 2.5)
    _pluck_cache[key] = out
    return out


def kick(n=0.4):
    t = np.arange(int(n * SR)) / SR
    f = 45 + 95 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)


def noise(n, seed=0):
    return np.random.default_rng(seed).uniform(-1, 1, n)


def snap(n=0.18):
    m = int(n * SR)
    x = np.diff(noise(m + 1, 5))
    return x * np.exp(-np.arange(m) / SR * 30) * 0.6


def hat(n=0.05, seed=1):
    m = int(n * SR)
    x = np.diff(np.diff(noise(m + 2, seed)))
    return x * np.exp(-np.arange(m) / SR * 90) * 0.18


def bass808(f, dur):
    t = np.arange(int(dur * SR)) / SR
    x = np.sin(2 * np.pi * f * t + 2 * np.sin(2 * np.pi * f * t) * np.exp(-t * 12))
    return np.tanh(2.2 * x) * np.exp(-t * 1.6) * np.minimum(t / 0.004, 1)


def square_stab(f, dur):
    t = np.arange(int(dur * SR)) / SR
    x = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + np.sign(np.sin(2 * np.pi * f * 1.005 * t)) * 0.5
    k = np.ones(18) / 18
    return np.convolve(x, k, "same") * env(len(t), 0.004, 0.12)


def add(buf, x, t, g=1.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    x = x[: len(buf) - i]
    buf[i:i + len(x)] += g * x


def make_music(total):
    m = np.zeros(int(total * SR))
    drop = sum(s[2] for s in SEGMENTS[:-1])   # start of last clip
    end = drop + SEGMENTS[-1][2]
    # tiptoe motif in A minor, 8th notes (None = rest); 2 bars
    motif = [57, None, 60, None, 64, 63, 64, None, 67, None, 64, None, 60, None, 59, None,
             57, None, 60, None, 64, 63, 64, None, 65, 64, 62, None, 59, None, 56, None]
    eighth = BEAT / 2
    t = 0.0
    i = 0
    while t < drop - 0.3:
        n = motif[i % len(motif)]
        if n:
            add(m, pluck(note(n - 12), 0.35), t, 0.55)
            add(m, pluck(note(n), 0.25), t, 0.25)
        t += eighth
        i += 1
    # light drums from bar 2 until the drop
    b = 0
    t = BAR
    while t < drop - 0.3:
        k = b % 4
        if k in (0, 2):
            add(m, kick(), t, 0.7)
        if k in (1, 3):
            add(m, snap(), t, 0.5)
        add(m, hat(seed=b), t + BEAT / 2, 1.0)
        t += BEAT
        b += 1
    # riser into the drop, then silence 0.3 s
    rl = 1.5
    r = noise(int(rl * SR), 9) * np.linspace(0, 1, int(rl * SR)) ** 2
    r = np.convolve(r, np.ones(6) / 6, "same") * 0.35
    add(m, r, drop - 0.3 - rl)
    m[int((drop - 0.3) * SR):int(drop * SR)] = 0
    # the drop: 808 + 4-on-floor kick + claps + 16th hats + stabs
    roots = [45, 41, 43, 40]  # A F G E
    chords = [[57, 60, 64], [53, 57, 60], [55, 59, 62], [52, 56, 59]]
    t = drop
    b = 0
    while t < end - 1e-6:
        bar = int((t - drop) // BAR) % 4
        if b % 4 == 0:
            add(m, bass808(note(roots[bar]), BAR * 0.95), t, 0.55)
        add(m, kick(), t, 0.8)
        if b % 2 == 1:
            add(m, snap(0.25), t, 0.75)
        for h in range(4):
            add(m, hat(seed=b * 4 + h), t + h * BEAT / 4, 1.3 if h % 2 else 0.8)
        if b % 2 == 0:
            for cn in chords[bar]:
                add(m, square_stab(note(cn), 0.25), t + BEAT / 2, 0.09)
        # motif on top, an octave up
        for e in range(2):
            n = motif[(b * 2 + e) % len(motif)]
            if n:
                add(m, pluck(note(n + 12), 0.2), t + e * eighth, 0.2)
        t += BEAT
        b += 1
    # final hit at the end card
    add(m, kick(0.8), end, 0.9)
    add(m, bass808(note(45), 2.2), end, 0.5)
    add(m, snap(0.4), end, 0.6)
    return m


def make_sfx(total):
    s = np.zeros(int(total * SR))
    t = 0.0
    for si, seg in enumerate(SEGMENTS):
        if si > 0:   # whoosh into every cut
            n = int(0.35 * SR)
            w = noise(n, si) * np.sin(np.linspace(0, np.pi, n)) ** 2
            w = np.convolve(w, np.ones(12) / 12, "same")
            add(s, w, t - 0.3, 0.5)
        if seg[4] == "punch":  # deep boom on the side-eye zoom
            tt = np.arange(int(0.9 * SR)) / SR
            boom = np.sin(2 * np.pi * (38 + 60 * np.exp(-tt * 20)) * tt) * np.exp(-tt * 3.5)
            add(s, np.tanh(2 * boom), t + BEAT, 0.6)
        t += seg[2]
    return s


def clip_audio(total):
    """Original phone audio (staff voices / laughs), concatenated, kept low."""
    parts = []
    for name, start, length, *_ in SEGMENTS:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(length), "-i",
             f"{ROOT}/assets/{name}", "-vn", "-ac", "1", "-ar", str(SR),
             "-af", "highpass=f=120,lowpass=f=9000", "-f", "f32le", "-"],
            capture_output=True, check=True).stdout
        a = np.frombuffer(raw, np.float32).astype(np.float64)
        n = int(length * SR)
        a = np.pad(a, (0, max(0, n - len(a))))[:n]
        f = int(0.02 * SR)
        a[:f] *= np.linspace(0, 1, f)
        a[-f:] *= np.linspace(1, 0, f)
        parts.append(a)
    a = np.concatenate(parts)
    return np.pad(a, (0, int(total * SR) - len(a)))


def write_wav(path, x):
    x = np.clip(x / (np.max(np.abs(x)) + 1e-9) * 0.89, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def main():
    total = sum(s[2] for s in SEGMENTS) + END_LEN
    out = f"{ROOT}/output"
    os.makedirs(out, exist_ok=True)
    music = make_music(total)
    write_wav(f"{out}/muzik.wav", music)
    mix = music / (np.max(np.abs(music)) + 1e-9) * 0.8 + make_sfx(total) + \
        clip_audio(total) * 1.6
    write_wav(f"{out}/audio-mix.wav", mix)
    render_video(f"{out}/_video.mp4")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", f"{out}/_video.mp4", "-i", f"{out}/audio-mix.wav",
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-shortest", "-movflags", "+faststart",
         f"{out}/cust-awek-lain.mp4"], check=True)
    os.remove(f"{out}/_video.mp4")
    print("done", total, "s")


if __name__ == "__main__":
    main()
