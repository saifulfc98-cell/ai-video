# Hot Wheels × Touch 'n Go "Turbo Charged" – Buletin (40 s)

| Fail | Guna untuk |
|---|---|
| [`script.md`](script.md) | Papan cerita & dialog |
| [`teleprompter.txt`](teleprompter.txt) | Bacaan semasa rakaman |
| [`captions.srt`](captions.srt) | Sari kata |
| [`caption-tiktok.md`](caption-tiktok.md) | Caption, hashtag, pin komen |
| [`output/hot-wheels-draf.mp4`](output/hot-wheels-draf.mp4) | Video draf 40 s, tanpa suara | 
| [`script-v2.md`](script-v2.md) · [`output/hot-wheels-v2.mp4`](output/hot-wheels-v2.mp4) | Versi 2 (skrip "Tiba Lagi!", 43 s) — jana: `... make_hotwheels.py v2` |
| `assets/rakaman-*.mp4` | Rakaman telefon asal (shot kad | [`output/hot-wheels-draf.mp4`](output/hot-wheels-draf.mp4) | Video draf 40 s, tanpa suara | kereta) |

Jana semula: `PYTHONPATH=tools python3 tools/make_hotwheels.py`

## Versi 2 dengan suara & muzik

[`output/hot-wheels-v2-suara.mp4`](output/hot-wheels-v2-suara.mp4): suara pembaca berita (espeak-ng, luar talian; robotik) + muzik berita sintetik yang direndahkan bila suara masuk. Trek berasingan untuk CapCut: `output/v2-audio-voice.wav`, `output/v2-audio-music.wav`.

```
pip install espeakng-loader numpy
python3 tools/make_audio.py voice hot-wheels-turbo-charged/dialog-v2.txt 43 hot-wheels-turbo-charged/output/v2-audio
cp hot-wheels-turbo-charged/output/v2-audio-captions.srt hot-wheels-turbo-charged/captions-v2.srt
PYTHONPATH=tools python3 tools/make_hotwheels.py v2
python3 tools/make_audio.py mux hot-wheels-turbo-charged/output/hot-wheels-v2.mp4 hot-wheels-turbo-charged/output/v2-audio hot-wheels-turbo-charged/output/hot-wheels-v2-suara.mp4
```
