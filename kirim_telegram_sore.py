# ==========================================
# 🌆 KIRIM TELEGRAM SORE — referensi screening setelah pasar tutup
# Membaca radar_snapshot_sore.json (tidak menyentuh snapshot pagi)
# ==========================================
import os, json
import pandas as pd
import urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "Database")
CFG = os.path.join(BASE, "telegram_config.json")
NAMA_RUMUS = {
    1: "Smart Money Menyelam", 2: "Pantulan Jarum Bawah", 3: "Tutup Kuat Bandar Hajar",
    4: "Golden Cross Muda", 5: "Momentum Likuid Sehat", 6: "Ledakan Volume Senyap",
    7: "Anomali Machine Learning", 8: "Katalis Sentimen & Akuisisi", 9: "MACD Momentum Terukur"}

def wb_now():
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)

def kirim(text, cfg):
    url = f"https://api.telegram.org/bot{cfg['BOT_TOKEN']}/sendMessage"
    bagian = []
    while len(text) > 4000:
        cut = text.rfind("\n", 0, 4000)
        if cut < 100: cut = 4000
        bagian.append(text[:cut]); text = text[cut + 1:]
    bagian.append(text)
    for i, b in enumerate(bagian):
        data = urllib.parse.urlencode(
            {"chat_id": cfg["CHAT_ID"], "text": b, "parse_mode": "HTML",
             "disable_web_page_preview": "true"}).encode()
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=30) as r:
            resp = json.load(r)
        print(f"📤 Pesan {i+1}/{len(bagian)}: {'OK' if resp.get('ok') else resp}")

def unduh_r2(key, tmp):
    try:
        import r2_client
        return r2_client.download_arsip(key, tmp)
    except Exception as e:
        print(f"⚠️ R2 {key}: {e}"); return False

def utama():
    now = wb_now(); tgl = now.strftime("%Y-%m-%d")
    cfg = json.load(open(CFG))

    tmp_m = os.path.join(DB, "hasil_screener.csv")
    if not os.path.exists(tmp_m): unduh_r2("Database/hasil_screener.csv", tmp_m)
    df = pd.read_csv(tmp_m)
    harga = dict(zip(df["Ticker"], pd.to_numeric(df["Harga (Rp)"], errors="coerce")))
    change = dict(zip(df["Ticker"], pd.to_numeric(df["Change (%)"], errors="coerce")))

    tmp_s = os.path.join(DB, "radar_snapshot_sore.json")
    unduh_r2("Database/radar_snapshot_sore.json", tmp_s)
    keranjang, stempel = {}, None
    if os.path.exists(tmp_s):
        try:
            sn = json.load(open(tmp_s))
            keranjang, stempel = sn.get("keranjang") or {}, sn.get("stempel_data")
        except Exception: pass

    B = [f"🌆 <b>SCREENING SORE (REFERENSI)</b> — {now.strftime('%d %b %Y, %H:%M')} WIB"]
    B.append("⚠️ <i>Hanya untuk analisa — TIDAK dicetak sebagai daftar belanja</i>")
    if stempel:
        B.append(f"📅 Stempel data: {stempel}")
    if not keranjang:
        B.append("⚠️ Snapshot sore belum ada."); kirim("\n".join(B), cfg); return

    naik = int((df["Change (%)"] > 0).sum()); turun = int((df["Change (%)"] < 0).sum())
    sent = "🔥 Bullish" if naik > turun * 1.5 else ("🩸 Bearish" if turun > naik * 1.5 else "⚖️ Konsolidasi")
    B.append(f"🧭 Pasar: {sent} ({naik}↑ / {turun}↓ / {len(df)-naik-turun}=)")
    if not df.empty:
        tg = df.loc[df["Change (%)"].idxmax()]; tv = df.loc[df["Volume"].idxmax()]
        B.append(f"🏆 Top Gainer: <code>{tg['Ticker']}</code> {change.get(tg['Ticker'], 0):+.1f}%  |  🌊 Top Vol: <code>{tv['Ticker']}</code>")
    B.append("")

    semua, kosong = [], []
    for i in range(1, 10):
        lst = [t for t in (keranjang.get(f"RUMUS {i}") or []) if t]
        if not lst: kosong.append(i); continue
        B.append(f"🕵️ <b>RUMUS {i}</b> ({NAMA_RUMUS[i]})")
        for n, t in enumerate(lst[:5], 1):
            h = harga.get(t)
            semua.append(t)
            if h and pd.notna(h):
                B.append(f"{n}. <code>{t}</code> @ {h:.0f} ({change.get(t, 0):+.1f}%) → TP {int(round(h*1.05))} / CL {int(round(h*0.97))}")
            else:
                B.append(f"{n}. <code>{t}</code> (harga N/A)")
        B.append("")
    if kosong:
        B.append("⚠️ <b>RUMUS KOSONG:</b> " + ", ".join(f"R{i}" for i in kosong) + "\n")

    cnt = Counter(semua)
    kons = [(t, c) for t, c in cnt.items() if c >= 3]
    if kons:
        B.append("⭐ <b>KONSISTEN (≥3 rumus):</b>")
        for t, c in sorted(kons, key=lambda x: -x[1])[:6]:
            dimana = [i for i in range(1, 10) if t in (keranjang.get(f"RUMUS {i}") or [])]
            B.append(f"• <code>{t}</code> (R{', R'.join(map(str, dimana))})")
        B.append("")

    B.append("━━━━━━━━━━━━━━━━━━")
    B.append("🔗 https://minhaz0305.streamlit.app/")
    kirim("\n".join(B), cfg)
    print("✅ Telegram sore terkirim.")

if __name__ == "__main__":
    utama()
