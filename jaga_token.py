#!/usr/bin/env python3
# ==========================================
# 🔑 JAGA TOKEN STOCKBIT — penjaga token otomatis (run via cron tiap 10 menit)
# Sumber kanonik: /home/kaltaraid/Documents/SAHAM-SCREENING/token_stockbit.txt
# Tugas:
#   1. Cek exp token kanonik (umur 24 jam).
#   2. Sinkron salinan ke semua konsumen (DATA-CENTER, WEB-SCREENING, dsb).
#   3. Jika token mati: scan HAR baru di ~/Downloads (hasil ekspor DevTools
#      alur harian user — ambil_token.py) lalu extract token terbaru.
#   4. Alarm Telegram saat mati/berhasil pulih (tanpa spam — jeda alarm 3 jam).
#   5. Opsional --auto-sync-harian: scan HAR tiap pagi bursa & ambil token
#      terbaru (token baru hanya dipakai jika lebih segar dari yang aktif).
# Jalankan manual : ./.venv/bin/python jaga_token.py [--test] [--quiet]
# Cron (contoh)   : */10 6-18 * * * cd SAHAM-SCREENING && ./.venv/bin/python jaga_token.py --quiet
# ==========================================
import os
import sys
import json
import time
import shutil
import argparse
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from fetcher_exodus import baca_token, tulis_cache  # noqa: E402

WIB = timezone(timedelta(hours=7))
KANONIK = os.path.join(BASE, "token_stockbit.txt")
KONSUMEN = [
    "/home/kaltaraid/Documents/DATA-CENTER/token_stockbit.txt",
    "/home/kaltaraid/Documents/WEB-SCREENING/token_stockbit.txt",
]
CFG_TG = os.path.join(BASE, "telegram_config.json")
STATUS = os.path.join(BASE, "logs", "jaga_token_status.json")
ALARM_JEDA_JAM = 3
SINKRON_HARIAN_FLAG = "/tmp/jaga_token_sinkron_{}"

import urllib.request, urllib.parse  # noqa: E402


def wib_now():
    return datetime.now(WIB)


def status_token():
    """Return (tok, exp_epoch, sisa_jam, hidup)."""
    tok, exp = baca_token()
    if not tok:
        return "", 0, -1, False
    sisa = (exp - time.time()) / 3600
    return tok, exp, sisa, sisa > 0


def telegram_kirim(text):
    try:
        cfg = json.load(open(CFG_TG))
        data = urllib.parse.urlencode(
            {"chat_id": cfg["CHAT_ID"], "text": text, "parse_mode": "HTML"}).encode()
        with urllib.request.urlopen(urllib.request.Request(
                f"https://api.telegram.org/bot{cfg['BOT_TOKEN']}/sendMessage",
                data=data), timeout=30) as r:
            ok = json.load(r).get("ok")
        print(f"📡 Telegram: {'OK' if ok else 'gagal'}")
    except Exception as e:
        print(f"⚠️ Telegram gagal: {e}")


def alarm(kunci, text):
    """Kirim alarm dgn debounce (satu jenis alarm maks 1x / ALARM_JEDA_JAM)."""
    st = {}
    if os.path.exists(STATUS):
        try: st = json.load(open(STATUS))
        except Exception: st = {}
    now = time.time()
    if now - st.get(kunci, 0) < ALARM_JEDA_JAM * 3600:
        return
    st[kunci] = now
    os.makedirs(os.path.dirname(STATUS), exist_ok=True)
    json.dump(st, open(STATUS, "w"))
    telegram_kirim(text)


def sinkronkan(tok):
    """Salin token kanonik ke semua konsumen (perm 0600, atomic replace)."""
    for dst in KONSUMEN:
        d = os.path.dirname(dst)
        if not os.path.isdir(d):
            continue
        try:
            sama = False
            if os.path.exists(dst):
                with open(dst) as f, open(KANONIK) as g:
                    sama = f.read().strip() == g.read().strip()
            if not sama:
                tmp = dst + ".tmp"
                with open(KANONIK) as src, open(tmp, "w") as out:
                    out.write(src.read())
                os.chmod(tmp, 0o600)
                os.replace(tmp, dst)
                print(f"🔁 Sinkron → {dst}")
        except Exception as e:
            print(f"⚠️ Sinkron {dst} gagal: {e}")


def coba_extract_har(auto=False):
    """Scan HAR di ~/Downloads; tulis token terbaru ke kanonik bila lebih segar.
    Return True jika token kanonik sekarang hidup."""
    _, _, _, hidup = status_token()
    if hidup:
        return True
    # panggil ambil_token.py sebagai subprocess (main() pakai argparse+sys.exit)
    import subprocess
    cmd = [sys.executable, os.path.join(BASE, "ambil_token.py")]
    if not auto:
        cmd.append("--force")
    rc = subprocess.run(cmd, capture_output=True, text=True).returncode
    if rc == 0:
        tok, _, sisa, hidup2 = status_token()
        if hidup2:
            tulis_cache(tok)
            print(f"✅ Token baru dari HAR: sisa {sisa:.1f} jam")
            return True
    return False


def utama():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--test", action="store_true", help="uji request exodus 1x")
    ap.add_argument("--auto-sync-harian", action="store_true",
                    help="scan HAR ~/Downloads 1x/hari pagi (bursa buka)")
    args = ap.parse_args()

    now = wib_now()
    tok, exp, sisa, hidup = status_token()
    sinkronkan(tok) if tok else None

    # auto-sync harian: sekali sehari antara 08:50-10:30 WIB
    if args.auto_sync_harian and hidup and 8 <= now.hour < 11 and \
            not os.path.exists(SINKRON_HARIAN_FLAG.format(now.date())):
        try:
            rc = ambil_main(["--test", "--quiet"])  # tulis hanya jika HAR lebih segar
            os.system(f"touch {SINKRON_HARIAN_FLAG.format(now.date())}")
            tok, exp, sisa, hidup = status_token()
            sinkronkan(tok)
        except Exception as e:
            print(f"⚠️ auto-sync harian gagal: {e}")

    if args.test:
        try:
            from fetcher_exodus import HEADERS as _H
            r = __import__("requests").get(
                "https://exodus.stockbit.com/screener/metric",
                headers={**_H, "Authorization": f"Bearer {tok}"}, timeout=10)
            print(f"🧪 uji exodus: HTTP {r.status_code}"
                  + ("" if r.status_code == 200 else " ← token mungkin ditolak"))
        except Exception as e:
            print(f"🧪 uji exodus gagal: {e}")

    if hidup:
        if not args.quiet:
            print(f"✅ token OK — sisa {sisa:.1f} jam (exp "
                  f"{datetime.fromtimestamp(exp, WIB):%d %b %H:%M} WIB)")
        if sisa < 3:  # hampir habis: ingatkan 1x
            alarm("peringatan_segera_habis",
                  f"⚠️ <b>Token Stockbit</b> sisa {sisa:.0f} jam lagi.\n"
                  "Siapkan HAR baru dari DevTools stockbit.com sekarang.")
    else:
        print("❌ token MATI — mencoba pulihkan dari HAR ~/Downloads...")
        if coba_extract_har():
            tok, exp, sisa2, _ = status_token()
            sinkronkan(tok)
            alarm("pulih", f"✅ <b>Token Stockbit pulih</b> dari HAR baru "
                           f"(sisa {sisa2:.0f} jam) — pipeline kembali normal.")
        else:
            alarm("mati",
                  f"🚨 <b>Token Stockbit MATI</b> ({now:%d %b %H:%M} WIB)\n"
                  "Pipeline fallback ke Yahoo. Perbaikan:\n"
                  "1. Buka stockbit.com + DevTools (F12) → tab Network\n"
                  "2. Refresh halaman & login bila perlu\n"
                  "3. Klik kanan network → <b>Save all as HAR with content</b>\n"
                  "4. Simpan ke ~/Downloads → jaga_token.py siklus berikutnya "
                  "akan ambil otomatis dalam 10 menit.")


if __name__ == "__main__":
    utama()
