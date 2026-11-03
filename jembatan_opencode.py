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
RESET = os.path.join(BASE, "reset_porto.py")
BOT_SIM = os.path.join(BASE, "bot_simulator.py")

POLL = 5
BACKOFF_MAX = 60
_running = True
_reset_busy = 0  # epoch reset terakhir (guard dobel-klik)
_bot_busy = 0    # epoch bot simulator terakhir (cooldown 5 mnt)
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


def kirim_dengan_tombol(token, chat_id, text, tombol):
    kb = json.dumps({"inline_keyboard": tombol})
    tg("sendMessage", token, chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=kb)


def kirim_menu(token, chat_id):
    tombol = [
        [{"text": "📊 Status Portofolio", "callback_data": "stat:porto"},
         {"text": "📈 Status Screener", "callback_data": "stat:screener"}],
        [{"text": "🔑 Status Token", "callback_data": "stat:token"},
         {"text": "▶️ Jalankan Bot Simulator", "callback_data": "bot:ask"}],
        [{"text": "🗑️ Hapus & Ganti Daftar Belanja", "callback_data": "reset:ask"}],
    ]
    kirim_dengan_tombol(
        token, chat_id,
        "🤖 <b>Menu Bot</b>\nPilih aksi:",
        tombol)


def status_porto(token, chat_id):
    """Ringkasan 9 arena: jumlah saham, modal terpakai, realized P/L."""
    import csv
    baris = []
    total_modal, total_rp, total_saham = 0.0, 0.0, 0
    try:
        for i in range(1, 10):
            fp = os.path.join(BASE, "Database", f"portofolio_aktif_rumus_{i}.csv")
            fh = os.path.join(BASE, "Database", f"histori_transaksi_rumus_{i}.csv")
            nsaham = modal = rp = 0
            if os.path.exists(fp):
                with open(fp) as f:
                    nsaham = max(0, sum(1 for _ in f) - 1)
                try:
                    dfp = pd_read_csv(fp)
                    modal = float(dfp.get("Total_Modal", pd.Series(dtype=float)).fillna(0).sum())
                except Exception:
                    modal = 0.0
            if os.path.exists(fh):
                try:
                    dfh = pd_read_csv(fh)
                    rp = float(dfh.get("Total_Return_Rp", pd.Series(dtype=float)).fillna(0).sum())
                except Exception:
                    rp = 0.0
            total_saham += nsaham
            total_modal += modal
            total_rp += rp
            baris.append(f"Arena {i}: {nsaham} saham | modal Rp {modal:,.0f} | realized Rp {rp:,.0f}")
        teks = ("📊 <b>Status Portofolio</b>\n<pre>" + _esc("\n".join(baris)) +
                f"\nTOTAL: {total_saham} saham | modal Rp {total_modal:,.0f} | realized Rp {total_rp:,.0f}</pre>")
    except Exception as e:
        teks = f"⚠️ Gagal baca portofolio: <pre>{_esc(str(e))}</pre>"
    kirim(token, chat_id, teks)


def pd_read_csv(path):
    """Baca CSV tanpa pandas: list-of-dict dengan angka diparse."""
    import csv
    with open(path) as f:
        return [{k: _angka(v) for k, v in row.items()} for row in csv.DictReader(f)]


def _angka(v):
    try:
        f = float(v)
        return f
    except (TypeError, ValueError):
        return 0.0


def status_screener(token, chat_id):
    """Ringkasan feed/status.json dari DATA-CENTER."""
    sj = os.path.join(os.path.dirname(BASE), "DATA-CENTER", "feed", "status.json")
    try:
        with open(sj) as f:
            s = json.load(f)
        umur_menit = int((time.time() - float(s.get("epoch", 0))) / 60)
        segar = "🟢 segar" if umur_menit <= 15 else ("🟡 " + str(umur_menit) + " mnt lalu" if umur_menit <= 60 else "🔴 " + str(umur_menit) + " mnt lalu")
        sumber = s.get("sumber_harga", "?")
        ikon = "🟢" if sumber == "STOCKBIT" else "🟡"
        kirim(token, chat_id,
              f"📈 <b>Status Screener</b>\n"
              f"Update: {s.get('stempel_waktu', '?')} ({segar})\n"
              f"Baris: {s.get('baris', '?')} | Sumber: {ikon} {sumber}")
    except FileNotFoundError:
        kirim(token, chat_id, "⚠️ status.json tidak ditemukan (producer belum jalan?).")
    except Exception as e:
        kirim(token, chat_id, f"⚠️ Gagal baca status: <pre>{_esc(str(e))}</pre>")


def status_token(token, chat_id):
    """Exp token Stockbit + sisa umur."""
    try:
        sys.path.insert(0, BASE)
        import fetcher_exodus
        tok, exp = fetcher_exodus.baca_token()
        if not tok or not exp:
            kirim(token, chat_id, "🔴 Token tidak ada/korup.")
            return
        sisa = exp - time.time()
        if sisa <= 0:
            kirim(token, chat_id, "🔴 Token <b>mati</b> — export HAR baru dari browser Stockbit.")
            return
        exp_str = datetime.fromtimestamp(exp, WIB).strftime("%d-%m %H:%M")
        ikon = "🟢" if sisa > 3 * 3600 else "🟡"
        kirim(token, chat_id,
              f"🔑 <b>Status Token Stockbit</b>\n"
              f"{ikon} Hidup — mati {exp_str} WIB (sisa {sisa/3600:.1f} jam)")
    except Exception as e:
        kirim(token, chat_id, f"⚠️ Gagal cek token: <pre>{_esc(str(e))}</pre>")


def tanya_bot_simulator(token, chat_id):
    tombol = [
        [{"text": "✅ Ya, jalankan sekarang", "callback_data": "bot:yes"},
         {"text": "❌ Batal", "callback_data": "bot:no"}],
    ]
    kirim_dengan_tombol(
        token, chat_id,
        "▶️ <b>Jalankan Bot Simulator?</b>\n\n"
        "Bot akan mengeksekusi beli/jual sesuai sinyal di 9 arena "
        "(mode manual, sinkron R2, auto-save GitHub).\n\nLanjutkan?",
        tombol)


def jalankan_bot_simulator(token, chat_id):
    """Eksekusi bot_simulator.py --manual dan kirim ringkasan."""
    global _bot_busy
    if time.time() - _bot_busy < 300:
        kirim(token, chat_id, "⏳ Bot simulator baru saja jalan (<5 mnt); tunggu.")
        return
    _bot_busy = time.time()
    kirim(token, chat_id, "🔄 Menjalankan bot simulator (mode manual) ...")
    try:
        r = subprocess.run(
            [sys.executable, BOT_SIM, "--manual"],
            cwd=BASE, capture_output=True, text=True, timeout=600)
        out = (r.stdout or "").strip().splitlines()
        ringkas = "\n".join(out[-12:]) if out else "(tanpa output)"
        if r.returncode == 0:
            kirim(token, chat_id, f"✅ <b>Bot simulator selesai.</b>\n<pre>{_esc(ringkas[-1500:])}</pre>")
            _log("bot simulator OK")
        else:
            err = (r.stderr or "").strip().splitlines()[-3:]
            kirim(token, chat_id, f"⚠️ <b>Bot simulator gagal</b> (exit {r.returncode}).\n<pre>{_esc(chr(10).join(err))}</pre>")
            _log(f"bot simulator GAGAL exit={r.returncode}")
    except subprocess.TimeoutExpired:
        kirim(token, chat_id, "⏱️ Bot simulator timeout (>10 mnt); cek log manual.")
        _log("bot simulator TIMEOUT")
    except Exception as e:
        kirim(token, chat_id, f"⚠️ Bot simulator error: <pre>{_esc(str(e))}</pre>")
        _log(f"bot simulator ERROR: {e}")


def tanya_reset(token, chat_id):
    tombol = [
        [
            {"text": "✅ Ya, reset sekarang", "callback_data": "reset:yes"},
            {"text": "❌ Batal", "callback_data": "reset:no"},
        ]
    ]
    kirim_dengan_tombol(
        token, chat_id,
        "⚠️ <b>Konfirmasi Reset Daftar Belanja</b>\n\n"
        "Semua portofolio aktif + histori 9 arena akan <b>dikosongkan</b> "
        "(diarsipkan ke <code>Database/ARSIP_RESET_...</code>, modal kembali Rp 100jt/arena) "
        "lalu di-mirror ke R2.\n\nLanjutkan?",
        tombol)


def _jawab_callback(token, cq_id, text):
    try:
        tg("answerCallbackQuery", token, callback_query_id=cq_id, text=text[:190])
    except Exception as e:
        _log(f"answerCallbackQuery gagal: {e}")


def jalankan_reset(token, chat_id):
    """Eksekusi reset_porto.py --yes dan kirim ringkasan hasilnya."""
    global _reset_busy
    if time.time() - _reset_busy < 5:
        _jawab_callback(token, "", "")  # no-op; guard di bawah yang bicara
        kirim(token, chat_id, "⏳ Reset sedang berjalan; tunggu sebentar.")
        return
    _reset_busy = time.time()
    kirim(token, chat_id, "🔄 Menjalankan reset daftar belanja ...")
    try:
        r = subprocess.run(
            [sys.executable, RESET, "--yes"],
            cwd=BASE, capture_output=True, text=True, timeout=180)
        out = (r.stdout or "").strip().splitlines()
        ringkas = "\n".join(out[-6:]) if out else "(tanpa output)"
        if r.returncode == 0:
            kirim(token, chat_id, f"✅ <b>Reset selesai — daftar belanja baru siap.</b>\n<pre>{_esc(ringkas)}</pre>")
            _log("reset portofolio OK")
        else:
            err = (r.stderr or "").strip().splitlines()[-3:]
            kirim(token, chat_id, f"⚠️ <b>Reset gagal</b> (exit {r.returncode}).\n<pre>{_esc(chr(10).join(err))}</pre>")
            _log(f"reset portofolio GAGAL exit={r.returncode}")
    except subprocess.TimeoutExpired:
        kirim(token, chat_id, "⏱️ Reset timeout (>180s); cek logs/ atau jalankan manual.")
        _log("reset portofolio TIMEOUT")
    except Exception as e:
        kirim(token, chat_id, f"⚠️ Reset error: <pre>{_esc(str(e))}</pre>")
        _log(f"reset portofolio ERROR: {e}")


def proses_callback(token, chat_id, cq):
    """Tangani tombol inline. Return True jika update diproses."""
    data = cq.get("data") or ""
    cid_cb = ((cq.get("message") or {}).get("chat") or {}).get("id")
    if cid_cb != chat_id:
        return True  # bukan chat kita — abaikan tapi tandai selesai
    if data == "reset:ask":
        _jawab_callback(token, cq["id"], "Konfirmasi diperlukan")
        tanya_reset(token, chat_id)
    elif data == "reset:yes":
        _jawab_callback(token, cq["id"], "Memproses...")
        jalankan_reset(token, chat_id)
    elif data == "reset:no":
        _jawab_callback(token, cq["id"], "Dibatalkan")
        kirim(token, chat_id, "↩️ Reset dibatalkan. Daftar belanja tidak diubah.")
    elif data == "stat:porto":
        _jawab_callback(token, cq["id"], "Membaca portofolio...")
        status_porto(token, chat_id)
    elif data == "stat:screener":
        _jawab_callback(token, cq["id"], "Membaca status screener...")
        status_screener(token, chat_id)
    elif data == "stat:token":
        _jawab_callback(token, cq["id"], "Mengecek token...")
        status_token(token, chat_id)
    elif data == "bot:ask":
        _jawab_callback(token, cq["id"], "Konfirmasi diperlukan")
        tanya_bot_simulator(token, chat_id)
    elif data == "bot:yes":
        _jawab_callback(token, cq["id"], "Memproses...")
        jalankan_bot_simulator(token, chat_id)
    elif data == "bot:no":
        _jawab_callback(token, cq["id"], "Dibatalkan")
        kirim(token, chat_id, "↩️ Bot simulator tidak dijalankan.")
    else:
        _jawab_callback(token, cq["id"], "Tombol tidak dikenal")
    return True


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
    try:
        if subprocess.run(["tmux", "has-session", "-t", tmux], capture_output=True).returncode != 0:
            return False
    except FileNotFoundError:
        _log("tmux tidak terpasang; suntikan dilewati dengan aman.")
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
                # --- Tombol inline (callback_query) ---
                cq = u.get("callback_query")
                if cq:
                    proses_callback(token, chat_id, cq)
                    continue
                m = u.get("message") or {}
                if m.get("chat", {}).get("id") != chat_id:
                    continue
                teks = (m.get("text") or "").strip()
                if not teks:
                    continue
                # --- Perintah menu daftar belanja (di luar mode tanya) ---
                if not tunda and teks.lower() in ("/menu", "/belanja", "/belanja@sesi_opencode_bot", "/reset", "/reset@sesi_opencode_bot", "menu", "belanja"):
                    kirim_menu(token, chat_id)
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