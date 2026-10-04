# ==========================================
# 🔄 RESET PORTOFOLIO KE KONDISI AWAL (dengan ARSIP aman)
# Pindah porto/histori/sinyal lama ke Database/ARSIP_RESET_<tanggal>/
# Buat ulang file kosong (modal 100jt/arena) + mirror ke R2.
# Jalankan: ./.venv/bin/python reset_porto.py [--yes]
# ==========================================
import os, sys, shutil
import pandas as pd
from datetime import datetime, timedelta, timezone

now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)
tag = now.strftime("%Y-%m-%d_%H%M")
folder = os.path.join("Database", f"ARSIP_RESET_{tag}")
os.makedirs(folder, exist_ok=True)

KOLOM_PORTO = ['Tanggal_Beli', 'Ticker', 'Harga_Beli', 'Lot', 'Total_Modal', 'Target_TP', 'Target_CL', 'Mode_Beli', 'Change_Beli']
KOLOM_HIST = ['Tanggal_Beli', 'Tanggal_Jual', 'Ticker', 'Harga_Beli', 'Harga_Jual', 'Status', 'Total_Return_Rp', 'Return_%', 'Mode_Beli', 'Change_Beli']

dipindah = 0
for i in range(1, 10):
    for jenis in ["portofolio_aktif", "histori_transaksi", "sinyal_ai"]:
        src = os.path.join("Database", f"{jenis}_rumus_{i}.csv")
        if os.path.exists(src):
            shutil.move(src, os.path.join(folder, f"{jenis}_rumus_{i}.csv"))
            dipindah += 1

# Buat ulang file kosong (header sesuai skema bot) — modal 100jt per arena dihitung otomatis
for i in range(1, 10):
    pd.DataFrame(columns=KOLOM_PORTO).to_csv(os.path.join("Database", f"portofolio_aktif_rumus_{i}.csv"), index=False)
    pd.DataFrame(columns=KOLOM_HIST).to_csv(os.path.join("Database", f"histori_transaksi_rumus_{i}.csv"), index=False)

print(f"✅ {dipindah} file lama diarsipkan ke {folder}")
print("✅ 9 arena dibuat ulang kosong (modal awal Rp 100.000.000/arena, profit 0)")

# Mirror R2: hapus file lama di R2 yang tidak ada lokal, upload file kosong baru
try:
    import r2_client
    if r2_client.upload_database(mirror=True):
        print("☁️ R2 sudah dicerminkan: portofolio kosong di cloud juga.")
except Exception as e:
    print(f"⚠️ Mirror R2 gagal (perbaiki manual): {e}")

if "--yes" not in sys.argv:
    print("\nLangkah push GitHub (atau biarkan cron yang push):")
    print('  git add -A Database/ && git commit -m "Reset portofolio: arsip lama, mulai lembar baru" && git push origin main')
