# ==========================================
# 🌉 BRIDGE OPENCODE <-> TELEGRAM v2.1 (ROBUST)
# Perilaku (PROMPT_OPENCODE_FIX BAGIAN 3.1):
#  - Lock file (fcntl.flock) di awal main(); instance kedua keluar sendiri.
#  - Pada HTTPError 409: tunggu 5s lalu retry; jangan backoff panjang; jangan keluar.
#  - HTTPError lain: backoff eksponensial <=60s.
#  - Semua fitur dual-channel v2 tetap (TANYA->TG, angka->tmux).
#  - Graceful shutdown SIGINT/SIGTERM; log ber-timestamp; tanpa secrets.
# ==========================================
import os, sys, json, time, hashlib, signal, fcntl
import subprocess
import urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
CFG   = os.path.join(BASE, "telegram_opencode.json")
TANYA = os.path.join(BASE, "TANYA_OPENCODE.md")
MARK  = os.path.join(BASE, ".tanya_terkirim.hash")
LOCK  = os.path.join(BASE, ".bridge.lock")

POLL = 25
BACKOFF_MAX = 60
_running = True
WIB = timezone(timedelta(hours=7))


def _log(msg):
    ts = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _load_cfg():
    with open(CFG) as f:
        return json.load(f)


def _save_cfg(c):
    with open(CFG, "w") as f:
        json.dump(c, f, indent=2)


def tg(method, token, **p):
    url = f"https://api.telegram.org/bot{token}/{method}"
    req = urllib.request.Request(url, data=urllib.parse.urlencode(p).encode())
    with urllib.request.urlopen(req, timeout=POLL + 10) as r:
        return json.load(r)


def _esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _file_hash():
    if not os.path.exists(TANYA):
        return None
    h = hashlib.md5(open(TANYA, "rb").read()).hexdigest()
    return h


def kirim(token, chat_id, text):
    tg("sendMessage", token, chat_id=chat_id, text=text, parse_mode="HTML")


def bind_chat(token):
    """CHAT_ID kosong -> ambil chat pertama yang mengirim pesan apa pun."""
    r = tg("getUpdates", token, timeout=5)
    for u in r.get("result", []):
        cid = (u.get("message") or {}).get("chat", {}).get("id")
        if cid:
            return int(cid)
    return None


def _suntik_tmux(tmux, n):
    """Kirim (n-1) Down lalu Enter ke tmux session untuk memilih opsi ke-N."""
    if not tmux:
        return False
    if subprocess.run(["tmux", "has-session", "-t", tmux], capture_output=True).returncode != 0:
        return False
    for _ in range(max(0, n - 1)):
        subprocess.run(["tmux", "send-keys", "-t", tmux, "Down"])
    subprocess.run(["tmux", "send-keys", "-t", tmux, "Enter"])
    return True


def _shutdown(signum, frame):
    global _running
    _running = False
    _log(f"menerima sinyal {signum}, memulai shutdown mulus ...")


def _acquire_lock():
    """Ambil lock eksklusif. Instance kedua keluar sendiri."""
    try:
        f = open(LOCK, "w")
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        f.write(str(os.getpid()))
        f.flush()
        return f
    except (OSError, IOError):
        return None


def main():
    global _running

    lf = _acquire_lock()
    if lf is None:
        _log("instance lain aktif (.bridge.lock tertahan); keluar.")
        sys.exit(1)

    cfg = _load_cfg()
    token = cfg["BOT_TOKEN"]
    chat_id = cfg.get("CHAT_ID") or 0
    tmux = cfg.get("TMUX_SESSION", "oc")
    last_update = 0
    backoff = 3

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    _log(f"bridge v2.1 start | chat_id={'<bind>' if not chat_id else chat_id} | tmux={tmux}")

    while _running:
        try:
            # --- Bind chat jika kosong ---
            if not chat_id:
                cid = bind_chat(token)
                if cid:
                    chat_id = cid
                    cfg["CHAT_ID"] = cid
                    _save_cfg(cfg)
                    _log(f"terikat ke chat {cid}")
                    kirim(token, chat_id, "🔗 <b>Bridge v2.1 terikat ke chat ini.</b>\nKirim angka untuk memilih opsi saat ada pertanyaan tertunda.")
                else:
                    time.sleep(5)
                    continue

            # --- Poll TANYA_OPENCODE.md via hash ---
            h_now = _file_hash()
            h_mark = open(MARK).read().strip() if os.path.exists(MARK) else None
            if h_now is not None and h_now != h_mark:
                isi = open(TANYA, encoding="utf-8").read()[:3500]
                kirim(token, chat_id, "❓ <b>OPENCODE BERTANYA</b>\n<pre>" + _esc(isi) + "</pre>\nBalas <b>angka</b> pilihan opsi Anda.")
                open(MARK, "w").write(h_now)
                _log("TANYA baru dikirim ke Telegram.")
            elif h_now is None and h_mark is not None:
                kirim(token, chat_id, "ℹ️ Pertanyaan sudah dijawab/dihilangkan di laptop.")
                if os.path.exists(MARK):
                    os.remove(MARK)
                _log("TANYA dihapus dari laptop; notifikasi terkirim.")

            # --- Long-poll getUpdates ---
            try:
                r = tg("getUpdates", token, timeout=POLL, offset=last_update + 1)
            except urllib.error.HTTPError as e:
                if e.code == 409:
                    _log("HTTP 409 (terminated/conflict); tunggu 5s lalu retry.")
                    time.sleep(5)
                    continue
                _log(f"HTTPError {e.code}; backoff {backoff}s")
                time.sleep(backoff); backoff = min(backoff * 2, BACKOFF_MAX); continue
            backoff = 3
            tunda = os.path.exists(TANYA)
            for u in r.get("result", []):
                last_update = u["update_id"]
                m = u.get("message") or {}
                if m.get("chat", {}).get("id") != chat_id:
                    continue
                teks = (m.get("text") or "").strip()
                if not teks:
                    continue
                if tunda and teks.isdigit():
                    n = int(teks)
                    ok = _suntik_tmux(tmux, n)
                    kirim(token, chat_id, f"✅ Opsi {n} disuntik ke tmux." if ok else f"⚠️ tmux '{tmux}' tidak ada; opsi {n} tidak dikirim.")
                    _log(f"jawaban angka={n} -> tmux {'OK' if ok else 'GAGAL'}")
                elif tunda and not teks.isdigit():
                    kirim(token, chat_id, "↩️ Balas dengan <b>angka</b> opsi (1,2,3,...). Balasan teks tidak diproses saat ada pertanyaan tertunda.")
                else:
                    kirim(token, chat_id, "ℹ️ Tidak ada pertanyaan tertunda sekarang. Pesan diterima tapi tidak ditindaklanjuti.")
        except Exception as e:
            _log(f"error loop: {e}; backoff {backoff}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, BACKOFF_MAX)

    if lf:
        try:
            fcntl.flock(lf, fcntl.LOCK_UN)
        except Exception:
            pass
    try:
        os.remove(LOCK)
    except Exception:
        pass
    _log("bridge v2.1 berhenti.")


if __name__ == "__main__":
    main()