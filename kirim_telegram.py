# ==========================================
# 📡 KIRIM TELEGRAM — Radar BSJP, Sen-Jum 16:05 WIB
# Sumber: Database/radar_snapshot.json di R2 (hasil sidang AI yang sama
# dengan Radar Live web). Script ini TIDAK menjalankan sidang sendiri.
# ==========================================
import os, json
import pandas as pd
import urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "Database")
CFG = os.path.join(BASE, "telegram_config.json")
HIST = os.path.join(DB, "telegram_hist.json")
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

def posisi_terbeli_hari_ini(tgl):
    """Baca portofolio aktif yang dibeli hari ini (Mode_Beli JADWAL)."""
    terbeli = []
    for i in range(1, 10):
        fp = os.path.join(DB, f"portofolio_aktif_rumus_{i}.csv")
        if os.path.exists(fp):
            try:
                df = pd.read_csv(fp)
                if 'Mode_Beli' in df.columns and 'Tanggal_Beli' in df.columns:
                    df_hari = df[(df['Mode_Beli'] == 'JADWAL') & 
                                 (df['Tanggal_Beli'].astype(str).str.startswith(tgl))]
                    for _, row in df_hari.iterrows():
                        terbeli.append({
                            'rumus': i, 'ticker': row['Ticker'],
                            'harga': row['Harga_Beli'], 'lot': row['Lot'],
                            'tp': row['Target_TP'], 'cl': row['Target_CL']
                        })
            except Exception:
                pass
    return terbeli

def unduh_r2(key, tmp):
    try:
        import r2_client
        return r2_client.download_arsip(key, tmp)
    except Exception as e:
        print(f"⚠️ R2 {key}: {e}"); return False

def utama():
    now = wb_now(); tgl = now.strftime("%Y-%m-%d")
    cfg = json.load(open(CFG))

    # 1) Data market (lokal dulu, fallback R2)
    tmp_m = os.path.join(DB, "hasil_screener.csv")
    if not os.path.exists(tmp_m): unduh_r2("Database/hasil_screener.csv", tmp_m)
    df = pd.read_csv(tmp_m)
    harga = dict(zip(df["Ticker"], pd.to_numeric(df["Harga (Rp)"], errors="coerce")))
    change = dict(zip(df["Ticker"], pd.to_numeric(df["Change (%)"], errors="coerce")))

    # 2) Snapshot sidang AI dari R2
    tmp_s = os.path.join(DB, "radar_snapshot.json")
    unduh_r2("Database/radar_snapshot.json", tmp_s)
    keranjang, stempel = {}, None
    if os.path.exists(tmp_s):
        try:
            sn = json.load(open(tmp_s))
            keranjang, stempel = sn.get("keranjang") or {}, sn.get("stempel_data")
        except Exception: pass

    B = [f"📡 <b>RADAR BSJP</b> — {now.strftime('%d %b %Y, %H:%M')} WIB"]
    if stempel and stempel[:10] != tgl:
        B.append(f"⚠️ Sidang terakhir: {stempel} (bukan hari ini)")
    if not keranjang:
        B.append("⚠️ Snapshot sidang belum ada — jalankan Auto-Pilot / Bagian 1 di web hari ini.")

    # 3) Ringkasan sentimen pasar
    naik = int((df["Change (%)"] > 0).sum()); turun = int((df["Change (%)"] < 0).sum())
    sent = "🔥 Sangat Bullish" if naik > turun * 1.5 else ("🩸 Sangat Bearish" if turun > naik * 1.5 else "⚖️ Konsolidasi")
    B.append(f"🧭 Pasar: {sent} ({naik}↑ / {turun}↓ / {len(df)-naik-turun}=)")
    if not df.empty:
        tg = df.loc[df["Change (%)"].idxmax()]; tv = df.loc[df["Volume"].idxmax()]
        B.append(f"🏆 Top Gainer: <code>{tg['Ticker']}</code> {change.get(tg['Ticker'], 0):+.1f}%  |  🌊 Top Vol: <code>{tv['Ticker']}</code>")
    B.append("")

    # 4) Top-5 per rumus + TP/CL
    semua, kosong = [], []
    for i in range(1, 10):
        lst = [t for t in (keranjang.get(f"RUMUS {i}") or []) if t]
        if not lst: kosong.append(i); continue
        B.append(f"🕵️ <b>RUMUS {i}</b> ({NAMA_RUMUS[i]})")
        for n, t in enumerate(lst[:5], 1):
            h = harga.get(t)
            semua.append(t)
            if h and pd.notna(h):
                B.append(f"{n}. <code>{t}</code> @ {h:.0f} → TP {int(round(h*1.05))} / CL {int(round(h*0.97))}")
            else:
                B.append(f"{n}. <code>{t}</code> (harga N/A)")
        B.append("")
    if kosong:
        B.append("⚠️ <b>RUMUS KOSONG:</b> " + ", ".join(f"R{i}" for i in kosong) + "\n")

    # 5) Consensus ≥3 rumus
    cnt = Counter(semua)
    kons = [(t, c) for t, c in cnt.items() if c >= 3]
    if kons:
        B.append("⭐ <b>KONSISTEN (≥3 rumus):</b>")
        for t, c in sorted(kons, key=lambda x: -x[1])[:6]:
            dimana = [i for i in range(1, 10) if t in (keranjang.get(f"RUMUS {i}") or [])]
            B.append(f"• <code>{t}</code> (R{', R'.join(map(str, dimana))})")
        B.append("")

    # 6) Repeat offender vs sidang sebelumnya
    hist = {}
    if os.path.exists(HIST):
        try: hist = json.load(open(HIST))
        except Exception: hist = {}
    prev = set()
    for d in sorted(hist.keys(), reverse=True):
        if d < tgl: prev = set(hist[d]); break
    repeat = sorted(set(semua) & prev)
    if repeat:
        B.append("🔁 <b>MUNCUL LAGI:</b> " + ", ".join(f"<code>{t}</code>" for t in repeat[:8]) + "\n")
    hist[tgl] = sorted(set(semua))
    json.dump({k: v for k, v in sorted(hist.items())[-30:]}, open(HIST, "w"), indent=2)

    # 7) Alert suspend (posisi aktif hilang dari data market)
    try:
        import r2_client
        r2_client.download_database()
        susp = set()
        for i in range(1, 10):
            fp = os.path.join(DB, f"portofolio_aktif_rumus_{i}.csv")
            if os.path.exists(fp):
                for t in pd.read_csv(fp)["Ticker"].tolist():
                    if t not in harga: susp.add(t)
        if susp:
            B.append("⚠️ <b>ALERT SUSPEND:</b> " + ", ".join(f"<code>{t}</code>" for t in sorted(susp)) + " — pertimbangkan liquidate manual\n")
    except Exception as e:
        print(f"⚠️ cek suspend: {e}")

    # 8) Rekap mingguan (khusus Jumat)
    if now.weekday() == 4:
        try:
            rows = []
            for i in range(1, 10):
                fh = os.path.join(DB, f"histori_transaksi_rumus_{i}.csv")
                if os.path.exists(fh):
                    h = pd.read_csv(fh)
                    if not h.empty: rows.append(h)
            if rows:
                hall = pd.concat(rows, ignore_index=True)
                senin = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
                mg = hall[pd.to_datetime(hall["Tanggal_Jual"], errors="coerce").dt.strftime("%Y-%m-%d") >= senin]
                if not mg.empty:
                    w = int((mg["Return_%"] > 0).sum()); l = int((mg["Return_%"] < 0).sum())
                    B.append(f"📈 <b>MINGGU INI:</b> {w}W / {l}L / {len(mg)-w-l}BE | Rp {mg['Total_Return_Rp'].sum():,.0f}".replace(",", ".") + "\n")
        except Exception as e:
            print(f"⚠️ rekap mingguan: {e}")

    # 9) Posisi terbeli hari ini (Mode JADWAL)
    terbeli = posisi_terbeli_hari_ini(tgl)
    if terbeli:
        B.append("🛒 <b>POSISI TERBELI HARI INI (JADWAL):</b>")
        for t in terbeli[:10]:  # batas 10 saham
            B.append(f"• R{t['rumus']} <code>{t['ticker']}</code> {t['lot']} lot @ {t['harga']:.0f} → TP {t['tp']} / CL {t['cl']}")
        if len(terbeli) > 10:
            B.append(f"... dan {len(terbeli)-10} lainnya")
        B.append("")

    B.append("━━━━━━━━━━━━━━━━━━")
    B.append("🔗 https://minhaz0305.streamlit.app/")
    kirim("\n".join(B), cfg)
    print("✅ Telegram terkirim.")

if __name__ == "__main__":
    utama()