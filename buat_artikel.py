#!/usr/bin/env python3
# ==========================================
# 📝 GENERATOR ARTIKEL HARIAN — buat halaman artikel statis dari data screener
# Sumber : Database/hasil_screener.csv (hasil cron update_data.py)
# Output : docs/artikel/index.html (indeks) + docs/artikel/<tanggal>.html
# Jalankan: ./.venv/bin/python buat_artikel.py            (hanya jika data hari ini belum dipublikasi)
#           ./.venv/bin/python buat_artikel.py --force    (regenerasi hari ini)
# Cron   : 17:10 WIB kerja (setelah update data terakhir) — proses ±2 detik, tidak mengganggu Streamlit
# ==========================================
import os, sys, html, glob
from datetime import datetime, timezone, timedelta
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from konfig_situs import (SITE_URL, SITE_NAME, SITE_DESC, ADSENSE_CLIENT,
                          ADSENSE_SLOT_ATAS, ADSENSE_SLOT_TENGAH, ADSENSE_SLOT_BAWAH,
                          BROKER_REF, TELEGRAM_URL, SEO_KEYWORDS)

DIR_ARTIKEL = os.path.join(BASE, "docs", "artikel")
WIB = timezone(timedelta(hours=7))
HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN_ID = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
            "Agustus", "September", "Oktober", "November", "Desember"]


def tanggal_id(dt):
    return f"{HARI_ID[dt.weekday()]}, {dt.day} {BULAN_ID[dt.month]} {dt.year}"


def adsense_head():
    """Skrip AdSense hanya dimuat jika ADSENSE_CLIENT sudah diisi."""
    if not ADSENSE_CLIENT:
        return ""
    return f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={html.escape(ADSENSE_CLIENT)}" crossorigin="anonymous"></script>'


def adsense_unit(slot):
    if not ADSENSE_CLIENT or not slot:
        return ""
    return (f'<ins class="adsbygoogle" style="display:block" data-ad-client="{html.escape(ADSENSE_CLIENT)}" '
            f'data-ad-slot="{html.escape(slot)}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
            '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>')


def footer_affiliate():
    baris = "".join(
        f'<a href="{html.escape(b["url"])}" target="_blank" rel="sponsored noopener">{html.escape(b["nama"])}</a>'
        f'<span class="afil-desk">{html.escape(b["deskripsi"])}</span>'
        for b in BROKER_REF if b.get("url"))
    tg = (f'<a href="{html.escape(TELEGRAM_URL)}" target="_blank" rel="noopener">📢 Channel Telegram</a>'
          if TELEGRAM_URL else "")
    return baris + tg


def _amankan_num(v):
    return pd.to_numeric(v, errors="coerce")


def susun_blok(df, stempel, tgl_hari):
    """Konten artikel: ringkasan pasar + tabel saham menarik. Semua angka dari data."""
    chg = _amankan_num(df.get("Change (%)"))
    naik = int((chg > 0).sum()); turun = int((chg < 0).sum())
    total = len(df)
    sentimen = "Sangat Bullish 🔥" if naik > turun * 1.5 else ("Sangat Bearish 🩸" if turun > naik * 1.5 else "Konsolidasi ⚖️")

    d = df.copy()
    d["_chg"] = _amankan_num(d["Change (%)"])
    d["_vol"] = _amankan_num(d.get("Volume"))
    d["_score"] = pd.to_numeric(d.get("Total Score"), errors="coerce").fillna(0)

    # Top mover & anomali — kolom dinamis mengikuti data
    top = d.sort_values("_chg", ascending=False).head(10)
    bottom = d.sort_values("_chg").head(10)
    vol = d.sort_values("_vol", ascending=False).head(10)
    # Anomali: RVOL tinggi + masih naik tipis (kandidat akumulasi) — pakai kolom jika tersedia
    rkol = "RVOL (Anomali Vol)" if "RVOL (Anomali Vol)" in d.columns else None
    if rkol:
        mask_rvol = d[rkol].astype(str).isin(["Anomali Tinggi (150-300%)", "Ledakan Ekstrem (> 300%)"])
        anomali = d[mask_rvol & (d["_chg"] > 0) & (d["_chg"] <= 5)].sort_values("_vol", ascending=False).head(10)
    else:
        anomali = d.iloc[0:0]

    def tabel(sub, kolom):
        if sub.empty:
            return "<p class='kosong'>Tidak ada data.</p>"
        kolom_ada = [c for c in kolom if c in sub.columns]
        baris = []
        for _, r in sub.iterrows():
            sel = []
            for c in kolom_ada:
                v = r.get(c)
                if c == "Ticker":
                    sel.append(f"<code>{html.escape(str(v))}</code>")
                elif isinstance(v, float):
                    sel.append(f"{v:,.2f}".replace(",", "."))
                else:
                    sel.append(html.escape(str(v)))
            baris.append("<tr>" + "".join(f"<td>{s}</td>" for s in sel) + "</tr>")
        head = "".join(f"<th>{html.escape(c)}</th>" for c in kolom_ada)
        return f"<div class='tbl'><table><thead><tr>{head}</tr></thead><tbody>{''.join(baris)}</tbody></table></div>"

    kolom_umum = ["Ticker", "Harga (Rp)", "Change (%)", "Volume"]
    if "Total Score" in df.columns:
        kolom_umum.append("Total Score")

    bagian = []
    bagian.append(f"""
    <h2>Kondisi Pasar IHSG {tgl_hari}</h2>
    <p>Dari <strong>{total}</strong> saham yang dipantau: <span class="up">{naik} naik</span>,
    <span class="down">{turun} turun</span>, {total - naik - turun} stagnan.
    Sentimen pasar: <strong>{sentimen}</strong>. Data diambil pukul {html.escape(str(stempel))} WIB.</p>
    <h2>Saham Penguat Teratas</h2>""")
    bagian.append(tabel(top, kolom_umum))
    bagian.append("<h2>Saham Pelemah Teratas</h2>")
    bagian.append(tabel(bottom, kolom_umum))
    bagian.append("<h2>Volume Terbesar</h2>")
    bagian.append(tabel(vol, kolom_umum))
    if rkol:
        bagian.append("<h2>Kandidat Akumulasi Senyap (RVOL Tinggi, Belum Terbang)</h2>"
                      "<p>Saham dengan lonjakan volume dibanding rata-rata, harga masih naik tipis — pola yang sering muncul sebelum saham menguat.</p>")
        bagian.append(tabel(anomali, kolom_umum))
    return "\n".join(bagian)


def halaman(titel, isi, tanggal_slug, indeks=False):
    aff = footer_affiliate()
    nav = f'''<nav class="topnav">
      <a class="active" href="{SITE_URL}">Beranda</a>
      <a href="{SITE_URL}market.html">Market</a>
      <a href="{SITE_URL}screener.html">Screener</a>
      <a href="{SITE_URL}radar.html">Radar AI</a>
      <a href="{SITE_URL}detektif.html">Detektif</a>
    </nav>'''
    if not indeks:
        nav += f'<p><a class="back" href="{SITE_URL}">&larr; Beranda</a></p>'
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(titel)} | {html.escape(SITE_NAME)}</title>
<meta name="description" content="{html.escape(SITE_DESC)}">
<meta name="keywords" content="{html.escape(SEO_KEYWORDS)}">
{adsense_head()}
<style>
:root{{--bg:#0f172a;--card:#1e293b;--line:#334155;--txt:#cbd5e1;--hi:#f8fafc;--acc:#38bdf8;--up:#22c55e;--dn:#ef4444}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--txt);line-height:1.65}}
 .wrap{{max-width:1040px;margin:0 auto;padding:24px 18px}}
 header{{padding:26px 0 12px}}
 header h1{{margin:0;font-size:clamp(1.8rem,4vw,3.2rem);line-height:1.1;color:var(--hi);letter-spacing:-.04em}}
 header h1 a{{color:var(--acc);text-decoration:none}}
 header p{{max-width:700px;color:#94a3b8;font-size:1.02rem}}
 .topnav{{display:flex;gap:8px;flex-wrap:wrap;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:12px 0;margin:12px 0 26px}}
 .topnav a{{color:#94a3b8;text-decoration:none;padding:7px 11px;border-radius:7px;font-size:.9rem}}
 .topnav a:hover,.topnav a.active{{background:var(--card);color:var(--acc)}}
 h2{{color:var(--hi);margin-top:34px}}
p{{margin:.6em 0}}
code{{background:var(--card);padding:2px 8px;border-radius:6px;color:var(--acc);font-weight:600}}
.tbl{{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin:14px 0}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}
th{{background:var(--card);color:var(--hi);text-align:left;padding:10px 12px;border-bottom:2px solid var(--acc)}}
td{{padding:9px 12px;border-bottom:1px solid var(--line)}}
tr:nth-child(even) td{{background:rgba(30,41,59,.4)}}
.up{{color:var(--up);font-weight:600}}.down{{color:var(--dn);font-weight:600}}
.cta{{display:block;text-align:center;background:linear-gradient(135deg,#38bdf8,#818cf8);color:#0f172a;
font-weight:700;padding:14px;border-radius:12px;text-decoration:none;margin:28px 0;font-size:1.05rem}}
.ad{{margin:26px 0;min-height:90px}}
.afil{{margin-top:40px;border-top:1px solid var(--line);padding-top:18px;font-size:.92rem;display:flex;flex-wrap:wrap;gap:10px 22px;align-items:center}}
.afil a{{color:var(--acc);font-weight:600}}
.afil-desk{{color:#94a3b8;margin-left:6px}}
.kosong{{color:#94a3b8;font-style:italic}}
.back{{color:var(--acc)}}
footer{{margin-top:48px;border-top:1px solid var(--line);padding-top:16px;font-size:.85rem;color:#94a3b8}}
 ul.artikel-list{{list-style:none;padding:0}}ul.artikel-list li{{padding:10px 0;border-bottom:1px solid var(--line)}}
 .hero{{background:radial-gradient(circle at 90% 0%,rgba(56,189,248,.2),transparent 38%),linear-gradient(145deg,#172a46,#101827);border:1px solid #2b5171;border-radius:18px;padding:30px;margin:8px 0 24px;box-shadow:0 18px 50px rgba(0,0,0,.2)}}
 .hero .eyebrow{{color:var(--acc);font-size:.78rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}}
 .hero h2{{font-size:clamp(1.5rem,3.5vw,2.4rem);margin:9px 0 10px;max-width:760px}}
 .hero p{{max-width:700px;color:#cbd5e1;font-size:1.02rem}}
 .hero-links{{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px}}
 .hero-links a{{background:var(--acc);color:#07111f;text-decoration:none;font-weight:800;padding:10px 14px;border-radius:9px}}
 .hero-links a.alt{{background:transparent;color:var(--txt);border:1px solid var(--line)}}
 .feature-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0 28px}}
 .feature{{background:rgba(30,41,59,.58);border:1px solid var(--line);border-radius:12px;padding:15px}}
 .feature b{{display:block;color:var(--hi);margin:7px 0 4px}}.feature span{{font-size:.88rem;color:#94a3b8}}
 @media(max-width:700px){{.feature-grid{{grid-template-columns:repeat(2,1fr)}}.hero{{padding:22px 18px}}}}
 @media(max-width:420px){{.feature-grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body><div class="wrap">
<header><h1><a href="{SITE_URL}">{html.escape(SITE_NAME)}</a></h1>
<p>{html.escape(SITE_DESC)}</p></header>
{nav}
    <div class="ad">{adsense_unit(ADSENSE_SLOT_ATAS)}</div>
{isi}
<div class="ad">{adsense_unit(ADSENSE_SLOT_TENGAH)}</div>
    <div class="ad">{adsense_unit(ADSENSE_SLOT_BAWAH)}</div>
<div class="afil"><strong>Bekal trading kamu:</strong> {aff}</div>
<footer>Disclaimer: seluruh konten bersifat informasi &amp; edukasi, bukan rekomendasi jual-beli efek.
Data berasal dari pemantauan otomatis dan dapat berubah. Do Your Own Research.</footer>
</div></body></html>"""


def tabel_indeks():
    files = sorted(glob.glob(os.path.join(DIR_ARTIKEL, "20*.html")), reverse=True)
    li = []
    for f in files[:60]:
        nama = os.path.basename(f)[:-5]
        tgl = datetime.strptime(nama, "%Y-%m-%d")
        li.append(f'<li>📄 <a href="artikel/{nama}.html">Ringkasan pasar {tanggal_id(tgl)}</a></li>')
    return f"<h2>Artikel Terbaru</h2><ul class='artikel-list'>{''.join(li) if li else '<li>Belum ada artikel.</li>'}</ul>"


def utama():
    os.makedirs(DIR_ARTIKEL, exist_ok=True)
    now = datetime.now(WIB)
    tgl_hari = now.strftime("%Y-%m-%d")
    out_hari = os.path.join(DIR_ARTIKEL, f"{tgl_hari}.html")

    if os.path.exists(out_hari) and "--force" not in sys.argv:
        print(f"📄 Artikel {tgl_hari} sudah ada — dilewati (--force untuk regenerasi).")
    else:
        fp = os.path.join(BASE, "Database", "hasil_screener.csv")
        if not os.path.exists(fp):
            print("❌ hasil_screener.csv tidak ada — jalankan update_data.py dulu."); sys.exit(1)
        df = pd.read_csv(fp)
        if df.empty:
            print("❌ Data screener kosong."); sys.exit(1)
        stempel = str(df["Terakhir Update"].iloc[0])[11:16] if "Terakhir Update" in df.columns else "-"
        isi = susun_blok(df, stempel, tanggal_id(now))
        judul = f"Ringkasan Pasar Saham IHSG {tanggal_id(now)}"
        with open(out_hari, "w") as f:
            f.write(halaman(judul, isi, tgl_hari))
        print(f"✅ Artikel hari ini: docs/artikel/{tgl_hari}.html ({len(df)} saham)")

    # Indeks landing page utama selalu diperbarui
    isi_idx = f"""
    <section class="hero">
      <div class="eyebrow">IHSG MARKET INTELLIGENCE</div>
      <h2>Data pasar yang ringkas, tajam, dan mudah dipahami.</h2>
      <p>Analisis harian 900+ saham IHSG dalam satu tempat: momentum, volume, fase bandar, radar AI, dan fundamental. Buka data publiknya tanpa login dan tanpa melewati dashboard yang rumit.</p>
      <div class="hero-links"><a href="{SITE_URL}market.html">Lihat Market Hari Ini</a><a class="alt" href="{SITE_URL}screener.html">Jelajahi Screener</a></div>
    </section>
    <div class="feature-grid">
      <div class="feature">📊<b>Market Overview</b><span>Sentimen, gainers, losers, dan volume.</span></div>
      <div class="feature">🔍<b>Screener</b><span>Kandidat berdasarkan score dan momentum.</span></div>
      <div class="feature">🤖<b>Radar AI</b><span>Snapshot kandidat dari sembilan rumus.</span></div>
      <div class="feature">🕵️<b>Detektif</b><span>RVOL, supply, dan anomali pergerakan.</span></div>
    </div>
    <h2>Jelajahi Analisis Publik</h2>
    <p>Semua halaman diperbarui otomatis mengikuti data screening terbaru. Gunakan sebagai bahan riset awal, bukan sebagai instruksi transaksi.</p>
    {tabel_indeks()}
    """
    with open(os.path.join(BASE, "docs", "index.html"), "w") as f:
        f.write(halaman(f"Beranda | {SITE_NAME}", isi_idx, tgl_hari, indeks=True))
    print("✅ Landing page: docs/index.html diperbarui")

    # Halaman publik tab non-portfolio dibuat terpisah agar pengunjung tidak perlu
    # masuk ke Streamlit hanya untuk membaca ringkasan hasil screening.
    try:
        import buat_halaman_publik
        buat_halaman_publik.main()
    except Exception as e:
        print(f"⚠️ Halaman publik tab gagal dibuat: {e}")


if __name__ == "__main__":
    utama()
