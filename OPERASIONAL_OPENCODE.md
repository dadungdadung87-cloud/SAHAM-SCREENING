# 📒 OPERASIONAL OPENCODE — Panduan Sesi Depan

> Berlaku untuk `jembatan_opencode.py` **v2** (DUAL-CHANNEL) + opencode di `tmux`.
> Baca file ini jika akan memulai sesi opencode jangka panjang.

## Arsitektur singkat

```
 opencode (tmux:oc)  ──tulis──▶  TANYA_OPENCODE.md  ──baca(bridge v2)──▶  Telegram (pemilik HP)
 opencode (tmux:oc)  ◀─suntik─   tmux keystrokes        ◀──balasan angka───  Telegram
```

Dua kanal:
1. **Tanya keluar**: opencode menulis `TANYA_OPENCODE.md`, bridge mengirim isinya ke Telegram.
2. **Jawab masuk**: pemilik balas angka di Telegram, bridge menyuntik `(N-1) Down` lalu `Enter` ke tmux session `oc` → memilih opsi ke-N di dialog interaktif opencode.

## Prasyarat (sekali saja)

1. `telegram_opencode.json` berisi `BOT_TOKEN` (dari @BotFather) + `TMUX_SESSION` (default `oc`). `CHAT_ID` boleh dikosongkan (`0`) — bridge akan bind otomatis.
2. Bot belum pernah menerima pesan dari pemilik → kirim `/start` ke bot di Telegram (atau pesan apa pun). Bridge akan menangkap chat pertama, menyimpan `CHAT_ID` ke config, lalu mengirim pesan konfirmasi.
3. `tmux` terpasang.

## Menjalankan sesi (urutan wajib)

### 1. Buka tmux session bernama `oc`

```bash
cd ~/Documents/SAHAM-SCREENING
tmux new -s oc
```

> Di dalam tmux inilah opencode berjalan, agar bridge bisa menyuntik keystroke pilihan jawaban.

### 2. Jalankan bridge v2 (di terminal terpisah, BUKAN di tmux)

```bash
cd ~/Documents/SAHAM-SCREENING
nohup ./.venv/bin/python jembatan_opencode.py > logs/bridge_v2.log 2>&1 &
```

Bridge lalu long-poll Telegram. Log tanpa token, hanya metadata (`chat_id`, opsi N, status tmux).

### 3. Mulai opencode di dalam tmux

```bash
# dari dalam tmux (attachment sudah dilakukan otomatis setelah tmux new)
opencode
```

## Cara opencode bertanya (DUAL)

Saat opencode terhenti dan perlu keputusan pemilik, alurnya:

1. **Tampilkan dialog interaktif normal** (pilihan bernomor) di dalam tmux — opencode select.
2. **Tulis isi pertanyaan + opsi ke `TANYA_OPENCODE.md`**, **lalu tunggu**.
3. Bridge v2 mendeteksi hash file berubah → mengirim ke Telegram.
4. Pemilik balas angka dari HP → bridge menyuntik ke tmux → dialog otomatis terpilih → opencode lanjut.

> Mekanisme ini membuat sesi opencode bisa berjalan tanpa pengawasan terminal: pertanyaan masuk ke HP, jawaban kembali via tmux.

## Cara pemilik menjawab

### Dari HP (Telegram)
- Saat ada pesan "❓ OPENCODE BERTANYA", balas dengan **angka** opsi (1, 2, 3, …).
- Bridge menyuntik `(N-1)` `Down` + `Enter` ke tmux → opencode melanjutkan.
- Balasan **bukan angka** (saat pertanyaan tertunda) → bridge balas "balas dengan angka opsi" (tidak menindaklanjuti teks).

### Dari laptop
- Hapus/edit `TANYA_OPENCODE.md` langsung + pilih di dialog tmux manual. Bridge melihat file hilang → kirim "sudah dijawab di laptop".

## Catatan penting

- Bridge **hanya** mengirim ke chat yang ter-bind (BAGIAN 5 #4). Pesan dari chat lain diabaikan.
- Saat tidak ada pertanyaan tertunda, balasan apa pun diabaikan dengan info.
- Graceful shutdown: `kill -TERM <pid>` atau `kill -INT <pid>` → bridge berhenti mulus (bukan kill -9).
- Jika Telegram error (HTTPError), backoff eksponensial hingga 60s, lalu retry.
- Token **tidak pernah** dicetak ke log.

## Menghentikan sesi

```bash
# hentikan opencode (dari tmux: Ctrl+C atau :q)
# hentikan bridge: cari PID lalu kirim SIGTERM
pkill -TERM -f jembatan_opencode.py
```

---

**Ringkasan 1-baris untuk sesi baru:** `tmux new -s oc && (di terminal lain) nohup ./.venv/bin/python jembatan_opencode.py > logs/bridge_v2.log 2>&1 &` lalu jalankan opencode di tmux — kirim `/start` ke bot saat pertama kali.