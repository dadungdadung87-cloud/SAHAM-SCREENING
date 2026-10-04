# PROMPT OPENCODE v5.2 + BRIDGE TELEGRAM — PROYEK SAHAM-SCREENING

## BAGIAN 0 — CARA PAKAI & PROTOKOL TANYA (SESI INI)
1. Baca file ini SELURUHNYA sebelum menulis kode.
2. Kerja di branch `feat/v52-bridge`. JANGAN merge ke main.
3. PROTOKOL TANYA SESI INI = KOTAK-SURAT: jika buntu/ambigu, JANGAN tampilkan dialog
   interaktif. Tulis pertanyaan + opsi bernomor ke `TANYA_OPENCODE.md`, lalu BERHENTI
   total. Pemilik menjawab lewat file/Telegram dan melanjutkan sesi baru.
4. JANGAN ubah/hapus file prompt ini. JANGAN jalankan reset_porto.py.
5. Akhiri dengan laporan BAGIAN 7.

## BAGIAN 1 — KONTEKS
- Repo: web Streamlit `app.py` (root) + skrip cron Python; data di Cloudflare R2.
- Rumus screener hidup DUPLIKAT: `app.py` (PART 12) dan `sidang_lib.py` (`hitung_rumus`).
  Setiap perubahan rumus WAJIB identik di keduanya + naikkan `VERSI_SIDANG`.
- Bridge Telegram: `jembatan_opencode.py` (v1 kotak-surat, sedang jalan via nohup) +
  config `telegram_opencode.json` (untracked, chmod 600). File tanya/jawab:
  `TANYA_OPENCODE.md`, `JAWAB_OPENCODE.md` di akar repo.
- Invariant: aturan jual/suspend/square-off/mirror/stempel TIDAK boleh berubah.

## BAGIAN 2 — TUJUAN
A. Rumus v5.2: longgarkan R4, R7, R9 agar kandidat tidak tipis, tanpa buang disiplin
   closing (vwap) dan tanpa batas change.
B. Upgrade `jembatan_opencode.py` ke v2 DUAL-CHANNEL + tulis panduan operasional.
C. Verifikasi syntax + jumlah kandidat + laporan.

## BAGIAN 3 — SPESIFIKASI EKSEKUSI
### 3.1 RUMUS v5.2 (identik di app.py PART12 & sidang_lib.hitung_rumus; VERSI_SIDANG="v5.2")
Gunakan definisi bantu yang SUDAH ada (vwap_ok, vwap_kuat, akumulasi_pro).
- R4: ((MA Cross == 'Golden Cross') ATAU (MACD in ['Strong Bullish','Bullish MACD']))
      & (Vol Breakout == 'Tembus MA20') & (MA Signal == 'Uptrend') & vwap_kuat
      & ((Tekanan Bandar == 'Dominan Beli (Hajar Kanan)') ATAU akumulasi_pro)
- R7: (Prediksi Machine Learning == '🔥 ANOMALI BANDAR (Siap Ledakan)') & vwap_kuat
      & ((Status Stochastic in ['Oversold (Jenuh Jual - Peluang)','Golden Cross (Awal Bullish)'])
         ATAU (Tekanan Bandar == 'Dominan Beli (Hajar Kanan)'))
- R9: (MACD in ['Strong Bullish','Bullish MACD']) & (Momentum == 'Positif') & vwap_ok
      & ((Risk/Reward Ratio in ['Sangat Menarik (> 1:3)','Ideal (1:2)'])
         ATAU (Posisi Entry == 'Dekat Support (Low Risk)'))
- R1,R2,R3,R5,R6,R8: TANPA perubahan.
- Selaraskan dict `kenapa_lolos` (Tab 5) agar diagnosis cocok v5.2.
### 3.2 BRIDGE v2 (timpa jembatan_opencode.py; perilaku WAJIB):
- Baca config telegram_opencode.json (BOT_TOKEN, CHAT_ID, TMUX_SESSION).
- Jika CHAT_ID kosong/0: bind ke chat pertama yang mengirim pesan apa pun, simpan ke config.
- Loop: jika TANYA_OPENCODE.md ada & hash baru -> kirim isinya ke Telegram (escape HTML),
  tandai hash. Jika TANYA hilang tapi hash ada -> kirim "sudah dijawab di laptop", hapus hash.
- Long-poll getUpdates; balasan berupa ANGKA saat ada pertanyaan tertunda ->
  suntik keystroke ke tmux session: (N-1) kali "Down" lalu "Enter". Balasan bukan angka ->
  balas "balas dengan angka opsi".
- Sertakan graceful shutdown, retry/backoff ringan, log tanpa secrets.
### 3.3 Tulis OPERASIONAL_OPENCODE.md (file baru) berisi panduan SESI DEPAN:
  cara opencode bertanya DUAL (tampilkan dialog normal + tulis TANYA_OPENCODE.md + tunggu),
  cara bridge v2 menyuntik jawaban dari Telegram, cara pemilik menjawab dari laptop/HP,
  dan kewajiban menjalankan opencode di dalam `tmux new -s oc`.
### 3.4 VERIFIKASI: syntax app.py & sidang_lib.py; jalankan hitung_rumus pada
  Database/hasil_screener.csv dan laporkan jumlah kandidat per rumus (R4/R7/R9 harus
  NAIK vs v5.1: {4:2, 7:2, 9:1}); streamlit headless HTTP 200; import jembatan_opencode
  tanpa error.

## BAGIAN 4 — KRITERIA SELESAI
1. R4/R7/R9 kandidat meningkat; R6 tetap terisi; tidak ada rumus jadi kosong.
2. Rumus v5.2 identik app.py vs sidang_lib (buktikan ticker-set sama).
3. jembatan_opencode.py v2 memenuhi semua perilaku 3.2; OPERASIONAL_OPENCODE.md ada.
4. Diff hanya: app.py, sidang_lib.py, jembatan_opencode.py, OPERASIONAL_OPENCODE.md.

## BAGIAN 5 — LARANGAN
1. JANGAN ubah skrip produksi lain (bot_simulator FASE A/jual, update_data, r2_client,
   sidang_jadwal, kirim_telegram*, jalankan_bot.sh).
2. JANGAN pindah/rename folder data; JANGAN jalankan reset; JANGAN sentuh secrets.
3. JANGAN tambah dependensi; JANGAN merge main; JANGAN hapus fitur/tombol/tab.
4. JANGAN kirim pesan Telegram sungguhan selain ke chat ter-bind; JANGAN log token.

## BAGIAN 6 — BACKLOG (JANGAN DIEKSEKUSI)
Fase 2 (VM Oracle), Fase 3 (Spreadsheet etalase), UI polish, migrasi google.genai,
rapor winrate per Mode_Beli/Change_Beli.

## BAGIAN 7 — LAPORAN AKHIR
1. Tabel kandidat per rumus v5.1 vs v5.2.
2. Bukti identik app.py vs sidang_lib.
3. Ringkasan perilaku bridge v2 yang diimplementasi + cara uji.
4. git diff main...HEAD --stat + risiko + rollback.
5. Catatan untuk pemilik: "kirim /start ke bot, lalu balas satu pesan uji" agar loop hidup.