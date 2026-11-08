Objective
- Kelola pipeline SAHAM-SCREENING (Streamlit lokal + Streamlit Cloud https://minhaz0305.streamlit.app/) dan pastikan 9 rumus screener (tab 3) menghasilkan kandidat di SEMUA deployment — lokal dan cloud — tanpa menggantungkan SAHAM-SCREENING pada WEB-SCREENING (proyek terpisah, user minta isolasi penuh).
Important Details
- User berbahasa Indonesia; jawab dalam Bahasa Indonesia. User memberi izin penuh (tanpa perlu tanya/izin) untuk perbaikan.
- Arsitektur: cron */5 9-17 1-5 → DATA-CENTER/jalankan_data_center.sh (producer) → feed/hasil_screener.csv → SAHAM-SCREENING/jalankan_bot.sh (consumer: copy feed → Database/, R2 upload, TP/SL) → R2 → Streamlit (ttl=300). Cronie.service aktif.
- Web SAHAM-SCREENING = Streamlit lokal port 8501 dijaga jaga_web.sh (cron @reboot + */5). Web Railway (WEB-SCREENING, FastAPI) MATI sejak 23-10 ("Application not found") — dianggap masalah akun Railway user, TIDAK memengaruhi SAHAM (audit: 0 dependensi kode dua arah; satu-satunya sentuhan = jaga_token.py:32 salin token ke WEB, loop-nya skip jika folder tak ada).
- Rumus didefinisikan DUPLIKAT di dua tempat yang harus identik: app.py PART 12 (blok "SUSUNAN RUMUS", ~baris 1908–1998 + VERSI_SIDANG baris 1885) dan sidang_lib.py hitung_rumus(). Sekarang VERSI_SIDANG = "v6.1" di kedua file.
- v6.1 gate ganda: reb_dini = reb ≥3% dari low intraday ATAU naik ≥3% dari harga pembukaan (helper muat_open_state() baru). Perbaikan bug: filter sisir lama (contains "Pola Sisir") ikut menangkap "Pola Sisir Lemah" — kini pakai "spike 12H". Pembekal kemarin hanya pelunak (R4, bekal_min = skor>=2).
- Nama rumus v6.1 (label dropdown app.py sudah terganti): R1 Hajar Kanan Momentum 🥊, R2 Marubozu Breakout, R3 Sisir Aktif Breakout, R4 Pantulan Hammer, R5 Akumulasi Turnaround, R6 Mark-Up Kontinu, R7 Momentum Besar, R8 MACD Bull Rebound, R9 Skor Tinggi Konfirmasi.
- Bukti 04-11: 20 winner naik ≥10% dari OPEN (BOBA 34.6%, YUPI 30%, ANTM/INKP/BREN/PGEO big-cap) mayoritas Downtrend + bekal 1–2; konsisten: Hajar Kanan 16/20, VWAP Kuat 15/20, Vol Tembus MA20 13/20. Backtest v6.1: 09:35 pagi sudah 79 kandidat (dulu 0); akhir hari 16/20 winner tertangkap; R7 presisi 55%, R2 44%; R6 & R8 0 winner hari itu (pantau).
- Bukti akar masalah cloud kosong: git ls-files Arsip_Data_Harian/ kosong (arsip tidak di-git); R2 arsip mentok di screener_2026-10-14.csv (stale) karena jalankan_bot.sh tidak pernah upload arsip harian; helper intraday di cloud tanpa arsip lokal → {} → semua rumus 0 (label baru tampil, tabel kosong).
- Token Stockbit: exp Rab 04-11-2026 21:12 WIB (kadaluarsa — user harus perbarui manual via ambil_token.py; jaga_token.py alarm Telegram).
- Commit terakhir: 09e43e98 (v6.1), 6a9df4e0 (jaga_web), 75e9fb19 (v6.0+bridge). Remote origin = git@github.com:dadungdadung87-cloud/SAHAM-SCREENING.git (deploy Streamlit Cloud auto dari repo ini).
Work State
Completed
- v6.0 sebelumnya ditulis, dicommit, dipush (75e9fb19); v6.1 ditulis & dipush (09e43e98): gate ganda + fix sisir + 9 rumus baru identik di app.py & sidang_lib.py, label dropdown & kenapa_lolos (app.py:2973) diselaraskan, py_compile OK, AppTest 0 exception.
- Isolasi SAHAM vs WEB diaudit & dicatat; jaga_web.sh dibuat + cron @reboot & */5 terpasang (uji restart OK); Streamlit lokal jalan (terakhir pid 448145, HTTP 200, restart bersih sudah dilakukan 21:5x WIB 04-11).
- sidang_lib.py: helper _arsip_hari_ini(base_dir, hari_lalu=False) ditambahkan — fallback R2 (Arsip_Data_Harian/screener_YYYY-MM-DD.csv via r2_client.download_arsip, cache file .r2_<nama>, skip Sabtu/Minggu ke Jumat); muat_open_state, muat_rebound_state, muat_skor_pembekal kini pakai helper itu (bukan glob files-1/files-2).
- jalankan_bot.sh: blok python R2 diperluas — upload arsip hari ini + arsip kemarin (pembekal) ke R2 tiap siklus.
Active
- BARU SAJA selesai edit jalankan_bot.sh (upload arsip R2) — BELUM diverifikasi sintaks bash/python inline (nested quoting "datetime" dalam f-string raw berisiko), BELUM di-test run, BELUM di-commit/push.
- R2 arsip masih stale (terakhir 2026-10-14): perlu backfill manual — upload Arsip_Data_Harian/screener_2026-11-04.csv (dan 11-03 untuk pembekal) ke R2 agar cloud langsung hidup tanpa menunggu siklus cron.
Blocked
- Streamlit Cloud (minhaz0305) akan tetap kosong sampai: (a) perbaikan jalankan_bot.sh ter-commit+push → auto-redeploy, DAN (b) arsip 11-04/11-03 ter-upload ke R2 (atau siklus cron hari bursa berikutnya meng-upload). Verifikasi cloud tidak bisa dari laptop — perlu user buka URL.
- Web Railway (WEB-SCREENING) tetap down — butuh login dashboard Railway user (CLI railway tidak terinstall di laptop).
- Uptime WEB-SCREENING DOWN tercatat di cron cek_uptime.sh */15 (di crontab, milik WEB-SCREENING — biarkan).
Next Move
1. Verifikasi sintaks & jalankan smoke test jalankan_bot.sh bagian R2 baru (bash -n + uji snippet python inline secara terpisah; perbaiki quoting nested "datetime" jika error), lalu commit + push → Streamlit Cloud auto-redeploy.
2. Backfill R2 manual: .venv/bin/python -c "import r2_client; r2_client.upload_arsip('Arsip_Data_Harian/screener_2026-11-04.csv','Arsip_Data_Harian/screener_2026-11-04.csv')" (dan 11-03), lalu uji _arsip_hari_ini fallback: hapus sementara arsip lokal dari path uji (jangan hapus asli — pakai base_dir temp dengan cache .r2_*) dan pastikan muat_open_state() menghasilkan state; restart Streamlit lokal (pkill + ./jaga_web.sh) dan minta user cek https://minhaz0305.streamlit.app/ setelah redeploy.
Relevant Files
- /home/kaltaraid/Documents/SAHAM-SCREENING/sidang_lib.py: hitung_rumus() v6.1 + helper baru _arsip_hari_ini(), muat_open_state(), muat_rebound_state(), muat_skor_pembekal() (fallback R2, baru saja diedit).
- /home/kaltaraid/Documents/SAHAM-SCREENING/app.py: PART 12 (baris ~1883–2030) blok rumus v6.1 identik + VERSI_SIDANG = "v6.1" (baris 1885), label dropdown (2010), kenapa_lolos (baris 2963–2973).
- /home/kaltaraid/Documents/SAHAM-SCREENING/jalankan_bot.sh: blok R2 upload baru (arsip hari ini + kemarin) — baru diedit, belum tervalidasi.
- /home/kaltaraid/Documents/SAHAM-SCREENING/r2_client.py: upload_arsip(local, object_name), download_arsip(object_name, local), list_arsip() (prefix Arsip_Data_Harian/), kredensial via env/r2_config.json/streamlit secrets.
- /home/kaltaraid/Documents/SAHAM-SCREENING/jaga_web.sh + crontab (@reboot + */5): penjaga Streamlit port 8501.
- /home/kaltaraid/Documents/SAHAM-SCREENING/Arsip_Data_Harian/screener_2026-11-0{2,3,4}.csv: arsip lokal untuk backtest & state intraday.
- /home/kaltaraid/Documents/SAHAM-SCREENING/compact_saham_screeningt.md: state harian (sudah diupdate sampai v6.1, belum memuat temuan root-cause cloud).
- /home/kaltaraid/Documents/DATA-CENTER/feed/arsip/screener_*.csv: arsip producer (sumber backtest).
- /home/kaltaraid/Documents/WEB-SCREENING/: proyek TERPISAH (Railway/FastAPI down) — jangan digabung dengan SAHAM-SCREENING.