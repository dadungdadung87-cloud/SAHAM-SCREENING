#!/usr/bin/env python3
"""Generate public static views of the four non-portfolio Streamlit tabs."""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from konfig_situs import SITE_NAME, SITE_DESC  # noqa: E402
import template_situs  # noqa: E402

OUT = os.path.join(BASE, "docs")
WIB = timezone(timedelta(hours=7))


def esc(value):
    return template_situs.esc("-" if pd.isna(value) else str(value))


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
        "market.html": ("Market Overview", market_page(df, stamp)),
        "screener.html": ("Screener", screener_page(df)),
        "radar.html": ("Radar AI", radar_page(df)),
        "detektif.html": ("Detektif", detective_page(df)),
    }
    for filename, (judul, body) in pages.items():
        with open(os.path.join(OUT, filename), "w") as f:
            f.write(template_situs.layout(judul, body, path_rel=filename))
    print(f"Generated {len(pages)} public pages from {len(df)} stocks.")


if __name__ == "__main__":
    main()
