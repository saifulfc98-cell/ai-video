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

## Promo "Gempak" (13 s, 9:16, untuk jualan)

[`output/hot-wheels-promo-gempak.mp4`](output/hot-wheels-promo-gempak.mp4): dibina daripada klip Gemini 16:9 (`assets/gemini-turbo-charged.mp4`). Ada slow-mo, zoom hentakan, kilat putih, gegaran kamera, teks jualan, babak "pilih warna" (merah/kuning) dan kad CTA "BELI DI KAUNTER". Audionya ialah SFX asal klip ditambah beat 140 BPM dan bunyi hentakan pada setiap potongan.

```
python3 tools/make_promo.py hot-wheels-turbo-charged/assets/gemini-turbo-charged.mp4 hot-wheels-turbo-charged/output/hot-wheels-promo-gempak.mp4
```

**Versi 20 s:** [`output/hot-wheels-promo-gempak-20s.mp4`](output/hot-wheels-promo-gempak-20s.mp4). Babak lebih panjang, ditambah zoom pada kad merah ("MERAH GARANG!") dan kad kuning ("KUNING MENYALA!"), dan CTA lebih lama. Jana: tambah `20` di hujung arahan di atas (dengan nama fail output `-20s`).
