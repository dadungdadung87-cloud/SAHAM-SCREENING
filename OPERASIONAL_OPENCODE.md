# 📒 OPERASIONAL OPENCODE — Panduan Sesi Depan

> Berlaku untuk `jembatan_opencode.py` **v2.1** (ROBUST: lock file, 409 retry, setsid) + opencode di `tmux`.

## Arsitektur singkat

```
 opencode (tmux:oc)  ──tulis──▶  TANYA_OPENCODE.md  ──baca(bridge v2.1)──▶  Telegram (pemilik HP)
 opencode (tmux:oc)  ◀─suntik─   tmux keystrokes        ◀──balasan angka───  Telegram
```

Dua kanal:
1. **Tanya keluar**: opencode menulis `TANYA_OPENCODE.md`, bridge mengirim isinya ke Telegram.
2. **Jawab masuk**: pemilik balas angka di Telegram, bridge menyuntik `(N-1) Down` lalu `Enter` ke tmux session `oc`.

## Prasyarat (sekali saja)

1. `telegram_opencode.json` berisi `BOT_TOKEN` + `TMUX_SESSION` (default `oc`). `CHAT_ID` boleh `0` — bridge bind otomatis.
2. Kirim `/start` ke bot dari Telegram. Bridge menangkap chat pertama, simpan `CHAT_ID`, kirim konfirmasi.
3. `tmux` terpasang.

## Menjalankan sesi (urutan wajib)

### 1. Buka tmux session bernama `oc`

```bash
cd ~/Documents/SAHAM-SCREENING
tmux new -s oc
```

### 2. Jalankan bridge v2.1 (di terminal terpisah, BUKAN di tmux)

**PENTING — gunakan `setsid` agar kebal Ctrl+C terminal:**

```bash
cd ~/Documents/SAHAM-SCREENING
setsid nohup ./.venv/bin/python jembatan_opencode.py > logs/bridge_v2.log 2>&1 &
```

- `setsid` melepaskan proses dari controlling terminal → Ctrl+C di terminal tidak mematikan bridge.
- `SIGTERM` (`kill -TERM`) tetap untuk shutdown mulus (membersihkan lock file).
- Lock file `.bridge.lock` memastikan **hanya satu instance** hidup. Instance kedua keluar sendiri dengan log "instance lain aktif".

### 3. Jalankan opencode di dalam tmux

```bash
# dari dalam tmux (attachment sudah dilakukan otomatis setelah tmux new)
opencode
```

## Cara opencode bertanya (DUAL)

1. **Tampilkan dialog interaktif normal** (pilihan bernomor) di dalam tmux.
2. **Tulis isi pertanyaan + opsi ke `TANYA_OPENCODE.md`**, **lalu tunggu**.
3. Bridge v2.1 mendeteksi hash file berubah → mengirim ke Telegram.
4. Pemilik balas angka dari HP → bridge menyuntik ke tmux → dialog terpilih → opencode lanjut.

## Cara pemilik menjawab

### Dari HP (Telegram)
- Balas pesan "❓ OPENCODE BERTANYA" dengan **angka** opsi (1, 2, 3, …).
- Bridge menyuntik `(N-1)` `Down` + `Enter` ke tmux.
- Balasan **bukan angka** saat pertanyaan tertunda → bridge balas "balas dengan angka opsi".

### Dari laptop
- Hapus/edit `TANYA_OPENCODE.md` langsung + pilih di dialog tmux. Bridge melihat file hilang → kirim "sudah dijawab di laptop".

## Catatan penting

- Bridge hanya mengirim ke chat ter-bind. Pesan dari chat lain diabaikan.
- **HTTP 409**: bridge tunggu 5s lalu retry — tidak keluar, tidak backoff panjang.
- Graceful shutdown: `kill -TERM <pid>` → bersihkan lock. **Bukan** `kill -9`.
- Jika `.bridge.lock` tertahan (crash sebelumnya), hapus manual lalu start ulang.
- Log ber-timestamp WIB; tanpa token.

## Menghentikan sesi

```bash
pkill -TERM -f jembatan_opencode.py
```

---

**Ringkasan:** `tmux new -s oc` → (terminal lain) `setsid nohup ./.venv/bin/python jembatan_opencode.py > logs/bridge_v2.log 2>&1 &` → opencode di tmux.