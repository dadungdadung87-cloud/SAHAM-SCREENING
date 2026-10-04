# PROMPT OPENCODE — FIX SQUARE-OFF TAHAN BELI HARI INI

## BAGIAN 0 — CARA PAKAI
1. Baca file ini seluruhnya. Kerja di branch `fix/squareoff-tahan-hari-ini`. JANGAN merge ke main.
2. Protokol tanya = KOTAK-SURAT: jika buntu, tulis `TANYA_OPENCODE.md` lalu BERHENTI.
3. JANGAN jalankan reset_porto.py (tugas pemilik). JANGAN sentuh secrets. Akhiri laporan BAGIAN 5.

## BAGIAN 1 — KONTEKS & AKAR MASALAH
- `bot_simulator.py` FASE A = mesin jual. Urutan cabang per posisi (setelah fix TP/CL kemarin):
  liquidate → square-off → TP → CL → tahan.
- BUG: kemarin logika "beli hari ini tahan" dihapus dari SEMUA jalur. Akibatnya square-off
  (open-ended, aktif saat jam >= 15:30) ikut menjual posisi yang BARU dibeli hari itu
  (contoh: beli 15:23 jadwal, jual 15:37 AUTO_SQUARE_OFF). Ini melanggar invariant BSJP:
  square-off hanya untuk posisi hari kemarin ke atas; posisi beli hari ini ditahan sampai besok.
- INVARIANT YANG BENAR:
  * TP/CL  -> jual kapan pun, TERMASUK posisi beli hari ini (JANGAN diberi gerbang tanggal).
  * Square-off -> jual HANYA jika tanggal_beli != hari_ini (beri gerbang tanggal).
  * Suspend -> jual paksa, tanpa gerbang tanggal.
  * Liquidate -> jual semua termasuk hari ini (perintah paksa pemilik), tanpa gerbang tanggal.
- JADWAL TIDAK BERUBAH: sidang 15:20-15:35, square-off tetap open-ended mulai 15:30.
  Perbaikan murni di logika FASE A, bukan di cron/jam.

## BAGIAN 2 — TUJUAN
Kembalikan gerbang "tahan beli hari ini" HANYA pada cabang square-off, tanpa menyentuh
cabang TP/CL/suspend/liquidate, tanpa mengubah file lain.

## BAGIAN 3 — SPESIFIKASI EKSEKUSI (HANYA bot_simulator.py)
3.1 Di fungsi jalankan_bot(), kembalikan baris yang kemarin dihapus:
        tanggal_hari_ini = now.strftime('%Y-%m-%d')
    (tepat setelah `now = ...` / sebelum `jam_sekarang`).
3.2 Di loop FASE A (for idx, posisi in df_porto.iterrows()), kembalikan:
        tgl_beli_saham = str(posisi['Tanggal_Beli']).split()[0]
3.3 Ubah HANYA kondisi cabang square-off menjadi ber-gerbang tanggal:
        if is_square_off_time and tgl_beli_saham != tanggal_hari_ini:
            terjual = True; status_jual = "AUTO_SQUARE_OFF 🧹"; harga_jual = harga_sekarang
    PASTIKAN cabang TP dan CL (elif berikutnya) TIDAK mengandung gerbang tanggal apa pun.
    PASTIKAN cabang liquidate & suspend tetap tanpa gerbang tanggal.
    Struktur akhir cabang yang benar:
        if liquidate:                         -> LIQUIDATE (jual semua)
        elif is_square_off_time and tgl!=hari -> AUTO_SQUARE_OFF (hanya posisi lama)
        elif harga >= Target_TP:              -> TAKE_PROFIT
        elif harga <= Target_CL:              -> CUT_LOSS
        else:                                 -> tahan (porto_baru)
3.4 JANGAN ubah file lain (jalankan_bot.sh, app.py, sidang_*, kirim_telegram*, r2_client,
    update_data, bangun_buku_besar). JANGAN ubah FASE B, mirror R2, auto-save, stempel sinyal.

## BAGIAN 4 — VERIFIKASI (WAJIB)
4.1 grep bukti di bot_simulator.py:
    - baris square-off mengandung "tgl_beli_saham != tanggal_hari_ini"
    - baris TAKE_PROFIT / CUT_LOSS TIDAK mengandung "tanggal_hari_ini"
    - "tanggal_hari_ini = now.strftime" ada tepat 1x; "tgl_beli_saham =" ada 1x
4.2 Tes terisolasi di /tmp (data sintetis, TIDAK menyentuh Database/), meniru branching 3.3,
    buktikan 4 kasus:
    (a) posisi hari ini + window square-off + harga netral  -> TAHAN
    (b) posisi hari ini + window square-off + harga >= TP    -> TAKE_PROFIT (bukan square-off)
    (c) posisi kemarin + window square-off + harga netral    -> AUTO_SQUARE_OFF
    (d) liquidate + posisi hari ini                           -> LIQUIDATE
4.3 streamlit run app.py --server.headless true -> HTTP 200 (regresi web nihil).
4.4 git diff main...HEAD --stat WAJIB hanya bot_simulator.py.

## BAGIAN 5 — LAPORAN
1. Kutip baris kondisi square-off sebelum vs sesudah + bukti grep 4.1.
2. Hasil 4 kasus tes 4.2 (PASS/FAIL per kasus).
3. git diff main...HEAD --stat + risiko + rollback.
4. Konfirmasi: tidak ada file lain yang berubah; TP/CL tetap jual kapan pun.

## BAGIAN 6 — LARANGAN
JANGAN ubah jadwal/cron; JANGAN reset; JANGAN merge main; JANGAN tambah dependensi;
JANGAN hapus fitur/log/pesan; JANGAN cetak secrets; JANGAN sentuh folder data.