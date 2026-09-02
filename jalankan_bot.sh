#!/bin/bash

# Masuk ke folder repositori
cd /home/kaltaraid/Documents/SAHAM-SCREENING/ || exit 1

# ==========================================
#  P3K GIT: batalkan rebase/merge menggantung dari siklus sebelumnya
# (mencegah cron macet total akibat git yang berhenti setengah jalan)
# ==========================================
git rebase --abort >/dev/null 2>&1
git merge --abort >/dev/null 2>&1

# ==========================================
# LANGKAH 1: TARIK DATA TERBARU DULU (sinyal AI dari web, dll)
# agar bot laptop mengeksekusi "kertas belanja" terbaru
# ==========================================
git pull --rebase origin main || git rebase --abort

echo "⏳ Memulai pembaruan data saham..."

# 2. Jalankan skrip Python WAJIB menggunakan .venv agar paket/modul terbaca
./.venv/bin/python update_data.py

# 3. JALANKAN BOT SIMULATOR (Menggunakan .venv juga)
./.venv/bin/python bot_simulator.py

# ==========================================
# FITUR SAPU OTOMATIS (MAX 50 HARI)
# Menggunakan nama folder yang benar: Arsip_Data_Harian
find Arsip_Data_Harian/ -name "*.csv" -type f -mtime +50 -delete
# ==========================================

echo "📤 Mengupload ke GitHub..."

# 4) COMMIT dulu perubahan lokal agar TIDAK tertimpa saat pull
git add Database/*.csv
git add Arsip_Data_Harian/*.csv
git commit -m "Auto-update data, arsip, dan bot simulator" || echo "Tidak ada perubahan"

# 5) Tarik lagi (rebase) untuk menjemput commit yang masuk selama proses berjalan
git pull --rebase origin main || git rebase --abort

# 6) Kirim ke GitHub (dengan 1x percobaan ulang jika ditolak)
git push origin main || { git rebase --abort >/dev/null 2>&1; git pull --rebase origin main; git push origin main; }

echo "✅ Proses 100% Selesai!"