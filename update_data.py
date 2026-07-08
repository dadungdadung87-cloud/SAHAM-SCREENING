import yfinance as yf
import pandas as pd
import numpy as np
import os
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def scrape_bandarmology(ticker):
    """
    Fungsi ini bertugas membuka website finansial publik
    dan membaca tabel Broker Summary.
    """
    # Ganti URL ini dengan portal saham publik langgananmu yang tidak perlu login
    url = f"https://www.contoh-portal-saham.com/saham/{ticker}/broker-summary"
    
    # Header wajib agar server website tidak memblokir skrip Python kita
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return "Data Tidak Tersedia"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # --- ZONA KUSTOMISASI HTML ---
        # Di sinilah kamu harus menginspeksi web target (Klik Kanan -> Inspect).
        # Cari tahu apa nama 'class' dari tabel Top Broker-nya.
        # Contoh imajiner:
        # tabel_broker = soup.find('table', {'class': 'broker-summary-table'})
        # baris = tabel_broker.find_all('tr')
        # ... proses perulangan untuk mengambil total volume Net Buy dan Net Sell
        
        # 🌟 SIMULASI HASIL SCRAPING (Hapus ini jika logika HTML di atas sudah kamu buat)
        total_net_buy = 50000 
        total_net_sell = 20000 
        
        # Logika Kategori Bandarmology
        if total_net_buy > (total_net_sell * 1.5):
            return "Big Accumulation"
        elif total_net_buy > total_net_sell:
            return "Accumulation"
        elif total_net_sell > (total_net_buy * 1.5):
            return "Big Distribution"
        elif total_net_sell > total_net_buy:
            return "Distribution"
        else:
            return "Netral"
            
    except Exception as e:
        print(f"⚠️ Gagal scrape {ticker}: {e}")
        return "Netral"

def main():
    print("⏳ Memulai pembaruan data saham dan scraping bandarmology...")
    
    if not os.path.exists("saham.txt"):
        print("❌ Error: File 'saham.txt' tidak ditemukan!")
        return
        
    with open("saham.txt", "r") as file:
        daftar_saham = [baris.strip().upper() for baris in file if baris.strip()]
        
    # Mengambil data harga & volume dasar dari Yahoo Finance
    tickers_jk = [f"{t}.JK" for t in daftar_saham]
    tickers_str = " ".join(tickers_jk)
    data_mentah = yf.download(tickers_str, period="2mo", interval="1d", group_by='ticker', threads=True, progress=False)
    
    hasil = []
    total_saham = len(daftar_saham)
    
    for urutan, ticker in enumerate(daftar_saham, 1):
        try:
            t_jk = f"{ticker}.JK"
            if t_jk in data_mentah:
                df_saham = data_mentah[t_jk].dropna(subset=['Close', 'Volume'])
                
                if len(df_saham) >= 25:
                    close_today = df_saham['Close'].iloc[-1].item()
                    close_yest = df_saham['Close'].iloc[-2].item()
                    vol_val = df_saham['Volume'].iloc[-1].item()
                    vol_today = int(vol_val) if not pd.isna(vol_val) else 0
                    
                    change_rp = close_today - close_yest
                    change_pct = (change_rp / close_yest) * 100
                    momentum = "Positif" if change_rp > 0 else "Negatif"
                    
                    # Indikator Teknikal MA & Bollinger Bands
                    ma_20 = df_saham['Close'].rolling(window=20).mean().iloc[-1].item()
                    vol_ma_20 = df_saham['Volume'].rolling(window=20).mean().iloc[-1].item()
                    ma_signal = "Uptrend" if close_today > ma_20 else "Downtrend"
                    vol_breakout = "Tembus MA20" if vol_today > vol_ma_20 else "Normal"
                    
                    std_20 = df_saham['Close'].rolling(window=20).std().iloc[-1].item()
                    upper_bb = ma_20 + (std_20 * 2)
                    lower_bb = ma_20 - (std_20 * 2)
                    bandwidth = ((upper_bb - lower_bb) / ma_20) * 100 if ma_20 != 0 else 0
                        
                    if bandwidth < 8.0: status_bb = "Squeeze"
                    elif close_today > upper_bb: status_bb = "Breakout Upper"
                    elif close_today > lower_bb and (abs(close_today - lower_bb) / lower_bb) < 0.02: status_bb = "Bottom Rebound"
                    else: status_bb = "Normal"
                    
                    # 🌟 MEMANGGIL FUNGSI SCRAPING BANDARMOLOGY
                    print(f"[{urutan}/{total_saham}] Menganalisis teknikal & bandar untuk {ticker}...")
                    status_bandar = scrape_bandarmology(ticker)
                    
                    # Jeda waktu 1-2 detik agar IP tidak diblokir oleh website target karena dianggap spam/DDoS
                    time.sleep(1.5)
                    
                    # Kalkulasi Skor Akhir
                    score = 0
                    if vol_today > vol_ma_20: score += 1
                    if momentum == "Positif": score += 1
                    if ma_signal == "Uptrend": score += 1
                    if status_bandar in ["Accumulation", "Big Accumulation"]: score += 1

                    rekomendasi = "BELI" if score == 4 else "WAIT & SEE"
                    nilai_transaksi = close_today * vol_today
                    likuiditas = "> 1 Miliar" if nilai_transaksi > 1000000000 else "< 1 Miliar"
                    
                    hasil.append({
                        "Ticker": ticker,
                        "Harga (Rp)": close_today,
                        "Change (%)": change_pct,
                        "Volume": vol_today,
                        "Vol Breakout": vol_breakout,
                        "Momentum": momentum,
                        "MA Signal": ma_signal,
                        "Status BB": status_bb, 
                        "Status Bandar": status_bandar, # 🌟 Kolom baru untuk Streamlit
                        "Likuiditas": likuiditas,
                        "Total Score": score,
                        "Rekomendasi": rekomendasi,
                        "Terakhir Update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
        except Exception as e:
            pass

    if hasil:
        df_hasil = pd.DataFrame(hasil)
        df_hasil.to_csv("hasil_screener.csv", index=False)
        print(f"\n✅ Selesai! Data berhasil diperbarui dan CSV telah dibuat.")

if __name__ == "__main__":
    main()