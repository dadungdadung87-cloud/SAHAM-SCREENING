#!/bin/bash

# ==========================================
# 🔒 FLOCK: cegah dua siklus bot berjalan bersamaan
# (pembunuh utama penyebab penjualan dobel/hilang)
# ==========================================
exec 200>/tmp/bot_simulator.lock
flock -n 200 || { echo "⏳ Siklus dilewati: bot sebelumnya masih berjalan."; exit 0; }

# Masuk ke folder repositori
cd /home/kaltaraid/Documents/SAHAM-SCREENING/ || exit 1

# ==========================================
#  P3K GIT: batalkan rebase/merge menggantung dari siklus sebelumnya
# ==========================================
git rebase --abort >/dev/null 2>&1
git merge --abort >/dev/null 2>&1

# ==========================================
# LANGKAH 1: TARIK DATA TERBARU DULU (sinyal AI dari web, dll)
# ==========================================
git pull --rebase origin main || git rebase --abort

echo "⏳ Memulai pembaruan data saham..."

# 2. Jalankan skrip Python WAJIB menggunakan .venv agar paket/modul terbaca
./.venv/bin/python update_data.py

# 3. JALANKAN BOT SIMULATOR (Menggunakan .venv juga)
./.venv/bin/python bot_simulator.py

# ==========================================
# FITUR SAPU OTOMATIS (MAX 50 HARI)
# ==========================================
find Arsip_Data_Harian/ -name "*.csv" -type f -mtime +50 -delete

echo "📤 Mengupload ke GitHub..."

# 4) COMMIT dulu — -A agar PENGHAPUSAN sinyal terbakar ikut tercatat
git add -A Database/
git commit -m "Auto-update data dan bot simulator (arsip via R2)" || echo "Tidak ada perubahan"

# 5) Tarik lagi (rebase) untuk menjemput commit yang masuk selama proses berjalan
git pull --rebase origin main || git rebase --abort

# 6) Kirim ke GitHub (dengan 1x percobaan ulang jika ditolak)
git push origin main || { git rebase --abort >/dev/null 2>&1; git pull --rebase origin main; git push origin main; }

echo "✅ Proses 100% Selesai!"