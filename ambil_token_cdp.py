#!/usr/bin/env python3
# ==========================================
# 🎫 AMBIL TOKEN VIA CDP — tanpa HAR manual!
# Metode 1 (utama): intersep respons endpoint auth/v1/session saat halaman
#   Stockbit dimuat — selalu berisi access_token segar (terbukti 20 Nov:
#   cookie credentialStorage kosong, tapi respons session tetap penuh).
# Metode 2 (fallback): cookie credentialStorage (carakerja lama).
# Uji validitas: exodus.stockbit.com via curl_cffi (requests polos kena 403).
#
# Alur otomatis: token kedaluwarsa → jaga_token.py panggil skrip ini →
# skrip reload halaman → intersep token → tulis kanonik → sinkron.
#
# Pemakaian:
#   ./.venv/bin/python ambil_token_cdp.py            # ambil + tulis jika lebih segar
#   ./.venv/bin/python ambil_token_cdp.py --navigasi # buka halaman auth dulu (picu fetch token)
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
URL_EXODUS_TEST = "https://exodus.stockbit.com/company-price-feed/historical/summary/BUMI"  # bebas paywall (screener/metric kena 402)
URL_AUTH_PICU = "https://stockbit.com/#/portfolio"   # halaman yang memicu fetch auth
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


async def _intersep_session(ws_url):
    """Navigasikan tab ke halaman ber-auth, intersep respons auth/v1/session,
    ambil data.access_token. Return (token, expired_at) atau (None, None)."""
    async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
        await ws.send(json.dumps({"id": 2, "method": "Page.navigate",
                                  "params": {"url": URL_AUTH_PICU}}))
        akhir = time.time() + 45
        while time.time() < akhir:
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=3))
            except asyncio.TimeoutError:
                continue
            except Exception:
                break
            if msg.get("method") == "Network.responseReceived":
                url = msg["params"]["response"]["url"]
                if "auth/v1/session" in url:
                    rid = msg["params"]["requestId"]
                    status = msg["params"]["response"]["status"]
                    await ws.send(json.dumps({"id": 99, "method": "Network.getResponseBody",
                                              "params": {"requestId": rid}}))
            elif msg.get("id") == 99:
                body = msg.get("result", {}).get("body", "")
                if not body:
                    return None, None
                try:
                    d = json.loads(body)
                except Exception:
                    return None, None
                data = d.get("data") or {}
                tok = data.get("access_token") or ""
                return (tok if tok else None), data.get("expired_at")
    return None, None


async def _segarkan_cookie(ws_url):
    """Reload halaman stockbit.com agar web app fetch token & set cookie."""
    async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"id": 2, "method": "Page.navigate",
                                  "params": {"url": "https://stockbit.com/"}}))
        await asyncio.sleep(6)


def ambil_via_intersep():
    """Metode 1: intersep respons auth/v1/session. Return (tok, exp, sumber/alasan)."""
    ws_url = tab_stockbit()
    if not ws_url:
        return None, 0, "tab Stockbit tidak ditemukan di Thorium (port 9223)"
    try:
        tok, expired_at = asyncio.run(_intersep_session(ws_url))
        if not tok:
            # coba sekali lagi dgn reload eksplisit (kadang navigasi hash tidak memicu fetch)
            asyncio.run(_segarkan_cookie(ws_url))
            ws_url2 = tab_stockbit()
            tok, expired_at = asyncio.run(_intersep_session(ws_url2)) if ws_url2 else (None, None)
        if not tok:
            return None, 0, "respons auth/v1/session tidak tertangkap / tanpa token"
        pl = payload_jwt(tok)
        if not pl or not pl.get("exp"):
            return None, 0, "token dari session bukan JWT valid"
        return tok, int(pl["exp"]), f"intersep auth/v1/session (uid {pl.get('data', {}).get('uid')})"
    except Exception as e:
        return None, 0, f"error intersep: {e}"


def ambil_via_cookie():
    """Metode 2 (fallback): cookie credentialStorage. Return (tok, exp, sumber/alasan)."""
    ws_url = tab_stockbit()
    if not ws_url:
        return None, 0, "tab Stockbit tidak ditemukan di Thorium (port 9223)"
    try:
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
        return tok, int(pl["exp"]), f"cookie credentialStorage (uid {pl.get('data', {}).get('uid')})"
    except Exception as e:
        return None, 0, f"error cookie: {e}"


def ambil_dari_browser(navigasi_dulu=False):
    """Gabungan: intersep dulu, cookie jadi fallback. Return (tok, exp, sumber/alasan)."""
    tok, exp, sumber = ambil_via_intersep()
    if tok:
        return tok, exp, sumber
    print(f"ℹ️ intersep gagal ({sumber}) — coba cookie credentialStorage...")
    return ambil_via_cookie()


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
    ap.add_argument("--navigasi", action="store_true", help="buka halaman ber-auth dulu (picu fetch token)")
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
