"""Render the Shell Café Wow Wednesday bulletin as a 9:16 draft video.

Usage: python3 tools/make_video.py <photo> <captions.srt> <out.mp4> [presenter] [full|30s]

Presenter shots use the reference photo (slow zoom); B-roll shots are
motion-graphic placeholders. Video is silent: add voiceover/music in an editor.
"""
import math
import random
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
RED, YEL, WHITE, DARK = (221, 29, 33), (251, 206, 7), (255, 255, 255), (25, 25, 25)
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
CUTS = {
    "full": [(0, 11), (11, 23), (23, 38), (38, 50), (50, 57)],
    "30s": [(0, 7), (7, 15), (15, 23), (23, 27), (27, 30)],
}
SHOTS = CUTS["full"]
XFADE = 0.25

_fonts = {}


def font(size, bold=True):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(BOLD if bold else REG, size)
    return _fonts[key]


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def text_w(d, s, f):
    return d.textlength(s, font=f)


def fit(d, s, max_w, size, bold=True):
    while size > 20 and text_w(d, s, font(size, bold)) > max_w:
        size -= 2
    return font(size, bold)


def centered(d, y, s, f, fill, stroke=0, stroke_fill=DARK):
    d.text(((W - text_w(d, s, f)) / 2, y), s, font=f, fill=fill,
           stroke_width=stroke, stroke_fill=stroke_fill)


def gradient(top, bottom):
    img = Image.new("RGB", (1, H))
    for y in range(H):
        k = y / (H - 1)
        img.putpixel((0, y), tuple(int(a + (b - a) * k) for a, b in zip(top, bottom)))
    return img.resize((W, H))


# ---------- overlays ----------

def lower_third(img, t, title, sub, y=1330):
    d = ImageDraw.Draw(img)
    off = -W * (1 - ease(t / 0.5))
    ft = fit(d, title, 860, 64)
    d.rectangle([off, y, off + W - 60, y + 112], fill=RED)
    d.rectangle([off, y, off + 40, y + 112], fill=YEL)
    d.text((off + 80, y + 20), title, font=ft, fill=WHITE)
    off2 = -W * (1 - ease((t - 0.2) / 0.5))
    fs = fit(d, sub, 820, 44, bold=False)
    d.rectangle([off2, y + 112, off2 + W - 160, y + 192], fill=WHITE)
    d.text((off2 + 80, y + 126), sub, font=fs, fill=DARK)


def breaking_badge(img, t):
    d = ImageDraw.Draw(img)
    f = font(46)
    label = "BERITA TERKINI"
    w = text_w(d, label, f) + 120
    x, y = 60, 230
    d.rounded_rectangle([x, y, x + w, y + 80], 14, fill=RED)
    if int(t * 2) % 2 == 0:
        d.ellipse([x + 30, y + 26, x + 58, y + 54], fill=WHITE)
    d.text((x + 84, y + 14), label, font=f, fill=WHITE)


def name_super(img, t, name):
    if t < 1.2 or t > 6:
        return
    d = ImageDraw.Draw(img)
    a = ease((t - 1.2) / 0.4) * (1 - ease((t - 5.6) / 0.4))
    x = 60 - 40 * (1 - a)
    f1, f2 = font(44), font(32, bold=False)
    d.rectangle([x, 330, x + 420, 430], fill=(0, 0, 0))
    d.rectangle([x, 330, x + 10, 430], fill=YEL)
    d.text((x + 30, 337), name.upper(), font=f1, fill=WHITE)
    d.text((x + 30, 387), "Wartawan", font=f2, fill=YEL)


def captions(img, t, cues):
    for start, end, text in cues:
        if start <= t < end:
            break
    else:
        return
    d = ImageDraw.Draw(img)
    f = font(50)
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if text_w(d, trial, f) > 940 and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    lines.append(cur)
    y = 1290 - len(lines) * 66 - 20
    for ln in lines:
        centered(d, y, ln, f, WHITE, stroke=6)
        y += 66


# ---------- icons ----------

def cup(d, cx, cy, s, steam_t=None, foam=0.0):
    top_w, bot_w, h = 300 * s, 220 * s, 380 * s
    body = [(cx - top_w / 2, cy - h / 2), (cx + top_w / 2, cy - h / 2),
            (cx + bot_w / 2, cy + h / 2), (cx - bot_w / 2, cy + h / 2)]
    d.polygon(body, fill=WHITE)
    band_y0, band_y1 = cy - h * 0.1, cy + h * 0.22
    k0, k1 = (band_y0 - (cy - h / 2)) / h, (band_y1 - (cy - h / 2)) / h
    w0, w1 = top_w + (bot_w - top_w) * k0, top_w + (bot_w - top_w) * k1
    d.polygon([(cx - w0 / 2, band_y0), (cx + w0 / 2, band_y0),
               (cx + w1 / 2, band_y1), (cx - w1 / 2, band_y1)], fill=RED)
    d.text((cx, (band_y0 + band_y1) / 2), "CAFÉ", font=font(int(54 * s)),
           fill=YEL, anchor="mm")
    d.rounded_rectangle([cx - top_w / 2 - 18 * s, cy - h / 2 - 50 * s,
                         cx + top_w / 2 + 18 * s, cy - h / 2], 16 * s, fill=(235, 235, 235))
    if foam > 0:
        rnd = random.Random(3)
        for _ in range(int(14 * foam)):
            bx = cx + rnd.uniform(-top_w / 2, top_w / 2)
            r = rnd.uniform(14, 30) * s
            d.ellipse([bx - r, cy - h / 2 - 50 * s - r, bx + r, cy - h / 2 - 50 * s + r],
                      fill=(250, 240, 220))
    if steam_t is not None:
        for i in (-1, 0, 1):
            pts = []
            for j in range(14):
                yy = cy - h / 2 - 80 * s - j * 9 * s
                xx = cx + i * 70 * s + math.sin(j * 0.35 + steam_t * 4 + i) * 18 * s
                pts.append((xx, yy))
            d.line(pts, fill=(255, 255, 255), width=int(10 * s), joint="curve")


def phone(img, t, mode):
    d = ImageDraw.Draw(img)
    x0, y0, pw, ph = 300, 270, 480, 740
    d.rounded_rectangle([x0 - 16, y0 - 16, x0 + pw + 16, y0 + ph + 16], 60, fill=(15, 15, 15))
    d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], 46, fill=WHITE)
    d.rounded_rectangle([x0, y0, x0 + pw, y0 + 150], 46, fill=RED)
    d.rectangle([x0, y0 + 100, x0 + pw, y0 + 150], fill=RED)
    d.text((x0 + pw / 2, y0 + 85), "Shell App", font=font(48), fill=YEL, anchor="mm")
    if mode == "app":
        a = ease(t / 0.6)
        cy = y0 + 190 + 40 * (1 - a)
        d.rounded_rectangle([x0 + 30, cy, x0 + pw - 30, cy + 300], 26, fill=YEL)
        d.text((x0 + pw / 2, cy + 80), "WOW", font=font(72), fill=RED, anchor="mm")
        d.text((x0 + pw / 2, cy + 160), "WEDNESDAY", font=font(52), fill=RED, anchor="mm")
        d.text((x0 + pw / 2, cy + 240), "Tawaran hari Rabu", font=font(30, False),
               fill=DARK, anchor="mm")
        pulse = 1 + 0.05 * math.sin(t * 6)
        bw, bh = 320 * pulse, 90 * pulse
        by = y0 + 560
        d.rounded_rectangle([x0 + pw / 2 - bw / 2, by, x0 + pw / 2 + bw / 2, by + bh], 45, fill=RED)
        d.text((x0 + pw / 2, by + bh / 2), "TEBUS", font=font(44), fill=WHITE, anchor="mm")
    else:
        rnd = random.Random(7)
        qs, qx, qy, n = 336, x0 + 72, y0 + 180, 21
        cell = qs / n
        for i in range(n):
            for j in range(n):
                finder = any(i0 <= i < i0 + 7 and j0 <= j < j0 + 7
                             for i0, j0 in ((0, 0), (0, n - 7), (n - 7, 0)))
                on = rnd.random() < 0.5
                if finder:
                    ii, jj = i % 7 if i < 7 else (i - (n - 7)), j % 7 if j < 7 else (j - (n - 7))
                    on = ii in (0, 6) or jj in (0, 6) or (2 <= ii <= 4 and 2 <= jj <= 4)
                if on:
                    d.rectangle([qx + j * cell, qy + i * cell,
                                 qx + (j + 1) * cell, qy + (i + 1) * cell], fill=DARK)
        if t < 3.0:
            sy = qy + (math.sin(t * 3) * 0.5 + 0.5) * qs
            d.rectangle([qx - 20, sy - 4, qx + qs + 20, sy + 4], fill=(0, 200, 90))
            d.text((x0 + pw / 2, y0 + 600), "Mengimbas...", font=font(40), fill=DARK, anchor="mm")
        else:
            a = ease((t - 3.0) / 0.3)
            r = 70 * a
            cx, cy = x0 + pw / 2, y0 + 640
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 170, 80))
            if a > 0.9:
                d.line([(cx - 32, cy), (cx - 8, cy + 26), (cx + 36, cy - 26)], fill=WHITE, width=14)
            d.text((x0 + pw / 2, y0 + 545), "BERJAYA DITEBUS!", font=font(40),
                   fill=(0, 140, 70), anchor="mm")


def croissant(d, cx, cy, s, col):
    for i, (dx, r) in enumerate([(-110, 45), (-60, 62), (0, 75), (60, 62), (110, 45)]):
        dy = abs(dx) * 0.35
        d.ellipse([cx + dx * s - r * s, cy + dy * s - r * s * 0.8,
                   cx + dx * s + r * s, cy + dy * s + r * s * 0.8], fill=col,
                  outline=(150, 85, 30), width=int(4 * s))


# ---------- shots ----------

class Photo:
    def __init__(self, path):
        src = Image.open(path).convert("RGB")
        k = H * 1.15 / src.height
        self.base = src.resize((int(src.width * k), int(src.height * k)), Image.LANCZOS)
        shade = Image.new("L", (1, H))
        for y in range(H):
            shade.putpixel((0, y), int(max(0, (y - H * 0.55) / (H * 0.45)) * 170))
        self.shade = shade.resize((W, H))
        self.black = Image.new("RGB", (W, H), (0, 0, 0))

    def frame(self, z, fx, fy):
        bw, bh = self.base.size
        cw, ch = W * 1.15 / z, H * 1.15 / z
        x = min(max(fx * bw - cw / 2, 0), bw - cw)
        y = min(max(fy * bh - ch / 2, 0), bh - ch)
        img = self.base.resize((W, H), Image.BILINEAR, box=(x, y, x + cw, y + ch))
        return Image.composite(self.black, img, self.shade)


def dur(i):
    return SHOTS[i][1] - SHOTS[i][0]


def shot1(t, ctx):
    p = t / dur(0)
    img = ctx["photo"].frame(1.0 + 0.08 * p, 0.45, 0.45)
    breaking_badge(img, t)
    name_super(img, t, ctx["name"])
    lower_third(img, t - 0.3, "SHELL CAFÉ", "Promosi 'Wow Wednesday' Kembali")
    return img


def shot2(t, ctx):
    img = ctx["bg_coffee"].copy()
    d = ImageDraw.Draw(img)
    plen = dur(1) / 3
    phase = min(int(t // plen), 2)
    lt = t - phase * plen
    labels = ["ESPRESSO SEGAR", "SUSU BERBUIH LEMBUT", "SEDIA UNTUK ANDA"]
    pop = 1 + 0.12 * math.sin(min(lt, 0.5) / 0.5 * math.pi) if phase == 2 else 1
    cup(d, W / 2, 790, 1.25 * pop, steam_t=t, foam=ease(lt / 2) if phase >= 1 else 0)
    if phase == 0:
        for i in range(4):
            dy = ((t * 1.6 + i / 4) % 1)
            y = 320 + dy * 160
            d.ellipse([W / 2 - 14, y, W / 2 + 14, y + 36], fill=(90, 45, 20))
    if phase == 2:
        for i in range(10):
            ang = i * math.pi / 5 + t
            r = 330 + 20 * math.sin(t * 5 + i)
            x, y = W / 2 + math.cos(ang) * r, 790 + math.sin(ang) * r
            d.regular_polygon((x, y, 18), 4, rotation=45, fill=YEL)
    f = font(56)
    a = ease(lt / 0.4)
    centered(d, 190 - 30 * (1 - a), labels[phase], f, YEL)
    lower_third(img, t, "KOPI SEGAR & MINUMAN PILIHAN", "Tawaran Khas Setiap Hari Rabu")
    return img


def shot3(t, ctx):
    plen = dur(2) / 3
    if t < plen:
        img = ctx["bg_red"].copy()
        phone(img, t, "app")
    elif t < 2 * plen:
        img = ctx["bg_red"].copy()
        phone(img, (t - plen) * 5 / plen, "qr")
    else:
        lt = t - 2 * plen
        img = ctx["bg_warm"].copy()
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([120, 560, 960, 960], 30, fill=(70, 70, 75))
        d.rounded_rectangle([140, 580, 940, 940], 24, fill=(110, 110, 118))
        cols = [(222, 150, 60), (230, 165, 70), (214, 140, 52)]
        for i, (cx, cy) in enumerate([(330, 700), (750, 700), (540, 840)]):
            a = ease((lt - i * 0.25) / 0.5)
            croissant(d, cx, cy + 60 * (1 - a), 0.95 * max(a, 0.01), cols[i])
        for i in range(3):
            pts = [(330 + i * 210 + math.sin(j * 0.4 + lt * 4) * 14, 520 - j * 10) for j in range(14)]
            d.line(pts, fill=(255, 245, 230), width=8)
        centered(d, 200, "PASTRI SEGAR", font(76), YEL, stroke=4)
        centered(d, 300, "& KOPI PREMIUM", font(60), WHITE, stroke=4)
    lower_third(img, t, "TEBUS GUNA SHELL APP", "Imbas di kaunter semasa bayar")
    return img


def shot4(t, ctx):
    p = t / dur(3)
    img = ctx["photo"].frame(1.12 + 0.03 * p, 0.42, 0.40)
    breaking_badge(img, t)
    lower_third(img, t - 0.2, "TERSEDIA DI SHELL CAFÉ TERPILIH", "Hari Rabu Sahaja")
    return img


def shot5(t, ctx):
    img = ctx["bg_red"].copy()
    d = ImageDraw.Draw(img)
    for i in range(-6, 14):
        x = i * 160 + (t * 60) % 160
        d.polygon([(x, 0), (x + 50, 0), (x + 50 - 600, H), (x - 600, H)], fill=(200, 22, 28))
    a = ease(t / 0.6)
    cup(d, W / 2, 580 + 80 * (1 - a), 1.1, steam_t=t)
    centered(d, 880, "SINGGAH", font(84), YEL, stroke=4, stroke_fill=(120, 0, 0))
    centered(d, 980, "SHELL CAFÉ HARI INI", font(72), WHITE, stroke=4, stroke_fill=(120, 0, 0))
    b = ease((t - 0.6) / 0.5)
    bw = 640 * b
    if bw > 10:
        d.rounded_rectangle([W / 2 - bw / 2, 1390, W / 2 + bw / 2, 1500], 55, fill=YEL)
        if b > 0.8:
            centered(d, 1415, "Tebus di Shell App", font(54), RED)
    return img


SHOT_FN = [shot1, shot2, shot3, shot4, shot5]


def parse_srt(path):
    raw = open(path, encoding="utf-8").read().strip()
    cues = []
    ts = lambda s: sum(float(x) * m for x, m in zip(s.replace(",", ".").split(":"), (3600, 60, 1)))
    for block in re.split(r"\n\s*\n", raw):
        lines = block.strip().splitlines()
        start, end = [ts(x.strip()) for x in lines[1].split("-->")]
        cues.append((start, end, " ".join(lines[2:])))
    return cues


def render(t, ctx):
    idx = next(i for i, (s, e) in enumerate(SHOTS) if t < e or i == len(SHOTS) - 1)
    s = SHOTS[idx][0]
    img = SHOT_FN[idx](t - s, ctx)
    if idx > 0 and t - s < XFADE:
        prev = SHOT_FN[idx - 1](t - SHOTS[idx - 1][0], ctx)
        img = Image.blend(prev, img, (t - s) / XFADE)
    captions(img, t, ctx["cues"])
    return img


def main():
    photo, srt, out = sys.argv[1:4]
    global SHOTS
    name = sys.argv[4] if len(sys.argv) > 4 else "Haslam"
    SHOTS = CUTS[sys.argv[5] if len(sys.argv) > 5 else "full"]
    ctx = {
        "photo": Photo(photo), "name": name, "cues": parse_srt(srt),
        "bg_coffee": gradient((45, 24, 14), (130, 70, 35)),
        "bg_red": gradient((235, 40, 40), (150, 10, 15)),
        "bg_warm": gradient((120, 55, 20), (60, 25, 10)),
    }
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)
    for n in range(SHOTS[-1][1] * FPS):
        ff.stdin.write(render(n / FPS, ctx).tobytes())
    ff.stdin.close()
    sys.exit(ff.wait())


if __name__ == "__main__":
    main()
