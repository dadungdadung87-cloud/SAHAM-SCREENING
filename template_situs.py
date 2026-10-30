# ==========================================
# 🎨 TEMPLATE SITUS — satu sumber untuk semua halaman publik
# Dipakai: buat_artikel.py, buat_halaman_publik.py, (nanti) buat_halaman_saham.py
# Berisi: CSS tema gelap terpadu, nav, header, footer, canonical,
#         Open Graph/Twitter card, JSON-LD (WebSite/Article), AdSense hook.
# Ganti tema cukup di sini — semua halaman ikut.
# ==========================================
import html
import json
import sys
import os
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from konfig_situs import (SITE_URL, SITE_NAME, SITE_DESC, ADSENSE_CLIENT,
                          ADSENSE_SLOT_ATAS, ADSENSE_SLOT_TENGAH, ADSENSE_SLOT_BAWAH,
                          BROKER_REF, TELEGRAM_URL, SEO_KEYWORDS)

WIB = timezone(timedelta(hours=7))
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E"
           "%3Ctext y='.9em' font-size='90'%3E%F0%9F%93%88%3C/text%3E%3C/svg%3E")

NAV_ITEMS = [
    ("", "Beranda"),
    ("market.html", "Market"),
    ("screener.html", "Screener"),
    ("radar.html", "Radar AI"),
    ("detektif.html", "Detektif"),
    ("artikel/index.html", "Artikel"),
    ("saham/", "Grafik Saham"),
]

# Tema gelap terpadu — superset dari dua template lama (.tbl & .table-wrap,
# .grid/.card & .feature-grid, .hero, .notice, dsb) agar semua halaman lama tetap tampil benar.
CSS = """
:root{--bg:#0f172a;--card:#1e293b;--line:#334155;--txt:#cbd5e1;--hi:#f8fafc;
--acc:#38bdf8;--up:#22c55e;--dn:#ef4444;--warn:#facc15}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font:16px/1.65 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:24px 18px}
header{padding:22px 0 12px}
header h1{margin:0;font-size:clamp(1.7rem,4vw,3rem);line-height:1.1;color:var(--hi);letter-spacing:-.04em}
header h1 a{color:var(--acc);text-decoration:none}
header p{max-width:720px;color:#94a3b8;font-size:1.02rem;margin:.5em 0 0}
.topnav{display:flex;gap:8px;flex-wrap:wrap;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:12px 0;margin:12px 0 26px}
.topnav a{color:#94a3b8;text-decoration:none;padding:7px 11px;border-radius:7px;font-size:.9rem}
.topnav a:hover,.topnav a.active{background:var(--card);color:var(--acc)}
h2{color:var(--hi);margin-top:34px}h3{color:var(--acc)}
p{margin:.6em 0}
a{color:var(--acc)}
code{background:var(--card);padding:2px 8px;border-radius:6px;color:var(--acc);font-weight:600}
.tbl,.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin:14px 0}
table{border-collapse:collapse;width:100%;min-width:560px;font-size:.9rem}
th{background:var(--card);color:var(--hi);text-align:left;padding:10px 12px;border-bottom:2px solid var(--acc);white-space:nowrap}
td{padding:9px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
tr:nth-child(even) td{background:rgba(30,41,59,.4)}
.up{color:var(--up);font-weight:600}.down{color:var(--dn);font-weight:600}
.cta{display:inline-block;background:linear-gradient(135deg,#38bdf8,#818cf8);color:#07111f;font-weight:700;padding:12px 16px;border-radius:10px;text-decoration:none;margin:22px 0}
.grid,.feature-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:18px 0 24px}
.card,.feature{background:rgba(30,41,59,.58);border:1px solid var(--line);border-radius:12px;padding:15px}
.card strong{font-size:1.45rem;color:var(--hi);display:block}.card small{color:#94a3b8}
.feature b{display:block;color:var(--hi);margin:7px 0 4px}.feature span{font-size:.88rem;color:#94a3b8}
.hero{background:radial-gradient(circle at 90% 0%,rgba(56,189,248,.2),transparent 38%),linear-gradient(145deg,#172a46,#101827);border:1px solid #2b5171;border-radius:18px;padding:30px;margin:8px 0 24px;box-shadow:0 18px 50px rgba(0,0,0,.2)}
.hero .eyebrow{color:var(--acc);font-size:.78rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}
.hero h2{font-size:clamp(1.5rem,3.5vw,2.3rem);margin:9px 0 10px;max-width:760px}
.hero p{max-width:700px;color:#cbd5e1;font-size:1.02rem}
.hero-links{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px}
.hero-links a{background:var(--acc);color:#07111f;text-decoration:none;font-weight:800;padding:10px 14px;border-radius:9px}
.hero-links a.alt{background:transparent;color:var(--txt);border:1px solid var(--line)}
.notice{border-left:4px solid var(--warn);background:#241f0d;padding:12px;border-radius:6px}
.muted,.kosong{color:#94a3b8}.kosong{font-style:italic}
.back{color:var(--acc)}
.ad{margin:26px 0;min-height:90px}
.afil{margin-top:40px;border-top:1px solid var(--line);padding-top:18px;font-size:.92rem;display:flex;flex-wrap:wrap;gap:10px 22px;align-items:center}
.afil a{color:var(--acc);font-weight:600}.afil-desk{color:#94a3b8}
ul.artikel-list{list-style:none;padding:0}ul.artikel-list li{padding:10px 0;border-bottom:1px solid var(--line)}
.meta-line{color:#94a3b8;font-size:.88rem;margin:0 0 6px}
footer{margin-top:48px;border-top:1px solid var(--line);padding-top:16px;font-size:.85rem;color:#94a3b8}
@media(max-width:700px){.hero{padding:22px 18px}.wrap{padding:18px 12px}}
"""


def esc(v):
    return html.escape(str(v))


def url_full(path_rel=""):
    return SITE_URL + path_rel


def adsense_head():
    if not ADSENSE_CLIENT:
        return ""
    return (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'
            f'?client={esc(ADSENSE_CLIENT)}" crossorigin="anonymous"></script>')


def adsense_unit(slot):
    if not ADSENSE_CLIENT or not slot:
        return ""
    return (f'<ins class="adsbygoogle" style="display:block" data-ad-client="{esc(ADSENSE_CLIENT)}" '
            f'data-ad-slot="{esc(slot)}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
            '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>')


def footer_affiliate():
    baris = "".join(
        f'<a href="{esc(b["url"])}" target="_blank" rel="sponsored noopener">{esc(b["nama"])}</a>'
        f'<span class="afil-desk">{esc(b["deskripsi"])}</span>'
        for b in BROKER_REF if b.get("url"))
    tg = (f'<a href="{esc(TELEGRAM_URL)}" target="_blank" rel="noopener">📢 Channel Telegram</a>'
          if TELEGRAM_URL else "")
    return baris + tg


def json_ld(jenis, judul, path_rel, waktu_publish=None):
    if jenis == "article":
        data = {
            "@context": "https://schema.org", "@type": "Article",
            "headline": judul, "inLanguage": "id-ID",
            "author": {"@type": "Organization", "name": SITE_NAME},
            "publisher": {"@type": "Organization", "name": SITE_NAME},
            "mainEntityOfPage": url_full(path_rel),
        }
        if waktu_publish:
            data["datePublished"] = waktu_publish
            data["dateModified"] = waktu_publish
    else:
        data = {
            "@context": "https://schema.org", "@type": "WebSite",
            "name": SITE_NAME, "url": SITE_URL, "description": SITE_DESC,
            "inLanguage": "id-ID",
        }
    return (f'<script type="application/ld+json">'
            f'{html.escape(json.dumps(data, ensure_ascii=False), quote=False)}'
            f'</script>')


def layout(judul, isi, path_rel="", jenis="website", waktu_publish=None,
           deskripsi=None, css_extra="", active_path=None, head_extra=""):
    """Bangun halaman HTML lengkap.
    judul          : judul halaman TANPA nama situs (otomatis digabung, bebas bug dobel)
    path_rel       : path relatif dari root situs utk canonical/OG ("" = beranda)
    jenis          : "website" | "article" (JSON-LD)
    waktu_publish  : datetime (utk article:published_time & JSON-LD)
    deskripsi      : override meta description per halaman
    active_path    : path nav yang ditandai aktif (default = path_rel)
    head_extra     : HTML tambahan di <head> (mis. <script src> eksternal)
    """
    path_rel = path_rel.lstrip("/")
    aktif = active_path if active_path is not None else path_rel
    full_title = f"{judul} | {SITE_NAME}" if judul else SITE_NAME
    desc = deskripsi or SITE_DESC
    canonical = url_full(path_rel)
    iso = waktu_publish.astimezone(WIB).isoformat() if waktu_publish else None

    nav = "".join(
        f'<a{" class=\"active\"" if p == aktif else ""} href="{url_full(p)}">{label}</a>'
        for p, label in NAV_ITEMS)

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="keywords" content="{esc(SEO_KEYWORDS)}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{esc(canonical)}">
<link rel="icon" href="{FAVICON}">
<meta property="og:type" content="{('article' if jenis == 'article' else 'website')}">
<meta property="og:site_name" content="{esc(SITE_NAME)}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:locale" content="id_ID">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{esc(full_title)}">
<meta name="twitter:description" content="{esc(desc)}">
{f'<meta property="article:published_time" content="{iso}">' if iso else ''}
{adsense_head()}
{json_ld(jenis, judul, path_rel, iso)}
{head_extra}
<style>{CSS}{css_extra}</style>
</head>
<body><div class="wrap">
<header><h1><a href="{url_full()}">{esc(SITE_NAME)}</a></h1>
<p>{esc(SITE_DESC)}</p></header>
<nav class="topnav">{nav}</nav>
<div class="ad">{adsense_unit(ADSENSE_SLOT_ATAS)}</div>
{isi}
<div class="ad">{adsense_unit(ADSENSE_SLOT_TENGAH)}</div>
<div class="ad">{adsense_unit(ADSENSE_SLOT_BAWAH)}</div>
<div class="afil"><strong>Bekal trading kamu:</strong> {footer_affiliate()}</div>
<footer>Disclaimer: seluruh konten bersifat informasi &amp; edukasi, bukan rekomendasi jual-beli efek.
Data berasal dari pemantauan otomatis dan dapat berubah. Do Your Own Research.</footer>
</div></body></html>"""
