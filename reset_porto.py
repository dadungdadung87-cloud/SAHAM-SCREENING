# ==========================================
# 🔄 RESET PORTOFOLIO KE KONDISI AWAL (dengan ARSIP aman)
# Pindah porto/histori/sinyal lama ke Database/ARSIP_RESET_<tanggal>/
# File kosong akan dibuat ulang otomatis oleh bot/web.
# ==========================================
import os, shutil
from datetime import datetime, timedelta, timezone

now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)
tag = now.strftime("%Y-%m-%d_%H%M")
folder = os.path.join("Database", f"ARSIP_RESET_{tag}")
os.makedirs(folder, exist_ok=True)

dipindah = 0
for i in range(1, 10):
    for jenis in ["portofolio_aktif", "histori_transaksi", "sinyal_ai"]:
        src = os.path.join("Database", f"{jenis}_rumus_{i}.csv")
        if os.path.exists(src):
            shutil.move(src, os.path.join(folder, f"{jenis}_rumus_{i}.csv"))
            dipindah += 1

print(f"✅ {dipindah} file dipindah ke {folder} (arsip permanen, ikut ter-push ke GitHub).")
print("Langkah berikutnya di laptop:")
print('  1) Mirror ke R2 : ./.venv/bin/python -c "import r2_client; r2_client.upload_database(mirror=True)"')
print('  2) Push GitHub  : git add -A Database/ && git commit -m "Reset portofolio: arsip lama, mulai lembar baru" && git pull --rebase origin main && git push origin main')