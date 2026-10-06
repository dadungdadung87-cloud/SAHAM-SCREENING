#!/usr/bin/env python3
"""Generate public static views of the four non-portfolio Streamlit tabs."""
import html
import json
import os
import sys
from datetime import datetime, timezone, timedelta

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from konfig_situs import SITE_URL, SITE_NAME, SITE_DESC, APP_URL  # noqa: E402

OUT = os.path.join(BASE, "docs")
WIB = timezone(timedelta(hours=7))


def esc(value):
    return html.escape("-" if pd.isna(value) else str(value))


def number(value, decimals=2):
    value = pd.to_numeric(value, errors="coerce")
    if pd.isna(value):
        return "-"
    return f"{value:,.{decimals}f}".replace(",", ".")


def table(df, columns, limit=25):
    columns = [c for c in columns if c in df.columns]
    if not columns or df.empty:
        return '<p class="muted">Data belum tersedia.</p>'
    rows = []
    for _, row in df.head(limit).iterrows():
        cells = []
        for col in columns:
            value = row.get(col)
            if col == "Ticker":
                cells.append(f"<code>{esc(value)}</code>")
            elif col in {"Harga (Rp)", "Volume", "Mkt Cap (Exodus)"}:
                cells.append(number(value, 0))
            elif col in {"Change (%)", "PE TTM (Exodus)", "PBV (Exodus)", "RS Rating", "F-Score", "Total Score"}:
                cells.append(number(value, 2))
            else:
                cells.append(esc(value))
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    heads = "".join(f"<th>{esc(c)}</th>" for c in columns)
    return f"<div class='table-wrap'><table><thead><tr>{heads}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"


def layout(title, body):
    nav = "".join(
        f'<a href="{SITE_URL}{path}">{label}</a>'
        for path, label in [
            ("", "Beranda"),
            ("market.html", "Market Overview"),
            ("screener.html", "Screener"),
            ("radar.html", "Radar AI"),
            ("detektif.html", "Detektif"),
        ]
    )
    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | {esc(SITE_NAME)}</title><meta name="description" content="{esc(SITE_DESC)}">
<style>
:root{{--bg:#0b1220;--card:#152238;--line:#293b55;--txt:#cbd5e1;--hi:#f8fafc;--blue:#38bdf8;--green:#22c55e;--red:#ef4444;--yellow:#facc15}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--txt);font:15px system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.55}}
.wrap{{max-width:1180px;margin:auto;padding:18px}}header{{padding:14px 0;border-bottom:1px solid var(--line)}}
h1{{color:var(--hi);font-size:1.7rem;margin:0}}h2{{color:var(--hi);margin-top:28px}}h3{{color:var(--blue)}}
nav{{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}}nav a{{color:var(--txt);border:1px solid var(--line);border-radius:8px;padding:7px 11px;text-decoration:none}}nav a:hover{{border-color:var(--blue);color:var(--blue)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:18px 0}}.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:15px}}.card strong{{font-size:1.45rem;color:var(--hi);display:block}}.card small{{color:#94a3b8}}
.table-wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin:12px 0}}table{{border-collapse:collapse;width:100%;min-width:650px}}th{{background:var(--card);color:var(--hi);text-align:left;padding:10px;border-bottom:2px solid var(--blue)}}td{{padding:9px 10px;border-bottom:1px solid var(--line)}}tr:nth-child(even) td{{background:#101d30}}
code{{color:var(--blue);font-weight:700}}.muted{{color:#94a3b8}}.notice{{border-left:4px solid var(--yellow);background:#241f0d;padding:12px;border-radius:6px}}
.cta{{display:inline-block;margin:20px 0;background:linear-gradient(135deg,var(--blue),#818cf8);color:#07111f;font-weight:700;padding:11px 16px;border-radius:9px;text-decoration:none}}
footer{{margin-top:42px;border-top:1px solid var(--line);padding-top:14px;color:#94a3b8;font-size:.85rem}}
@media(max-width:600px){{.wrap{{padding:12px}}h1{{font-size:1.35rem}}}}
</style></head><body><div class="wrap"><header><h1>{esc(SITE_NAME)}</h1><p>{esc(SITE_DESC)}</p></header>
<nav>{nav}</nav><main>{body}</main><a class="cta" href="{esc(APP_URL)}" target="_blank" rel="noopener">Buka aplikasi interaktif</a>
<footer>Data edukasi, bukan rekomendasi jual-beli efek. Data dapat berubah dan harus diverifikasi.</footer></div></body></html>"""


def load_data():
    path = os.path.join(BASE, "Database", "hasil_screener.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


def market_page(df, stamp):
    change = pd.to_numeric(df.get("Change (%)"), errors="coerce")
    up, down = int((change > 0).sum()), int((change < 0).sum())
    flat = len(df) - up - down
    sentiment = "Bullish" if up > down * 1.5 else "Bearish" if down > up * 1.5 else "Konsolidasi"
    gain = df.assign(_change=change).sort_values("_change", ascending=False)
    volume = df.assign(_volume=pd.to_numeric(df.get("Volume"), errors="coerce")).sort_values("_volume", ascending=False)
    body = f"<h2>Market Overview</h2><p>Stempel data: <strong>{esc(stamp)}</strong> WIB</p>"
    body += f"<div class='grid'><div class='card'>Total saham<strong>{len(df)}</strong></div><div class='card'>Naik<strong>{up}</strong></div><div class='card'>Turun<strong>{down}</strong></div><div class='card'>Stagnan<strong>{flat}</strong></div><div class='card'>Sentimen<strong>{sentiment}</strong></div></div>"
    body += "<h2>Top Gainers</h2>" + table(gain, ["Ticker", "Harga (Rp)", "Change (%)", "Volume", "Total Score"])
    body += "<h2>Top Volume</h2>" + table(volume, ["Ticker", "Harga (Rp)", "Volume", "Change (%)", "Total Score"])
    return body


def screener_page(df):
    score = pd.to_numeric(df.get("Total Score"), errors="coerce")
    ranked = df.assign(_score=score).sort_values(["_score", "Change (%)"], ascending=False)
    body = "<h2>Screener Utama</h2><p>Daftar publik ini menampilkan kandidat berdasarkan score dan momentum. Filter interaktif lanjutan tetap tersedia di data harian.</p>"
    body += table(ranked, ["Ticker", "Harga (Rp)", "Change (%)", "Volume", "Kategori", "Total Score", "Rekomendasi", "Fase Siklus Bandar", "Tekanan Bandar"], 100)
    return body


def radar_page(df):
    path = os.path.join(BASE, "Database", "radar_snapshot.json")
    snapshot = {}
    if os.path.exists(path):
        try:
            snapshot = json.load(open(path))
        except Exception:
            snapshot = {}
    body = "<h2>Radar AI</h2>"
    body += f"<p>Snapshot: <strong>{esc(snapshot.get('waktu', 'belum tersedia'))}</strong></p>"
    basket = snapshot.get("keranjang") or {}
    if not basket:
        return body + '<p class="notice">Snapshot radar belum tersedia.</p>'
    for name, tickers in basket.items():
        valid = [t for t in tickers if t]
        rows = df[df["Ticker"].isin(valid)] if "Ticker" in df.columns else pd.DataFrame()
        body += f"<h3>{esc(name)}</h3>" + table(rows, ["Ticker", "Harga (Rp)", "Change (%)", "Total Score", "Rekomendasi"], 5)
    return body


def detective_page(df):
    score = pd.to_numeric(df.get("Total Score"), errors="coerce")
    volume = pd.to_numeric(df.get("Volume"), errors="coerce")
    candidates = df.assign(_score=score, _volume=volume).sort_values(["_score", "_volume"], ascending=False)
    body = "<h2>Detektif Ledakan</h2><p>Ringkasan publik kandidat dengan score dan volume tertinggi. Halaman ini tidak menampilkan portfolio atau fungsi transaksi.</p>"
    body += table(candidates, ["Ticker", "Harga (Rp)", "Change (%)", "Volume", "RVOL (Anomali Vol)", "Prediksi Machine Learning", "Kondisi Supply", "Status BB"], 50)
    return body


def main():
    os.makedirs(OUT, exist_ok=True)
    df = load_data()
    if df.empty:
        print("Data screener kosong; halaman tidak dibuat.")
        raise SystemExit(1)
    stamp = str(df["Terakhir Update"].iloc[0]) if "Terakhir Update" in df.columns else datetime.now(WIB).strftime("%Y-%m-%d %H:%M")
    pages = {
        "market.html": market_page(df, stamp),
        "screener.html": screener_page(df),
        "radar.html": radar_page(df),
        "detektif.html": detective_page(df),
    }
    for filename, body in pages.items():
        with open(os.path.join(OUT, filename), "w") as f:
            f.write(layout(filename[:-5].replace("-", " ").title(), body))
    print(f"Generated {len(pages)} public pages from {len(df)} stocks.")


if __name__ == "__main__":
    main()
