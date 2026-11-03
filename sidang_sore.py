# ==========================================
# 🌆 SIDANG SORE — screening referensi setelah pasar tutup (16:05)
# Mode: read-only (TIDAK menulis sinyal, TIDAK membeli)
# ==========================================
import os, sys
import pandas as pd
import sidang_lib

KEY_PATH = os.path.expanduser("~/.config/bsjp/gemini.key")

def main():
    if not os.path.exists(KEY_PATH):
        print(f"❌ Gemini key tidak ditemukan: {KEY_PATH}")
        sys.exit(1)
    api_key = open(KEY_PATH).read().strip()
    fs = os.path.join(sidang_lib.DIR_DB, "hasil_screener.csv")
    if not os.path.exists(fs):
        print("❌ hasil_screener.csv tidak ada."); sys.exit(1)
    df = pd.read_csv(fs)
    daftar = sidang_lib.hitung_rumus(df)
    print(f"🌆 Sidang sore (referensi) dimulai ({len(df)} saham)...")
    keranjang, err = sidang_lib.jalankan_sidang(daftar, df, api_key, mode_tulis=False)
    if err:
        print("❌", err); sys.exit(1)
    isi = {k: len([t for t in v if t]) for k, v in keranjang.items()}
    print("✅ Sidang sore selesai:", isi)

if __name__ == "__main__":
    main()
