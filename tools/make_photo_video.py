"""Turn one photo + one audio track into a 9:16 video with smooth Ken Burns moves.

Usage: python3 tools/make_photo_video.py <photo> <audio> <out.mp4>
"""
import subprocess
import sys

from PIL import Image

W, H, FPS = 1080, 1920, 30
# (time s, centre x, centre y, crop width) as fractions of the photo
KEYS = [
    (0.0, 0.50, 0.50, 1.00),
    (6.0, 0.50, 0.62, 0.80),   # drift down toward the team
    (11.0, 0.30, 0.74, 0.55),  # left side of the group
    (16.0, 0.70, 0.74, 0.55),  # pan to the right side
    (21.0, 0.32, 0.30, 0.60),  # look up at the canopy & pump sign
    (26.0, 0.50, 0.70, 0.75),  # back to the whole team
    (99.0, 0.50, 0.55, 0.95),
]


def ease(x):
    return x * x * (3 - 2 * x)


def at(t):
    for a, b in zip(KEYS, KEYS[1:]):
        if t <= b[0]:
            k = ease((t - a[0]) / (b[0] - a[0]))
            return [a[i] + (b[i] - a[i]) * k for i in (1, 2, 3)]
    return KEYS[-1][1:]


def main(photo, audio, out):
    dur = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", audio]))
    img = Image.open(photo).convert("RGB")
    iw, ih = img.size
    big = img.resize((iw * 2, ih * 2), Image.LANCZOS)  # supersample for smooth motion
    bw, bh = big.size
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", audio,
        "-filter_complex",
        f"[0:v]fade=in:st=0:d=0.8,fade=out:st={dur - 1.2:.2f}:d=1.2[v];"
        f"[1:a]afade=in:st=0:d=0.3,afade=out:st={dur - 1.2:.2f}:d=1.2[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out,
    ], stdin=subprocess.PIPE)
    for n in range(int(dur * FPS)):
        cx, cy, cw = at(n / FPS)
        w = cw * bw
        h = w * H / W
        if h > bh:
            h, w = bh, bh * W / H
        x = min(max(cx * bw - w / 2, 0), bw - w)
        y = min(max(cy * bh - h / 2, 0), bh - h)
        frame = big.resize((W, H), Image.BICUBIC, box=(x, y, x + w, y + h))
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    sys.exit(ff.wait())


if __name__ == "__main__":
    main(*sys.argv[1:4])
