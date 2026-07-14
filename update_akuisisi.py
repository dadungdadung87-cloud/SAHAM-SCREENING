import feedparser
import pandas as pd
import os

def load_keywords(filename):
    """Memuat daftar kata kunci dari file txt."""
    if not os.path.exists(filename):
        print(f"⚠️ Peringatan: File '{filename}' tidak ditemukan. Menggunakan daftar kosong.")
        return []
    
    with open(filename, "r", encoding="utf-8") as file:
        # Membaca per baris, membersihkan spasi/enter, dan mengubah ke huruf kecil
        return [line.strip().lower() for line in file if line.strip()]

def get_news_titles(ticker):
    """Menarik judul berita terbaru dari Google News RSS"""
    query = f"saham+{ticker}+akuisisi"
    url = f"https://news.google.com/rss/search?q={query}&hl=id&gl=ID&ceid=ID:id"
    feed = feedparser.parse(url)
    titles = [entry.title for entry in feed.entries[:5]]
    return " | ".join(titles) if titles else "Tidak ada berita terbaru."

def analyze_acquisition_status(news_text, kata_rencana, kata_dalam):
    """Menyimpulkan status akuisisi menggunakan logika kata kunci eksternal"""
    if news_text == "Tidak ada berita terbaru.":
        return "TIDAK ADA"
        
    teks_kecil = news_text.lower()
    
    # Cek status DALAM AKUISISI terlebih dahulu (Prioritas Utama)
    if any(kata in teks_kecil for kata in kata_dalam):
        return "DALAM AKUISISI"
        
    # Jika tidak ada kecocokan di atas, baru cek RENCANA AKUISISI
    if any(kata in teks_kecil for kata in kata_rencana):
        return "RENCANA AKUISISI"
        
    return "TIDAK ADA"

def main():
    print("🔍 Memulai pemindaian berita dengan metode Kata Kunci (Bebas Limit)...")
    
    if not os.path.exists("saham.txt"):
        print("❌ Error: File 'saham.txt' tidak ditemukan!")
        return

    # 1. Membaca ratusan kata kunci dari kedua file teks
    kata_rencana = load_keywords("RENCANA_AKUISISI.txt")
    kata_dalam = load_keywords("DALAM_AKUISISI.txt")

    # 2. Membaca daftar saham
    with open("saham.txt", "r") as file:
        daftar_saham = [baris.strip().upper() for baris in file if baris.strip()]
        
    hasil_akuisisi = []
    
    # 3. Proses pemindaian tanpa jeda waktu (ngebut)
    for ticker in daftar_saham:
        print(f"Memindai berita untuk {ticker}...")
        berita = get_news_titles(ticker)
        status = analyze_acquisition_status(berita, kata_rencana, kata_dalam)
        
        hasil_akuisisi.append({
            "Ticker": ticker,
            "Status Akuisisi": status
        })
        
    # 4. Simpan ke CSV
    if hasil_akuisisi:
        df = pd.DataFrame(hasil_akuisisi)
        df.to_csv("data_akuisisi.csv", index=False)
        print("✅ Selesai! File 'data_akuisisi.csv' berhasil diperbarui.")

if __name__ == "__main__":
    main()