Objective
- Pulihkan data hari ini (12 Nov 2026) untuk project SAHAM-SCREENING setelah token Stockbit mati seharian (HTTP 401) yang membuat data beku berisi data kemarin — isi ulang OHLCV harian, fundamental, net foreign, arsip intraday hari ini, lalu jalankan cek TP/SL portofolio seperti biasa (user siapkan token sehat mulai besok).
Important Details
- Root cause: token expired 12 Nov 06:15 WIB tidak ter-refresh sepanjang bursa → producer kena 401 ("Intraday selesai: 0 OK, 944 gagal") → fallback history_cache basi → arsip 2026-11-12 lama berisi 97 snapshot identik data 11 Nov (BBCA beku 5325/92.364.800).
- Token baru sehat: exp 13 Nov 19:33 WIB; kanonik di SAHAM-SCREENING/token_stockbit.txt, disinkron jaga_token.py (cron */10 6-18) ke DATA-CENTER & WEB-SCREENING.
- Stockbit exodus TIDAK punya bar intraday historis (varian period intraday → HTTP 400, endpoint intraday → 404); Yahoo 5m tersedia untuk sesi hari ini (kalibrasi: Yahoo = Stockbit, volume ×100).
- Temuan baru malam ini: marketdetectors (broksum) → HTTP 402 {"error_type":"PAYWALL","message":"paywall"} — kemarin (11 Nov) broksum nyata terisi (B: ZP, AK, AZ | S: CC, YU, BK | (Acc), 19.563/78.493 baris); paywall tidak dipulihkan malam ini, skor broker hari ini = 0 (hari lama tetap terhitung).
- Feed hasil_screener.csv = 52 kolom (Waktu Update, Ticker, Broksum, Kategori, Valuasi, PER (x), PBV (x), Harga (Rp), Change (%), Volume, …, Rekomendasi, Net Asing (Rp), Skor Broker).
- Producer hanya mengarsip saat 9≤jam<17 ("Mode Malam") → arsip rekon manual tidak akan tertimpa producer.
- jalankan_bot.sh menyalin feed/arsip/screener_YYYY-MM-DD.csv → Arsip_Data_Harian/ + upload R2 → arsip rekon wajib ada di feed/arsip SEBELUM consumer jalan (sudah).
- TP/SL: bot_simulator.py --tp-sl-only; jual bila harga_sekarang >= Target_TP / <= Target_CL (bot_simulator.py:402-421); fallback harga dari arsip (harga_terakhir_dari_arsip).
- Porto aktif: 44 posisi di 9 arena (Database/portofolio_aktif_rumus_1..9.csv), semua dibeli 2026-11-11 21:45 (WMUU, MYOR, POLA, TRUS, IFII, AGAR, GIAA, LMAX, RUNS, KAEF, GOLD…).
- Konteks sesi lama: commit 3f71947c (BUG-1/2/3) & 88aa22be (suspend fix) sudah push; minor belum diperbaiki (app.py "openrouter/free", gemini-3.7/3.6 fiktif, r2_client.py:56 tanpa try/except).
Work State
Completed
- Backup arsip beku → Arsip_Reset/rekon_2026-11-12/ (screener2026-11-12_BEKU_asli.csv, feed_arsip2026-11-12_BEKU_asli.csv, broker_scores_BEKU.json).
- fetcher_exodus.py fundamental sukses: 948 saham × 12 metrik → Database/fundamental_exodus.csv + R2; disalin ke DATA-CENTER/feed/fundamental_exodus.csv.
- Producer cycle 1 sukses (21:40): 944/944 OK, feed/hasil_screener.csv berisi bar hari ini asli (BBCA 5475 +2.82% vol 192.936.300; breadth 560 naik/147 turun); status.json stempel 2026-11-12 21:40:23, sumber_harga: STOCKBIT.
- net_foreign.py sukses → feed/net_foreign.csv data hari ini (BBCA +246.98 M, BMRI +51.33 M).
- Rekonstruksi arsip selesai via /tmp/opencode/rekon_arsip.py (fix: date_range(..., tz="Asia/Jakarta")): 78.709 baris, 832 ticker, snapshot/ticker median 96; BBCA 09:00=5325 vol 2.047.800 → 16:55=5475 vol 190.937.300; 54 MB; ditulis ke DATA-CENTER/feed/arsip/screener_2026-11-12.csv dan SAHAM-SCREENING/Arsip_Data_Harian/screener_2026-11-12.csv. Kolom indikator statis dari feed final; broksum tidak tersedia (paywall).
- Verifikasi mekanisme TP/SL di bot_simulator.py selesai.
Active
- Tahap akhir pipeline BELUM dijalankan: refresh skor_broker.py → producer cycle 2 (merge fundamental+net foreign+skor broker ke feed) → skor_sistem.py snapshot+evaluasi (skor_rumus.json masih dari data beku 17:07) → consumer jalankan_bot.sh (sync feed + buat_state_intraday.py + R2 + bot_simulator.py --tp-sl-only + bangun_buku_besar + git push).
- Pertimbangan patch 1-baris get_broksum_aman di DATA-CENTER/update_data.py: early-return saat HTTP 402 agar tidak spam ±800 request paywall tiap siklus.
Blocked
- Broksum (marketdetectors) paywall 402 — tidak bisa dipulihkan malam ini; kolom Broksum feed = "Error HTTP 402" (placeholder, tidak merusak parser skor).
Next Move
1. (Opsional) patch get_broksum_aman untuk 402; lalu cd /home/kaltaraid/Documents/DATA-CENTER && ./venv/bin/python skor_broker.py, producer ulang (bash jalankan_data_center.sh), lalu skor_sistem snapshot+evaluasi.
2. Jalankan bash /home/kaltaraid/Documents/SAHAM-SCREENING/jalankan_bot.sh (sync feed, state_intraday, R2, --tp-sl-only, buku besar, git push); verifikasi posisi porto yang kena TP/CL di output/log dan pastikan commit/push sukses.
Relevant Files
- /home/kaltaraid/Documents/SAHAM-SCREENING/ — consumer utama (app.py, bot_simulator.py, jalankan_bot.sh, jaga_token.py, Database/portofolio_aktif_rumus_1..9.csv, Arsip_Data_Harian/).
- /home/kaltaraid/Documents/DATA-CENTER/update_data.py — producer (Stockbit primary + yfinance fallback, history_cache parquet feed/history_cache/, arsip window 9-17).
- /home/kaltaraid/Documents/DATA-CENTER/skor_broker.py — skor broker dari arsip (usecols Ticker/Harga (Rp)/Broksum; swing>10%; output feed/broker_scores.json).
- /home/kaltaraid/Documents/DATA-CENTER/net_foreign.py — 60 saham watchlist → feed/net_foreign.csv.
- /home/kaltaraid/Documents/DATA-CENTER/skor_sistem.py — snapshot+evaluasi skor rumus (perlu re-run).
- /tmp/opencode/rekon_arsip.py (+ /tmp/opencode/rekon_arsip.log) — script rekonstruksi arsip Yahoo 5m.
- /home/kaltaraid/Documents/DATA-CENTER/feed/{hasil_screener.csv,status.json,fundamental_exodus.csv,net_foreign.csv,broker_scores.json} — feed produksi.
- /home/kaltaraid/Documents/SAHAM-SCREENING/Arsip_Reset/rekon_2026-11-12/ — backup arsip beku (jangan dihapus).
- Log eksekusi: /tmp/opencode/producer_rekon.log, /tmp/opencode/fund_rekon.log.
- venv: SAHAM-SCREENING/.venv (Python 3.14), DATA-CENTER/venv.