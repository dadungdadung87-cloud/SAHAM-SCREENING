import random

# Komponen kata yang lebih spesifik dan formal
kata_kerja = ["rencana", "kaji", "proses", "tahap", "upaya", "bidik", "siapkan", "teken", "resmi", "tuntaskan"]
kata_aksi = ["akuisisi", "merger", "pengambilalihan", "pembelian", "konsolidasi", "integrasi", "transaksi", "kepemilikan"]
kata_objek = ["saham", "aset", "bisnis", "perusahaan", "unit usaha", "pangsa pasar", "entitas"]

def generate_keywords(filename, aksi_list):
    with open(filename, "w", encoding="utf-8") as f:
        # Generate 250 variasi 2 Kata
        for _ in range(250):
            f.write(f"{random.choice(kata_kerja)} {random.choice(kata_aksi)}\n")
            
        # Generate 250 variasi 3 Kata
        for _ in range(250):
            f.write(f"{random.choice(kata_kerja)} {random.choice(aksi_list)} {random.choice(kata_objek)}\n")
            
    print(f"✅ {filename} berhasil dibuat!")

# Untuk Rencana
generate_keywords("RENCANA_AKUISISI.txt", ["akuisisi", "merger", "pengambilalihan"])

# Untuk Dalam (Ganti kata kerja ke yang lebih definitif)
kata_kerja_dalam = ["resmi", "tuntas", "selesai", "sepakat", "rampung", "sah"]
with open("DALAM_AKUISISI.txt", "w", encoding="utf-8") as f:
    for _ in range(500):
        frasa = f"{random.choice(kata_kerja_dalam)} {random.choice(kata_aksi)} {random.choice(kata_objek)}"
        f.write(f"{frasa}\n")