#!/usr/bin/env python3
# ==========================================
# 📝 GENERATOR ARTIKEL HARIAN — buat halaman artikel statis dari data screener
# Sumber : Database/hasil_screener.csv (hasil cron jalankan_bot.sh / DATA-CENTER)
# Output : docs/artikel/index.html (indeks) + docs/artikel/<tanggal>.html
#          + docs/robots.txt + docs/sitemap.xml
# Jalankan: ./.venv/bin/python buat_artikel.py            (hanya jika data hari ini belum dipublikasi)
#           ./.venv/bin/python buat_artikel.py --force    (regenerasi hari ini)
# Cron   : 17:10 WIB kerja (setelah update data terakhir) — proses ±2 detik, tidak mengganggu Streamlit
# ==========================================
import os, sys, glob
from datetime import datetime, timezone, timedelta
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from konfig_situs import SITE_URL, SITE_NAME, SITE_DESC, SEO_KEYWORDS  # noqa: E402
import template_situs  # noqa: E402

DIR_ARTIKEL = os.path.join(BASE, "docs", "artikel")
WIB = timezone(timedelta(hours=7))
HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN_ID = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
            "Agustus", "September", "Oktober", "November", "Desember"]


def tanggal_id(dt):
    return f"{HARI_ID[dt.weekday()]}, {dt.day} {BULAN_ID[dt.month]} {dt.year}"


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
                    sel.append(f"<code>{template_situs.esc(v)}</code>")
                elif isinstance(v, float):
                    sel.append(f"{v:,.2f}".replace(",", "."))
                else:
                    sel.append(template_situs.esc(v))
            baris.append("<tr>" + "".join(f"<td>{s}</td>" for s in sel) + "</tr>")
        head = "".join(f"<th>{template_situs.esc(c)}</th>" for c in kolom_ada)
        return f"<div class='tbl'><table><thead><tr>{head}</tr></thead><tbody>{''.join(baris)}</tbody></table></div>"

    kolom_umum = ["Ticker", "Harga (Rp)", "Change (%)", "Volume"]
    if "Total Score" in df.columns:
        kolom_umum.append("Total Score")

    bagian = []
    bagian.append(f"""
    <h2>Kondisi Pasar IHSG {tgl_hari}</h2>
    <p>Dari <strong>{total}</strong> saham yang dipantau: <span class="up">{naik} naik</span>,
    <span class="down">{turun} turun</span>, {total - naik - turun} stagnan.
    Sentimen pasar: <strong>{sentimen}</strong>. Data diambil pukul {template_situs.esc(stempel)} WIB.</p>
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


def halaman(judul, isi, tanggal_slug, indeks=False, path_rel=""):
    """Halaman artikel/beranda via template bersama (canonical + OG + JSON-LD otomatis)."""
    tgl_pub = datetime.strptime(tanggal_slug, "%Y-%m-%d") if (tanggal_slug and not indeks) else None
    return template_situs.layout(
        judul, isi, path_rel=path_rel,
        jenis=("website" if indeks else "article"),
        waktu_publish=tgl_pub, active_path=("artikel/index.html" if not indeks else ""))


def tabel_indeks():
    files = sorted(glob.glob(os.path.join(DIR_ARTIKEL, "20*.html")), reverse=True)
    li = []
    for f in files[:60]:
        nama = os.path.basename(f)[:-5]
        tgl = datetime.strptime(nama, "%Y-%m-%d")
        li.append(f'<li>📄 <a href="{nama}.html">Ringkasan pasar {tanggal_id(tgl)}</a></li>')
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
            f.write(halaman(judul, isi, tgl_hari, path_rel=f"artikel/{tgl_hari}.html"))
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
    <p><a href="{SITE_URL}artikel/index.html">Lihat semua arsip artikel &rarr;</a></p>
    """
    with open(os.path.join(BASE, "docs", "index.html"), "w") as f:
        f.write(halaman("", isi_idx, tgl_hari, indeks=True))
    print("✅ Landing page: docs/index.html diperbarui")

    # Halaman indeks artikel (docs/artikel/index.html) + perbaikan link di beranda
    isi_daftar = ("<h2>Semua Artikel Harian</h2>"
                  "<p>Arsip ringkasan pasar IHSG, terbaru di atas.</p>"
                  + tabel_indeks())
    with open(os.path.join(DIR_ARTIKEL, "index.html"), "w") as f:
        f.write(halaman("Arsip Artikel", isi_daftar, tgl_hari, indeks=True, path_rel="artikel/index.html"))
    print("✅ Indeks artikel: docs/artikel/index.html diperbarui")

    tulis_robots_dan_sitemap()

    # Halaman publik tab non-portfolio dibuat terpisah agar pengunjung tidak perlu
    # masuk ke Streamlit hanya untuk membaca ringkasan hasil screening.
    try:
        import buat_halaman_publik
        buat_halaman_publik.main()
    except Exception as e:
        print(f"⚠️ Halaman publik tab gagal dibuat: {e}")


def tulis_robots_dan_sitemap():
    """robots.txt + sitemap.xml: artikel & halaman statis yang ada di docs/."""
    docs = os.path.join(BASE, "docs")
    urls = [("", "daily", "1.0"), ("market.html", "daily", "0.9"),
            ("screener.html", "daily", "0.9"), ("radar.html", "daily", "0.8"),
            ("detektif.html", "daily", "0.8"), ("artikel/index.html", "daily", "0.8"),
            ("saham/", "weekly", "0.6")]
    for f in sorted(glob.glob(os.path.join(docs, "saham", "*.html"))):
        if os.path.basename(f) != "index.html":
            urls.append((f"saham/{os.path.basename(f)}", "weekly", "0.5"))
    for f in sorted(glob.glob(os.path.join(DIR_ARTIKEL, "20*.html")), reverse=True)[:60]:
        urls.append((f"artikel/{os.path.basename(f)}", "monthly", "0.7"))

    with open(os.path.join(docs, "robots.txt"), "w") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n")

    kini = datetime.now(WIB).strftime("%Y-%m-%d")
    entri = "".join(
        f"<url><loc>{SITE_URL}{p}</loc><changefreq>{cf}</changefreq>"
        f"<priority>{pr}</priority>{f'<lastmod>{kini}</lastmod>' if cf != 'monthly' else ''}</url>"
        for p, cf, pr in urls)
    with open(os.path.join(docs, "sitemap.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f'{entri}</urlset>\n')
    print(f"✅ robots.txt + sitemap.xml ({len(urls)} URL)")


if __name__ == "__main__":
    utama()
