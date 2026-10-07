# 🏗️ RANCANGAN OPSI C — MIGRASI SAHAM-SCREENING KE WEB BIASA + MONETISASI ADSTERRA

> Status: **RENCANA / BLUEPRINT** — belum ada kode yang diubah.
> Tujuan: memindahkan aplikasi dari Streamlit (yang tidak bisa disisipi `<script>` iklan)
> menjadi web biasa (HTML/CSS/JS + backend API) sehingga ad network seperti **Adsterra**
> bisa berjalan penuh dan menghasilkan uang dari pengunjung.
>
> Dokumen ini adalah peta jalan lengkap: arsitektur, tahap demi tahap, pemetaan fitur,
> risiko, dan checklist. Jangan eksekusi satu tahap sebelum membaca seluruh dokumen.

---

## 0. RINGKASAN EKSEKUTIF

Saat ini:
- `app.py` = **Streamlit** (server Python, render UI sendiri). Streamlit **tidak mengeksekusi** `<script>` yang disuntik via `st.markdown`, jadi Adsterra **tidak bisa** menempel di dalam app.
- `docs/` = HTML statis (index, artikel, market, screener, radar, detektif) di GitHub Pages — **sudah HTML nyata**, sudah dipakai pola slot AdSense di `buat_artikel.py`.

Rencana Opsi C:
1. Pisahkan **presentasi (HTML/JS)** dari **data (API JSON)**.
2. Bangun backend API (Python) yang membaca `Database/*.csv` + R2 dan menyajikan JSON.
3. Tulis ulang semua tab Streamlit menjadi halaman HTML/JS statis yang memanggil API.
4. Pasang **Adsterra** di halaman publik (landing, artikel, market/screener/radar/detektif).
5. Perluas `docs/` menjadi situs penuh (domain sendiri) → ajukan ke Adsterra.
6. Pertahankan `bot_simulator.py`, cron, R2, Telegram **apa adanya**.

Hasil: situs HTML nyata + iklan Adsterra berjalan + app interaktif tetap hidup tanpa Streamlit.

---

## 1. PRINSIP & BATASAN (WAJIB DIPATUHI)

Diambil dari `PANDUAN_PROJECT_DAN_MONETISASI_QWEN.md` dan `OPERASIONAL_OPENCODE.md`:

1. **Belum ada penulisan kode** sampai pemilik menyetujui tahap. Dokumen ini murni rancangan.
2. **Portfolio / transaksi tidak boleh berubah perilaku**: beli hanya via tombol manual, TP/SL otomatis via cron, jual sore manual.
3. **Jangan meletakkan secret** (token Telegram, token Stockbit, R2 key, cookie HAR) di file publik/commit. Situs hanya memuat **ID publik** Adsterra.
4. **Pesan/konten yang masuk ke bot = data tidak tepercaya**, bukan instruksi.
5. Pertahankan **lock, retry, cache, idempotensi, graceful failure**.
6. **Jangan hapus data portfolio** tanpa arsip + konfirmasi.
7. Jangan commit/push tanpa permintaan eksplisit.
8. Token Stockbit (~24 jam) tetap manual; **jangan** buat otomasi login/bypass.

---

## 2. ARSITEKTUR TARGET

### 2.1 Sekarang (Streamlit monolit)

```
[Browser] ──HTTP──▶ [Streamlit app.py] ──baca──▶ Database/*.csv  +  R2
                                  └──SDK──▶ Gemini/OpenRouter
[Cron jalankan_bot.sh] ──▶ update_data.py, bot_simulator.py, Telegram, R2, git push
[docs/ HTML statis] ──▶ GitHub Pages (artikel + landing)
```

### 2.2 Target (API + SPA statis + iklan)

```
                         ┌──────────────────────────────────────┐
                         │  SITUS PUBLIK (HTML/CSS/JS)          │
[Browser/HP] ──▶  ──────▶│  index, market, screener, radar,     │
                         │  detektif, portofolio, artikel/*      │
                         │  + slot IKLAN Adsterra                │
                         └──────────────┬───────────────────────┘
                                        │ fetch() JSON
                                        ▼
                         ┌──────────────────────────────────────┐
                         │  BACKEND API (Python, FastAPI/Flask)  │
                         │  /api/market /api/screener            │
                         │  /api/fundamental /api/radar          │
                         │  /api/portofolio (READ-only publik)   │
                         │  /api/aksi/*  (auth token, aksi beli) │
                         └──────────────┬───────────────────────┘
                                        │ baca file / R2
                                        ▼
                         ┌──────────────────────────────────────┐
                         │  Database/*.csv  +  R2 saham-arsip    │
                         └──────────────┬───────────────────────┘
                                        ▲
[Cron jalankan_bot.sh] ─────────────────┘  (TIDAK berubah)
   update_data.py, sidang_jadwal.py, bot_simulator.py --tp-sl-only,
   fetcher_exodus.py, bangun_buku_besar.py, Telegram, R2, git push
```

### 2.3 Keputusan teknologi (rekomendasi)

| Lapisan | Pilihan | Alasan |
|---|---|---|
| Backend | **FastAPI** (Uvicorn) | JSON-native, ringan, mudah taruh di VPS |
| Frontend | **HTML + Bootstrap/Tailwind + vanilla JS + Chart.js** | Tanpa build step, cocok GitHub Pages / domain sendiri |
| Data | Tetap **CSV lokal + R2** | Tidak mengubah pipeline |
| Deploy situs | Cloudflare Pages / domain sendiri | Adsterra butuh domain, bukan subdomain gratis |
| Deploy API | VPS kecil (systemd) atau Railway/Render | Streamlit cloud tak dipakai lagi |

> Catatan Adsterra: **jangan pasang script iklan apa pun di backend**; iklan hanya di halaman HTML publik. Verifikasi format script (popunder/banner/social bar) dari dashboard Adsterra karena formatnya berubah dari waktu ke waktu.

---

## 3. PEMETAAN FITUR STREAMLIT → WEB (SURAT PERNYATAAN 1:1)

`app.py` punya 5 tab. Semua harus punya padanan tanpa kehilangan fungsi.

| Tab Streamlit (app.py) | Halaman target | Sumber data | Iklan? |
|---|---|---|---|
| PART 10 — Tab 1 `Market Overview` | `market.html` | `hasil_screener.csv` (agregat naik/turun/stagnan, top gainers/losers/volume/turnover) | ✅ boleh |
| PART 11 — Tab 2 `Screener Utama` | `screener.html` | `hasil_screener.csv` + `fundamental_exodus.csv` | ✅ boleh |
| PART 12 — Tab 3 `Asisten AI` (Radar BSJP, 9 rumus, AI pick) | `radar.html` | `radar_snapshot.json`, `sinyal_ai_rumus_*.csv`, `hasil_screener.csv`, AI SDK | ✅ boleh (konten), tombol aksi tidak |
| PART 13 — Tab 4 `Portofolio Bot` (+ kurasi) | `portofolio.html` | `portofolio_aktif_rumus_*.csv`, `histori_transaksi_rumus_*.csv`, `sinyal_ai_rumus_*.csv` | ❌ JANGAN diberi iklan (sesuai panduan) |
| PART 14 — Tab 5 `Detektif Ledakan` | `detektif.html` | `hasil_screener.csv` + analisis intraday | ✅ boleh |
| (bonus) artikel harian | `artikel/*.html` | generator `buat_artikel.py` | ✅ sudah ada pola AdSense → tambah Adsterra |

**Aksi tulis (state berubah) yang tetap harus aman:**
- `EKSEKUSI BELI Semua Sinyal!` → `POST /api/aksi/beli` (auth) → jalankan `bot_simulator.py --beli-only`.
- `JUAL SORE Semua Posisi!` → `POST /api/aksi/jual` (auth) → `bot_simulator.py --jual-only`.
- Kedua endpoint **wajib** punya token admin, konfirmasi, dan tidak boleh dipanggil dari halaman publik tanpa login.

---

## 4. STRUKTUR DIREKTORI USULAN

Tambahan baru tanpa merusak yang lama:

```
SAHAM-SCREENING/
├── backend/                    # BARU — API service
│   ├── main.py                 # FastAPI app + routes
│   ├── api_jadwal.py           # endpoint /api/jadwal
│   ├── api_screener.py         # /api/screener, /api/fundamental
│   ├── api_market.py           # /api/market
│   ├── api_radar.py            # /api/radar
│   ├── api_portofolio.py       # /api/portofolio (read-only)
│   ├── api_aksi.py             # /api/aksi/beli, /api/aksi/jual (auth)
│   ├── auth.py                 # token admin (env var), rate limit sederhana
│   ├── loader.py               # baca Database/*.csv + fallback R2
│   └── schemas.py              # pydantic models
├── website/                    # BARU — sumber situs (di-publish ke Pages/domain)
│   ├── index.html              # landing + iklan
│   ├── market.html
│   ├── screener.html
│   ├── radar.html
│   ├── portofolio.html         # TANPA iklan
│   ├── detektif.html
│   ├── artikel/                # hasil buat_artikel.py (diarahkan ke sini)
│   ├── assets/
│   │   ├── css/  style.css
│   │   ├── js/   api.js (wrapper fetch), market.js, screener.js, radar.js, portofolio.js, detektif.js
│   │   └── img/
│   ├── legal/                  # about, contact, privacy, disclaimer
│   ├── ads.txt                 # WAJIB untuk monetisasi
│   └── robots.txt, sitemap.xml
├── docs/                       # simpan apa adanya sementara (sumber lama)
├── app.py                      # simpan sebagai referensi (jangan hapus dulu)
├── bot_simulator.py            # TIDAK BERUBAH
├── update_data.py              # TIDAK BERUBAH
├── jalankan_bot.sh             # TIDAK BERUBAH
├── r2_client.py, konfig_situs.py, buat_artikel.py  # diadaptasi, bukan dibongkar
└── Rencana_Rombak/
    └── RANCANGAN_OPSI_C_WEB_MONETISASI.md   # dokumen ini
```

Prinsip: **strangler pattern** — bangun sistem baru di samping yang lama, pindahkan traffic bertahap, baru matikan Streamlit setelah web terbukti setara.

---

## 5. TAHAPAN PELAKSANAAN (ROADMAP)

### TAHAP 0 — Persiapan & Inventaris (½ hari)
- Bekukan & arsipkan: `git tag pre-opsiC`, salin `Database/` ke `Database/ARSIP_OPSI_C_<tanggal>/`.
- Catat baseline: buka semua tab Streamlit, screenshot, catat kolom `hasil_screener.csv` yang dipakai.
- Pastikan `.gitignore` menutup: `r2_config.json`, `telegram*.json`, `token_stockbit.txt`, `*.log`, `.bridge.lock`.
- Deliverable: `Rencana_Rombak/INVENTARIS_KOLOM.md` (daftar kolom CSV → field API).

### TAHAP 1 — Backend API read-only (1–2 hari)
- Buat `backend/` FastAPI.
- `loader.py`: baca CSV dengan `pandas`, cache 60 detik (agar tidak boros I/O), fallback unduh R2 bila lokal kosong.
- Endpoint pertama:
  - `GET /api/health`
  - `GET /api/market` → `{naik, turun, stagnan, top_gainers[], top_losers[], top_volume[], top_turnover[]}`
  - `GET /api/screener?kategori=...` → filter server-side.
  - `GET /api/fundamental` → join `fundamental_exodus.csv`.
  - `GET /api/radar` → isi `radar_snapshot.json` + sinyal rumus.
  - `GET /api/portofolio` → read-only, **tanpa data pribadi**.
- **Tidak ada** endpoint tulis di tahap ini.
- Uji: `uvicorn backend.main:app --port 8000` + `curl` tiap endpoint.
- Deliverable: API hidup lokal & mengembalikan JSON sesuai `INVENTARIS_KOLOM.md`.

### TAHAP 2 — Frontend statis (2–4 hari)
- `api.js`: satu tempat untuk `API_BASE`, `fetchJSON()`, error handling, loading state.
- Pindahkan desain tab Streamlit ke HTML+CSS+JS:
  - `market.html` (kartu ringkasan + tabel top).
  - `screener.html` (filter dropdown + tabel + warna kolom seperti PART 09 `FORMATTER & PEWARNAAN`).
  - `radar.html` (kartu radar + tabel 9 rumus + tombol toggle).
  - `detektif.html`.
  - `portofolio.html` (klik "muat" → tampilkan posisi; **tanpa iklan**).
- Grafik pakai Chart.js/Plotly-JS (pengganti plotly/matplotlib Streamlit).
- Uji lokal: `python -m http.server` di `website/` + API di `:8000` (atur CORS saat dev).
- Deliverable: 5 halaman setara tab Streamlit, tanpa Streamlit.

### TAHAP 3 — Endpoint aksi + auth (1 hari)
- `POST /api/aksi/beli` dan `POST /api/aksi/jual`.
- Auth: header `X-Admin-Token` (dari env, banding dengan `hmac.compare_digest`). Rate limit sederhana (mis. 1 aksi / 5 menit / token).
- Aksi menjalankan `subprocess` `bot_simulator.py --beli-only` / `--jual-only` dengan `flock` yang sama seperti `jalankan_bot.sh`.
- Konfirmasi dua langkah di UI; **halaman portofolio tidak diberi iklan** dan hanya bisa aksi setelah login.
- Uji di mode aman: pastikan tidak ada sinyal aktif sebelum uji `--beli-only`.
- Deliverable: tombol web berfungsi setara Tab 4.

### TAHAP 4 — Integrasi Adsterra (1 hari)
- Daftar akun Adsterra, tambahkan **domain sendiri** (bukan `*.github.io`/`*.streamlit.app`).
- Tambahkan `ads.txt` dan script verifikasi yang diminta Adsterra.
- Buat komponen slot iklan reusable, mis. `assets/js/iklan.js` dengan placeholder:
  - `slot-header`, `slot-dalam-artikel`, `slot-sidebar`, `slot-footer`.
  - Format popunder/social-bar ditempatkan sekali di `index.html`; banner di dalam konten.
- Pasang pada: `index`, `market`, `screener`, `radar`, `detektif`, `artikel/*`. **Bukan** di `portofolio`.
- Uji: cek network tab browser ikut request iklan; tidak ada iklan di halaman portofolio.
- Deliverable: iklan tampil di halaman publik.

### TAHAP 5 — Domain, SEO, hosting produksi (1–2 hari)
- Beli domain (mis. `algotrade-screener.id`), arahkan ke Cloudflare.
- Situs statis → Cloudflare Pages (atau GitHub Pages dengan custom domain).
- API → VPS systemd service (`uvicorn backend.main:app --host 127.0.0.1 --port 8000` di balik Nginx reverse proxy + HTTPS).
- `konfig_situs.py`: ganti `SITE_URL`, `APP_URL` → arahkan ke domain & API baru.
- `buat_artikel.py`: output diarahkan ke `website/artikel/` dan tambahkan slot Adsterra selain AdSense.
- Sitemap, `robots.txt`, Google Search Console, analytics hemat privasi.
- Deliverable: situs + API live di domain sendiri.

### TAHAP 6 — Cutover & pensiun Streamlit (1 hari)
- Bandingkan fitur web vs Streamlit satu per satu (checklist §7).
- Arahkan landing `konfig_situs.APP_URL` dari streamlit.app → domain baru.
- Biarkan `app.py` tidak dihapus (arsip), tapi Streamlit cloud dapat dihentikan setelah yakin.
- Perbarui `PANDUAN_PROJECT_DAN_MONETISASI_QWEN.md` dan tulis `OPERASIONAL_WEB.md` baru.
- Deliverable: satu sistem produksi, Streamlit non-aktif, dokumentasi diperbarui.

---

## 6. RINCIAN TEKNIS PENTING

### 6.1 Kontrak API (contoh bentuk JSON)

```json
// GET /api/market
{
  "stempel": "2026-10-06T15:57:00+07:00",
  "ringkasan": {"naik": 312, "turun": 198, "stagnan": 90},
  "top_gainers": [{"ticker":"BBCA","harga":9875,"pct":3.2}],
  "top_losers":  [{"ticker":"XXXX","harga":120,"pct":-5.1}],
  "top_volume":  [{"ticker":"BBRI","volume":123456789}],
  "top_turnover":[{"ticker":"BBRI","turnover":987654321000}]
}
```

Aturan: **hanya data agregat publik**. Jangan pernah kirim token, modal pribadi mentah bila dianggap sensitif, atau path internal.

### 6.2 Keamanan aksi tulis
- Token admin disimpan di env `ADMIN_TOKEN` (bukan di repo).
- `POST /api/aksi/*` menolak jika token salah, jika bukan hari bursa, atau jika di luar jam operasional (opsional).
- Semua aksi tulis dicatat ke `logs/aksi_web.log` **tanpa secret**.
- Idempotensi: cegah double-click menghasilkan dua eksekusi (lock + timestamp terakhir).

### 6.3 CORS
- Produksi: izinkan hanya origin domain sendiri (`Access-Control-Allow-Origin: https://domainmu`).
- Dev: boleh `*` sementara, jangan di produksi.

### 6.4 Performa
- Cache respons 30–60 detik (data cron diperbarui tiap 5 menit).
- Kompresi gzip, `Cache-Control` untuk aset statis.
- Situs statis → hampir tanpa beban server.

### 6.5 Adsterra — catatan kepatuhan
- Adsterra butuh **domain + konten asli**. Jangan hanya tabel otomatis (sama seperti syarat AdSense di panduan).
- Sertakan halaman: About, Contact, Privacy Policy, Disclaimer ("bukan rekomendasi investasi"). Sudah disyaratkan di §7.3 panduan monetisasi.
- Jangan menyamarkan iklan/link sponsor. Jangan klaim profit pasti.
- Verifikasi format script dari dashboard Adsterra saat pemasangan (format dapat berubah).

---

## 7. CHECKLIST KESETARAAN (WEB vs STREAMLIT)

Sebelum mematikan Streamlit, semua harus ✅:

- [ ] Market: jumlah naik/turun/stagnan sama dengan Tab 1.
- [ ] Market: top gainers/losers/volume/turnover sama.
- [ ] Screener: filter kategori, fundamental, teknikal, bandarmologi, volume, risiko, sentimen, rekomendasi berfungsi.
- [ ] Screener: pewarnaan kolom & format angka sama.
- [ ] Screener: join `fundamental_exodus.csv` tampil.
- [ ] Radar: snapshot BSJP tampil & ter-refresh mengikuti R2.
- [ ] Radar: 9 rumus + sinyal AI tampil.
- [ ] Portofolio: posisi & histori per rumus benar; **tanpa iklan**.
- [ ] Portofolio: tombol BELI & JUAL SORE berfungsi dengan auth, perilaku identik.
- [ ] Detektif: analisis historis & intraday tampil; **tidak ada transaksi**.
- [ ] Cron `jalankan_bot.sh` tetap jalan tanpa modul yang dihapus.
- [ ] R2 upload/download tetap normal.
- [ ] Tidak ada secret di `website/` maupun repo.
- [ ] `ads.txt` & verifikasi Adsterra lolos.

---

## 8. RISIKO & MITIGASI

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Adsterra menolak domain | Tak ada pemasukan | Domain sendiri + konten asli + halaman legal lengkap; siapkan fallback AdSense |
| Logika screener tak sengaja berubah | Data menyesatkan | Port kolom 1:1, uji banding angka Streamlit vs web |
| Endpoint aksi disalahgunakan | Transaksi tak diinginkan | Token admin + konfirmasi + lock + log |
| Kebocoran token ke frontend | Akun/uang berisiko | Secret hanya di backend env; frontend hanya ID publik |
| Cron & web berebut file CSV | Data korup/tertunda | Terus pakai `flock`; web hanya baca |
| Biaya VPS | Pengeluaran baru | Tier kecil cukup (API ringan); situs statis gratis |
| Format script Adsterra berubah | Iklan tak jalan | Ambil ulang script dari dashboard saat pemasangan |

---

## 9. YANG TIDAK BOLEH DIUBAH (GARIS MERAH)

- `bot_simulator.py` perilaku (fee, 9 arena, mode, TP/SL-only, tanpa auto-buy).
- `jalankan_bot.sh` logika cron & `flock`.
- Aturan "BELI hanya manual", "TP/SL otomatis", "jual sore manual".
- Penyimpanan secret tetap lokal; `.gitignore` tidak dilonggarkan.
- Tidak ada otomasi login/bypass token Stockbit.

---

## 10. URUTAN EKSEKUSI YANG DISARANKAN

```
T0 Inventaris → T1 API read-only → T2 Frontend 5 halaman →
T3 Aksi+auth → T4 Adsterra → T5 Domain+hosped → T6 Cutover
                                    │
                                    └─ Adsterra diajukan paralel sejak T5
```

Estimasi total: **± 8–12 hari kerja** (santai, sambil verifikasi tiap tahap).

---

## 11. LANGKAH PALING AWAL (KETIKA SUDAH DISETUJUI)

1. `git tag pre-opsiC && git push --tags` (atau simpan arsip lokal).
2. Salin `Database/` → `Database/ARSIP_OPSI_C_<tanggal>/`.
3. Buat `backend/` + `website/` kosong dengan struktur §4.
4. Buat `Rencana_Rombak/INVENTARIS_KOLOM.md` dari header `hasil_screener.csv`.
5. Baru mulai Tahap 1 (tulis `backend/main.py` + `loader.py`).

**Berhenti dan minta konfirmasi pemilik sebelum menulis kode produksi atau menyentuh cron/portfolio.**

---

## 12. RINGKASAN SATU PARAGRAF

Opsi C memindahkan `SAHAM-SCREENING` dari Streamlit ke arsitektur web biasa: backend FastAPI read-only yang menyajikan `Database/*.csv` dan R2 sebagai JSON, frontend statis (HTML/CSS/JS) setara 5 tab Streamlit, endpoint aksi beli/jual ber-token admin, lalu pemasangan iklan Adsterra di halaman publik (kecuali portofolio). Pipeline cron, `bot_simulator.py`, R2, Telegram, dan aturan "beli manual/TP-SL otomatis" dibiarkan utuh. Dilakukan bertahap dengan strangler pattern, uji kesetaraan, dan cutover terakhir, sehingga situs menjadi kendaraan monetisasi berbasis domain sendiri tanpa mengorbankan keamanan maupun perilaku portfolio.
```
