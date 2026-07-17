import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime

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
                # Membutuhkan kolom 'Open' untuk mendeteksi warna candle (Akumulasi/Distribusi)
                df_saham = data_mentah[t_jk].dropna(subset=['Open', 'Close', 'Volume', 'High', 'Low'])
                
                if len(df_saham) >= 26:
                    close_today = df_saham['Close'].iloc[-1].item()
                    close_yest = df_saham['Close'].iloc[-2].item()
                    open_today = df_saham['Open'].iloc[-1].item()
                    vol_val = df_saham['Volume'].iloc[-1].item()
                    vol_today = int(vol_val) if not pd.isna(vol_val) else 0
                    
                    change_rp = close_today - close_yest
                    change_pct = (change_rp / close_yest) * 100
                    momentum = "Positif" if change_rp > 0 else "Negatif"
                    
                    # MA dan Volume MA
                    ma_20 = df_saham['Close'].rolling(window=20).mean().iloc[-1].item()
                    vol_ma_20 = df_saham['Volume'].rolling(window=20).mean().iloc[-1].item()
                    ma_signal = "Uptrend" if close_today > ma_20 else "Downtrend"
                    vol_breakout = "Tembus MA20" if vol_today > vol_ma_20 else "Normal"
                    
                    # MA Crossover
                    ma_5 = df_saham['Close'].rolling(window=5).mean().iloc[-1].item()
                    ma_5_prev = df_saham['Close'].rolling(window=5).mean().iloc[-2].item()
                    ma_20_prev = df_saham['Close'].rolling(window=20).mean().iloc[-2].item()
                    
                    if ma_5 > ma_20 and ma_5_prev <= ma_20_prev: ma_cross = "Golden Cross"
                    elif ma_5 < ma_20 and ma_5_prev >= ma_20_prev: ma_cross = "Death Cross"
                    elif ma_5 > ma_20: ma_cross = "Bullish"
                    else: ma_cross = "Bearish"

                    # MACD
                    ema_12 = df_saham['Close'].ewm(span=12, adjust=False).mean()
                    ema_26 = df_saham['Close'].ewm(span=26, adjust=False).mean()
                    macd_line = ema_12 - ema_26
                    signal_line = macd_line.ewm(span=9, adjust=False).mean()
                    
                    macd_val = macd_line.iloc[-1].item()
                    sig_val = signal_line.iloc[-1].item()
                    
                    if macd_val > sig_val and macd_val > 0: status_macd = "Strong Bullish"
                    elif macd_val > sig_val: status_macd = "Bullish MACD"
                    elif macd_val < sig_val and macd_val < 0: status_macd = "Strong Bearish"
                    else: status_macd = "Bearish MACD"
                    
                    # --- IDE BARU 1: STATUS BANDAR (Deteksi Anomali Volume + Price Action) ---
                    # Jika volume hari ini melonjak > 2x lipat dari rata-rata (Uang besar beraksi)
                    if vol_today > (vol_ma_20 * 2):
                        if close_today > open_today:
                            status_bandar = "Akumulasi Kuat" # Tarik harga ke atas
                        elif close_today < open_today:
                            status_bandar = "Distribusi Kuat" # Buang barang (Guyur)
                        else:
                            status_bandar = "Normal"
                    else:
                        status_bandar = "Normal"

                    # --- IDE BARU 2: ON-BALANCE VOLUME (OBV) TREND ---
                    obv = [0]
                    for i in range(1, len(df_saham)):
                        if df_saham['Close'].iloc[i] > df_saham['Close'].iloc[i-1]:
                            obv.append(obv[-1] + df_saham['Volume'].iloc[i])
                        elif df_saham['Close'].iloc[i] < df_saham['Close'].iloc[i-1]:
                            obv.append(obv[-1] - df_saham['Volume'].iloc[i])
                        else:
                            obv.append(obv[-1])
                    df_saham['OBV'] = obv
                    
                    # Cek tren OBV 5 hari terakhir
                    obv_sekarang = df_saham['OBV'].iloc[-1]
                    obv_5_hari_lalu = df_saham['OBV'].iloc[-6]
                    if obv_sekarang > obv_5_hari_lalu:
                        obv_trend = "Akumulasi (Naik)"
                    elif obv_sekarang < obv_5_hari_lalu:
                        obv_trend = "Distribusi (Turun)"
                    else:
                        obv_trend = "Netral"
                    
                    # Bollinger Bands & Risiko
                    std_20 = df_saham['Close'].rolling(window=20).std().iloc[-1].item()
                    upper_bb = ma_20 + (std_20 * 2)
                    lower_bb = ma_20 - (std_20 * 2)
                    bandwidth = ((upper_bb - lower_bb) / ma_20) * 100 if ma_20 != 0 else 0
                        
                    if bandwidth < 8.0: status_bb = "Squeeze"
                    elif close_today > upper_bb: status_bb = "Breakout Upper"
                    elif close_today > lower_bb and (abs(close_today - lower_bb) / lower_bb) < 0.02: status_bb = "Bottom Rebound"
                    else: status_bb = "Normal"

                    support_20 = df_saham['Low'].rolling(window=20).min().iloc[-1].item()
                    resist_20 = df_saham['High'].rolling(window=20).max().iloc[-1].item()

                    if bandwidth > 15.0: risiko = "Tinggi"
                    elif bandwidth > 8.0: risiko = "Sedang"
                    else: risiko = "Rendah"
                    
                    # RSI
                    delta = df_saham['Close'].diff()
                    gain = delta.where(delta > 0, 0)
                    loss = -delta.where(delta < 0, 0)
                    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
                    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
                    rs = avg_gain / avg_loss
                    rsi_raw = (100 - (100 / (1 + rs))).iloc[-1].item()
                    rsi = int(round(rsi_raw)) if not pd.isna(rsi_raw) else 0
                    
                    # Kalkulasi Skor (Maksimal 8)
                    score = 0
                    if vol_today > vol_ma_20: score += 1
                    if rsi > 50: score += 1
                    if momentum == "Positif": score += 1
                    if ma_signal == "Uptrend": score += 1
                    if ma_cross in ["Golden Cross", "Bullish"]: score += 1
                    if status_macd in ["Strong Bullish", "Bullish MACD"]: score += 1
                    if status_bandar == "Akumulasi Kuat": score += 1  # Skor Bandarmologi
                    if obv_trend == "Akumulasi (Naik)": score += 1   # Skor Bandarmologi

                    rekomendasi = "BELI" if score >= 6 else "WAIT & SEE"
                    nilai_transaksi = close_today * vol_today
                    likuiditas = "> 1 Miliar" if nilai_transaksi > 1000000000 else "< 1 Miliar"
                    
                    waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    hasil.append({
                        "Ticker": ticker,
                        "Harga (Rp)": close_today,
                        "Harga MA20": int(ma_20),
                        "Support": int(support_20),
                        "Resistance": int(resist_20),
                        "Change (%)": change_pct,
                        "Volume": vol_today,
                        "Vol Breakout": vol_breakout,
                        "RSI (14D)": rsi,
                        "Momentum": momentum,
                        "MA Signal": ma_signal,
                        "MA Cross": ma_cross,         
                        "MACD": status_macd,
                        "Status Bandar": status_bandar, # <--- KOLOM BARU DITAMBAHKAN
                        "OBV Trend": obv_trend,         # <--- KOLOM BARU DITAMBAHKAN
                        "Status BB": status_bb, 
                        "Risiko": risiko,
                        "Likuiditas": likuiditas,
                        "Total Score": score,
                        "Rekomendasi": rekomendasi,
                        "Terakhir Update": waktu_sekarang
                    })
        except Exception as e:
            pass

    if hasil:
        df_hasil = pd.DataFrame(hasil)
        df_hasil.to_csv("hasil_screener.csv", index=False)
        print(f"✅ Selesai! Data berhasil diperbarui.")

if __name__ == "__main__":
    main()