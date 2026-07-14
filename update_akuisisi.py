import google.generativeai as genai
import feedparser
import pandas as pd
import time
import os

# Mengambil API Key dari sistem (yang sudah kamu masukkan di venv)
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("❌ Error: API Key tidak ditemukan di sistem!")
    exit()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_news_titles(ticker):
    """Menarik judul berita terbaru dari Google News RSS"""
    query = f"saham+{ticker}+akuisisi"
    url = f"https://news.google.com/rss/search?q={query}&hl=id&gl=ID&ceid=ID:id"
    feed = feedparser.parse(url)
    titles = [entry.title for entry in feed.entries[:5]]
    return " | ".join(titles) if titles else "Tidak ada berita terbaru."

def analyze_acquisition_status(ticker, news_text):
    """Meminta AI menyimpulkan status akuisisi"""
    if news_text == "Tidak ada berita terbaru.":
        return "TIDAK ADA"
        
    prompt = f"""
    Kamu adalah analis saham profesional. 
    Baca kumpulan judul berita berikut untuk saham {ticker}:
    {news_text}
    
    Apakah ada informasi valid tentang aksi korporasi akuisisi?
    Wajib balas HANYA dengan satu dari tiga pilihan ini, tanpa penjelasan apapun:
    TIDAK ADA
    RENCANA AKUISISI
    DALAM AKUISISI
    """
    
    try:
        response = model.generate_content(prompt)
        kesimpulan = response.text.strip().upper() 
        if kesimpulan not in ["TIDAK ADA", "RENCANA AKUISISI", "DALAM AKUISISI"]:
            return "TIDAK ADA"
        return kesimpulan
    except Exception as e:
        print(f"⚠️ Error menganalisis {ticker}: {e}")
        return "TIDAK ADA"

def main():
    print("🤖 Memulai pengecekan berita akuisisi menggunakan AI...")
    
    if not os.path.exists("saham.txt"):
        print("❌ Error: File 'saham.txt' tidak ditemukan!")
        return

    with open("saham.txt", "r") as file:
        daftar_saham = [baris.strip().upper() for baris in file if baris.strip()]
        
    hasil_akuisisi = []
    
    for ticker in daftar_saham:
        print(f"Menganalisis berita untuk {ticker}...")
        berita = get_news_titles(ticker)
        status = analyze_acquisition_status(ticker, berita)
        
        hasil_akuisisi.append({
            "Ticker": ticker,
            "Status Akuisisi": status
        })
        
        # Jeda 3 detik agar tidak membebani server Google
        time.sleep(3) 
        
    if hasil_akuisisi:
        df = pd.DataFrame(hasil_akuisisi)
        df.to_csv("data_akuisisi.csv", index=False)
        print("✅ Selesai! File 'data_akuisisi.csv' berhasil dibuat.")

if __name__ == "__main__":
    main()