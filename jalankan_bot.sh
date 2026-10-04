#!/bin/bash
# ==========================================
# ⚠️ MODE FULL-MANUAL: bot TIDAK PERNAH membeli/menjual otomatis.
# Semua eksekusi beli/jual hanya lewat tombol di web Tab 4.
# Cron ini hanya: update data -> sidang AI -> telegram -> buku besar.
# ==========================================
exec 200>/tmp/bot_simulator.lock
flock -n 200 || { echo "⏳ Siklus dilewati: bot sebelumnya masih berjalan."; exit 0; }

cd /home/kaltaraid/Documents/SAHAM-SCREENING/ || exit 1

git rebase --abort >/dev/null 2>&1
git merge --abort >/dev/null 2>&1
git pull --rebase origin main || git rebase --abort

echo "⏳ Memulai pembaruan data saham..."
./.venv/bin/python update_data.py

JAM_SEKARANG=$(date +%H%M)
FLAG_PAGI="/tmp/bsjp_pagi_$(date +%F)"
FLAG_SORE="/tmp/bsjp_sore_$(date +%F)"
FLAG_FUND="/tmp/exodus_fund_$(date +%F)"

if [ "$JAM_SEKARANG" -ge "1615" ] && [ "$JAM_SEKARANG" -le "1645" ]; then
    if [ ! -f "$FLAG_FUND" ]; then
        echo "🧪 [16:15-16:45] Tarik fundamental exodus (Stockbit)..."
        if ./.venv/bin/python fetcher_exodus.py fundamental; then
            touch "$FLAG_FUND"
        else
            echo "⚠️ Fundamental exodus gagal (token mati?) — dicoba lagi siklus berikutnya."
        fi
    else
        echo "⏭️ Fundamental exodus sudah jalan hari ini, dilewati."
    fi
fi

if [ "$JAM_SEKARANG" -ge "1520" ] && [ "$JAM_SEKARANG" -le "1535" ]; then
    if [ ! -f "$FLAG_PAGI" ]; then
        echo "🧠 [15:20-15:35] Sidang jadwal (hanya bikin sinyal — TIDAK membeli)..."
        if ./.venv/bin/python sidang_jadwal.py; then
            echo "📲 [15:36] Telegram pagi..."
            ./.venv/bin/python kirim_telegram.py
            touch "$FLAG_PAGI"
        else
            echo "❌ Sidang jadwal gagal — dicoba lagi siklus berikutnya."
        fi
    else
        echo "⏭️ Sidang pagi sudah jalan hari ini, dilewati."
    fi
elif [ "$JAM_SEKARANG" -ge "1600" ] && [ "$JAM_SEKARANG" -le "1610" ]; then
    if [ ! -f "$FLAG_SORE" ]; then
        echo "🌆 [16:00-16:10] Sidang sore (referensi)..."
        if ./.venv/bin/python sidang_sore.py && ./.venv/bin/python kirim_telegram_sore.py; then
            touch "$FLAG_SORE"
        else
            echo "❌ Sidang/Telegram sore gagal — dicoba lagi siklus berikutnya."
        fi
    fi
else
    echo "🔒 Mode full-manual: cron tidak mengeksekusi beli/jual apa pun."
fi

./.venv/bin/python bangun_buku_besar.py

find Arsip_Data_Harian/ -name "*.csv" -type f -mtime +50 -delete

echo "📤 Mengupload ke GitHub..."
git add -A Database/
git commit -m "Auto-update data dan bot simulator (arsip via R2)" || echo "Tidak ada perubahan"
git pull --rebase origin main || git rebase --abort
git push origin main || { git rebase --abort >/dev/null 2>&1; git pull --rebase origin main; git push origin main; }

echo "✅ Proses 100% Selesai!"
