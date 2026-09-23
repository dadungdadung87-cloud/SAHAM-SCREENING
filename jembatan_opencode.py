# ==========================================
# 🌉 BRIDGE OPENCODE <-> TELEGRAM (mode kotak-surat)
# Melihat TANYA_OPENCODE.md -> kirim ke TG; balasan TG -> JAWAB_OPENCODE.md
# ==========================================
import os, json, time, subprocess, hashlib
import urllib.request, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
CFG   = os.path.join(BASE, "telegram_opencode.json")
TANYA = os.path.join(BASE, "TANYA_OPENCODE.md")
JAWAB = os.path.join(BASE, "JAWAB_OPENCODE.md")
MARK  = os.path.join(BASE, ".tanya_terkirim.hash")

cfg = json.load(open(CFG))
TOKEN = cfg["BOT_TOKEN"]; CHAT_ID = cfg.get("CHAT_ID") or None
TMUX = cfg.get("TMUX_SESSION", "oc"); AUTO_RESUME = cfg.get("AUTO_RESUME", True)
POLL = 25; last_update = 0

def tg(method, **p):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    with urllib.request.urlopen(urllib.request.Request(
            url, data=urllib.parse.urlencode(p).encode()), timeout=POLL+10) as r:
        return json.load(r)

def kirim(t):
    if CHAT_ID: tg("sendMessage", chat_id=CHAT_ID, text=t, parse_mode="HTML")

def bind():
    global CHAT_ID, last_update
    for u in tg("getUpdates", timeout=5).get("result", []):
        last_update = max(last_update, u["update_id"])
        cid = (u.get("message") or {}).get("chat", {}).get("id")
        if cid:
            CHAT_ID = cid; cfg["CHAT_ID"] = cid
            json.dump(cfg, open(CFG, "w"), indent=2); return True
    return False

def resume():
    if not AUTO_RESUME: return False
    if subprocess.run(["tmux","has-session","-t",TMUX], capture_output=True).returncode: return False
    subprocess.run(["tmux","send-keys","-t",TMUX,
        "Baca JAWAB_OPENCODE.md, terapkan sebagai keputusan final, hapus TANYA_OPENCODE.md dan JAWAB_OPENCODE.md, lalu lanjutkan langkah berikutnya.",
        "Enter"])
    return True

while True:
    try:
        if CHAT_ID is None:
            if bind(): kirim("🔗 Bridge Opencode terikat ke chat ini.")
            else: time.sleep(5); continue
        if os.path.exists(TANYA):
            h = hashlib.md5(open(TANYA,"rb").read()).hexdigest()
            if not (os.path.exists(MARK) and open(MARK).read().strip()==h):
                isi = open(TANYA, encoding="utf-8").read()[:3500]
                kirim("❓ <b>OPENCODE BERTANYA</b>\n<pre>"+isi.replace("<","&lt;").replace(">","&gt;")+"</pre>\nBalas angka/teks pilihan Anda.")
                open(MARK,"w").write(h)
        for u in tg("getUpdates", timeout=POLL, offset=last_update+1).get("result", []):
            last_update = u["update_id"]
            m = u.get("message") or {}
            if m.get("chat",{}).get("id") != CHAT_ID: continue
            teks = (m.get("text") or "").strip()
            if not teks: continue
            if teks == "/lanjut":
                kirim("▶️ Sesi dilanjutkan." if resume() else "⚠️ tmux tidak ada; lanjutkan manual.")
            elif os.path.exists(TANYA):
                open(JAWAB,"w",encoding="utf-8").write(teks+"\n")
                kirim(f"✅ Jawaban tersimpan: <code>{teks}</code>\n" +
                      ("▶️ Sesi dilanjutkan otomatis." if resume() else "📌 Kirim /lanjut atau lanjutkan manual."))
            else:
                kirim("ℹ️ Tidak ada pertanyaan tertunda; balasan diabaikan.")
    except Exception:
        time.sleep(5)
