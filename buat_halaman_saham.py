#!/usr/bin/env python3
# ==========================================
# 🕯️ HALAMAN DETAIL SAHAM — grafik candlestick per saham (F)
# Data: yfinance 2y OHLCV (format ringan purbaya: [[ts,o,h,l,c,v],...])
# Output: docs/saham/{TICKER}.html + docs/saham/index.html (palette)
# URL publik: .../SAHAM-SCREENING/saham/BBRI dst.
# Jalankan manual: ./venv/bin/python buat_halaman_saham.py [TICKER ...]
#   tanpa argumen = semua saham di feed
# Cron: mengikuti buat_artikel.py (17:10) via import, atau manual
# ==========================================
import os, sys, json, time
from datetime import datetime, timezone, timedelta
import pandas as pd
import yfinance as yf

BASE = "/home/kaltaraid/Documents/SAHAM-SCREENING"
sys.path.insert(0, BASE)
from konfig_situs import SITE_URL, SITE_NAME, SITE_DESC  # noqa: E402

OUT_DIR = os.path.join(BASE, "docs", "saham")
WIB = timezone(timedelta(hours=7))
HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

CHART_JS = "https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"


def ambil_ohlcv(ticker, periode="2y"):
    df = yf.download(f"{ticker}.JK", period=periode, interval="1d", progress=False)
    if df.empty:
        return []
    rows = []
    for d, r in df.iterrows():
        try:
            c = r["Close"].item()
            if pd.isna(c) or c <= 0:
                continue
            rows.append([int(pd.Timestamp(d).timestamp() * 1000),
                         round(r["Open"].item()), round(r["High"].item()),
                         round(r["Low"].item()), round(c), int(r["Volume"].item())])
        except Exception:
            continue
    return rows


def layout_saham(kode, nama, bars_json, last):
    chg = last.get("chg", 0)
    warna = "#22c55e" if chg >= 0 else "#ef4444"
    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{kode} {nama} — Grafik & Analisa | {SITE_NAME}</title>
<meta name="description" content="Grafik candlestick {kode} ({nama}) 2 tahun terakhir, volume, dan ringkasan indikator teknikal. Data pasar Indonesia.">
<script src="{CHART_JS}"></script>
<style>
:root{{--bg:#0b1220;--card:#152238;--line:#293b55;--txt:#cbd5e1;--hi:#f8fafc;--blue:#38bdf8;--green:#22c55e;--red:#ef4444}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--txt);font:15px system-ui,-apple-system,Segoe UI,sans-serif}}
.wrap{{max-width:1180px;margin:auto;padding:16px}}
header h1{{color:var(--hi);font-size:1.5rem;margin:0}}
header h1 span{{color:{warna}}}
.sub{{color:#94a3b8;font-size:.9rem;margin:4px 0 14px}}
.price{{font-size:2.2rem;font-weight:800;color:{warna}}}
.price small{{font-size:1rem;color:{warna};font-weight:600}}
#chart{{height:420px;margin:18px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:16px 0}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}}
.card b{{display:block;color:var(--hi);font-size:1.1rem}}.card small{{color:#94a3b8}}
a.back{{color:var(--blue);text-decoration:none;display:inline-block;margin:10px 0}}
footer{{margin-top:34px;border-top:1px solid var(--line);padding-top:12px;color:#94a3b8;font-size:.85rem}}
@media(max-width:600px){{.price{{font-size:1.6rem}}#chart{{height:320px}}}}
</style></head><body><div class="wrap">
<header><a class="back" href="{SITE_URL}saham/">&larr; Daftar saham</a>
<h1>{kode} <span>{chg:+.2f}%</span></h1>
<div class="sub">{nama}</div>
<div class="price">Rp {last.get('close', 0):,}<small> {chg:+.2f}%</small></div>
</header>
<div id="chart"></div>
<script>
const bars = {bars_json};
const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
  layout: {{ background: {{ type: 'solid', color: '#0b1220' }}, textColor: '#cbd5e1' }},
  grid: {{ vertLines: {{ color: '#1c2b45' }}, horzLines: {{ color: '#1c2b45' }} }},
  timeScale: {{ timeVisible: false }},
  crosshair: {{ mode: 0 }},
}});
const candle = chart.addCandlestickSeries({{
  upColor: '#22c55e', downColor: '#ef4444', borderVisible: false,
  wickUpColor: '#22c55e', wickDownColor: '#ef4444',
}});
candle.setData(bars.map(b => ({{ time: b[0]/1000, open: b[1], high: b[2], low: b[3], close: b[4] }})));
const vol = chart.addHistogramSeries({{ priceFormat: {{ type: 'volume' }}, priceScaleId: '' }});
vol.setData(bars.map(b => ({{ time: b[0]/1000, value: b[5], color: b[4] >= b[1] ? '#22c55e55' : '#ef444455' }})));
chart.timeScale().fitContent();
</script>
<footer>Data edukasi, bukan rekomendasi jual-beli efek. Sumber: Yahoo Finance (OHLCV harian). Do Your Own Research.</footer>
</div></body></html>"""


def layout_palette(daftar):
    item = "".join(
        f'<a class="tk" href="{SITE_URL}saham/{r["code"]}.html"><b>{r["code"]}</b><span>{r["name"][:38]}</span></a>'
        for r in daftar)
    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daftar Saham — Grafik & Analisa | {SITE_NAME}</title>
<meta name="description" content="Daftar lengkap saham IDX dengan grafik candlestick 2 tahun. Pilih saham untuk melihat grafik dan analisa.">
<style>
:root{{--bg:#0b1220;--card:#152238;--line:#293b55;--txt:#cbd5e1;--hi:#f8fafc;--blue:#38bdf8}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--txt);font:15px system-ui,sans-serif}}
.wrap{{max-width:1180px;margin:auto;padding:16px}}
h1{{color:var(--hi)}}a.back{{color:var(--blue);text-decoration:none}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px;margin:18px 0}}
.tk{{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:10px 12px;text-decoration:none;color:var(--txt);display:block}}
.tk:hover{{border-color:var(--blue)}}
.tk b{{color:var(--blue);font-size:1.05rem;display:block}}
.tk span{{font-size:.82rem;color:#94a3b8}}
footer{{margin-top:30px;border-top:1px solid var(--line);padding-top:12px;color:#94a3b8;font-size:.85rem}}
</style></head><body><div class="wrap">
<h1>📈 Daftar Saham IDX — {len(daftar)} ticker</h1>
<a class="back" href="{SITE_URL}">&larr; Beranda</a>
<div class="grid">{item}</div>
<footer>Data edukasi, bukan rekomendasi jual-beli efek.</footer>
</div></body></html>"""


def utama(args):
    os.makedirs(OUT_DIR, exist_ok=True)
    feed = pd.read_csv(os.path.join(BASE, "Database", "hasil_screener.csv"))
    nama_map = {}
    if "Nama" not in feed.columns:
        # coba dari konfigurasi names purbaya-style tidak ada; pakai kode saja
        feed["Nama"] = ""
    tickers = args if args else feed["Ticker"].astype(str).str.strip().tolist()
    daftar_palette = []
    dibuat = 0
    for t in tickers:
        t = t.strip().upper()
        if not t or len(t) > 6 or not t.isalpha():
            continue
        out_f = os.path.join(OUT_DIR, f"{t}.html")
        bars_file = os.path.join(OUT_DIR, f"{t}.json")
        # cache 20 jam — regenerasi berat hanya jika file lama
        perlu = (not os.path.exists(out_f)) or (time.time() - os.path.getmtime(out_f) > 20 * 3600)
        if perlu:
            bars = ambil_ohlcv(t)
            if not bars:
                continue
            first = bars[0]; last = bars[-1]
            chg = (last[4] - bars[-2][4]) / bars[-2][4] * 100 if len(bars) > 1 else 0
            lastd = {"close": last[4], "chg": round(chg, 2)}
            with open(out_f, "w") as f:
                f.write(layout_saham(t, t, json.dumps(bars), lastd))
            with open(bars_file, "w") as f:
                json.dump(bars, f)
            daftar_palette.append({"code": t, "name": ""})
            dibuat += 1
            time.sleep(0.4)  # sopan ke Yahoo
            if dibuat >= 300:  # batas aman per run
                print(f"batas 300/run tercapai — sisanya besok"); break
        else:
            daftar_palette.append({"code": t, "name": ""})
    # palette index
    daftar_palette.sort(key=lambda r: r["code"])
    with open(os.path.join(OUT_DIR, "index.html"), "w") as f:
        f.write(layout_palette(daftar_palette))
    print(f"✅ {dibuat} halaman baru + palette: docs/saham/index.html (total {len(daftar_palette)})")


if __name__ == "__main__":
    utama(sys.argv[1:])
