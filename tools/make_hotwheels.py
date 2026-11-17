"""Render the Hot Wheels x Touch 'n Go "Turbo Charged" bulletin (40 s, 9:16, silent).

Usage (from repo root): PYTHONPATH=tools python3 tools/make_hotwheels.py [v1|v2]
Reuses the overlays from make_video.py. Product shots use the real phone footage
(landscape clips sit on a blurred copy of themselves); the end card uses the photo.
"""
import subprocess
import sys

from PIL import Image, ImageDraw

import make_video as mv

D = "hot-wheels-turbo-charged"
SHOTS = [(0, 8), (8, 18), (18, 28), (28, 36), (36, 40)]
W, H, FPS = mv.W, mv.H, mv.FPS


def shot_presenter(t, ctx, z, title, sub, name=False):
    img = ctx["host"].frame(z, 0.45, 0.45)
    mv.breaking_badge(img, t)
    if name:
        mv.name_super(img, t, ctx["name"], ctx["role"])
    mv.lower_third(img, t - 0.3, title, sub)
    return img


def shot1(t, ctx):
    return shot_presenter(t, ctx, 1.0 + 0.08 * t / 8, "HOT WHEELS × TOUCH 'n GO",
                          "Kad Edisi 'Turbo Charged' Kini Tiba", name=True)


PORTRAIT = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
LANDSCAPE = ("split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,"
             "crop=1080:1920,boxblur=30,eq=brightness=-0.15[bg];"
             "[b]scale=-2:1000,crop=1080:1000[fg];[bg][fg]overlay=0:300")


class Clip:
    """Reads one segment of a phone clip as 1080x1920 frames, in order."""

    def __init__(self, path, start, dur, vf):
        self.proc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", path,
             "-vf", f"fps={FPS},{vf}", "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE)
        self.n, self.last = -1, None

    def frame(self, t):
        want = int(t * FPS)
        while self.n < want:
            buf = self.proc.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            self.last, self.n = Image.frombytes("RGB", (W, H), buf), self.n + 1
        return self.last.copy()


def shot2(t, ctx):
    img = ctx["cards"].frame(t)
    mv.lower_third(img, t, "KAD TOUCH 'n GO ENHANCED", "Edisi Turbo Charged – Kuning & Merah")
    return img


def shot3(t, ctx):
    img = ctx["pan"].frame(t) if t < 6.4 else ctx["cars"].frame(t - 6.4)
    mv.lower_third(img, t, "KOLEKSI KERETA HOT WHEELS", "Kereta sport & kereta rali")
    return img


def shot4(t, ctx):
    return shot_presenter(t, ctx, 1.12 + 0.03 * t / 8, "KINI DI KAUNTER KAMI",
                          "Tanya staf untuk butiran lanjut")


def shot5(t, ctx):
    img = ctx["prod"].frame(1.0 + 0.04 * t / 4, 0.5, 0.5)
    img = Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), 0.45)
    d = ImageDraw.Draw(img)
    a = mv.ease(t / 0.5)
    mv.centered(d, 760 - 60 * (1 - a), "SINGGAH", mv.font(110), mv.YEL, stroke=6)
    mv.centered(d, 890 - 60 * (1 - a), "& KUMPUL!", mv.font(100), mv.WHITE, stroke=6)
    b = mv.ease((t - 0.5) / 0.5)
    bw = 680 * b
    if bw > 10:
        d.rounded_rectangle([W / 2 - bw / 2, 1390, W / 2 + bw / 2, 1500], 55, fill=mv.RED)
        if b > 0.8:
            mv.centered(d, 1415, "Tanya di kaunter", mv.font(54), mv.WHITE)
    return img


FNS = [shot1, shot2, shot3, shot4, shot5]


# ---------- v2: skrip hebahan "Tiba Lagi!" ----------

def v2_shot1(t, ctx):
    return shot_presenter(t, ctx, 1.0 + 0.08 * t / 11, "HOT WHEELS TIBA LAGI!",
                          "Bersama kad Touch 'n Go 'Turbo Charged'", name=True)


def v2_shot2(t, ctx):
    img = ctx["pan"].frame(t) if t < 6.4 else ctx["cars"].frame(t - 6.4)
    mv.lower_third(img, t, "MODEL KERETA HOT WHEELS", "+ Kad Touch 'n Go edisi khas")
    return img


def v2_shot3(t, ctx):
    if t < 5.5:
        p = mv.ease(t / 5.5)
        img = ctx["prod"].frame(1.6, 0.6 - 0.15 * p, 0.12 + 0.43 * p)
    else:
        img = ctx["cards"].frame(t - 5.5)
    mv.lower_third(img, t, "KOLEKSI EDISI 2026", "Dapatkan sementara stok masih ada")
    return img


def v2_shot4(t, ctx):
    return shot_presenter(t, ctx, 1.12 + 0.03 * t / 6, "AIN SALSABILA MELAPORKAN",
                          "Info terkini bersama kami")


def v2_shot5(t, ctx, tag="Di lokasi terpilih"):
    img = ctx["prod"].frame(1.0 + 0.04 * t / 3, 0.5, 0.5)
    img = Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), 0.45)
    d = ImageDraw.Draw(img)
    a = mv.ease(t / 0.5)
    mv.centered(d, 760 - 60 * (1 - a), "TURBO", mv.font(120), mv.YEL, stroke=6)
    mv.centered(d, 895 - 60 * (1 - a), "CHARGED", mv.font(120), mv.WHITE, stroke=6)
    b = mv.ease((t - 0.5) / 0.5)
    bw = 720 * b
    if bw > 10:
        d.rounded_rectangle([W / 2 - bw / 2, 1390, W / 2 + bw / 2, 1500], 55, fill=mv.RED)
        if b > 0.8:
            mv.centered(d, 1415, tag, mv.font(54), mv.WHITE)
    return img


# ---------- v3: "Buletin Khas Kasual" (kereta = hiasan, kad = kuasa turbo) ----------

def v3_shot1(t, ctx):
    if t < 10:
        return shot_presenter(t, ctx, 1.0 + 0.06 * t / 10, "LAPORAN KHAS GAYA HIDUP",
                              "Trend terkini di stesen minyak", name=True)
    if t < 16.5:
        img = ctx["pan"].frame(t - 10)
        mv.lower_third(img, t - 10, "SUDUT PAMERAN", "Deretan kereta mainan mewah & rali")
        return img
    return shot_presenter(t - 16.5, ctx, 1.1 + 0.04 * (t - 16.5) / 8, "FAKTA MENARIK",
                          "Yang ramai terlepas pandang!")


def v3_shot2(t, ctx):
    img = ctx["new_cars"].frame(t)
    mv.lower_third(img, t, "KERETA MAINAN = HIASAN", "Maskot pameran semata-mata")
    return img


def v3_shot3(t, ctx):
    if t < 4:
        img = ctx["new_cards"].frame(t)
    elif t < 11:
        img = ctx["cards"].frame(t - 4)
    else:
        p = mv.ease((t - 11) / 6)
        img = ctx["prod"].frame(1.6, 0.6 - 0.15 * p, 0.12 + 0.43 * p)
    mv.lower_third(img, t, "KUASA TURBO SEBENAR", "Kad Touch 'n Go Enhanced 'Turbo Charged'")
    return img


def v3_shot4(t, ctx):
    return shot_presenter(t, ctx, 1.12 + 0.03 * t / 11, "DAPATKAN DI KAUNTER",
                          "Sementara stok masih ada")


def v3_shot5(t, ctx):
    return v2_shot5(t, ctx, "Di kaunter berdekatan")


VERSIONS = {
    "v1": ([(0, 8), (8, 18), (18, 28), (28, 36), (36, 40)], FNS, "captions.srt",
           "hot-wheels-draf.mp4", (2.0, 10.5), "presenter-reference.jpg", "Haslam", "Wartawan"),
    "v2": ([(0, 11), (11, 22), (22, 34), (34, 40), (40, 43)],
           [v2_shot1, v2_shot2, v2_shot3, v2_shot4, v2_shot5], "captions-v2.srt",
           "hot-wheels-v2.mp4", (2.0, 7.0), "presenter-ain.jpg", "Ain Salsabila",
           "Pembaca Berita"),
    "v3": ([(0, 24.5), (24.5, 32.5), (32.5, 49.5), (49.5, 60.5), (60.5, 63.5)],
           [v3_shot1, v3_shot2, v3_shot3, v3_shot4, v3_shot5], "captions-v3.srt",
           "hot-wheels-v3.mp4", (2.0, 7.0), "presenter-ain.jpg", "Ain Salsabila",
           "Pembaca Berita"),
}


def render(t, ctx):
    idx = next(i for i, (s, e) in enumerate(SHOTS) if t < e or i == len(SHOTS) - 1)
    s = SHOTS[idx][0]
    img = FNS[idx](t - s, ctx)
    if idx > 0 and t - s < mv.XFADE:
        prev = FNS[idx - 1](t - SHOTS[idx - 1][0], ctx)
        img = Image.blend(prev, img, (t - s) / mv.XFADE)
    mv.captions(img, t, ctx["cues"])
    return img


def main():
    global SHOTS, FNS
    SHOTS, FNS, srt, out, (c0, cdur), host, name, role = VERSIONS[sys.argv[1] if len(sys.argv) > 1 else "v1"]
    if len(sys.argv) > 3:  # optional: <captions.srt> <out.mp4> overrides
        srt, out = sys.argv[2], sys.argv[3]
    ctx = {
        "host": mv.Photo(f"{D}/assets/{host}"), "name": name, "role": role,
        "prod": mv.Photo(f"{D}/assets/produk-kaunter.jpg"),
        "cues": mv.parse_srt(srt if "/" in srt else f"{D}/{srt}"),
        "cards": Clip(f"{D}/assets/rakaman-closeup.mp4", c0, cdur, LANDSCAPE),
        "pan": Clip(f"{D}/assets/rakaman-pan-kaunter.mp4", 0, 6.5, PORTRAIT),
        "cars": Clip(f"{D}/assets/rakaman-closeup.mp4", 16.0, 5.0, LANDSCAPE),
        "new_cards": Clip(f"{D}/assets/rakaman-kad-kereta.mp4", 0, 4.1, LANDSCAPE),
        "new_cars": Clip(f"{D}/assets/rakaman-kad-kereta.mp4", 4.0, 8.0, LANDSCAPE),
    }
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-c:v", "libx264", "-crf", "21", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", "-movflags", "+faststart", out if "/" in out else f"{D}/output/{out}"],
        stdin=subprocess.PIPE)
    for n in range(int(SHOTS[-1][1] * FPS)):
        ff.stdin.write(render(n / FPS, ctx).tobytes())
    ff.stdin.close()
    for k in ("cards", "pan", "cars", "new_cards", "new_cars"):
        ctx[k].proc.kill()
    raise SystemExit(ff.wait())


if __name__ == "__main__":
    main()
