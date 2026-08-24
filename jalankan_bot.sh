#!/bin/bash

# Masuk ke folder repositori
cd /home/kaltaraid/Documents/SAHAM-SCREENING/

echo "⏳ Memulai pembaruan data saham..."

# 1. Jalankan skrip Python WAJIB menggunakan .venv agar paket/modul terbaca
./.venv/bin/python update_data.py

# 2. JALANKAN BOT SIMULATOR (Menggunakan .venv juga)
./.venv/bin/python bot_simulator.py

# ==========================================
# FITUR SAPU OTOMATIS (MAX 50 HARI)
# Menggunakan nama folder yang benar: Arsip_Data_Harian
find Arsip_Data_Harian/ -name "*.csv" -type f -mtime +50 -delete
# ==========================================

echo "📤 Mengupload ke GitHub..."

# Tarik data dulu agar tidak tabrakan (diverged)
git pull origin main --no-rebase

# Masukkan SEMUA file di dalam folder Database dan Arsip (Jauh lebih praktis & aman)
git add Database/*.csv
git add Arsip_Data_Harian/*.csv

# Simpan dan kirim ke GitHub
git commit -m "Auto-update data, arsip, dan bot simulator" || echo "Tidak ada perubahan"
git push origin main

echo "✅ Proses 100% Selesai!"