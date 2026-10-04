# PROMPT OPENCODE FIX — BRIDGE ROBUS + JUAL TP/CL OTOMATIS

## BAGIAN 0 — CARA PAKAI
1. Baca file ini seluruhnya. Kerja di branch `fix/bridge-tpcl`. JANGAN merge ke main.
2. Protokol tanya = KOTAK-SURAT: jika buntu, tulis `TANYA_OPENCODE.md` lalu BERHENTI.
3. JANGAN jalankan reset_porto.py. JANGAN sentuh secrets. Akhiri laporan BAGIAN 5.

## BAGIAN 1 — KONTEKS
- `jembatan_opencode.py` = bridge v2 dual-channel (TANYA->Telegram, balasan angka->tmux).
  Gejala saat ini: HTTPError 409 (dua instance polling token sama) dan proses mudah mati
  oleh sinyal terminal.
- `bot_simulator.py` FASE A = penjual otomatis (TP/CL/square-off/suspend), dipanggil cron
  tiap 5 menit via `jalankan_bot.sh`.
- INVARIANT: aturan "beli hari ini tahan" HANYA berlaku untuk square-off sore;
  TP/CL WAJIB menjual kapan pun tersentuh selama jam bursa, meski posisi dibeli hari ini.
- Keluhan pemilik: posisi menyentuh TP/CL di pagi hari tetapi TIDAK dijual otomatis.

## BAGIAN 2 — TUJUAN
A. Bridge robust: satu instance, tahan 409, tidak mati oleh Ctrl+C terminal.
B. Temukan AKAR PENYEBAB TP/CL tidak menjual, lalu perbaiki.

## BAGIAN 3 — SPESIFIKASI
### 3.1 Bridge
- Tambah lock file (fcntl.flock) di awal main(); instance kedua wajib keluar sendiri
  dengan log "instance lain aktif".
- Pada HTTPError 409: tunggu 5s, retry; jangan langsung backoff panjang; jangan keluar.
- Update OPERASIONAL_OPENCODE.md: jalankan bridge via
  `setsid nohup ./.venv/bin/python jembatan_opencode.py > logs/bridge_v2.log 2>&1 &`
  agar kebal Ctrl+C terminal; SIGTERM tetap untuk shutdown mulus.
- Verifikasi: start dua instance bersamaan -> yang kedua keluar sendiri; log ber-timestamp.
### 3.2 TP/CL
- Inspeksi: FASE A di bot_simulator.py, blok if/elif di jalankan_bot.sh, dan bot.log
  pagi ini (grep TAKE_PROFIT/CUT_LOSS/"tidur"/error).
- Periksa kandidat akar penyebab: (a) kondisi tanggal/aturan tahan ikut menahan TP/CL;
  (b) deteksi jam bursa membuat bot tidur di pagi hari; (c) Target_TP/Target_CL terbaca
  string sehingga perbandingan numerik gagal; (d) harga yang dipakai bukan harga terbaru;
  (e) jendela if/elif melewatkan pemanggilan bot_simulator.
- Perbaiki sehingga tiap siklus jam bursa: harga >= Target_TP -> jual TAKE_PROFIT;
  harga <= Target_CL -> jual CUT_LOSS; tanpa pengecualian tanggal beli.
- Buat tes terisolasi di /tmp (data sintetis, TIDAK menyentuh Database/) yang membuktikan
  posisi dengan harga melewati TP benar-benar terjual.
- JANGAN ubah: mirror R2, auto-save git, stempel sinyal, logika suspend, FASE B.

## BAGIAN 4 — KRITERIA SELESAI
1. Dua instance bridge -> hanya satu hidup; 409 tidak mematikan proses.
2. Tes terisolasi TP/CL lolos; akar penyebab tertulis eksplisit di laporan.
3. Diff hanya: jembatan_opencode.py, bot_simulator.py, OPERASIONAL_OPENCODE.md.

## BAGIAN 5 — LAPORAN
1. Akar penyebab TP/CL tidak menjual + baris kode terkait.
2. Ringkasan perubahan bridge + bukti uji dua instance.
3. git diff main...HEAD --stat + risiko + rollback.
4. Catatan pemilik: cara menjalankan bridge yang benar pasca-fix.

## BAGIAN 6 — LARANGAN
JANGAN ubah skrip produksi lain; JANGAN reset; JANGAN merge main; JANGAN tambah
dependensi; JANGAN hapus fitur/log/pesan; JANGAN cetak secrets.