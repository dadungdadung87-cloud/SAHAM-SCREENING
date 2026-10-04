#!/usr/bin/env python3
# ==========================================
# 🔑 AMBIL TOKEN — ekstrak token Stockbit dari file HAR
# Sumber: ekspor DevTools "Save all as HAR with content" (bukan versi sanitized)
# Output: token_stockbit.txt (backup otomatis ke .bak)
# Jalankan: ./.venv/bin/python ambil_token.py [--folder ~/Downloads] [--dry-run] [--test]
# Exit code: 0 sukses | 2 token tidak ditemukan | 3 semua token kedaluwarsa
# ==========================================
import os, sys, json, glob, re, base64, argparse, shutil
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DEFAULT = os.path.join(BASE, "token_stockbit.txt")
WIB = timezone(timedelta(hours=7))
JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*")
HEADER_AUTH = {"authorization", "cookie", "x-auth-token", "x-token", "x-access-token"}


def _b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def parse_jwt(tok):
    """Kembalikan payload JWT jika valid & punya klaim exp; selain itu None."""
    try:
        parts = tok.split(".")
        if len(parts) < 2:
            return None
        payload = json.loads(_b64d(parts[1]))
        exp = payload.get("exp")
        if not isinstance(exp, (int, float)):
            return None
        payload["exp"] = int(exp)
        return payload
    except Exception:
        return None


def adalah_token_stockbit(payload):
    """Token exodus/stream: iss='STOCKBIT' (JWT klasik), ATAU bukan token khusus
    partner lain (mis. EIPO_PARTNER_ACCESS). Menghindari salah ambil token eIPO."""
    if not payload:
        return False
    iss = str(payload.get("iss", "")).upper()
    if "STOCKBIT" in iss:
        return True
    tipe = str(payload.get("token_type", "")).upper()
    return not tipe  # JWT tanpa token_type spesifik → perlakukan sebagai token umum


def kandidat_dari_har(path):
    """Yield (token, sumber) untuk semua JWT-like di dalam satu file HAR."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            har = json.load(f)
    except Exception as e:
        print(f"⚠️ Gagal baca {path}: {e}")
        return
    entries = har.get("log", {}).get("entries", [])
    for i, e in enumerate(entries):
        req = e.get("request") or {}
        res = e.get("response") or {}
        url = req.get("url", "")

        # 1) Header request (Authorization, Cookie, dsb.)
        for h in req.get("headers", []):
            v = h.get("value") or ""
            if h.get("name", "").lower() in HEADER_AUTH or "eyJ" in v:
                for m in JWT_RE.findall(v):
                    yield m, f"header {h['name']} @ entry[{i}] {url[:60]}"

        # 2) Cookie terstruktur (array HAR)
        for c in (req.get("cookies") or []) + (res.get("cookies") or []):
            for m in JWT_RE.findall(str(c.get("value") or "")):
                yield m, f"cookie {c.get('name')} @ entry[{i}]"

        # 3) Set-Cookie di response
        for h in res.get("headers", []):
            if h.get("name", "").lower() == "set-cookie":
                for m in JWT_RE.findall(h.get("value") or ""):
                    yield m, f"set-cookie @ entry[{i}] {url[:60]}"

        # 4) Body response (mis. endpoint refresh token) & body POST
        txt = (res.get("content") or {}).get("text") or ""
        if "eyJ" in txt:
            for m in JWT_RE.findall(txt):
                yield m, f"body-response @ entry[{i}] {url[:60]}"
        pd = (req.get("postData") or {}).get("text") or ""
        if "eyJ" in pd:
            for m in JWT_RE.findall(pd):
                yield m, f"body-request @ entry[{i}] {url[:60]}"

        # 5) Query string URL
        if "eyJ" in url:
            for m in JWT_RE.findall(url):
                yield m, f"query @ entry[{i}] {url[:60]}"


def pilih_token(files):
    """Pilih token terbaik: exp terbaru yang masih hidup. Return (token, payload, sumber) atau (None, payload_expired, sumber)."""
    hidup, mati = [], []
    for path in files:
        for tok, sumber in kandidat_dari_har(path):
            payload = parse_jwt(tok)
            if payload is None:
                continue
            if not adalah_token_stockbit(payload):
                continue  # token penyedia lain (mis. EIPO_PARTNER_ACCESS)
            (hidup if payload["exp"] > datetime.now(timezone.utc).timestamp() else mati).append((tok, payload, sumber))
    if hidup:
        hidup.sort(key=lambda x: x[1]["exp"], reverse=True)
        return hidup[0]
    if mati:
        mati.sort(key=lambda x: x[1]["exp"], reverse=True)
        return (None,) + mati[0][1:]
    return None, None, None


def uji_token(token):
    """1x request ringan ke exodus untuk memastikan token diterima."""
    try:
        from curl_cffi import requests as cr
        r = cr.get("https://exodus.stockbit.com/screener/metric", impersonate="chrome",
                   headers={"Authorization": f"Bearer {token}", "accept": "application/json",
                            "origin": "https://stockbit.com", "referer": "https://stockbit.com/"}, timeout=15)
        return r.status_code
    except ImportError:
        import urllib.request, urllib.error
        req = urllib.request.Request("https://exodus.stockbit.com/screener/metric",
                                     headers={"Authorization": f"Bearer {token}", "accept": "application/json",
                                              "origin": "https://stockbit.com", "referer": "https://stockbit.com/"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
    except Exception as e:
        print(f"⚠️ Uji jaringan gagal: {e}")
        return -1


def tulis_token(token, out_path, dry_run):
    if os.path.exists(out_path):
        bak = out_path + ".bak"
        shutil.copy2(out_path, bak)
        if not dry_run:
            print(f"🗃️  Token lama dicadangkan: {bak}")
    if dry_run:
        print(f"🧪 DRY-RUN — token TIDAK ditulis ke {out_path}")
        return
    with open(out_path, "w") as f:
        f.write(token + "\n")
    os.chmod(out_path, 0o600)
    print(f"✅ Token ditulis: {out_path}")


def main():
    ap = argparse.ArgumentParser(description="Ekstrak token Stockbit dari file HAR")
    ap.add_argument("--folder", default=os.path.expanduser("~/Downloads"), help="folder berisi *.har (default: ~/Downloads)")
    ap.add_argument("--files", nargs="*", help="path HAR eksplisit (mengabaikan --folder)")
    ap.add_argument("--out", default=OUT_DEFAULT, help="file output token")
    ap.add_argument("--dry-run", action="store_true", help="lapor saja, jangan tulis file")
    ap.add_argument("--force", action="store_true", help="tulis walau token sudah kedaluwarsa")
    ap.add_argument("--test", action="store_true", help="uji 1x request ke exodus setelah ekstraksi")
    ap.add_argument("--quiet", action="store_true", help="output singkat (untuk cron)")
    args = ap.parse_args()

    files = args.files or sorted(glob.glob(os.path.join(args.folder, "*.har")), key=os.path.getmtime, reverse=True)
    if not files:
        print(f"❌ Tidak ada file .har di {args.folder}")
        sys.exit(2)
    if not args.quiet:
        print(f"📂 Memindai {len(files)} file HAR (terbaru: {os.path.basename(files[0])}) ...")

    token, payload, sumber = pilih_token(files)
    if payload is None:
        print("❌ Tidak ada JWT dengan klaim exp di HAR ini.")
        print("   → Ekspor ulang dari DevTools: klik kanan jaringan → 'Save all as HAR with content'")
        print("     (bukan 'Export HAR (sanitized)' — versi itu menghapus token/cookie).")
        sys.exit(2)

    exp_wib = datetime.fromtimestamp(payload["exp"], WIB)
    sisa = payload["exp"] - datetime.now(timezone.utc).timestamp()
    if token is None and not args.force:
        print(f"⌛ Token ditemukan ({sumber}) tapi KEDALUWARSA {exp_wib.strftime('%Y-%m-%d %H:%M WIB')} ({-sisa/3600:.1f} jam lalu).")
        print("   Token tidak ditulis. Ambil HAR baru dari sesi yang masih login, atau pakai --force.")
        sys.exit(3)

    if not args.quiet:
        print(f"🔑 Token ditemukan: {sumber}")
        print(f"   exp = {exp_wib.strftime('%Y-%m-%d %H:%M WIB')} (sisa {sisa/3600:.1f} jam)")

    if args.test and token:
        kode = uji_token(token)
        arti = {200: "OK — token diterima", 401: "Ditolak (401) — token mati/invalid",
                403: "Diblok Cloudflare (403) — status token tak pasti"}.get(kode, f"HTTP {kode}")
        print(f"🧪 Uji exodus: {arti}")
        if kode == 401 and not args.force:
            print("   Token tidak ditulis karena gagal uji.")
            sys.exit(3)

    tulis_token(token, args.out, args.dry_run)
    sys.exit(0)


if __name__ == "__main__":
    main()
