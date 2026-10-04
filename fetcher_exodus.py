#!/usr/bin/env python3
# ==========================================
# 📡 FETCHER EXODUS — ambil data screener Stockbit (Financial Metric & hasil)
# Sumber: exodus.stockbit.com dengan Bearer token (sesi milik sendiri)
# Token : token_stockbit.txt (umur 24 jam, diperbarui manual — cek exp otomatis)
# Cache : Database/cache_exodus/*.json (TTL menit)
# Jalankan: ./.venv/bin/python fetcher_exodus.py metric          -> katalog 360 metrik
#           ./.venv/bin/python fetcher_exodus.py hasil 6769839   -> hasil template (semua halaman)
#           ./.venv/bin/python fetcher_exodus.py fundamental     -> fundamental semua saham -> Database/fundamental_exodus.csv
#           ./.venv/bin/python fetcher_exodus.py status          -> cek umur token
# Exit: 0 sukses | 2 token hilang/mati | 3 HTTP error | 4 data cacat
# ==========================================
import os, sys, json, time, argparse
from datetime import datetime, timezone, timedelta
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
FILE_TOKEN = os.path.join(BASE, "token_stockbit.txt")
DIR_CACHE = os.path.join(BASE, "Database", "cache_exodus")
FILE_FUND = os.path.join(BASE, "Database", "fundamental_exodus.csv")
WIB = timezone(timedelta(hours=7))
URL_METRIC = "https://exodus.stockbit.com/screener/metric"
URL_TEMPLATE = "https://exodus.stockbit.com/screener/templates/{tid}"
URL_RUN = "https://exodus.stockbit.com/screener/templates"
HEADERS = {
    "accept": "application/json",
    "origin": "https://stockbit.com",
    "referer": "https://stockbit.com/",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
}

# Kolom fundamental yang ditarik (nama sesuai katalog /screener/metric).
# Catatan: metrik Profitability (id 12/13/14: Gross/Operating/Net Profit Margin)
# ditolak server (404) saat dipakai di run endpoint — tidak bisa diikutkan.
KOLOM_FUNDAMENTAL = [
    "Price", "Market Cap", "Current PE Ratio (TTM)", "Current Price to Book Value",
    "Current Price to Sales (TTM)", "Earnings Yield (TTM)", "Dividend Yield",
    "Piotroski F-Score", "EPS Rating", "Relative Strength Rating",
    "Current Book Value Per Share", "PEG Ratio",
]
FILTER_BAWAAN = -999999999  # ambang "selalu lolos" agar tiap kolom ikut ter-render
PAGE_DELAY = 1.0  # jeda antar halaman (sopan, tanpa membanjiri server)


def _b64d(s):
    import base64
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def baca_token():
    """Baca token + payload exp. Return (token, exp) atau (None, None)."""
    if not os.path.exists(FILE_TOKEN):
        return None, None
    tok = open(FILE_TOKEN).read().strip()
    if not tok:
        return None, None
    try:
        payload = json.loads(_b64d(tok.split(".")[1]))
        exp = int(payload["exp"])
        return tok, exp
    except Exception:
        return None, None


def status_token(quiet=False):
    tok, exp = baca_token()
    if tok is None:
        if not quiet:
            print("❌ Token tidak ada / rusak:", FILE_TOKEN)
        return None, None
    sisa = (exp - datetime.now(timezone.utc).timestamp()) / 3600
    if not quiet:
        t = datetime.fromtimestamp(exp, WIB).strftime("%Y-%m-%d %H:%M WIB")
        emoji = "✅" if sisa > 1 else ("⚠️" if sisa > 0 else "⌛")
        print(f"{emoji} Token: sisa {sisa:.1f} jam (exp {t})")
    return tok, sisa


def _cache_path(nama):
    os.makedirs(DIR_CACHE, exist_ok=True)
    return os.path.join(DIR_CACHE, nama + ".json")


def baca_cache(nama, ttl_menit):
    p = _cache_path(nama)
    if not os.path.exists(p):
        return None
    if time.time() - os.path.getmtime(p) > ttl_menit * 60:
        return None
    try:
        return json.load(open(p))
    except Exception:
        return None


def tulis_cache(nama, data):
    p = _cache_path(nama)
    with open(p, "w") as f:
        json.dump(data, f)


def _get(url, token, params=None):
    r = requests.get(url, headers={**HEADERS, "Authorization": f"Bearer {token}"},
                     params=params, timeout=20)
    return r


def ambil_metric(token, paksa=False):
    """Katalog Select Financial Metric: 15 grup, 360 metrik (fitem_id & nama)."""
    if not paksa:
        c = baca_cache("metric", 1440)  # katalog jarang berubah: TTL 24 jam
        if c is not None:
            print("📦 Katalog metrik dari cache (24 jam). --force untuk segarkan.")
            return c
    r = _get(URL_METRIC, token)
    if r.status_code != 200:
        print(f"❌ HTTP {r.status_code} — {r.text[:100]}")
        sys.exit(3)
    d = r.json()
    grup = d.get("data") or []
    if not grup:
        print("❌ Data katalog kosong/cacat.")
        sys.exit(4)
    hasil = {"diambil": datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S"),
             "jumlah_grup": len(grup),
             "jumlah_metrik": sum(len(g.get("child", [])) for g in grup),
             "grup": grup}
    tulis_cache("metric", hasil)
    print(f"✅ Katalog metrik: {hasil['jumlah_grup']} grup, {hasil['jumlah_metrik']} metrik → {DIR_CACHE}/metric.json")
    return hasil


def ambil_hasil_template(token, template_id, paksa=False):
    """Hasil screening template custom: semua halaman (calcs = nilai metrik per saham)."""
    nama = f"template_{template_id}"
    if not paksa:
        c = baca_cache(nama, 15)  # hasil screening: TTL 15 menit
        if c is not None:
            print("📦 Hasil template dari cache (15 menit). --force untuk segarkan.")
            return c
    # Halaman 1: dapatkan totalrows & perpage
    r = _get(URL_TEMPLATE.format(tid=template_id), token, params={"type": "TEMPLATE_TYPE_CUSTOM", "page": 1})
    if r.status_code != 200:
        print(f"❌ HTTP {r.status_code} — {r.text[:100]}")
        sys.exit(3)
    d1 = (r.json().get("data") or {})
    total = int(d1.get("totalrows") or 0)
    per = int(d1.get("perpage") or 25)
    if not total:
        print("❌ Template kosong / tidak ditemukan (cek id & bahwa template milik akunmu).")
        sys.exit(4)
    n_hal = (total + per - 1) // per
    calcs = list(d1.get("calcs") or [])
    print(f"📄 Template {template_id}: {total} saham, {n_hal} halaman...")
    for pg in range(2, n_hal + 1):
        time.sleep(PAGE_DELAY)
        rp = _get(URL_TEMPLATE.format(tid=template_id), token,
                  params={"type": "TEMPLATE_TYPE_CUSTOM", "page": pg})
        if rp.status_code != 200:
            print(f"⚠️ Halaman {pg} gagal (HTTP {rp.status_code}) — pakai yang sudah terkumpul.")
            break
        calcs += (rp.json().get("data") or {}).get("calcs") or []
        print(f"   halaman {pg}/{n_hal}: total {len(calcs)} baris")
    hasil = {"diambil": datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S"),
             "template_id": template_id, "totalrows": total,
             "screen_name": d1.get("screen_name"), "rules": d1.get("rules"),
             "universe": d1.get("universe"), "calcs": calcs}
    tulis_cache(nama, hasil)
    print(f"✅ {len(calcs)}/{total} baris tersimpan → {DIR_CACHE}/{nama}.json")
    return hasil


def _id_metrik(katalog, nama):
    for g in katalog.get("grup", []):
        for c in g.get("child", []):
            if c["fitem_name"] == nama:
                return c["fitem_id"]
    return None


def _run_screener(token, katalog, page):
    """POST /screener/templates (save:0, run-only) — kolom fundamental, semua saham IHSG.
    Trik: tiap metrik juga dipasang sebagai filter '> ambang super rendah' agar
    server merender kolomnya; satu-satunya penyaring efektif adalah Price>0.
    Retry otomatis utk 429/5xx/timeout (2x percobaan). Return (data, None) atau
    (None, err) — err berawalan 'KATALOG:' bila katalog perlu disegarkan."""
    ids = []
    for n in KOLOM_FUNDAMENTAL:
        i = _id_metrik(katalog, n)
        if i is None:
            print(f"⚠️ Metrik '{n}' tidak ada di katalog — dilewati.")
        else:
            ids.append(i)
    if len(ids) < 2:
        print("❌ Terlalu sedikit metrik valid — tarik katalog dulu: fetcher_exodus.py metric")
        sys.exit(4)
    filters = [{"type": "basic", "item1": i, "item1name": "", "operator": ">",
                "item2": str(FILTER_BAWAAN), "multiplier": "0"} for i in ids]
    p = {"name": "TEMPLATE_BUILD_EXODUS_FETCH", "description": "", "save": "0",
         "ordertype": "asc", "ordercol": 2, "page": page, "screenerid": "0",
         "type": "TEMPLATE_TYPE_CUSTOM",
         "universe": json.dumps({"scope": "IHSG", "scopeID": "0", "name": "IHSG"}),
         "filters": json.dumps(filters), "sequence": ",".join(map(str, ids))}
    backoff = 3
    for percobaan in range(1, 4):
        try:
            r = requests.post(URL_RUN, headers={**HEADERS, "Authorization": f"Bearer {token}"},
                              json=p, timeout=60)
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Halaman {page} jaringan gagal (coba {percobaan}/3): {e}")
            time.sleep(backoff); backoff = min(backoff * 2, 20)
            continue
        if r.status_code == 200:
            return r.json().get("data") or {}, None
        if r.status_code == 404:
            return None, "KATALOG:Item Metrics Not Found (katalog bergeser)"
        if r.status_code in (429, 500, 502, 503, 504):
            print(f"⚠️ Halaman {page} HTTP {r.status_code} (coba {percobaan}/3) — tunggu {backoff}s")
            time.sleep(backoff); backoff = min(backoff * 2, 20)
            continue
        return None, f"HTTP {r.status_code}: {r.text[:100]}"
    return None, f"HTTP error berulang pada halaman {page}"


def ambil_fundamental(token, paksa=False):
    """Fundamental SEMUA saham IHSG → Database/fundamental_exodus.csv (+ upload R2)."""
    import pandas as pd
    if not paksa:
        c = baca_cache("fundamental", 180)  # data fundamental lambat berubah: TTL 3 jam
        if c is not None:
            print("📦 Fundamental dari cache (3 jam). --force untuk segarkan.")
            return c
    katalog = baca_cache("metric", 10**9)  # pakai katalog tersimpan apa adanya
    if not katalog:
        katalog = ambil_metric(token)
    d1, err = _run_screener(token, katalog, 1)
    if err and err.startswith("KATALOG:"):
        # Katalog bergeser → segarkan lalu coba sekali lagi
        print("🔄 Katalog metrik usang, segarkan...")
        katalog = ambil_metric(token, paksa=True)
        d1, err = _run_screener(token, katalog, 1)
    if err:
        print("❌", err); sys.exit(3)
    total = int(d1.get("totalrows") or 0)
    per = int(d1.get("perpage") or 25)
    if not total:
        print("❌ Run screener kosong."); sys.exit(4)
    n_hal = (total + per - 1) // per
    calcs = list(d1.get("calcs") or [])
    print(f"📄 Fundamental: {total} saham, {n_hal} halaman...")
    for pg in range(2, n_hal + 1):
        time.sleep(PAGE_DELAY)
        dp, err = _run_screener(token, katalog, pg)
        if err:
            if err.startswith("KATALOG:"):
                # Katalog bergeser di tengah jalan → segarkan & ulangi halaman ini
                katalog = ambil_metric(token, paksa=True)
                dp, err = _run_screener(token, katalog, pg)
            if err:
                print(f"⚠️ Halaman {pg} gagal ({err}) — pakai yang sudah terkumpul.")
                break
        calcs += dp.get("calcs") or []
        print(f"   halaman {pg}/{n_hal}: total {len(calcs)} baris")

    # Bentuk DataFrame: ticker + kolom nilai (raw)
    baris = []
    for c in calcs:
        row = {"Ticker": c.get("company", {}).get("symbol", "").upper()}
        for r_ in c.get("results", []):
            row[r_["item"]] = r_.get("raw")
        baris.append(row)
    df = pd.DataFrame(baris).drop_duplicates(subset="Ticker")
    if df.empty:
        print("❌ Tidak ada baris valid dari run screener."); sys.exit(4)
    df = df[~df["Ticker"].astype(str).str.contains(r"\.", na=False)]  # buang warrants (B*-W dll.)
    # Buang baris semua-nol (saham tidak aktif — contoh: SWAP) agar tidak jadi noise di web
    num_cols = [c for c in df.columns if c != "Ticker"]
    if num_cols:
        mask_nol = (df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0) == 0).all(axis=1)
        n_buang = int(mask_nol.sum())
        if n_buang:
            df = df[~mask_nol]
            print(f"🧹 {n_buang} baris semua-nol (saham tidak aktif) dibuang.")
    if df.empty:
        print("❌ Semua baris kosong setelah pembersihan."); sys.exit(4)
    df["Diambil"] = datetime.now(WIB).strftime("%Y-%m-%d %H:%M")
    df.to_csv(FILE_FUND, index=False)
    hasil = {"diambil": df["Diambil"].iloc[0], "jumlah": len(df), "kolom": KOLOM_FUNDAMENTAL}
    tulis_cache("fundamental", hasil)
    print(f"✅ {len(df)} saham × {len(KOLOM_FUNDAMENTAL)} metrik → {FILE_FUND}")
    try:
        import r2_client
        if r2_client.upload_arsip(FILE_FUND, "Database/fundamental_exodus.csv"):
            print("☁️ fundamental_exodus.csv ter-upload ke R2 (web bisa baca).")
    except Exception as e:
        print(f"⚠️ Upload R2 gagal (file lokal tetap ada): {e}")
    return hasil


def main():
    ap = argparse.ArgumentParser(description="Fetcher data screener exodus Stockbit")
    ap.add_argument("perintah", choices=["metric", "hasil", "fundamental", "status"])
    ap.add_argument("template_id", nargs="?", help="id template custom (untuk 'hasil'), mis. 6769839")
    ap.add_argument("--force", action="store_true", help="abaikan cache")
    args = ap.parse_args()

    tok, sisa = status_token()
    if args.perintah == "status":
        sys.exit(0 if tok else 2)
    if tok is None:
        print("   Perbarui token_stockbit.txt (umur token 24 jam — ambil dari browser).")
        sys.exit(2)
    if sisa is not None and sisa <= 0:
        print("❌ Token sudah kedaluwarsa. Perbarui token_stockbit.txt dulu.")
        sys.exit(2)

    if args.perintah == "metric":
        ambil_metric(tok, paksa=args.force)
    elif args.perintah == "hasil":
        if not args.template_id:
            print("❌ Sebutkan id template. Contoh: fetcher_exodus.py hasil 6769839")
            print("   Lihat daftar: Database/cache_exodus — atau endpoint /screener/favorites")
            sys.exit(2)
        ambil_hasil_template(tok, args.template_id, paksa=args.force)
    elif args.perintah == "fundamental":
        ambil_fundamental(tok, paksa=args.force)


if __name__ == "__main__":
    main()
