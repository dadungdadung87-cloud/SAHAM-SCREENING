import random

# Daftar kata dasar yang lebih kaya
kata_kerja = ["rencana", "kaji", "proses", "tahap", "upaya", "niat", "target", "analisis", "diskusi", "bidik"]
kata_aksi = ["akuisisi", "merger", "pengambilalihan", "beli", "konsolidasi", "integrasi", "ekspansi"]
kata_objek = ["saham", "aset", "bisnis", "perusahaan", "usaha", "portofolio", "pasar"]

def generate_keywords(filename):
    with open(filename, "w", encoding="utf-8") as f:
        # 1. Kelompok 1 Kata
        # Ambil langsung dari list aksi dan kerja
        satu_kata = list(set(kata_kerja + kata_aksi + kata_objek))
        for kata in satu_kata:
            f.write(f"{kata}\n")
        
        # 2. Kelompok 2 Kata (Kombinasi acak)
        for _ in range(150): # Membuat 150 variasi 2 kata
            frasa = f"{random.choice(kata_kerja)} {random.choice(kata_aksi)}"
            f.write(f"{frasa}\n")
            
        # 3. Kelompok 3 Kata (Kombinasi acak)
        for _ in range(150): # Membuat 150 variasi 3 kata
            frasa = f"{random.choice(kata_kerja)} {random.choice(kata_aksi)} {random.choice(kata_objek)}"
            f.write(f"{frasa}\n")
            
    print(f"✅ {filename} berhasil dibuat dengan struktur 1, 2, dan 3 kata.")

# Generate untuk kedua file
generate_keywords("RENCANA_AKUISISI.txt")
generate_keywords("DALAM_AKUISISI.txt")