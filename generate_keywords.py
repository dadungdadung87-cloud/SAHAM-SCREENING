# Daftar kata dasar untuk dikombinasikan
subjek = ["rencana", "strategi", "kaji", "proses", "tahap", "upaya", "niat", "target", "analisis", "diskusi"]
aksi = ["akuisisi", "pengambilalihan", "merger", "pembelian", "konsolidasi", "integrasi", "ekspansi"]
objek = ["saham", "aset", "bisnis", "perusahaan", "unit usaha", "portofolio", "pangsa pasar", "kontribusi"]
sektor = ["sektor energi", "sektor properti", "sektor perbankan", "sektor teknologi", "sektor ritel", "sektor logistik"]

def generate_file(filename, list_kata, jumlah):
    with open(filename, "w", encoding="utf-8") as f:
        for _ in range(jumlah):
            import random
            frasa = f"{random.choice(subjek)} {random.choice(aksi)} {random.choice(objek)} {random.choice(sektor)}"
            f.write(frasa + "\n")
    print(f"✅ {filename} berhasil dibuat dengan {jumlah} kata kunci!")

# Membuat RENCANA_AKUISISI.txt (200 baris)
generate_file("RENCANA_AKUISISI.txt", subjek, 200)

# Membuat DALAM_AKUISISI.txt (200 baris dengan kata kerja past tense/selesai)
aksi_selesai = ["telah akuisisi", "resmi beli", "selesai akuisisi", "tuntas merger", "sah kuasai", "rampungkan pengambilalihan"]
with open("DALAM_AKUISISI.txt", "w", encoding="utf-8") as f:
    for i in range(200):
        import random
        frasa = f"{random.choice(aksi_selesai)} {random.choice(objek)} {random.choice(sektor)}"
        f.write(frasa + "\n")
print("✅ DALAM_AKUISISI.txt berhasil dibuat!")