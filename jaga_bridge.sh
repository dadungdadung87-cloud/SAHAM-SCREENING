#!/bin/bash
# 🌉 Penjaga bridge Telegram: start jika belum jalan, aman dipanggil berulang.
# Dipanggil cron: @reboot + */5. Lock internal jembatan_opencode.py mencegah dobel.
cd /home/kaltaraid/Documents/SAHAM-SCREENING || exit 1
if pgrep -f "[j]embatan_opencode.py" >/dev/null 2>&1; then
    exit 0
fi
nohup ./.venv/bin/python jembatan_opencode.py >> logs/jembatan.log 2>&1 &
echo "[$(date '+%F %T')] bridge distart oleh jaga_bridge (pid $!)" >> logs/jembatan.log
