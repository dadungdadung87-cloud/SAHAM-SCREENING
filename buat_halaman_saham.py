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
import template_situs  # noqa: E402

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
    """Halaman detail satu saham via template bersama; warna naik/turun via css_extra."""
    chg = last.get("chg", 0)
    warna = "#22c55e" if chg >= 0 else "#ef4444"
    css_extra = f"""
header h1 span{{color:{warna}}}
.price{{font-size:2.2rem;font-weight:800;color:{warna}}}
.price small{{font-size:1rem;color:{warna};font-weight:600}}
#chart{{height:420px;margin:18px 0}}
@media(max-width:600px){{.price{{font-size:1.6rem}}#chart{{height:320px}}}}
"""
    desk = (f"Grafik candlestick {kode} 2 tahun terakhir, volume, dan ringkasan "
            f"indikator teknikal saham {nama}. Data pasar Indonesia.")
    isi = f"""
<p><a class="back" href="{SITE_URL}saham/">&larr; Daftar saham</a></p>
<header><h1>{kode} <span>{chg:+.2f}%</span></h1>
<div class="sub">{template_situs.esc(nama)}</div>
<div class="price">Rp {last.get('close', 0):,}<small> {chg:+.2f}%</small></div></header>
<div id="chart"></div>
<script>
const bars = {bars_json};
const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
  layout: {{ background: {{ type: 'solid', color: '#0f172a' }}, textColor: '#cbd5e1' }},
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
<p>Data edukasi, bukan rekomendasi jual-beli efek. Sumber: Yahoo Finance (OHLCV harian). Do Your Own Research.</p>"""
    return template_situs.layout(
        f"{kode} — Grafik & Analisa", isi, path_rel=f"saham/{kode}.html",
        deskripsi=desk, active_path="saham/",
        css_extra=css_extra, head_extra=f'<script src="{CHART_JS}"></script>')


def layout_palette(daftar):
    """Daftar saham via template bersama; grid ticker via css_extra."""
    item = "".join(
        f'<a class="tk" href="{template_situs.esc(r["code"])}.html">'
        f'<b>{template_situs.esc(r["code"])}</b><span>{template_situs.esc(r["name"][:38])}</span></a>'
        for r in daftar)
    isi = (f"<h2>📈 Daftar Saham IDX — {len(daftar)} ticker</h2>"
           f'<p><a href="{SITE_URL}">&larr; Beranda</a></p>'
           f'<div class="grid tk-grid">{item}</div>'
           f"<p>Data edukasi, bukan rekomendasi jual-beli efek.</p>")
    css_extra = """
.tk-grid{grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}
.tk{background:rgba(30,41,59,.58);border:1px solid var(--line);border-radius:9px;padding:10px 12px;text-decoration:none;color:var(--txt);display:block}
.tk:hover{border-color:var(--acc)}
.tk b{color:var(--acc);font-size:1.05rem;display:block}
.tk span{font-size:.82rem;color:#94a3b8}
"""
    return template_situs.layout(
        "Daftar Saham — Grafik & Analisa", isi, path_rel="saham/",
        deskripsi="Daftar lengkap saham IDX dengan grafik candlestick 2 tahun. Pilih saham untuk melihat grafik dan analisa.",
        active_path="saham/", css_extra=css_extra)


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
