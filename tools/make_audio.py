"""Add an offline Malay voiceover (espeak-ng) and a synthesized news music bed to a video.

Usage (from repo root), see main() for the two modes:
  python3 tools/make_audio.py voice <dialog.txt> <total_s> <out_base>
  python3 tools/make_audio.py mux <video.mp4> <out_base> <out.mp4>
The voice step also writes captions timed to the voice. Needs: pip install espeakng-loader numpy
"""
import ctypes
import subprocess
import sys
import wave

import espeakng_loader
import numpy as np

SR = 44100


# ---------- voice (espeak-ng via ctypes) ----------

def tts(text, voice="ms+f2", rate=175, pitch=55):
    lib = ctypes.CDLL(espeakng_loader.get_library_path())
    chunks = []
    CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)

    def cb(wav, n, _ev):
        if n > 0:
            chunks.append(np.ctypeslib.as_array(wav, shape=(n,)).copy())
        return 0

    keep = CB(cb)
    sr = lib.espeak_Initialize(2, 0, espeakng_loader.get_data_path().encode(), 0)
    lib.espeak_SetSynthCallback(keep)
    lib.espeak_SetVoiceByName(voice.encode())
    lib.espeak_SetParameter(1, rate, 0)   # espeakRATE (words/min)
    lib.espeak_SetParameter(3, pitch, 0)  # espeakPITCH
    lib.espeak_SetParameter(6, 25, 0)     # espeakRANGE: a little less sing-song
    data = text.encode("utf-8")
    lib.espeak_Synth(data, len(data) + 1, 0, 1, 0, 1, None, None)
    lib.espeak_Synchronize()
    x = np.concatenate(chunks).astype(np.float32) / 32768
    return np.interp(np.arange(0, len(x), sr / SR), np.arange(len(x)), x)  # resample


def fit_to(x, max_len):
    """Speed up (pitch kept) with ffmpeg atempo when x is longer than max_len samples."""
    if len(x) <= max_len:
        return x
    tempo = min(len(x) / max_len, 2.0)
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
         "-af", f"atempo={tempo:.4f}", "-f", "f32le", "-"],
        input=x.astype(np.float32).tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32)[:max_len]


def voice_track(groups, total):
    """groups: [(start, [line, ...])]. Lines in a group play back to back; the whole group
    is sped up evenly if it would overrun the next group. Returns audio and caption cues."""
    out = np.zeros(int(total * SR), dtype=np.float32)
    gap = np.zeros(int(0.18 * SR), dtype=np.float32)
    cues = []
    for i, (start, lines) in enumerate(groups):
        end = groups[i + 1][0] - 0.3 if i + 1 < len(groups) else total - 0.3
        parts = [tts(t) for t in lines]
        x = np.concatenate([np.concatenate([p, gap]) for p in parts])
        slot = int((end - start) * SR)
        k = max(1.0, len(x) / slot)
        x = fit_to(x, slot)
        t = start
        for line, p in zip(lines, parts):
            d = (len(p) + len(gap)) / SR / k
            cues.append((t, t + d, line))
            t += d
        s = int(start * SR)
        out[s:s + len(x)] += x[:len(out) - s]
    return out / (np.abs(out).max() + 1e-9) * 0.9, cues


def write_srt(path, cues):
    ts = lambda x: f"{int(x // 3600):02}:{int(x % 3600 // 60):02}:{int(x % 60):02},{int(x * 1000 % 1000):03}"
    with open(path, "w", encoding="utf-8") as f:
        for n, (a, b, text) in enumerate(cues, 1):
            f.write(f"{n}\n{ts(a)} --> {ts(b)}\n{text}\n\n")


# ---------- news music bed ----------

def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(t / attack, 1) * np.exp(-t / decay)


def saw(f, n):
    t = np.arange(n) / SR
    return 2 * ((t * f) % 1) - 1


def lowpass(x, alpha):
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):  # small 1-pole filter; fine for these short notes
        acc += alpha * (v - acc)
        y[i] = acc
    return y


def music(total, bpm=120):
    rnd = np.random.default_rng(1)
    out = np.zeros(int(total * SR) + SR, dtype=np.float32)
    beat = 60 / bpm
    add = lambda s, x: out.__setitem__(slice(int(s * SR), int(s * SR) + len(x)),
                                       out[int(s * SR):int(s * SR) + len(x)] + x[:len(out) - int(s * SR)])
    # chords: Am F C G (root Hz, triad Hz)
    prog = [(110.0, [220.0, 261.6, 329.6]), (87.3, [174.6, 220.0, 261.6]),
            (130.8, [261.6, 329.6, 392.0]), (98.0, [196.0, 246.9, 293.7])]
    kick_n = int(0.35 * SR)
    tk = np.arange(kick_n) / SR
    kick = np.sin(2 * np.pi * (50 * tk + 60 * (1 - np.exp(-tk * 30)) / 30)) * np.exp(-tk * 9)
    hat = rnd.standard_normal(int(0.05 * SR)) * env(int(0.05 * SR), 0.001, 0.012)
    hat = np.diff(hat, prepend=0)  # brighter
    stab_cache = {}
    n_beats = int(total / beat)
    for b in range(n_beats):
        t0 = b * beat
        root, triad = prog[(b // 4) % 4]
        add(t0, kick * 0.8)
        add(t0, hat * 0.25)
        add(t0 + beat / 2, hat * 0.18)
        bn = int(beat / 2 * SR)
        for k in range(2):  # pulsing eighth-note bass
            add(t0 + k * beat / 2, saw(root, bn) * env(bn, 0.005, 0.12) * 0.22)
        if b % 2 == 0:  # staccato string-like stabs on the off-beat
            key = tuple(triad)
            if key not in stab_cache:
                n = int(0.22 * SR)
                x = sum(saw(f, n) + saw(f * 1.004, n) for f in triad)
                stab_cache[key] = lowpass(x * env(n, 0.004, 0.08), 0.18).astype(np.float32)
            add(t0 + beat * 0.5, stab_cache[key] * 0.12)
    # opening hit: low boom + noise whoosh
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    add(0, (np.sin(2 * np.pi * 55 * t) * np.exp(-t * 2.5) * 0.9).astype(np.float32))
    whoosh = rnd.standard_normal(n) * np.sin(np.pi * np.minimum(t / 1.6, 1)) * 0.15
    add(0, lowpass(whoosh, 0.08).astype(np.float32))
    out = out[:int(total * SR)]
    fade = int(1.5 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out / (np.abs(out).max() + 1e-9) * 0.9


def write_wav(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def read_dialog(path):
    """'<start>|<spoken>|<caption>' starts a group; '|<spoken>|<caption>' continues it.
    <spoken> may use sound-alike spelling for the TTS; <caption> is what is shown."""
    groups, spoken = [], {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or "|" not in line:
            continue
        start, say, show = (p.strip() for p in line.split("|", 2))
        if start:
            groups.append((float(start), []))
        groups[-1][1].append(say)
        spoken[say] = show
    return groups, spoken


def main():
    """Modes:
      voice <dialog.txt> <total_s> <out_base>  -> out_base-voice.wav, -music.wav, -captions.srt
      mux <video.mp4> <out_base> <out.mp4>     -> video with voice + ducked music
    """
    if sys.argv[1] == "voice":
        dialog, total, base = sys.argv[2], float(sys.argv[3]), sys.argv[4]
        groups, show = read_dialog(dialog)
        voice, cues = voice_track(groups, total)
        write_wav(base + "-voice.wav", voice)
        write_wav(base + "-music.wav", music(total))
        write_srt(base + "-captions.srt", [(a, b, show[t]) for a, b, t in cues])
        return
    video, base, out = sys.argv[2:5]
    # music ducks under the voice; light EQ/compression to make espeak less harsh
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", video, "-i", base + "-voice.wav", "-i", base + "-music.wav",
         "-filter_complex",
         "[1:a]highpass=f=90,lowpass=f=7500,acompressor=threshold=-18dB:ratio=3,"
         "aecho=0.8:0.5:30:0.12,volume=1.6,asplit[v1][v2];"
         "[2:a]volume=0.45[m];[m][v1]sidechaincompress=threshold=0.03:ratio=8:release=400[md];"
         "[md][v2]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
         "-shortest", "-movflags", "+faststart", out], check=True)


if __name__ == "__main__":
    main()
