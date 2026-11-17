#!/usr/bin/env python3
# ==========================================
# 🎫 AMBIL TOKEN VIA CDP — tanpa HAR manual!
# Sumber: cookie "credentialStorage" di tab Stockbit yang sudah login
# (Thorium port 9223). Token ini terbukti VALID untuk exodus.stockbit.com
# (uji 2026-11-17: HTTP 200 via curl_cffi; requests polos kena 403 Cloudflare).
#
# Alur otomatis: token kedaluwarsa → jaga_token.py panggil skrip ini →
# skrip baca cookie browser (sesi login awet) → tulis ke kanonik → sinkron.
# Tidak perlu user ekspor HAR lagi selama sesi login browser masih hidup.
#
# Pemakaian:
#   ./.venv/bin/python ambil_token_cdp.py            # ambil + tulis jika lebih segar
#   ./.venv/bin/python ambil_token_cdp.py --navigasi # reload stockbit.com dulu (refresh cookie)
#   ./.venv/bin/python ambil_token_cdp.py --status   # cek status token kanonik
#   ./.venv/bin/python ambil_token_cdp.py --paksa    # timpa kanonik tanpa cek umur
# Exit: 0 sukses | 2 gagal ambil | 3 token tidak lebih segar
# ==========================================
import os
import sys
import json
import time
import base64
import argparse
import asyncio
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote

from curl_cffi import requests as cr
import websockets

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = 9223
TIMEOUT = 20
WIB = timezone(timedelta(hours=7))
URL_EXODUS_TEST = "https://exodus.stockbit.com/screener/metric"
HEADERS_EXODUS = {
    "accept": "application/json",
    "origin": "https://stockbit.com",
    "referer": "https://stockbit.com/",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
}


def _base():
    return f"http://127.0.0.1:{PORT}"


def tab_stockbit():
    """Return webSocketDebuggerUrl tab Stockbit yang aktif di Thorium."""
    tabs = cr.get(f"{_base()}/json", timeout=3).json()
    for t in tabs:
        if t.get("type") == "page" and "stockbit" in t.get("url", "").lower():
            return t.get("webSocketDebuggerUrl")
    return None


def _b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def payload_jwt(tok):
    try:
        p = tok.split(".")[1]
        return json.loads(_b64d(p))
    except Exception:
        return None


async def _eval_js(ws_url, ekspresi, id_msg=1):
    """Runtime.evaluate di tab; return nilai string."""
    async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"id": id_msg, "method": "Runtime.evaluate",
                                  "params": {"expression": ekspresi,
                                             "returnByValue": True,
                                             "awaitPromise": True}}))
        akhir = time.time() + TIMEOUT
        while time.time() < akhir:
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=max(0.3, akhir - time.time())))
            except asyncio.TimeoutError:
                break
            except Exception:
                break
            if msg.get("id") == id_msg:
                return (msg.get("result", {}).get("result", {}) or {}).get("value") or ""
    return ""


async def _segarkan_cookie(ws_url):
    """Reload halaman stockbit.com agar web app refresh token & cookie."""
    async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"id": 2, "method": "Page.navigate",
                                  "params": {"url": "https://stockbit.com/"}}))
        await asyncio.sleep(6)  # beri waktu app fetch token baru & set cookie


def ambil_dari_browser(navigasi_dulu=False):
    """Ambil (token, exp_epoch, sumber) dari cookie credentialStorage browser.
    Return (None, 0, alasan) bila gagal."""
    ws_url = tab_stockbit()
    if not ws_url:
        return None, 0, "tab Stockbit tidak ditemukan di Thorium (port 9223)"
    try:
        if navigasi_dulu:
            asyncio.run(_segarkan_cookie(ws_url))
        raw = asyncio.run(_eval_js(
            ws_url,
            "(() => { const c = document.cookie.match(/credentialStorage=([^;]+)/);"
            " return c ? c[1] : ''; })()"))
        if not raw:
            return None, 0, "cookie credentialStorage tidak ada (belum login?)"
        d = json.loads(unquote(raw))
        acc = (d.get("state") or {}).get("access") or {}
        tok = acc.get("token") or ""
        if not tok:
            return None, 0, "access.token kosong di credentialStorage"
        pl = payload_jwt(tok)
        if not pl or not pl.get("exp"):
            return None, 0, "token bukan JWT valid"
        if "STOCKBIT" not in str(pl.get("iss", "")).upper():
            return None, 0, f"iss bukan STOCKBIT ({pl.get('iss')})"
        return tok, int(pl["exp"]), f"cookie credentialStorage (uid {pl.get('data', {}).get('uid')})"
    except Exception as e:
        return None, 0, f"error: {e}"


def uji_exodus(tok):
    """True bila token diterima exodus (curl_cffi, bypass TLS fingerprint)."""
    try:
        r = cr.get(URL_EXODUS_TEST, impersonate="chrome",
                   headers={**HEADERS_EXODUS, "Authorization": f"Bearer {tok}"}, timeout=15)
        return r.status_code == 200
    except Exception:
        return False


def baca_kanonik():
    fp = os.path.join(BASE, "token_stockbit.txt")
    if not os.path.exists(fp):
        return "", 0
    tok = open(fp).read().strip()
    pl = payload_jwt(tok) if tok else None
    return tok, (int(pl["exp"]) if pl and pl.get("exp") else 0)


def simpan(tok):
    fp = os.path.join(BASE, "token_stockbit.txt")
    if os.path.exists(fp):
        import shutil
        shutil.copy2(fp, fp + ".bak")
    tmp = fp + ".tmp"
    with open(tmp, "w") as f:
        f.write(tok)
    os.chmod(tmp, 0o600)
    os.replace(tmp, fp)


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--navigasi", action="store_true", help="reload stockbit.com dulu (segar cookie)")
    ap.add_argument("--paksa", action="store_true", help="timpa kanonik tanpa cek umur")
    ap.add_argument("--tanpa-uji", action="store_true", help="lewati uji exodus (lebih cepat)")
    ap.add_argument("--status", action="store_true", help="hanya cek status")
    a = ap.parse_args()

    if a.status:
        tok, exp = baca_kanonik()
        if tok and exp > time.time():
            print(f"✅ kanonik OK — sisa {(exp - time.time()) / 3600:.1f} jam "
                  f"(exp {datetime.fromtimestamp(exp, WIB):%d %b %H:%M} WIB)")
        else:
            print("❌ kanonik MATI/kosong")
        sys.exit(0 if tok and exp > time.time() else 2)

    tok_baru, exp_baru, sumber = ambil_dari_browser(navigasi_dulu=a.navigasi)
    if not tok_baru:
        print(f"❌ {sumber}")
        sys.exit(2)

    exp_lama = baca_kanonik()[1]
    if not a.paksa and exp_baru <= exp_lama:
        print(f"⏭️ Token browser tidak lebih segar dari kanonik "
              f"(baru {datetime.fromtimestamp(exp_baru, WIB):%H:%M} vs lama "
              f"{datetime.fromtimestamp(exp_lama, WIB):%H:%M}) — tidak ditulis.")
        sys.exit(3)

    if not a.tanpa_uji and not uji_exodus(tok_baru):
        print("❌ Token browser DITOLAK exodus (uji gagal) — tidak ditulis.")
        sys.exit(2)

    simpan(tok_baru)
    sisa = (exp_baru - time.time()) / 3600
    print(f"✅ Token baru tersimpan (dari {sumber}) — sisa {sisa:.1f} jam "
          f"(exp {datetime.fromtimestamp(exp_baru, WIB):%d %b %H:%M} WIB)")
    print("   jaga_token.py akan menyinkronkan ke DATA-CENTER & WEB-SCREENING.")


if __name__ == "__main__":
    utama()
