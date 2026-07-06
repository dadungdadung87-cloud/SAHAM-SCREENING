import yfinance as yf
import pandas as pd
import numpy as np
import os

def main():
    print("⏳ Memulai pembaruan data saham (Triggered by GitHub Actions)...")
    
    if not os.path.exists("saham.txt"):
        print("❌ Error: File 'saham.txt' tidak ditemukan!")
        return
        
    with open("saham.txt", "r") as file:
        daftar_saham = [baris.strip().upper() for baris in file if baris.strip()]
        
    tickers_jk = [f"{t}.JK" for t in daftar_saham]
    tickers_str = " ".join(tickers_jk)
    
    data_mentah = yf.download(tickers_str, period="2mo", interval="1d", group_by='ticker', threads=True, progress=False)
    
    hasil = []
    
    for ticker in daftar_saham:
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
                    
                    # Kalkulasi Moving Average
                    ma_20 = df_saham['Close'].rolling(window=20).mean().iloc[-1].item()
                    vol_ma_20 = df_saham['Volume'].rolling(window=20).mean().iloc[-1].item()
                    ma_signal = "Uptrend" if close_today > ma_20 else "Downtrend"
                    vol_breakout = "Tembus MA20" if vol_today > vol_ma_20 else "Normal"
                    
                    # 🌟 KALKULASI BOLLINGER BANDS
                    std_20 = df_saham['Close'].rolling(window=20).std().iloc[-1].item()
                    upper_bb = ma_20 + (std_20 * 2)
                    lower_bb = ma_20 - (std_20 * 2)
                    
                    # Mencegah error pembagian dengan nol
                    if ma_20 != 0:
                        bandwidth = ((upper_bb - lower_bb) / ma_20) * 100
                    else:
                        bandwidth = 0
                        
                    # Menentukan Status Bollinger Bands
                    if bandwidth < 8.0:
                        status_bb = "Squeeze"
                    elif close_today > upper_bb:
                        status_bb = "Breakout Upper"
                    elif close_today > lower_bb and (abs(close_today - lower_bb) / lower_bb) < 0.02:
                        status_bb = "Bottom Rebound"
                    else:
                        status_bb = "Normal"
                    
                    # Kalkulasi RSI
                    delta = df_saham['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi_raw = 100 - (100 / (1 + rs)).iloc[-1].item()
                    rsi = int(round(rsi_raw)) if not pd.isna(rsi_raw) else 0
                    
                    # Kalkulasi Skor
                    score = 0
                    if vol_today > vol_ma_20: score += 1
                    if rsi > 50: score += 1
                    if momentum == "Positif": score += 1
                    if ma_signal == "Uptrend": score += 1

                    rekomendasi = "BELI" if score == 4 else "WAIT & SEE"
                    nilai_transaksi = close_today * vol_today
                    likuiditas = "> 1 Miliar" if nilai_transaksi > 1000000000 else "< 1 Miliar"
                    
                    hasil.append({
                        "Ticker": ticker,
                        "Harga (Rp)": close_today,
                        "Change (%)": change_pct,
                        "Volume": vol_today,
                        "Vol Breakout": vol_breakout,
                        "RSI (14D)": rsi,
                        "Momentum": momentum,
                        "MA Signal": ma_signal,
                        "Status BB": status_bb, # 🌟 DATA BARU DIMASUKKAN KE CSV
                        "Likuiditas": likuiditas,
                        "Total Score": score,
                        "Rekomendasi": rekomendasi
                    })
        except Exception as e:
            # Mengabaikan error pada ticker tertentu agar proses tetap berjalan
            pass

    if hasil:
        df_hasil = pd.DataFrame(hasil)
        df_hasil.to_csv("hasil_screener.csv", index=False)
        print(f"✅ Selesai! Data berhasil diperbarui.")

if __name__ == "__main__":
    main()