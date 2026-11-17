"""Turn the 10 s Gemini Hot Wheels clip (16:9) into a punchy 9:16 sales promo.

Usage (from repo root):
  python3 tools/make_promo.py <source.mp4> <out.mp4> [13|20]   (length in seconds, default 13)

Speed ramps, zoom punches, white flashes, camera shake, kinetic Malay sales copy,
a "pick your colour" freeze on the cards and a pulsing CTA end card. Audio is the
clip's own SFX (time-stretched with the picture) under a synthesized 140 BPM beat
with impact hits on every cut.
"""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, SR = 1080, 1920, 30, 44100
BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-BlackItalic.otf"
BOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
YEL, RED, WHITE, INK = (255, 214, 0), (230, 30, 45), (255, 255, 255), (12, 12, 12)

# (out_dur, src_start, src_end, caption key) -- src speed = (end-start)/out_dur
SEGS_13 = [
    (1.2, 2.0, 2.6, "hook"),      # sparks, slow-mo
    (1.6, 2.6, 3.4, "burst"),     # car bursts out of the card, slow-mo
    (1.4, 3.4, 4.6, "flame"),     # flames, near real time + shake
    (1.4, 4.6, 6.0, "drift"),     # drift
    (1.2, 6.0, 7.4, "lights"),    # headlights
    (2.4, 0.3, 0.3, "pick"),      # freeze on the two cards
    (1.4, 7.4, 8.8, "smoke"),     # smoke pass
    (2.4, 8.8, 10.0, "cta"),      # logo + CTA
]
SEGS_20 = [
    (1.6, 2.0, 2.6, "hook"),
    (2.0, 2.6, 3.4, "burst"),
    (1.8, 3.4, 4.6, "flame"),
    (1.8, 4.6, 6.0, "drift"),
    (1.6, 6.0, 7.4, "lights"),
    (1.6, 0.3, 0.3, "red"),       # push in on the red card
    (1.6, 0.3, 0.3, "yellow"),    # push in on the yellow card
    (2.2, 0.3, 0.3, "pick"),
    (2.0, 7.4, 8.8, "smoke"),
    (3.8, 8.6, 10.0, "cta"),
]
SEGS = SEGS_20 if len(sys.argv) > 3 and sys.argv[3] == "20" else SEGS_13
CUTS = np.cumsum([0] + [s[0] for s in SEGS])
TOTAL = float(CUTS[-1])


def font(path, size):
    return ImageFont.truetype(path, size)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def load_source(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, 720, 1280, 3)
    return frames, 24.0


def compose(src, zoom, shake=(0, 0), cx=0.5):
    """Blurred full-bleed background + sharp zoomed foreground band in the middle."""
    im = Image.fromarray(src)
    bg = im.resize((int(1280 * H / 720), H)).crop(((int(1280 * H / 720) - W) // 2, 0,
                                                    (int(1280 * H / 720) - W) // 2 + W, H))
    bg = bg.filter(ImageFilter.GaussianBlur(28))
    bg = Image.eval(bg, lambda v: int(v * 0.45))
    fw = int(W * 1.45 * zoom)
    fh = int(fw * 720 / 1280)
    fg = im.resize((fw, fh), Image.BILINEAR)
    band_h = min(1000, fh)
    x0 = min(max(int(cx * fw - W / 2), 0), fw - W) - shake[0]
    y0 = (fh - band_h) // 2 - shake[1]
    fg = fg.crop((x0, y0, x0 + W, y0 + band_h))
    bg.paste(fg, (0, 460 + (1000 - band_h) // 2))
    d = ImageDraw.Draw(bg)
    d.rectangle((0, 452, W, 460), fill=YEL)
    d.rectangle((0, 1460, W, 1468), fill=YEL)
    return bg


def text_c(d, y, s, f, fill, stroke=8, sfill=INK, x=None):
    w = d.textlength(s, font=f)
    d.text(((W - w) / 2 if x is None else x, y), s, font=f, fill=fill,
           stroke_width=stroke, stroke_fill=sfill)


def slam(img, lt, s, y, size, fill=YEL, delay=0.0):
    """Text that slams in from 2.2x scale to 1x over 0.18 s."""
    k = (lt - delay) / 0.18
    if k < 0:
        return
    sc = 1 + 1.2 * (1 - ease_out(k))
    f = font(BLACK, int(size * sc))
    d = ImageDraw.Draw(img)
    w = d.textlength(s, font=f)
    while w > W - 60 and sc <= 1.0:
        size -= 4
        f = font(BLACK, size)
        w = d.textlength(s, font=f)
    yy = y - (sc - 1) * size / 2
    text_c(d, yy, s, f, fill, stroke=max(6, size // 10))


def tag(img, lt, s, y, bg=RED, fg=WHITE, size=54, delay=0.0):
    """Pill label sliding in from the left."""
    k = ease_out((lt - delay) / 0.25)
    if lt < delay:
        return
    d = ImageDraw.Draw(img)
    f = font(BLACK, size)
    w = d.textlength(s, font=f) + 70
    x = (W - w) / 2 - (1 - k) * W
    d.rounded_rectangle((x, y, x + w, y + size + 40), radius=(size + 40) // 2, fill=bg,
                        outline=INK, width=6)
    d.text((x + 35, y + 14), s, font=f, fill=fg)


def overlay(img, key, lt, dur, t):
    if key == "hook":
        slam(img, lt, "STOP SCROLL!", 170, 130, WHITE)
        tag(img, lt, "KOLEKTOR WAJIB TENGOK", 1530, delay=0.25)
    elif key == "burst":
        slam(img, lt, "HOT WHEELS", 120, 140, YEL)
        slam(img, lt, "× TOUCH 'n GO", 280, 100, WHITE, delay=0.15)
        tag(img, lt, "KAD TNG EDISI KHAS", 1530, delay=0.3)
    elif key == "flame":
        slam(img, lt, "TURBO", 110, 170, YEL)
        slam(img, lt, "CHARGED!", 290, 130, RED, delay=0.12)
        tag(img, lt, "PANAS! BARU SAMPAI", 1530, bg=YEL, fg=INK, delay=0.25)
    elif key == "drift":
        slam(img, lt, "GEMPAK", 150, 170, WHITE)
        tag(img, lt, "DESIGN PALING POWER", 1530, delay=0.2)
    elif key == "lights":
        slam(img, lt, "TAP & GO", 150, 160, YEL)
        tag(img, lt, "TOL • PARKING • TRANSIT", 1530, bg=YEL, fg=INK, size=48, delay=0.2)
    elif key in ("red", "yellow"):
        red = key == "red"
        slam(img, lt, "MERAH" if red else "KUNING", 110, 170, RED if red else YEL)
        slam(img, lt, "GARANG!" if red else "MENYALA!", 290, 120, WHITE, delay=0.12)
        tag(img, lt, "HOT WHEELS × TNG CARD", 1530, bg=RED if red else YEL,
            fg=WHITE if red else INK, delay=0.25)
    elif key == "pick":
        slam(img, lt, "PILIH WARNA", 110, 130, WHITE)
        slam(img, lt, "KORANG!", 260, 130, YEL, delay=0.12)
        d = ImageDraw.Draw(img)
        bob = int(18 * np.sin(t * 14))
        for cx, s, col, dl in ((280, "MERAH", RED, 0.35), (800, "KUNING", YEL, 0.6)):
            if lt > dl:
                k = ease_out((lt - dl) / 0.2)
                f = font(BLACK, int(84 * (2 - k)))
                w = d.textlength(s, font=f)
                d.text((cx - w / 2, 1520 + bob), s, font=f, fill=col, stroke_width=8,
                       stroke_fill=INK)
                d.polygon([(cx - 40, 1500 + bob), (cx + 40, 1500 + bob), (cx, 1440 + bob)],
                          fill=col, outline=INK)
        if lt > 1.2:
            tag(img, lt, "MANA SATU PILIHAN KORANG?", 1700, bg=INK, fg=WHITE, size=46, delay=1.2)
    elif key == "smoke":
        slam(img, lt, "EDISI", 120, 150, WHITE)
        slam(img, lt, "KOLEKTOR", 290, 130, YEL, delay=0.12)
        tag(img, lt, "JANGAN SAMPAI TERLEPAS!", 1530, delay=0.25)
    elif key == "cta":
        d = ImageDraw.Draw(img)
        slam(img, lt, "DAPATKAN", 110, 150, WHITE)
        slam(img, lt, "SEKARANG!", 280, 150, YEL, delay=0.12)
        if lt > 0.4:
            pulse = 1 + 0.06 * np.sin((lt - 0.4) * 12)
            bw, bh = int(860 * pulse), int(170 * pulse)
            x, y = (W - bw) // 2, 1530 - (bh - 170) // 2
            d.rounded_rectangle((x + 10, y + 12, x + bw + 10, y + bh + 12), radius=bh // 2,
                                fill=INK)
            d.rounded_rectangle((x, y, x + bw, y + bh), radius=bh // 2, fill=RED,
                                outline=WHITE, width=8)
            f = font(BLACK, int(70 * pulse))
            s = "BELI DI KAUNTER"
            d.text(((W - d.textlength(s, font=f)) / 2, y + (bh - 70 * pulse) / 2 - 10), s,
                   font=f, fill=WHITE)
        if lt > 0.8:
            f = font(BOLD, 46)
            text_c(d, 1760, "Tanya staf kami hari ini!", f, WHITE, stroke=5)


def render_frame(src, fps_src, t):
    i = int(np.searchsorted(CUTS, t, side="right") - 1)
    i = min(i, len(SEGS) - 1)
    dur, s0, s1, key = SEGS[i]
    lt = t - CUTS[i]
    st = s0 + (s1 - s0) * (lt / dur)
    frame = src[min(int(st * fps_src), len(src) - 1)]
    # zoom punch at each cut, slow push otherwise
    zoom = 1.0 + 0.25 * (1 - ease_out(lt / 0.25)) + 0.06 * lt / dur
    if key == "pick":
        zoom = 0.72 + 0.04 * lt / dur
    if key == "cta":
        zoom = 1.0 + 0.05 * lt / dur
    cx = 0.5
    if key in ("red", "yellow"):
        zoom = 1.25 + 0.15 * ease_out(lt / dur)
        cx = 0.26 if key == "red" else 0.74
    shake = (0, 0)
    if key in ("flame", "burst") or lt < 0.15:
        amp = 14 if key == "flame" else 7
        shake = (int(amp * np.sin(t * 91)), int(amp * np.cos(t * 73)))
    img = compose(frame, zoom, shake, cx)
    overlay(img, key, lt, dur, t)
    # progress bar for watch time
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, int(W * t / TOTAL), 14), fill=YEL)
    arr = np.asarray(img, np.float32)
    # white flash on each cut
    fl = max(0.0, 1 - lt / 0.12) if i > 0 else max(0.0, 1 - lt / 0.2)
    if fl > 0:
        arr = arr + (255 - arr) * fl * 0.85
    # fade out the last 0.3 s
    if t > TOTAL - 0.3:
        arr *= max(0.0, (TOTAL - t) / 0.3)
    return arr.clip(0, 255).astype(np.uint8)


def make_audio(src_path, out_wav):
    n = int(TOTAL * SR)
    t = np.arange(n) / SR
    mix = np.zeros(n)
    # original SFX, time-mapped per segment
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src_path, "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    sfx = np.frombuffer(raw, np.float32).astype(np.float64)
    for (dur, s0, s1, key), c in zip(SEGS, CUTS):
        a, b = int(c * SR), int((c + dur) * SR)
        if s1 == s0:  # freeze: let the whoosh tail ring, no SFX
            continue
        pos = np.linspace(s0 * SR, s1 * SR, b - a, endpoint=False)
        mix[a:b] += 0.55 * np.interp(pos, np.arange(len(sfx)), sfx)
    # 140 BPM beat: kick every beat, clap on 2 & 4, hats on 8ths
    beat = 60 / 140
    rng = np.random.default_rng(7)
    for k in range(int(TOTAL / beat) + 1):
        a = int(k * beat * SR)
        L = int(0.35 * SR)
        tt = np.arange(L) / SR
        kick = np.sin(2 * np.pi * (45 * tt + 90 * (1 - np.exp(-tt * 30)) / 30)) * np.exp(-tt * 9)
        seg = mix[a:a + L]
        seg += 0.75 * kick[:len(seg)]
        if k % 2 == 1:
            Lc = int(0.15 * SR)
            clap = rng.normal(0, 1, Lc) * np.exp(-np.arange(Lc) / SR * 30)
            mix[a:a + Lc] += 0.25 * clap[:len(mix[a:a + Lc])]
        for h in (0, 0.5):
            ah = int((k + h) * beat * SR)
            Lh = int(0.04 * SR)
            hat = np.diff(rng.normal(0, 1, Lh + 1)) * np.exp(-np.arange(Lh) / SR * 120)
            mix[ah:ah + Lh] += 0.08 * hat[:len(mix[ah:ah + Lh])]
    # bass line (root notes, saw-ish) following the beat
    notes = [55.0, 55.0, 65.4, 49.0]
    for k in range(int(TOTAL / beat) + 1):
        a, L = int(k * beat * SR), int(beat * SR)
        tt = np.arange(L) / SR
        f0 = notes[(k // 4) % 4]
        b = (2 * ((tt * f0) % 1) - 1) * np.exp(-tt * 4)
        seg = mix[a:a + L]
        seg += 0.18 * b[:len(seg)]
    # impact boom + riser whoosh at each cut
    for c in CUTS[1:-1]:
        a = int(c * SR)
        L = int(0.6 * SR)
        tt = np.arange(L) / SR
        boom = np.sin(2 * np.pi * 38 * tt) * np.exp(-tt * 5) + rng.normal(0, 0.3, L) * np.exp(-tt * 25)
        seg = mix[a:a + L]
        seg += 0.6 * boom[:len(seg)]
        Lw = int(0.3 * SR)
        w = rng.normal(0, 1, Lw) * np.linspace(0, 1, Lw) ** 2
        w = np.convolve(w, np.ones(8) / 8, "same")
        s = max(0, a - Lw)
        mix[s:a] += 0.25 * w[Lw - (a - s):]
    mix[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))
    mix = np.tanh(mix * 1.3)
    mix /= np.abs(mix).max() / 0.95
    pcm = (mix * 32767).astype(np.int16)
    import wave
    with wave.open(out_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def main():
    src_path, out = sys.argv[1], sys.argv[2]
    frames, fps_src = load_source(src_path)
    wav = out.rsplit(".", 1)[0] + "-audio.wav"
    make_audio(src_path, wav)
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium",
         "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
         "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for n in range(int(TOTAL * FPS)):
        enc.stdin.write(render_frame(frames, fps_src, n / FPS).tobytes())
    enc.stdin.close()
    enc.wait()
    subprocess.run(["rm", "-f", wav])


if __name__ == "__main__":
    main()
