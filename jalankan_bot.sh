#!/bin/bash
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

if [ "$JAM_SEKARANG" -ge "1520" ] && [ "$JAM_SEKARANG" -le "1535" ]; then
    if [ ! -f "$FLAG_PAGI" ]; then
        echo "🧠 [15:20-15:35] Sidang jadwal..."
        if ./.venv/bin/python sidang_jadwal.py; then
            echo "🛒 [15:20-15:35] Beli jadwal..."
            ./.venv/bin/python beli_jadwal.py
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
    else
        echo "⏭️ Sidang sore sudah jalan hari ini, dilewati."
    fi
else
    ./.venv/bin/python bot_simulator.py
fi

./.venv/bin/python bangun_buku_besar.py

find Arsip_Data_Harian/ -name "*.csv" -type f -mtime +50 -delete

echo "📤 Mengupload ke GitHub..."
git add -A Database/
git commit -m "Auto-update data dan bot simulator (arsip via R2)" || echo "Tidak ada perubahan"
git pull --rebase origin main || git rebase --abort
git push origin main || { git rebase --abort >/dev/null 2>&1; git pull --rebase origin main; git push origin main; }

echo "✅ Proses 100% Selesai!"
