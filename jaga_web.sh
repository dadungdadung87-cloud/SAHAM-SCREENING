#!/bin/bash
# 🖥️ Penjaga web Streamlit SAHAM-SCREENING: start jika belum jalan, aman dipanggil berulang.
# Dipanggil cron: @reboot + */5. TERPISAH total dari WEB-SCREENING (Railway/FastAPI).
# Mati-cerdas: jika port 8501 dipegang proses lain (bukan streamlit kita), jangan dobel-start.
cd /home/kaltaraid/Documents/SAHAM-SCREENING || exit 1
mkdir -p logs

if pgrep -f "[s]treamlit run app.py --server.port 8501" >/dev/null 2>&1; then
    exit 0
fi

nohup ./.venv/bin/streamlit run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false >> logs/streamlit.log 2>&1 &
echo "[$(date '+%F %T')] streamlit distart oleh jaga_web (pid $!)" >> logs/jaga_web.log
