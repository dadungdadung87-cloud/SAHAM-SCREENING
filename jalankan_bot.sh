#!/bin/bash
# ==========================================
# ⚠️ MODE BELI MANUAL: pembelian hanya lewat tombol web Tab 4.
# Cron otomatis hanya memeriksa TP/SL; posisi lain dijual lewat tombol JUAL sore.
# Data TIDAK ditarik dari Yahoo di sini — producer = DATA-CENTER (feed lokal).
# ==========================================
exec 200>/tmp/bot_simulator.lock
flock -n 200 || { echo "⏳ Siklus dilewati: bot sebelumnya masih berjalan."; exit 0; }

cd /home/kaltaraid/Documents/SAHAM-SCREENING/ || exit 1

git rebase --abort >/dev/null 2>&1
git merge --abort >/dev/null 2>&1
git pull --rebase origin main || git rebase --abort

# ==========================================
# 📡 CONSUMER: tarik data dari DATA-CENTER feed (BUKAN dari Yahoo)
# Producer tunggal di /home/kaltaraid/Documents/DATA-CENTER
# ==========================================
FEED="/home/kaltaraid/Documents/DATA-CENTER/feed"
echo "📡 Menarik data dari DATA-CENTER feed..."
if [ -f "$FEED/hasil_screener.csv" ]; then
    mkdir -p Database Arsip_Data_Harian
    # Salin atomik: .tmp dulu lalu replace
    cp "$FEED/hasil_screener.csv" Database/hasil_screener.csv.tmp && mv Database/hasil_screener.csv.tmp Database/hasil_screener.csv
    [ -f "$FEED/fundamental_exodus.csv" ] && cp "$FEED/fundamental_exodus.csv" Database/fundamental_exodus.csv
    # Salin arsip intraday hari ini jika ada dan lebih baru
    HARI=$(date +%F)
    [ -f "$FEED/arsip/screener_${HARI}.csv" ] && cp "$FEED/arsip/screener_${HARI}.csv" "Arsip_Data_Harian/screener_${HARI}.csv"
    echo "✅ Feed masuk ke Database/ ($(stat -c %s Database/hasil_screener.csv) bytes)"
    # State intraday ringkas utk web cloud (ikut auto-commit git)
    ./.venv/bin/python buat_state_intraday.py || echo "⚠️ state_intraday gagal (biarkan siklus berikutnya)"
    # R2 mengejar feed: upload data market terbaru agar web Streamlit selalu segar
    ./.venv/bin/python -c "
import r2_client
try:
    if r2_client.upload_arsip('Database/hasil_screener.csv', 'Database/hasil_screener.csv'):
        print('☁️ hasil_screener ter-upload ke R2 (feed baru).')
    if __import__('os').path.exists('Database/fundamental_exodus.csv'):
        r2_client.upload_arsip('Database/fundamental_exodus.csv', 'Database/fundamental_exodus.csv')
        print('☁️ fundamental_exodus ter-upload ke R2.')
    # Arsip intraday: hari ini (gate rumus v6.1) + kemarin (skor pembekal) untuk web cloud
    import os
    _a = f'Arsip_Data_Harian/screener_{__import__(\"datetime\").date.today()}.csv'
    if os.path.exists(_a) and r2_client.upload_arsip(_a, _a):
        print(f'☁️ {_a} ter-upload ke R2.')
    import datetime as _dt
    _km = (_dt.date.today() - _dt.timedelta(days=1)).strftime('%Y-%m-%d')
    _ak = f'Arsip_Data_Harian/screener_{_km}.csv'
    if os.path.exists(_ak) and r2_client.upload_arsip(_ak, _ak):
        print(f'☁️ {_ak} ter-upload ke R2 (pembekal).')
except Exception as e:
    print(f'⚠️ Upload R2 feed gagal (biarkan siklus berikutnya): {e}')
"
else
    echo "⚠️ Feed DATA-CENTER belum tersedia — pakai data lokal terakhir (gembok data basi tetap aktif)."
fi

JAM_SEKARANG=$(date +%H%M)
FLAG_BELI="/tmp/bsjp_beli_$(date +%F)"

if [ "$JAM_SEKARANG" -ge "1550" ] && [ "$JAM_SEKARANG" -le "1559" ]; then
    # ==========================================
    # 🛒 SESI TUNGGAL 15:50 — daftar belanja (sidang AI) + BUY dalam satu waktu.
    # Feed sudah segar (producer upload R2 tiap 2 menit) → mode_beli_aktif aman.
    # Telegram hanya dikirim di sesi ini (satu-satunya notifikasi harian).
    # ==========================================
    if [ ! -f "$FLAG_BELI" ]; then
        echo "🧠 [15:50] Sidang AI: bikin daftar belanja 9 rumus..."
        if ./.venv/bin/python sidang_jadwal.py; then
            echo "📲 [15:52] Telegram: daftar belanja hari ini..."
            ./.venv/bin/python kirim_telegram.py
            echo "🛒 [15:53] BUY: eksekusi sinyal ke 9 rumus..."
            ./.venv/bin/python bot_simulator.py --jadwal
            touch "$FLAG_BELI"
        else
            echo "❌ Sidang 15:50 gagal — dicoba lagi siklus berikutnya (sampai 15:59)."
        fi
    else
        echo "⏭️ Sesi beli 15:50 sudah jalan hari ini, dilewati."
    fi
else
    echo "🎯 Auto TP/SL: memeriksa posisi yang menyentuh Target_TP/Target_CL..."
    ./.venv/bin/python bot_simulator.py --tp-sl-only
fi

./.venv/bin/python bangun_buku_besar.py

find Arsip_Data_Harian/ -name "*.csv" -type f -mtime +50 -delete

echo "📤 Mengupload ke GitHub..."
git add -A Database/
git commit -m "Auto-update data dan bot simulator (arsip via R2)" || echo "Tidak ada perubahan"
git pull --rebase origin main || git rebase --abort
git push origin main || { git rebase --abort >/dev/null 2>&1; git pull --rebase origin main; git push origin main; }

echo "✅ Proses 100% Selesai!"
