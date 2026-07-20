import yfinance as yf
import pandas as pd
import numpy as np
import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime

# ==========================================
# SECTION 1: KONFIGURASI & SESSION ANTI-BLOKIR
# ==========================================
FILE_SAHAM = "saham.txt"
FILE_HASIL = "hasil_screener.csv"
LOCK_FILE = "sedang_update.lock"

def get_safe_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    retry = Retry(connect=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def load_tickers():
    if not os.path.exists(FILE_SAHAM):
        print(f"❌ Error: File '{FILE_SAHAM}' tidak ditemukan!")
        return []
    with open(FILE_SAHAM, "r") as file:
        return [baris.strip().upper() for baris in file if baris.strip()]

# ==========================================
# SECTION 2: KALKULASI FUNDAMENTAL RINGAN
# ==========================================
def get_fundamental(ticker_jk):
    try:
        ticker_obj = yf.Ticker(ticker_jk)
        info_data = ticker_obj.info
        mcap = info_data.get('marketCap', 0)
        per = info_data.get('trailingPE', 0)
        pbv = info_data.get('priceToBook', 0)
    except:
        mcap, per, pbv = 0, 0, 0

    if mcap > 10000000000000: kategori_saham = "Big Cap (Lapis 1)"
    elif mcap > 1000000000000: kategori_saham = "Mid Cap (Lapis 2)"
    elif mcap > 0: kategori_saham = "Small Cap (Lapis 3)"
    else: kategori_saham = "Tidak Diketahui"
    
    return kategori_saham, per, pbv

# ==========================================
# SECTION 3: KALKULASI TEKNIKAL & BANDARMOLOGI
# ==========================================
def hitung_semua_indikator(df_saham):
    close_today = df_saham['Close'].iloc[-1].item()
    close_yest = df_saham['Close'].iloc[-2].item()
    open_today = df_saham['Open'].iloc[-1].item()
    high_today = df_saham['High'].iloc[-1].item()
    low_today = df_saham['Low'].iloc[-1].item()
    vol_today = int(df_saham['Volume'].iloc[-1].item()) if not pd.isna(df_saham['Volume'].iloc[-1].item()) else 0
    
    change_rp = close_today - close_yest
    change_pct = (change_rp / close_yest) * 100
    momentum = "Positif" if change_rp > 0 else "Negatif"
    
    gap_pct = ((open_today - close_yest) / close_yest) * 100
    if gap_pct >= 2.0: status_gap = f"Gap Up (+{gap_pct:.1f}%)"
    elif gap_pct <= -2.0: status_gap = f"Gap Down ({gap_pct:.1f}%)"
    else: status_gap = "Normal"
    
    range_today = high_today - low_today
    if range_today > 0:
        buying_power = (close_today - low_today) / range_today
        if buying_power > 0.7: tekanan = "Dominan Beli (Hajar Kanan)"
        elif buying_power < 0.3: tekanan = "Dominan Jual (Guyur)"
        else: tekanan = "Seimbang / Adu Mekanik"
    else:
        tekanan = "Tidak Ada Transaksi"

    body_candle = abs(close_today - open_today)
    upper_shadow = high_today - max(open_today, close_today)
    lower_shadow = min(open_today, close_today) - low_today
    
    if body_candle <= (range_today * 0.1): pola_candle = "Doji (Ragu-ragu)"
    elif lower_shadow > (body_candle * 2) and upper_shadow < (body_candle * 0.2): pola_candle = "Hammer (Potensi Reversal)"
    elif body_candle > (range_today * 0.8) and close_today > open_today: pola_candle = "Marubozu (Strong Bullish)"
    else: pola_candle = "Normal"

    ma_20 = df_saham['Close'].rolling(window=20).mean().iloc[-1].item()
    ma_50 = df_saham['Close'].rolling(window=50).mean().iloc[-1].item()
    vol_ma_20 = df_saham['Volume'].rolling(window=20).mean().iloc[-1].item()
    
    ma_signal = "Uptrend" if close_today > ma_20 else "Downtrend"
    vol_breakout = "Tembus MA20" if vol_today > vol_ma_20 else "Normal"
    
    # --- TAMBAHAN BARU: FASE SIKLUS (MA20 vs MA50) ---
    if close_today > ma_20 and ma_20 > ma_50: fase_siklus = "Stage 2 (Strong Uptrend)"
    elif close_today < ma_20 and ma_20 < ma_50: fase_siklus = "Stage 4 (Strong Downtrend)"
    else: fase_siklus = "Konsolidasi"
    
    ma_5 = df_saham['Close'].rolling(window=5).mean().iloc[-1].item()
    ma_5_prev = df_saham['Close'].rolling(window=5).mean().iloc[-2].item()
    ma_20_prev = df_saham['Close'].rolling(window=20).mean().iloc[-2].item()
    
    if ma_5 > ma_20 and ma_5_prev <= ma_20_prev: ma_cross = "Golden Cross"
    elif ma_5 < ma_20 and ma_5_prev >= ma_20_prev: ma_cross = "Death Cross"
    elif ma_5 > ma_20: ma_cross = "Bullish"
    else: ma_cross = "Bearish"

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
    
    if vol_today > (vol_ma_20 * 2):
        if close_today > open_today: status_bandar = "Akumulasi Kuat"
        elif close_today < open_today: status_bandar = "Distribusi Kuat"
        else: status_bandar = "Normal"
    else:
        status_bandar = "Normal"

    obv = [0]
    for i in range(1, len(df_saham)):
        if df_saham['Close'].iloc[i] > df_saham['Close'].iloc[i-1]: obv.append(obv[-1] + df_saham['Volume'].iloc[i])
        elif df_saham['Close'].iloc[i] < df_saham['Close'].iloc[i-1]: obv.append(obv[-1] - df_saham['Volume'].iloc[i])
        else: obv.append(obv[-1])
    df_saham['OBV'] = obv
    
    obv_sekarang = df_saham['OBV'].iloc[-1]
    obv_5_hari_lalu = df_saham['OBV'].iloc[-6]
    if obv_sekarang > obv_5_hari_lalu: obv_trend = "Akumulasi (Naik)"
    elif obv_sekarang < obv_5_hari_lalu: obv_trend = "Distribusi (Turun)"
    else: obv_trend = "Netral"
    
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

    jarak_support = ((close_today - support_20) / support_20) * 100 if support_20 > 0 else 0
    if jarak_support <= 3.0: posisi_entry = "Dekat Support (Low Risk)"
    elif jarak_support >= 10.0: posisi_entry = "Rawan Pucuk (High Risk)"
    else: posisi_entry = "Area Tengah"

    # --- TAMBAHAN BARU: POTENSI UPSIDE (JARAK KE RESISTANCE) ---
    jarak_resist = ((resist_20 - close_today) / close_today) * 100 if close_today > 0 else 0
    if jarak_resist >= 10.0: potensi_upside = "Ruang Lebar (>10%)"
    elif jarak_resist <= 3.0: potensi_upside = "Mepet Resisten (<3%)"
    else: potensi_upside = "Area Tengah (3-10%)"

    if bandwidth > 15.0: risiko = "Tinggi"
    elif bandwidth > 8.0: risiko = "Sedang"
    else: risiko = "Rendah"
    
    delta = df_saham['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi_raw = (100 - (100 / (1 + rs))).iloc[-1].item()
    rsi = int(round(rsi_raw)) if not pd.isna(rsi_raw) else 0

    return {
        "Harga (Rp)": close_today, "Harga MA20": int(ma_20), "Support": int(support_20), "Resistance": int(resist_20),
        "Change (%)": change_pct, "Volume": vol_today, "Vol Breakout": vol_breakout, "RSI (14D)": rsi,
        "Momentum": momentum, "MA Signal": ma_signal, "Fase Siklus": fase_siklus, "MA Cross": ma_cross, "MACD": status_macd,
        "Status Bandar": status_bandar, "OBV Trend": obv_trend, "Status Gap": status_gap, "Tekanan Bandar": tekanan, 
        "Status BB": status_bb, "Risiko": risiko,
        "Likuiditas": "> 1 Miliar" if (close_today * vol_today) > 1000000000 else "< 1 Miliar",
        "Pola Candle": pola_candle, "Posisi Entry": posisi_entry, "Potensi Upside": potensi_upside
    }

# ==========================================
# SECTION 4: EKSEKUSI UTAMA (MODE DETEKTIF)
# ==========================================
def main():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

    with open(LOCK_FILE, "w") as f:
        f.write("SEDANG PROSES")

    try:
        print("⏳ Memulai pembaruan data saham (Diagnostic Mode)...")
        daftar_saham = load_tickers()
        if not daftar_saham: 
            return
        
        tickers_jk = [f"{t}.JK" for t in daftar_saham]
        tickers_str = " ".join(tickers_jk)
        
        aman_session = get_safe_session()
        
        print(f"📥 Mengunduh {len(daftar_saham)} data saham secara bersamaan (Maks 8 jalur)...")
        # PERUBAHAN: period diubah menjadi 6mo agar MA50 bisa terkalkulasi dengan benar
        data_mentah = yf.download(
            tickers_str, 
            period="6mo", 
            interval="1d", 
            group_by='ticker', 
            threads=8, 
            session=aman_session, 
            progress=False
        )
        
        if data_mentah.empty:
            print("❌ ERROR FATAL: Yahoo Finance menolak permintaan data.")
            return

        hasil = []
        error_count = 0

        for ticker in daftar_saham:
            try:
                t_jk = f"{ticker}.JK"
                if t_jk in data_mentah:
                    df_saham = data_mentah[t_jk].dropna(subset=['Open', 'Close', 'Volume', 'High', 'Low'])
                    
                    if len(df_saham) >= 55: # Ditingkatkan ke 55 agar MA50 aman dihitung
                        ind = hitung_semua_indikator(df_saham)
                        kat, per, pbv = get_fundamental(t_jk)
                        
                        score = 0
                        if ind["Vol Breakout"] == "Tembus MA20": score += 1
                        if ind["RSI (14D)"] > 50: score += 1
                        if ind["Momentum"] == "Positif": score += 1
                        if ind["MA Signal"] == "Uptrend": score += 1
                        if ind["MA Cross"] in ["Golden Cross", "Bullish"]: score += 1
                        if ind["MACD"] in ["Strong Bullish", "Bullish MACD"]: score += 1
                        if ind["Status Bandar"] == "Akumulasi Kuat": score += 1  
                        if ind["OBV Trend"] == "Akumulasi (Naik)": score += 1   
                        if ind["Tekanan Bandar"] == "Dominan Beli (Hajar Kanan)": score += 1
                        if "Gap Up" in ind["Status Gap"]: score += 1

                        rekomendasi = "BELI" if score >= 7 else "WAIT & SEE"
                        
                        if per > 0 and per < 15 and pbv > 0 and pbv < 1.5: valuasi = "Undervalued (Murah)"
                        elif per > 25 or pbv > 3.0: valuasi = "Overvalued (Mahal)"
                        else: valuasi = "Fair Value (Wajar)"
                        
                        data_akhir = {"Ticker": ticker, "Kategori": kat, "Valuasi": valuasi, "PER (x)": per, "PBV (x)": pbv}
                        data_akhir.update(ind)
                        data_akhir.update({
                            "Total Score": score, 
                            "Rekomendasi": rekomendasi, 
                            "Status Akuisisi": "TIDAK ADA", 
                            "Terakhir Update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        hasil.append(data_akhir)
            except Exception as e:
                error_count += 1
                print(f"⚠️ Error pada perhitungan saham {ticker}: {e}")

        if hasil:
            df_hasil = pd.DataFrame(hasil)
            df_hasil.to_csv(FILE_HASIL, index=False)
            print(f"✅ Selesai! Data {len(hasil)} saham berhasil diperbarui.")
        else:
            print("\n⚠️ GAGAL TOTAL: Proses selesai namun list hasil kosong.")

    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

if __name__ == "__main__":
    main()