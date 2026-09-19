# ==========================================
# 🛒 BELI JADWAL — eksekusi otomatis sinyal hari ini (jendela 15:30 WIB)
# Jalankan: ./.venv/bin/python bot_simulator.py --jadwal
# ==========================================
import os, sys
import subprocess

def main():
    jeda = os.path.join("Database", "JEDA_BELI_JADWAL")
    if os.path.exists(jeda):
        print("⏸️ Sakelar JEDA aktif — pembelian jadwal dilewati.")
        return
    
    print("🛒 Memulai pembelian jadwal...")
    hasil = subprocess.run([sys.executable, "bot_simulator.py", "--jadwal"],
                          capture_output=False)
    sys.exit(hasil.returncode)

if __name__ == "__main__":
    main()
