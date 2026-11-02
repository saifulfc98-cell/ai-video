# Shell Café Wow Wednesday – Buletin Berita (Draf 1)

| Perkara | Butiran |
|---|---|
| Durasi sasaran | 45 – 60 saat (skrip ≈ 57 s) |
| Format | 9:16 vertikal, 1080×1920, 30 fps |
| Gaya | Wartawan penyiaran profesional – pantas, bertenaga, autoritatif |
| Penyampai | Haslam (rujukan: [`assets/presenter-reference.jpg`](assets/presenter-reference.jpg)) |
| Props | Mikrofon lapel / clip-on, cawan Shell Café, lanyard stesen |

## Fail

| Fail | Guna untuk |
|---|---|
| [`script.md`](script.md) | Papan cerita penuh: shot, kamera, teks skrin, SFX, dialog |
| [`teleprompter.txt`](teleprompter.txt) | Dialog sahaja, untuk dibaca semasa rakaman |
| [`captions.srt`](captions.srt) | Sari kata – import terus ke CapCut / Premiere / TikTok |
| [`ai-prompts.md`](ai-prompts.md) | Prompt untuk jana B-roll & animasi penyampai dengan AI |
| [`script-30s.md`](script-30s.md) | Versi pendek 30 saat |
| [`caption-tiktok.md`](caption-tiktok.md) | Caption, hashtag & teks pin komen |

## Sebelum terbit – semak

- [ ] Sahkan butiran promosi dengan Shell Malaysia (item, harga/diskaun, tarikh, cawangan terlibat). Skrip sengaja tidak menyebut angka.
- [ ] Dapatkan kebenaran guna logo & muzik/audio logo Shell.
- [ ] Label **#iklan / kandungan berbayar** jika ini kerjasama berbayar.
- [ ] Kebenaran rakaman di premis stesen & pelanggan yang muncul dalam B-roll.

## Video draf

[`output/wow-wednesday-draf.mp4`](output/wow-wednesday-draf.mp4): 57 s; [`output/wow-wednesday-30s.mp4`](output/wow-wednesday-30s.mp4): 30 s (guna `captions-30s.srt` + argumen `30s`), 1080×1920, sari kata tertanam, **tanpa suara** (tambah VO Haslam & muzik di CapCut).
Jana semula selepas ubah `captions.srt`:

```
python3 tools/make_video.py shell-cafe-wow-wednesday/assets/presenter-reference.jpg \
  shell-cafe-wow-wednesday/captions.srt shell-cafe-wow-wednesday/output/wow-wednesday-draf.mp4 Haslam
```
