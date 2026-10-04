# PROMPT MASTER UNTUK OPENCODE — PROYEK "SAHAM-SCREENING" (v2)

## BAGIAN 0 — CARA MEMAKAI
1. Baca BAGIAN 1 & BAGIAN 6 sebelum menulis kode.
2. Eksekusi HANYA BAGIAN 3. BAGIAN 7 = backlog, DILARANG disentuh.
3. Kerja di branch `feat/fase1-cache-rumus-v51`. JANGAN merge ke `main`.
4. Hasilkan laporan sesuai BAGIAN 8, lalu berhenti.

## BAGIAN 1 — KONTEKS SISTEM
- Web Streamlit: `app.py` di root (±2.000 baris, PART 01–14), deploy Streamlit Cloud.
- Data (hasil_screener, portofolio, histori, sinyal, snapshot JSON) di Cloudflare R2;
  web mengunduh per render → sumber lambatnya.
- Skrip produksi cron laptop: `jalankan_bot.sh`, `update_data.py`, `bot_simulator.py`,
  `sidang_lib.py`, `sidang_jadwal.py`, `sidang_sore.py`, `beli_jadwal.py`,
  `kirim_telegram.py`, `kirim_telegram_sore.py`, `bangun_buku_besar.py`,
  `r2_client.py`, `reset_porto.py`.
- Folder data: `Database/`, `Arsip_Data_Harian/`, `Buku_Besar/`, `logs/`.
- Invariant bisnis: beli=manual/jadwal; jual=otomatis (TP/CL/square-off/suspend);
  aturan "beli hari ini tahan sampai besok"; mirror R2; stempel sinyal anti-basi;
  9 arena independen.
- Rumus screener v5.0 hidup DUPLIKAT di `app.py` (PART 12) dan `sidang_lib.py`
  (fungsi `hitung_rumus`). SETIAP perubahan rumus WAJIB diterapkan di KEDUA file
  dengan kondisi identik, dan `VERSI_SIDANG` dinaikkan menjadi "v5.1" di keduanya.

## BAGIAN 2 — TUJUAN (4 PEKERJAAN)
A. Web instan: lapisan cache agar pindah tab tanpa loading.
B. Alokasi beli dinamis: seluruh kas arena terdeploy rata ke N sinyal, bukan
   pakem 20jt/saham yang menyisakan kas menganggur saat saldo > 100jt.
C. Rumus v5.1: perketat disiplin closing & ruang naik sesuai tabel BAGIAN 3.5.
D. Verifikasi reset portofolio (reset dieksekusi PEMILIK, lihat BAGIAN 3.0).

## BAGIAN 3 — SPESIFIKASI EKSEKUSI
### 3.0 PRASYARAT MANUAL (dilakukan PEMILIK di laptop, BUKAN oleh agent)
    `./.venv/bin/python reset_porto.py`
    `./.venv/bin/python -c "import r2_client; r2_client.upload_database(mirror=True)"`
    `git add -A Database/ && git commit -m "reset: lembar uji v5.1" && git push`
    Tugas agent HANYA memverifikasi pasca-merge: setiap
    `Database/portofolio_aktif_rumus_N.csv` kosong dan dashboard menampilkan
    kas Rp 100.000.000 per arena. JANGAN jalankan reset sendiri.
### 3.1 AUDIT LOADER (tanpa ubah kode): daftar semua titik unduh R2/baca CSV/JSON
    di `app.py` (pola: `download_arsip`, `download_database`, `pd.read_csv`,
    `json.load`, `muat_buku_besar`, `muat_arsip_harian`, `_sedot_porto_r2`).
### 3.2 LAPISAN CACHE: bungkus loader dengan
    `@st.cache_data(ttl=300, show_spinner=False)`; fungsi level modul; satu fungsi
    per sumber (market, portofolio/histori/sinyal per arena, snapshot pagi/sore,
    buku besar). Tambah tombol sidebar "🔄 Refresh Sekarang" →
    `st.cache_data.clear()`.
### 3.3 KOLOM RAMPING: konstanta daftar kolom per tab; setelah frame ter-cache,
    render pakai `df[kolom]`. JANGAN hapus kolom di sumber data.
### 3.4 CACHE RADAR: pembacaan cache_autopilot/sinyal/snapshot di Radar Live ikut
    ter-cache ttl 300 agar autorefresh tidak mengunduh per render.
### 3.5 RUMUS v5.1 (terapkan IDENTIK di `app.py` dan `sidang_lib.py`;
    naikkan `VERSI_SIDANG = "v5.1"` di kedua file):
    CATATAN PEMILIK: TIDAK ADA batas change dan TIDAK ADA penolakan saham ARA.
    Saham yang sudah naik tinggi tetap boleh lolos — ini keputusan sadar untuk
    mengukur kejujuran screening (direkam via kolom Change_Beli & log BELI-SAAT-ARA).
    R1: ganti vwap_ok → vwap_kuat; tambah Kondisi Supply tidak mengandung "Banjir".
    R2: TANPA perubahan.
    R3: TANPA perubahan.
    R4: tambah Tekanan Bandar == "Dominan Beli (Hajar Kanan)".
    R5: tambah (Tekanan Bandar == "Dominan Beli (Hajar Kanan)" ATAU
        Kekuatan A/D == "Akumulasi Pro (Smart Money)").
    R6: TANPA perubahan.
    R7: ganti vwap_ok → vwap_kuat.
    R8: TANPA perubahan.
    R9: tambah vwap_ok (tolak closing lembek).
    Definisi bantu:
      vwap_kuat   = Posisi VWAP == "Di Atas VWAP (Kuat)"
      vwap_ok     = Posisi VWAP != "Di Bawah VWAP (Lemah)"
      supply_banjir = kolom Kondisi Supply mengandung kata "Banjir"
### 3.6 ALOKASI BELI DINAMIS (HANYA di FASE B `bot_simulator.py`):
    Ganti pakem `alokasi = min(20_000_000, saldo)` dengan:
      sinyal_valid = sinyal lolos filter (stempel hari ini untuk mode jadwal,
                     belum dimiliki, ada di market, harga > 0)
      N = len(sinyal_valid); jika N == 0 lewati arena
      alokasi_rencana = saldo_sekarang / N
      untuk tiap sinyal:
          harga_per_lot = harga * 100 * (1 + FEE_BELI)
          lot = int(alokasi_rencana // harga_per_lot)
          lot = min(lot, int(saldo_tersisa // harga_per_lot))   # pagar saldo
          jika lot < 1: lewati sinyal ini
          beli seperti biasa dengan lot tersebut
    JANGAN ubah aturan jual, suspend, square-off, liquidate, mirror, auto-save.
### 3.7 VERIFIKASI & COMMIT: `streamlit run app.py --server.headless true` sehat;
    jalankan `sidang_jadwal.py` sekali untuk memastikan rumus v5.1 tidak error;
    `git diff main...HEAD --stat` hanya menampilkan `app.py`, `sidang_lib.py`,
    `bot_simulator.py`; commit per langkah `feat: ...`.

## BAGIAN 4 — KRITERIA SELESAI
1. Pindah tab instan setelah muat pertama; unduhan R2 ≤1x per file per 5 menit.
2. Simulasi: saldo 120jt dengan 5 sinyal → tiap saham ≈24jt (bukan 20jt + nganggur).
3. Rumus v5.1 aktif di web DAN cron (hasil sidang keduanya konsisten).
4. Portofolio terverifikasi kosong & kas 100jt per arena (pasca reset pemilik).
5. Semua fitur lama utuh; tidak ada file produksi lain yang berubah.

## BAGIAN 5 — UJI REGRESI WAJIB
- `bot_simulator.py --manual` di data terakhir: tidak error, log beli menampilkan
  lot hasil alokasi baru.
- Sidang v5.1: jumlah kandidat per rumus masuk akal (R6 tetap terisi, R8 boleh kosong).
- Web: tombol Eksekusi, Kurasi, Radar Live, autorefresh berfungsi.

## BAGIAN 6 — LARANGAN KERAS
1. JANGAN ubah skrip produksi selain yang diizinkan 3.6 (bot_simulator FASE B saja).
2. JANGAN pindahkan/rename isi folder data; JANGAN jalankan reset sendiri.
3. JANGAN sentuh secrets; JANGAN cetak isi secrets ke log/laporan.
4. JANGAN hapus fitur/tombol/tab/kolom tampilan/pesan log.
5. JANGAN tambah dependensi; JANGAN merge ke `main`; JANGAN sentuh BAGIAN 7.

## BAGIAN 7 — BACKLOG & KEPUTUSAN (DILARANG DIEKSEKUSI)
- SPREADSHEET: KEPUTUSAN FINAL = TIDAK migrasi penyimpanan ke Spreadsheet
  (kuota Apps Script & latensi Sheets kalah dari R2 yang egress-nya gratis).
  Spreadsheet hanya OPSIONAL di Fase 3 sebagai etalase baca + Sheet KONTROL
  (checkbox JEDA BELI); tidak pernah menjadi sumber kebenaran.
- FASE 2: pindahkan cron ke VM Oracle Cloud Free Tier agar laptop boleh mati.
- UI: design system, empty-state, branding (prompt agent visual terpisah).
- Telegram: alert real-time TP/CL, perintah balasan, opsi grup.
- Teknis: migrasi `google.generativeai` (deprecated) ke `google.genai`.
- Evaluasi: rapor winrate per Mode_Beli & per Change_Beli (ARA vs normal).

## BAGIAN 8 — FORMAT LAPORAN AKHIR
1. Tabel audit loader (fungsi → baris → cache ya/tidak).
2. Tabel perubahan rumus v5.0→v5.1 per file (app.py & sidang_lib.py) + bukti identik.
3. Bukti kriteria BAGIAN 4 & uji regresi BAGIAN 5.
4. `git diff main...HEAD --stat` + daftar risiko + cara rollback.
5. Konfirmasi tertulis: tiada larangan BAGIAN 6 yang dilanggar.