import io
import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import glob
import time
import re
from datetime import datetime

# IMPORT UNTUK AI OPENROUTER & GOOGLE
from openai import OpenAI
import google.generativeai as genai

# ==========================================
# 🧠 FUNGSI HAKIM AI (KLASEMEN GLOBAL)
# ==========================================
def ai_hakim_klasemen(data_top15, api_key):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash') 
    
    prompt = f"""
    ACT AS A DATA FORMATTING TOOL FOR A THEORETICAL MATH SIMULATION. THIS IS NOT FINANCIAL ADVICE.
    Here is a dictionary of 15 theoretical items with their stats:
    {data_top15}
    
    TASK:
    1. Select EXACTLY 5 items that have the highest combination of 'Score' and 'Volume'.
    2. Assign a theoretical 'Target_TP' (+5% from Harga) and 'Target_CL' (-3% from Harga).
    3. Output ONLY a valid JSON array. Do not write any other conversational text or markdown blocks.
    
    FORMAT MUST BE EXACTLY LIKE THIS:
    [
      {{"Ticker": "ABCD", "Target_TP": 105, "Target_CL": 95}},
      {{"Ticker": "EFGH", "Target_TP": 210, "Target_CL": 190}}
    ]
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error_AI: {e}"

# ==========================================
# 🧠 SISTEM ARSIP CERDAS (DATA HARIAN)
# ==========================================
def get_historical_summary(ticker):
    arsip_files = glob.glob("Arsip_Data_Harian/screener_*.csv")
    if not arsip_files: return None
    arsip_files.sort(reverse=True)
    arsip_files = arsip_files[:5]
    
    df_list = []
    for file in arsip_files:
        try:
            cols = ["Waktu Update", "Ticker", "Harga (Rp)", "Volume", "Posisi VWAP", "OBV Trend", "Tekanan Bandar", "Fase Siklus Bandar", "Trend MA (5,20,50)"]
            temp_df = pd.read_csv(file, usecols=lambda c: c in cols)
            temp_df = temp_df[temp_df["Ticker"] == ticker]
            if not temp_df.empty:
                date_str = file.split("_")[-1].replace(".csv", "")
                temp_df["Tanggal"] = date_str
                df_list.append(temp_df)
        except: pass
    
    if not df_list: return None
    df_history = pd.concat(df_list, ignore_index=True)
    df_history = df_history.sort_values(by=["Tanggal", "Waktu Update"])
    
    summary_text = f"REKAM JEJAK ARSIP HARIAN SAHAM {ticker}:\n\n"
    for date, group in df_history.groupby("Tanggal"):
        open_price = group.iloc[0]["Harga (Rp)"]
        close_price = group.iloc[-1]["Harga (Rp)"]
        max_vol = group["Volume"].max()
        tekanan_akhir = group.iloc[-1]["Tekanan Bandar"]
        siklus = group.iloc[-1]["Fase Siklus Bandar"]
        summary_text += f"📅 {date} | Buka: {open_price} | Tutup: {close_price} | Max Vol Harian: {max_vol} | Tekanan Akhir: {tekanan_akhir} | Siklus Wyckoff: {siklus}\n"
    return summary_text

def get_forensic_data(ticker):
    arsip_files = glob.glob("Arsip_Data_Harian/screener_*.csv")
    if not arsip_files: return None
    arsip_files.sort(reverse=True)
    arsip_files = arsip_files[:5] 
    
    df_list = []
    for file in arsip_files:
        try:
            cols = ["Waktu Update", "Ticker", "Harga (Rp)", "Volume", "Posisi VWAP", "OBV Trend", "Tekanan Bandar", "Fase Siklus Bandar", "Trend MA (5,20,50)", "Status BB", "RVOL (Anomali Vol)"]
            temp_df = pd.read_csv(file, usecols=lambda c: c in cols)
            temp_df = temp_df[temp_df["Ticker"] == ticker]
            if not temp_df.empty:
                date_str = file.split("_")[-1].replace(".csv", "")
                temp_df["Tanggal"] = date_str
                df_list.append(temp_df)
        except: pass
    
    if not df_list: return None
    df_history = pd.concat(df_list, ignore_index=True)
    df_history = df_history.sort_values(by=["Tanggal", "Waktu Update"])
    
    tanggal_unik = sorted(df_history["Tanggal"].unique())
    if len(tanggal_unik) > 1:
        tanggal_unik = tanggal_unik[:-1] 
        tanggal_unik = tanggal_unik[-3:] 
    else:
        return "Data historis sebelum hari ini belum tersedia di arsip."
        
    df_history = df_history[df_history["Tanggal"].isin(tanggal_unik)]
    
    summary_text = f"REKAM JEJAK H-3 SEBELUM MELEDAK SAHAM {ticker}:\n"
    for date, group in df_history.groupby("Tanggal"):
        close_price = group.iloc[-1]["Harga (Rp)"]
        max_vol = group["Volume"].max()
        tekanan_akhir = group.iloc[-1]["Tekanan Bandar"]
        siklus = group.iloc[-1]["Fase Siklus Bandar"]
        obv = group.iloc[-1]["OBV Trend"] if "OBV Trend" in group.columns else "N/A"
        rvol = group.iloc[-1]["RVOL (Anomali Vol)"] if "RVOL (Anomali Vol)" in group.columns else "N/A"
        bb = group.iloc[-1]["Status BB"] if "Status BB" in group.columns else "N/A"
        
        summary_text += f"📅 {date} | Tutup: {close_price} | Vol: {max_vol} | Tekanan: {tekanan_akhir} | Siklus: {siklus} | OBV: {obv} | RVOL: {rvol} | BB: {bb}\n"
    return summary_text

# ==========================================
# 🤖 OTAK KECERDASAN BUATAN (OPENROUTER)
# ==========================================

# AI BANDAR (V6)
def analisa_bandar_ai_multisaham(data_saham_dict, pilihan_ai):
    try:
        OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY"))
    except:
        OPENROUTER_API_KEY = None
    if not OPENROUTER_API_KEY: return "❌ Kunci API OpenRouter belum dipasang!"

    model_andalan = "openrouter/free" 

    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
        
        payload_text = ""
        for ticker, data in data_saham_dict.items():
            payload_text += f"\n--- STOCK: {ticker} ---\n"
            payload_text += f"Current Price: Rp {data['harga']}\n"
            payload_text += f"Today's Change: {data['change']}%\n"
            payload_text += f"Broker Summary: {data['broksum']}\n"
            payload_text += f"Wyckoff Phase: {data['status']}\n"
            payload_text += f"Technical Score: {data['skor']}/10\n"
            payload_text += f"Historical Trace (Daily):\n{data['histori']}\n"

        prompt = f"""
        You are the mastermind of an elite Indonesian stock market syndicate (Mega Bandar). 
        Your specialty is 'Gorengan' (highly volatile) stocks. You DO NOT buy stocks that have already pumped today. You look for "Stealth Accumulation"—stocks that are currently sideways or slightly up (Change is <= 5%), but have massive hidden accumulation in the historical intraday data, indicating they are ready to EXPLODE to top gainers tomorrow.

        I have filtered and provided {len(data_saham_dict)} candidate stocks that haven't pumped yet today.

        YOUR TASK:
        Analyze the 'Historical Trace' and 'Broker Summary' carefully. Select ONLY THE TOP 5 STOCKS that have completed their stealth accumulation phase today (by 15:00) and are 100% ready for a massive Mark-Up tomorrow morning (BSJP strategy).

        STOCK DATA TO ANALYZE:
        {payload_text}

        STRICT RULES:
        1. OUTPUT LANGUAGE: MUST be in Indonesian.
        2. DO NOT list all stocks. ONLY output your Top 5 selections.
        3. Create a Markdown table: [Peringkat, Ticker, Skor Ledakan (0-100%), Status Saat Ini].
        4. Below the table, provide a brutally analytical explanation for each stock. Prove why the pump is imminent by citing specific anomalies from the 'Historical Trace' and 'Broker Summary'.
        5. Provide a realistic Trading Plan (Buy Area near Current Price, Target Price for a massive pump >10%, and a tight Cut Loss). 
        6. Act like a ruthless market maker. No pleasantries. Start immediately with the table.
        """
        completion = client.chat.completions.create(
            model=model_andalan, messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=3000, top_p=1, stream=False,
        )
        
        hasil_mentah = completion.choices[0].message.content
        model_terpakai = completion.model
        
        if not hasil_mentah:
            return f"⚠️ Server AI (Model: {model_terpakai}) gagal memberikan jawaban. Silakan coba lagi."
            
        return hasil_mentah + f"\n\n---\n⚡ *Dianalisa otomatis menggunakan mesin: **{model_terpakai}** via OpenRouter*"
    except Exception as e: return f"❌ Gagal memproses data dengan OpenRouter menggunakan auto-model. Error: {e}"

# AI FORENSIK BANDAR (V7)
def analisa_forensik_ai(data_saham_dict, master_filters_keys):
    try:
        OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY"))
    except:
        OPENROUTER_API_KEY = None
    if not OPENROUTER_API_KEY: return "❌ Kunci API OpenRouter belum dipasang!"

    model_andalan = "openrouter/free" 

    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
        payload_text = ""
        for ticker, data in data_saham_dict.items():
            payload_text += f"\n--- STOCK: {ticker} ---\n"
            payload_text += f"Broker Summary (Hari H): {data['broksum']}\n"
            payload_text += f"{data['histori']}\n"

        prompt = f"""
        You are a legendary Quantitative Analyst and Stock Market Forensic Expert in Indonesia.
        I am giving you the historical data of {len(data_saham_dict)} stocks from EXACTLY 1 TO 3 DAYS BEFORE they skyrocketed to Top Gainers / ARA (>10%). This is their condition BEFORE the pump.

        YOUR OBJECTIVE:
        1. Reverse engineer the 'Bandar' strategy. Find the exact common "DNA" or hidden patterns that occurred in these stocks during the 3 days BEFORE they exploded, including their Broker Summary activity.
        2. Cross-reference your findings with the EXISTING WEB FILTERS in my application.
        3. Suggest new metrics if my existing filters are missing the secret sauce.

        DATA STOCKS (H-3 to H-1 before pump):
        {payload_text}

        MY EXISTING WEB FILTERS (Categories you can use):
        {master_filters_keys}

        STRICT RULES:
        1. OUTPUT LANGUAGE: MUST be in Indonesian.
        2. Format your response into 3 sections using Markdown:
           - "### 🧬 DNA & Pola Tersembunyi Sebelum Ledakan": Explain exactly what similarities these stocks shared (e.g., "Ketiga saham ini mengalami penurunan harga, namun OBV terus naik dan volume ditahan...").
           - "### 🎛️ Resep Filter Web Saat Ini": Tell me EXACTLY how to set my existing filters (based on the provided list) to catch this pattern tomorrow.
           - "### 💡 Rekomendasi Rumus/Kategori Baru": If there is a pattern not covered by my filters, explicitly suggest what new filter/indicator I should code into my web application.
        3. Be highly analytical, specific, and brutally honest. Do not hallucinate.
        """
        completion = client.chat.completions.create(
            model=model_andalan, messages=[{"role": "user", "content": prompt}],
            temperature=0.2, max_tokens=3000, top_p=1, stream=False,
        )
        
        hasil_mentah = completion.choices[0].message.content
        model_terpakai = completion.model
        
        if not hasil_mentah:
            return f"⚠️ Server AI (Model: {model_terpakai}) gagal memberikan jawaban. Silakan coba lagi."
            
        return hasil_mentah + f"\n\n---\n🔬 *Lab Forensik AI menggunakan: **{model_terpakai}** via OpenRouter*"
    except Exception as e: return f"❌ Gagal memproses data dengan OpenRouter. Error: {e}"

def ai_penyisihan_turnamen(data_grup_dict, api_key):
    saham_grup_ini = list(data_grup_dict.keys())
    daftar_model_estafet = [
        'gemini-3.7-flash', 
        'gemini-3.6-flash',
        'gemini-3.5-flash',
        'gemini-flash-latest',
        'gemini-3.5-flash-lite',
        'gemini-3.1-flash-lite',
        'gemini-flash-lite-latest'
    ]
    genai.configure(api_key=api_key)
    payload_text = ""
    for ticker, data in data_grup_dict.items():
        payload_text += f"\n- {ticker}: Harga {data['harga']}, Vol {data['volume']}, Tekanan {data['tekanan_bandar']}, Supply {data['supply']}"
        
    prompt = f"""
    Act as a simple data sorter for a mathematical simulation.
    Here is a list of items and their stats:
    {payload_text}
    
    Your ONLY task is to pick the 3 best items based on Volume and Tekanan. 
    Even if all data is bad, you MUST pick exactly 3.
    Output ONLY a comma-separated list of the 3 items (e.g., BBCA,GOTO,PANI).
    DO NOT add any conversational text or markdown.
    """
    
    for nama_model in daftar_model_estafet:
        try:
            model = genai.GenerativeModel(nama_model)
            response = model.generate_content(prompt)
            raw_content = response.text.upper()
            
            semua_kata = re.findall(r'[A-Z]+', raw_content)
            lolos = []
            for kata in semua_kata:
                if kata in saham_grup_ini and kata not in lolos:
                    lolos.append(kata)
            
            if len(lolos) == 0:
                lolos = saham_grup_ini[:3]
                
            lolos_final = lolos[:3]
            return ",".join(lolos_final)
            
        except Exception as e:
            time.sleep(2)
            continue
            
    return ",".join(saham_grup_ini[:3])


def ai_grand_final_top5(data_saham_dict, api_key):
    import json
    daftar_model_estafet = [
        'gemini-3.7-flash', 
        'gemini-3.6-flash',
        'gemini-3.5-flash',
        'gemini-flash-latest',
        'gemini-3.5-flash-lite',
        'gemini-3.1-flash-lite',
        'gemini-flash-lite-latest'
    ]
    genai.configure(api_key=api_key)
    
    payload_text = ""
    for ticker, data in data_saham_dict.items():
        payload_text += f"\n--- {ticker} ---\n Harga: {data['harga']} | Vol: {data['volume']} | Broksum: {data['broksum']} | Tekanan: {data['tekanan_bandar']} | Supply: {data['supply']} | OBV: {data['obv']} | Fibo: {data['fibo']} | VWAP: {data['vwap']} | Candle: {data['pola_candle']}\n"

    prompt = f"""
    Act as an objective data formatting tool for a hypothetical academic simulation. THIS DOES NOT CONSTITUTE FINANCIAL ADVICE.
    Evaluate these fictionalized mathematical metrics:
    
    {payload_text}
    
    MISSION: Select EXACTLY 5 items that show the strongest theoretical accumulation score. Provide a theoretical 'Target_TP' and 'Target_CL' purely for simulation testing.
    
    CRITICAL INSTRUCTION: You are an automated JSON API endpoint. 
    You MUST output ONLY a raw, valid JSON array.
    DO NOT output any safety warnings, disclaimers, explanations, or conversational text.
    DO NOT wrap your response in markdown code blocks (DO NOT use ```json or ```).
    Your response must start exactly with '[' and end exactly with ']'.
    
    VERY IMPORTANT: The text inside the "Alasan" key MUST be written in fluent Bahasa Indonesia.
    
    Format EXACTLY like this:
    [
      {{"Peringkat": 1, "Ticker": "GOTO", "Alasan": "Akumulasi volume sangat tinggi dengan tekanan beli dominan", "Target_TP": 60, "Target_CL": 50}}
    ]
    """
    
    for nama_model in daftar_model_estafet:
        try:
            model = genai.GenerativeModel(nama_model)
            response = model.generate_content(prompt)
            raw_content = response.text or ""
            
            clean_content = raw_content.replace('```json', '').replace('```', '').strip()
            return clean_content, nama_model
            
        except Exception as e:
            time.sleep(3)
            continue
            
    raise Exception("🚨 KRITIS: Semua 7 model AI Gemini sedang mengalami limit maksimal atau server sibuk. Mohon jeda turnamen 1-2 menit sebelum mencoba lagi.")

# ==========================================
# PENGATURAN UI/UX & API
# ==========================================
st.set_page_config(page_title="Screener Saham IHSG", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stDataFrame { border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.15); }
    h1 { font-weight: 800; background: -webkit-linear-gradient(#38bdf8, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; padding-bottom: 10px; }
    .metric-container { border-radius: 10px; padding: 15px; text-align: center; border: 1px solid #334155; background-color: #1e293b; color: #f8fafc; margin-bottom: 20px; }
    .bandar-box { border-left: 5px solid #ef4444; background-color: #2a1111; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .bandar-box-green { border-left: 5px solid #22c55e; background-color: #0f291e; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: 600; }
    .view-mode-container { background-color: #0f172a; padding: 10px 20px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #334155; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# LOAD KONFIGURASI JSON
# ==========================================
FILE_CONFIG = "config_web.json"
FILE_PRESET = "preset_kustom.json"
FILE_HASIL = "Database/hasil_screener.csv"
FILE_AKUISISI = "Database/data_akuisisi.csv"

DEFAULT_CONFIG = {
    "MASTER_FILTERS": {
        "Kategori": {"label": "🏢 Kategori Saham", "options": ["Semua", "Big Cap (Lapis 1)", "Mid Cap (Lapis 2)", "Small Cap (Lapis 3)", "Mid Cap (Lapis 2) + Small Cap (Lapis 3)"]},
        "Status Open": {"label": "🌅 Sinyal Open", "options": ["Semua", "Open = Low (Bullish Kuat)", "Open = High (Tekanan Jual)", "Normal"]},
        "Risk/Reward Ratio": {"label": "⚖️ Risk/Reward", "options": ["Semua", "Sangat Menarik (> 1:3)", "Ideal (1:2)", "Menengah (1:1)", "Tidak Ideal (< 1:1)", "Di Area Support"]},
        "Kelas Transaksi": {"label": "💸 Kelas Transaksi", "options": ["Semua", "Sultan (> 50M/hari)", "Ritel Aktif (5M - 50M)", "Gorengan Sepi (< 5M)"]},
        "Sinyal Cuci Barang": {"label": "🧹 Sinyal Shakeout", "options": ["Semua", "Jarum Bawah (Sinyal Pantulan Kuat)", "Normal"]},
        "Valuasi": {"label": "💎 Valuasi Fundamental", "options": ["Semua", "Undervalued (Murah)", "Fair Value (Wajar)", "Overvalued (Mahal)"]},
        "Posisi VWAP": {"label": "⚖️ Posisi thd VWAP", "options": ["Semua", "Di Atas VWAP (Kuat)", "Di Bawah VWAP (Lemah)", "Persis di VWAP"]},
        "Fase Siklus Bandar": {"label": "🔄 Siklus Wyckoff", "options": ["Semua", "Accumulation (Kumpul Barang)", "Mark-Up (Fase Pesta)", "Distribution (Fase Jualan)", "Mark-Down (Fase Runtuh)", "Sideways"]},
        "RVOL (Anomali Vol)": {"label": "🌋 Ledakan Volume", "options": ["Semua", "Ledakan Ekstrem (> 300%)", "Anomali Tinggi (150-300%)", "Normal (50-150%)", "Sepi (< 50%)"]},
        "Karakter Gorengan": {"label": "🕵️ Karakter Saham", "options": ["Semua", "Spesialis Tiang Jemuran (Banting Pucuk)", "Solid (Jarang Dibanting)", "Normal"]},
        "Status Bandar": {"label": "🕵️ Status Bandar", "options": ["Semua", "Akumulasi Kuat", "Distribusi Kuat", "Normal"]},
        "Tekanan Bandar": {"label": "⚔️ Tekanan Harian", "options": ["Semua", "Dominan Beli (Hajar Kanan)", "Dominan Jual (Guyur)", "Seimbang / Adu Mekanik"]},
        "Kekuatan A/D": {"label": "🧠 Smart Money (A/D)", "options": ["Semua", "Akumulasi Pro (Smart Money)", "Distribusi Pro (Guyuran)", "Netral"]},
        "OBV Trend": {"label": "🌊 Tren Uang (OBV)", "options": ["Semua", "Akumulasi (Naik)", "Distribusi (Turun)", "Netral"]},
        "Pola Candle": {"label": "🕯️ Price Action", "options": ["Semua", "Marubozu (Strong Bullish)", "Hammer (Potensi Reversal)", "Doji (Ragu-ragu)", "Normal"]},
        "Posisi Entry": {"label": "🎯 Jarak ke Support", "options": ["Semua", "Dekat Support (Low Risk)", "Area Tengah", "Rawan Pucuk (High Risk)"]},
        "Vol Breakout": {"label": "🔊 Volume", "options": ["Semua", "Tembus MA20", "Normal"]},
        "RSI (14D)": {"label": "📊 RSI (14D)", "options": ["Semua", "> 50 (Bullish)", "<= 50 (Bearish)"]},
        "MA Signal": {"label": "📈 Tren (MA20)", "options": ["Semua", "Uptrend", "Downtrend"]},
        "Momentum": {"label": "⚡ Momentum", "options": ["Semua", "Positif", "Negatif"]},
        "Total Score": {"label": "⭐ Total Score", "options": ["Semua", 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]},
        "Rekomendasi": {"label": "🎯 Rekomendasi", "options": ["Semua", "BELI", "WAIT & SEE"]},
        "Likuiditas": {"label": "💧 Likuiditas", "options": ["Semua", "> 1 Miliar", "< 1 Miliar"]},
        "Status BB": {"label": "🌐 Bollinger Bands", "options": ["Semua", "Squeeze", "Bottom Rebound", "Breakout Upper", "Normal"]},
        "MA Cross": {"label": "🔀 MA Cross (5/20)", "options": ["Semua", "Golden Cross", "Bullish", "Death Cross", "Bearish"]},
        "Risiko": {"label": "⚠️ Risiko Volatilitas", "options": ["Semua", "Tinggi", "Sedang", "Rendah"]},
        "Status Akuisisi": {"label": "🤝 Sentimen Akuisisi", "options": ["Semua", "TIDAK ADA", "RENCANA AKUISISI", "DALAM AKUISISI"]},
        "MACD": {"label": "📈 MACD", "options": ["Semua", "Strong Bullish", "Bullish MACD", "Strong Bearish", "Bearish MACD"]},
        "Status Stochastic": {"label": "🌊 Stochastic", "options": ["Semua", "Oversold (Jenuh Jual - Peluang)", "Golden Cross (Awal Bullish)", "Overbought (Jenuh Beli - Rawan)", "Death Cross (Awal Bearish)", "Netral / Sideways"]},
        "Status Sentimen": {"label": "📰 Sentimen Berita", "options": ["Semua", "Sentimen Positif 📰", "Sentimen Negatif ⚠️", "Netral / Sepi Berita"]},
        "Prediksi Machine Learning": {"label": "🧠 AI Machine Learning", "options": ["Semua", "🔥 ANOMALI BANDAR (Siap Ledakan)", "⚠️ Anomali (Sudah Terbang)", "Biasa / Mengikuti Pasar"]},
        "Kondisi Supply": {"label": "🏜️ Supply & Demand", "options": ["Semua", "Supply Kering (Siap Pump) 🏜️", "Supply Banjir (Distribusi) 🌊", "Normal / Sedang Transisi"]},
        "Status Fibonacci": {"label": "📏 Level Fibonacci", "options": ["Semua", "Golden Rebound Fibo 61.8% (Golden Ratio) 🎯", "Dekat Support Fibo 61.8% (Golden Ratio)", "Golden Rebound Fibo 50.0% 🎯", "Golden Rebound Fibo 38.2% 🎯", "Mengambang (Jauh dari Fibo)"]}
    }
}

if not os.path.exists(FILE_CONFIG):
    with open(FILE_CONFIG, "w") as f: json.dump(DEFAULT_CONFIG, f, indent=4)
else:
    with open(FILE_CONFIG, "r") as f: cek_config = json.load(f)
    if "Status Fibonacci" not in cek_config.get("MASTER_FILTERS", {}):
        with open(FILE_CONFIG, "w") as f: json.dump(DEFAULT_CONFIG, f, indent=4)

with open(FILE_CONFIG, "r") as f: WEB_CONFIG = json.load(f)

# Auto-patch
if "Mid Cap (Lapis 2) + Small Cap (Lapis 3)" not in WEB_CONFIG["MASTER_FILTERS"]["Kategori"]["options"]:
    WEB_CONFIG["MASTER_FILTERS"]["Kategori"]["options"] = ["Semua", "Big Cap (Lapis 1)", "Mid Cap (Lapis 2)", "Small Cap (Lapis 3)", "Mid Cap (Lapis 2) + Small Cap (Lapis 3)"]
    with open(FILE_CONFIG, "w") as f: json.dump(WEB_CONFIG, f, indent=4)

MASTER_FILTERS = WEB_CONFIG["MASTER_FILTERS"]

# ==========================================
# DATABASE PRESET & LOAD DATA
# ==========================================
def muat_preset():
    preset_bawaan = {
        "🌙 BSJP (Beli Sore 15:30)": {k: "Semua" for k in MASTER_FILTERS},
        "⚡ HAKA Sesi Pagi (Open=Low)": {k: "Semua" for k in MASTER_FILTERS},
        "🚀 Gorengan Aktif (High Risk)": {k: "Semua" for k in MASTER_FILTERS},
        "🎣 Pantulan Reversal Emas": {k: "Semua" for k in MASTER_FILTERS},
        "🔥 Bluechip Terakumulasi": {k: "Semua" for k in MASTER_FILTERS}
    }
    preset_bawaan["🌙 BSJP (Beli Sore 15:30)"].update({"Tekanan Bandar": "Dominan Beli (Hajar Kanan)", "Karakter Gorengan": "Solid (Jarang Dibanting)", "Status Bandar": "Akumulasi Kuat", "MA Signal": "Uptrend", "Rekomendasi": "BELI"})
    preset_bawaan["⚡ HAKA Sesi Pagi (Open=Low)"].update({"Status Open": "Open = Low (Bullish Kuat)", "Risk/Reward Ratio": "Sangat Menarik (> 1:3)"})
    preset_bawaan["🚀 Gorengan Aktif (High Risk)"].update({"Kategori": "Small Cap (Lapis 3)", "RVOL (Anomali Vol)": "Ledakan Ekstrem (> 300%)", "Posisi VWAP": "Di Atas VWAP (Kuat)"})
    preset_bawaan["🎣 Pantulan Reversal Emas"].update({"Sinyal Cuci Barang": "Jarum Bawah (Sinyal Pantulan Kuat)", "Kekuatan A/D": "Akumulasi Pro (Smart Money)"})
    preset_bawaan["🔥 Bluechip Terakumulasi"].update({"Status Bandar": "Akumulasi Kuat", "Kategori": "Big Cap (Lapis 1)", "MA Signal": "Uptrend"})

    if os.path.exists(FILE_PRESET):
        try:
            with open(FILE_PRESET, "r") as f: preset_bawaan.update(json.load(f))
        except: pass
    return preset_bawaan

daftar_preset_aktif = muat_preset()
if "preset_selector" not in st.session_state: st.session_state.preset_selector = "Matikan Preset (Manual)"

def apply_preset():
    if st.session_state.preset_selector != "Matikan Preset (Manual)":
        for k, v in daftar_preset_aktif[st.session_state.preset_selector].items():
            if k in MASTER_FILTERS: st.session_state[f"main_{k}"] = v

def manual_override(): st.session_state.preset_selector = "Matikan Preset (Manual)"

@st.cache_data(ttl=10)
def load_data_saham():
    if not os.path.exists(FILE_HASIL): return pd.DataFrame()
    df = pd.read_csv(FILE_HASIL)
    if os.path.exists(FILE_AKUISISI):
        df_akuisisi = pd.read_csv(FILE_AKUISISI)
        if "Status Akuisisi" in df.columns: df = df.drop(columns=["Status Akuisisi"])
        df = pd.merge(df, df_akuisisi, on="Ticker", how="left")
        df["Status Akuisisi"] = df["Status Akuisisi"].fillna("TIDAK ADA")
    else: df["Status Akuisisi"] = "TIDAK ADA"
    return df

df_hasil = load_data_saham()

# ==========================================
# HEADER & SIDEBAR
# ==========================================
if not df_hasil.empty and "Terakhir Update" in df_hasil.columns:
    waktu_update = str(df_hasil["Terakhir Update"].iloc[0]) + " WIB"
    st.sidebar.markdown(f"""
        <div style="border: 2px solid #06b6d4; padding: 10px; border-radius: 4px; text-align: center; margin-bottom: 15px; background-color: #0f172a; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
            <span style="font-size: 12px; color: #94a3b8; font-weight: 600;">Waktu Terakhir Update:</span><br>
            <strong style="color: #06b6d4; font-size: 14px;">{waktu_update}</strong>
        </div>
    """, unsafe_allow_html=True)

if st.sidebar.button("🔃 Sync & Muat Ulang Data Server", use_container_width=True):
    with st.spinner("Menarik data terbaru dari GitHub Server..."):
        try:
            os.system("git pull origin main") 
            time.sleep(2) 
        except Exception as e:
            st.sidebar.error(f"Gagal Sync: {e}")
    st.cache_data.clear()
    st.rerun()

st.sidebar.title("⚙️ Preset Filter Cepat")
st.sidebar.info("Gunakan **'BSJP (Beli Sore 15:30)'** untuk mencari saham yang mantap dibeli sebelum penutupan bursa!")

opsi_preset = ["Matikan Preset (Manual)"] + list(daftar_preset_aktif.keys())
idx_default = opsi_preset.index(st.session_state.preset_selector) if st.session_state.preset_selector in opsi_preset else 0
st.sidebar.selectbox("📌 Pilih Preset Aktif:", opsi_preset, index=idx_default, key="preset_selector", on_change=apply_preset)

kustom_presets = {}
if os.path.exists(FILE_PRESET):
    try:
        with open(FILE_PRESET, "r") as f: kustom_presets = json.load(f)
    except: pass

with st.sidebar.expander("🛠️ Manajemen Preset Kustom"):
    tab_edit, tab_hapus = st.tabs(["📝 Buat/Edit", "🗑️ Hapus"])
    with tab_edit:
        opsi_edit = ["-- Buat Baru --"] + list(kustom_presets.keys())
        pilih_edit = st.selectbox("Pilih Preset:", opsi_edit, key="select_edit")
        if pilih_edit == "-- Buat Baru --":
            nama_preset_baru = st.text_input("Nama Preset Baru:", placeholder="Contoh: Strategi X", key="nama_baru")
            nilai_awal = {k: info['options'][0] for k, info in MASTER_FILTERS.items()}
        else:
            nama_preset_baru = st.text_input("Simpan sebagai:", value=pilih_edit, key="nama_edit")
            nilai_awal = kustom_presets[pilih_edit]

        kustom_input = {}
        for k, info in MASTER_FILTERS.items():
            val_awal = nilai_awal.get(k, info['options'][0])
            idx_awal = info['options'].index(val_awal) if val_awal in info['options'] else 0
            kustom_input[k] = st.selectbox(f"P-{info['label']}", info['options'], index=idx_awal, key=f"edit_{k}")

        if st.button("💾 Simpan Preset"):
            if nama_preset_baru.strip():
                if pilih_edit != "-- Buat Baru --" and pilih_edit != nama_preset_baru.strip(): del kustom_presets[pilih_edit]
                kustom_presets[nama_preset_baru.strip()] = kustom_input
                with open(FILE_PRESET, "w") as f: json.dump(kustom_presets, f, indent=4)
                st.session_state.preset_selector = nama_preset_baru.strip()
                st.success("Preset berhasil disimpan!")
                st.rerun()
    with tab_hapus:
        if kustom_presets:
            pilih_hapus = st.selectbox("Pilih Preset untuk Dihapus:", list(kustom_presets.keys()))
            if st.button("🗑️ Hapus Preset"):
                del kustom_presets[pilih_hapus]
                with open(FILE_PRESET, "w") as f: json.dump(kustom_presets, f, indent=4)
                if st.session_state.preset_selector == pilih_hapus: st.session_state.preset_selector = "Matikan Preset (Manual)"
                st.success("Preset dihapus!")
                st.rerun()
        else: st.info("Belum ada preset kustom.")

st.title("⚡ AlgoTrade Screener - IHSG Ultimate")
st.markdown("Detektor Jejak Bandar, Anomali Volume, & Strategi BSJP.")
st.markdown("---")

# ==========================================
# FUNGSI PEWARNAAN & FORMATTER TABEL
# ==========================================
def format_skor(s): return "⭐" * int(s) if pd.notna(s) and int(s) > 0 else "-"
def format_pct(v): return f"{'▲ ' if v > 0 else '▼ '}{v:+.2f}%" if pd.notna(v) and v != 0 else "0.00%"
def format_mom(v): return "▲ Positif" if v == "Positif" else ("▼ Negatif" if v == "Negatif" else v)
def format_desimal(v): return f"{v:.2f}" if pd.notna(v) and v != 0 else "-"
def format_angka(v): return f"{int(v):,}".replace(",", ".") if pd.notna(v) else "-"

def format_singkat_vol(v):
    if pd.isna(v): return "-"
    if v >= 1_000_000: return f"{v/1_000_000:.2f} M Lot"
    elif v >= 1_000: return f"{v/1_000:.2f} K Lot"
    return f"{v:.0f} Lot"

def format_singkat_rp(v):
    if pd.isna(v): return "-"
    if v >= 1_000_000_000_000: return f"Rp {v/1_000_000_000_000:.2f} T"
    elif v >= 1_000_000_000: return f"Rp {v/1_000_000_000:.2f} M"
    elif v >= 1_000_000: return f"Rp {v/1_000_000:.2f} Jt"
    return f"Rp {v:,.0f}".replace(",", ".")

def warna_tabel(val):
    if isinstance(val, (int, float)): 
        return 'color: #22c55e; font-weight: 600;' if val > 0 else ('color: #ef4444; font-weight: 600;' if val < 0 else '')
    elif isinstance(val, str):
        if any(x in val for x in ["Positif", "Uptrend", "BELI", "Breakout Upper", "Bottom Rebound", "DALAM AKUISISI", "Rendah", "▲", "Golden Cross", "Bullish", "Tembus MA20", "Akumulasi", "Big Cap", "Gap Up", "Dominan Beli", "Undervalued", "Marubozu", "Dekat Support", "Hammer", "Di Atas VWAP", "Sultan", "Ledakan Ekstrem", "Solid", "Mark-Up", "Jarum Bawah", "Naik", "Open = Low", "Sangat Menarik", "Perfect Uptrend", "Awal Reversal", "Acc"]): return 'color: #22c55e; font-weight: 600;'
        elif any(x in val for x in ["Negatif", "Downtrend", "WAIT & SEE", "Tinggi", "▼", "Death Cross", "Bearish", "Distribusi", "Small Cap", "Gap Down", "Dominan Jual", "Overvalued", "Rawan Pucuk", "Di Bawah VWAP", "Gorengan Sepi", "Sepi", "Tiang Jemuran", "Mark-Down", "Turun", "Open = High", "Tidak Ideal", "Strong Downtrend", "Dist", "Token Mati", "Gagal", "Timeout"]): return 'color: #ef4444; font-weight: 600;'
        elif val == "> 1 Miliar": return 'color: #3b82f6; font-weight: 600;'
        elif any(x in val for x in ["Squeeze", "RENCANA AKUISISI", "Sedang", "Mid Cap", "Seimbang", "Fair Value", "Area Tengah", "Doji", "Ritel Aktif", "Anomali", "Accumulation", "Sideways", "Ideal", "Menengah", "Konsolidasi / Transisi", "Neutral"]): return 'color: #eab308; font-weight: 600;'
        elif "⭐" in val: return 'color: #22c55e;' if len(val) >= 6 else 'color: #ef4444;'
    return ''

def render_strategy_table(df_subset, file_name):
    if not df_subset.empty:
        sort_cols = [c for c in ['Total Score', 'Volume'] if c in df_subset.columns]
        if sort_cols: df_subset = df_subset.sort_values(by=sort_cols, ascending=[False, False]).reset_index(drop=True)
        if "Total Score" in df_subset.columns: df_subset["Total Score"] = df_subset["Total Score"].apply(format_skor)

        kolom_utama = ["Ticker", "Harga (Rp)", "Change (%)", "Volume", "Total Score", "Auto Trading Plan"]
        kolom_tambahan = ["Broksum", "Trend MA (5,20,50)", "RVOL (Anomali Vol)", "Tekanan Bandar", "Status Bandar", "Kekuatan A/D", "Sinyal Cuci Barang", "Status BB", "MA Signal"]
        kolom_tampil = [c for c in kolom_utama + kolom_tambahan if c in df_subset.columns]

        styler = df_subset[kolom_tampil].style.format({"Harga (Rp)": format_angka, "Volume": format_angka, "Change (%)": format_pct})
        subset_warna = [c for c in kolom_tampil if c not in ["Ticker", "Auto Trading Plan"]]
        tabel_jadi = styler.map(warna_tabel, subset=subset_warna) if hasattr(styler, 'map') else styler.applymap(warna_tabel, subset=subset_warna)

        st.dataframe(tabel_jadi, use_container_width=True, hide_index=True)

        c1, c2 = st.columns([1, 1])
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer: tabel_jadi.to_excel(writer, index=False, sheet_name='Screener')
        c1.download_button(label=f"📥 Download {file_name} (Excel)", data=buffer.getvalue(), file_name=f"{file_name}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_{file_name}")
        with c2:
            st.markdown("**📋 Salin Daftar Saham:**")
            st.code("\n".join(df_subset["Ticker"].tolist()), language="text")
            st.caption("Klik icon 'Copy' untuk paste ke Tab AI.")
    else: st.info("🔍 Belum ada pergerakan saham yang memenuhi kriteria strategi ini pada sesi saat ini.")

# ==============================================================================
# RENDER 4 TABS UTAMA (VERSI BERSIH 100%)
# ==============================================================================
if not df_hasil.empty:
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Market Overview", 
        "📌 Screener Utama", 
        "🤖 Asisten AI Spesial", 
        "💼 Portofolio Bot"
    ])
    
    # ==========================================================================
    # [TAB 1] MARKET OVERVIEW 
    # ==========================================================================
    with tab1:
        st.markdown("### 📊 Ringkasan Pasar IHSG")
        
        total_saham = len(df_hasil)
        saham_naik = len(df_hasil[df_hasil['Change (%)'] > 0]) if 'Change (%)' in df_hasil.columns else 0
        saham_turun = len(df_hasil[df_hasil['Change (%)'] < 0]) if 'Change (%)' in df_hasil.columns else 0
        saham_stagnan = total_saham - saham_naik - saham_turun
        
        if 'Turnover' not in df_hasil.columns:
            if 'Volume' in df_hasil.columns and 'Harga (Rp)' in df_hasil.columns:
                df_hasil['Turnover'] = df_hasil['Harga (Rp)'] * df_hasil['Volume'] * 100
            else:
                df_hasil['Turnover'] = 0

        if saham_naik > (saham_turun * 1.5): sentimen_teks, warna_sentimen = "🔥 Sangat Bullish", "#4ade80"
        elif saham_turun > (saham_naik * 1.5): sentimen_teks, warna_sentimen = "🩸 Sangat Bearish", "#f87171"
        else: sentimen_teks, warna_sentimen = "⚖️ Konsolidasi (Ragu)", "#facc15"
                
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.markdown(f"<div class='metric-container'><h3>🔍 Total Saham</h3><h2>{total_saham}</h2></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-container'><h3>🟢 Menguat</h3><h2 style='color: #4ade80;'>{saham_naik}</h2></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-container'><h3>🔴 Melemah</h3><h2 style='color: #f87171;'>{saham_turun}</h2></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='metric-container'><h3>⚪ Stagnan</h3><h2 style='color: #94a3b8;'>{saham_stagnan}</h2></div>", unsafe_allow_html=True)
        m5.markdown(f"<div class='metric-container'><h3>🧭 Sentimen Pasar</h3><h3 style='color: {warna_sentimen}; margin-top:5px;'>{sentimen_teks}</h3></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)

        def render_top_table(df_top, cols, format_dict):
            styler = df_top[cols].style.format(format_dict)
            tabel_warna = styler.map(warna_tabel, subset=['Change (%)']) if hasattr(styler, 'map') else styler.applymap(warna_tabel, subset=['Change (%)'])
            st.dataframe(tabel_warna, use_container_width=True, hide_index=True)

        with c1:
            st.markdown("#### 🔥 Top Gainers")
            if 'Change (%)' in df_hasil.columns:
                df_gainer = df_hasil.nlargest(10, 'Change (%)')
                render_top_table(df_gainer, ['Ticker', 'Harga (Rp)', 'Change (%)'], {'Harga (Rp)': format_angka, 'Change (%)': format_pct})
            
        with c2:
            st.markdown("#### 🩸 Top Losers")
            if 'Change (%)' in df_hasil.columns:
                df_loser = df_hasil.nsmallest(10, 'Change (%)')
                render_top_table(df_loser, ['Ticker', 'Harga (Rp)', 'Change (%)'], {'Harga (Rp)': format_angka, 'Change (%)': format_pct})
            
        st.markdown("<br>", unsafe_allow_html=True)
            
        with c3:
            st.markdown("#### 🌊 Top Volume")
            if 'Volume' in df_hasil.columns:
                df_vol = df_hasil.nlargest(10, 'Volume')
                render_top_table(df_vol, ['Ticker', 'Harga (Rp)', 'Volume', 'Change (%)'], {'Harga (Rp)': format_angka, 'Volume': format_singkat_vol, 'Change (%)': format_pct})
            
        with c4:
            st.markdown("#### 💰 Top Value (Turnover)")
            if 'Turnover' in df_hasil.columns:
                df_val = df_hasil.nlargest(10, 'Turnover')
                render_top_table(df_val, ['Ticker', 'Harga (Rp)', 'Turnover', 'Change (%)'], {'Harga (Rp)': format_angka, 'Turnover': format_singkat_rp, 'Change (%)': format_pct})

    # ==========================================================================
    # [TAB 2] SCREENER UTAMA
    # ==========================================================================
    with tab2:
        def reset_semua_filter():
            for k, info in MASTER_FILTERS.items():
                if f"main_{k}" in st.session_state:
                    st.session_state[f"main_{k}"] = info["options"][0]
            st.session_state["pencarian_ticker"] = ""
            st.session_state["pencarian_broker"] = ""
            st.session_state["batas_harga_min"] = 0
            st.session_state["batas_harga_max"] = 0

        with st.expander("🛠️ Buka Panel Filter Lengkap", expanded=False):
            st.button("🔄 Reset Semua Filter ke Bawaan (Semua)", on_click=reset_semua_filter, use_container_width=True)
            st.markdown("---")
            
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            filter_terpilih = {}
            for idx, (db_key, info) in enumerate(MASTER_FILTERS.items()):
                target_col = col_f1 if idx % 4 == 0 else (col_f2 if idx % 4 == 1 else (col_f3 if idx % 4 == 2 else col_f4))
                with target_col:
                    val_sekarang = st.session_state.get(f"main_{db_key}", info["options"][0])
                    idx_opsi = info["options"].index(val_sekarang) if val_sekarang in info["options"] else 0
                    filter_terpilih[db_key] = st.selectbox(info["label"], info["options"], index=idx_opsi, key=f"main_{db_key}", on_change=manual_override)

        col_search, col_broker, col_min, col_max = st.columns([1.5, 1.5, 1, 1])
        with col_search: 
            search_ticker = st.text_input("🔍 Cari Kode Saham", "", placeholder="Contoh: BBCA", key="pencarian_ticker")
        with col_broker: 
            search_broker = st.text_input("👤 Cari Kode Broker", "", placeholder="Contoh: MG / YP", key="pencarian_broker")
        with col_min: 
            min_price = st.number_input("⬇️ Harga Minimal (Rp)", min_value=0, value=0, step=10, key="batas_harga_min")
        with col_max: 
            max_price = st.number_input("⬆️ Harga Maksimal (Rp)", min_value=0, value=0, step=10, key="batas_harga_max")

        df_filtered = df_hasil.copy()
        
        if search_ticker: 
            df_filtered = df_filtered[df_filtered["Ticker"].astype(str).str.contains(search_ticker.upper(), na=False)]
            
        if search_broker and "Broksum" in df_filtered.columns: 
            df_filtered = df_filtered[df_filtered["Broksum"].astype(str).str.contains(search_broker.upper(), na=False)]
            
        if min_price > 0:
            df_filtered = df_filtered[df_filtered["Harga (Rp)"] >= min_price]
        if max_price > 0:
            df_filtered = df_filtered[df_filtered["Harga (Rp)"] <= max_price]
        
        for db_key, nilai in filter_terpilih.items():
            if nilai != "Semua":
                if db_key == "RSI (14D)":
                    if "RSI (14D)" in df_filtered.columns: df_filtered = df_filtered[df_filtered["RSI (14D)"] > 50] if "Bullish" in nilai else df_filtered[df_filtered["RSI (14D)"] <= 50]
                elif db_key == "Total Score":
                    if "Total Score" in df_filtered.columns: df_filtered = df_filtered[df_filtered["Total Score"] == int(nilai)]
                elif db_key == "Kategori" and nilai == "Mid Cap (Lapis 2) + Small Cap (Lapis 3)":
                    if "Kategori" in df_filtered.columns:
                        df_filtered = df_filtered[df_filtered["Kategori"].isin(["Mid Cap (Lapis 2)", "Small Cap (Lapis 3)"])]
                elif db_key in df_filtered.columns: 
                    df_filtered = df_filtered[df_filtered[db_key] == nilai]

        if not df_filtered.empty:
            st.caption(f"Menampilkan **{len(df_filtered)}** saham yang lolos filter dari total **{len(df_hasil)}** saham.")
            st.markdown("<div class='view-mode-container'>", unsafe_allow_html=True)
            mode_tampilan = st.radio("👁️ Pilih Mode Tampilan Tabel:", ["🚀 Ringkasan Cepat", "👤 Bandarmologi & Wyckoff", "📈 Teknikal & Support", "💎 Fundamental & Likuiditas", "🌌 Tampilkan Semua Kolom"], horizontal=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            cp1, cp2, cp3 = st.columns([1, 1, 2])
            with cp1: per_hal = st.selectbox("Tampilkan baris:", [20, 50, 100])
            tot_hal = int(np.ceil(len(df_filtered) / per_hal))
            with cp2: hal_aktif = st.selectbox("Halaman:", range(1, tot_hal + 1)) if tot_hal > 0 else 1
                    
            idx_awal = (hal_aktif - 1) * per_hal
            df_tampil = df_filtered.iloc[idx_awal : idx_awal + per_hal].copy()
            if "Total Score" in df_tampil.columns: df_tampil["Total Score"] = df_tampil["Total Score"].apply(format_skor)
            
            kolom_ringkasan = ["Ticker", "Harga (Rp)", "Change (%)", "Broksum", "Rekomendasi", "Status Open", "Posisi VWAP", "Total Score", "Volume", "Auto Trading Plan"]
            kolom_bandar = ["Ticker", "Harga (Rp)", "Change (%)", "Broksum", "Fase Siklus Bandar", "Kekuatan A/D", "Status Bandar", "RVOL (Anomali Vol)", "Karakter Gorengan", "Tekanan Bandar", "OBV Trend", "Kondisi Supply", "Prediksi Machine Learning"]
            kolom_teknikal = ["Ticker", "Harga (Rp)", "Change (%)", "Auto Trading Plan", "Risk/Reward Ratio", "Status Fibonacci", "Sinyal Cuci Barang", "Posisi Entry", "Pola Candle", "Trend MA (5,20,50)", "MA Signal", "Status BB", "RSI (14D)", "MACD", "Status Stochastic"]
            kolom_fundamental = ["Ticker", "Harga (Rp)", "Kategori", "Valuasi", "PER (x)", "PBV (x)", "Kelas Transaksi", "Likuiditas", "Status Sentimen"]
            kolom_semua = ["Ticker", "Broksum", "Status Open", "Risk/Reward Ratio", "Status Fibonacci", "Auto Trading Plan", "Streak Harian", "Sinyal Cuci Barang", "Kategori", "Kelas Transaksi", "Valuasi", "Harga (Rp)", "PER (x)", "PBV (x)", "Harga MA20", "Posisi VWAP", "Support", "Resistance", "Posisi Entry", "Pola Candle", "Change (%)", "Volume", "RVOL (Anomali Vol)", "Vol Breakout", "Status Gap", "Fase Siklus Bandar", "Karakter Gorengan", "Tekanan Bandar", "Kekuatan A/D", "Status Bandar", "OBV Trend", "RSI (14D)", "Momentum", "Trend MA (5,20,50)", "MA Signal", "MA Cross", "MACD", "Status Stochastic", "Status BB", "Risiko", "Likuiditas", "Status Sentimen", "Prediksi Machine Learning", "Kondisi Supply", "Total Score", "Rekomendasi"]
            
            if "Ringkasan" in mode_tampilan: kolom_pilih = kolom_ringkasan
            elif "Bandarmologi" in mode_tampilan: kolom_pilih = kolom_bandar
            elif "Teknikal" in mode_tampilan: kolom_pilih = kolom_teknikal
            elif "Fundamental" in mode_tampilan: kolom_pilih = kolom_fundamental
            else: kolom_pilih = kolom_semua

            kolom_ada = [c for c in kolom_pilih if c in df_tampil.columns]
            format_dict = {}
            for col in ["Harga (Rp)", "Harga MA20", "Support", "Resistance", "Volume"]:
                if col in df_tampil.columns: format_dict[col] = format_angka
            if "Change (%)" in df_tampil.columns: format_dict["Change (%)"] = format_pct
            if "Momentum" in df_tampil.columns: format_dict["Momentum"] = format_mom
            for col in ["PER (x)", "PBV (x)"]:
                if col in df_tampil.columns: format_dict[col] = format_desimal
            if "RSI (14D)" in df_tampil.columns: format_dict["RSI (14D)"] = "{:.0f}"

            styler_obj = df_tampil[kolom_ada].style.format(format_dict)
            subset_warna = [c for c in kolom_ada if c not in ["Ticker", "Auto Trading Plan"]]
            tabel_akhir = styler_obj.map(warna_tabel, subset=subset_warna) if hasattr(styler_obj, 'map') else styler_obj.applymap(warna_tabel, subset=subset_warna)
            st.dataframe(tabel_akhir, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            col_dl, col_wl = st.columns([1, 1])
            with col_dl:
                csv_filter = df_filtered[kolom_ada].to_csv(index=False).encode('utf-8')
                st.download_button(label=f"📥 Download Data Tabel CSV", data=csv_filter, file_name=f"Screener_View_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv", key="dl_tab2")
            with col_wl:
                st.markdown("**📋 Salin Daftar Saham:**")
                st.code("\n".join(df_filtered["Ticker"].tolist()), language="text")
                st.caption("Klik icon 'Copy' untuk paste massal ke Tab AI.")
        else: st.warning("Tidak ada data sesuai filter.")

    # ==========================================================================
    # [TAB 3] ASISTEN AI SPESIAL (TURNAMEN)
    # ==========================================================================
    with tab3:
        st.markdown("## 🦅 Radar BSJP & Laboratorium Forensik AI")
        st.markdown("<div class='bandar-box-green'><b>💡 INFO:</b> Gunakan kotak pilihan (Dropdown) di bawah ini untuk beralih antar strategi atau mode AI agar tampilan lebih rapi.</div>", unsafe_allow_html=True)
        
        if 'Tekanan Bandar' not in df_hasil.columns:
            st.warning("⏳ **Fitur Radar belum menerima data terbaru.** Harap jalankan 'update_data.py'.")
        else:
            # --- SYARAT MUTLAK: WAJIB SQUEEZE ---
            cond_squeeze = (df_hasil.get('Status BB', '') == 'Squeeze')

            # RUMUS 1 : Squeeze + Supply Kering
            cond_v1 = (cond_squeeze & df_hasil.get('Kondisi Supply', '').astype(str).str.contains('Supply Kering', na=False))
            df_v1 = df_hasil[cond_v1].copy() if not df_hasil.empty else pd.DataFrame()

            # RUMUS 2 : Squeeze + Anomali Bandar
            cond_v2 = (cond_squeeze & df_hasil.get('Prediksi Machine Learning', '').astype(str).str.contains('ANOMALI BANDAR', na=False))
            df_v2 = df_hasil[cond_v2].copy() if not df_hasil.empty else pd.DataFrame()

            # RUMUS 3 : Squeeze + Golden Rebound Fibo 61.8%
            cond_v3 = (cond_squeeze & df_hasil.get('Status Fibonacci', '').astype(str).str.contains('61.8%', na=False))
            df_v3 = df_hasil[cond_v3].copy() if not df_hasil.empty else pd.DataFrame()

            # RUMUS 4 : Squeeze + Golden Cross
            cond_v4 = (cond_squeeze & (df_hasil.get('MA Cross', '') == 'Golden Cross'))
            df_v4 = df_hasil[cond_v4].copy() if not df_hasil.empty else pd.DataFrame()

            # RUMUS 5 : Squeeze + Hammer
            cond_v5 = (cond_squeeze & (df_hasil.get('Pola Candle', '') == 'Hammer (Potensi Reversal)'))
            df_v5 = df_hasil[cond_v5].copy() if not df_hasil.empty else pd.DataFrame()

            # RUMUS 6 : Squeeze + Akumulasi Kuat
            cond_v6 = (cond_squeeze & (df_hasil.get('Status Bandar', '') == 'Akumulasi Kuat'))
            df_v6 = df_hasil[cond_v6].copy() if not df_hasil.empty else pd.DataFrame()

            # RUMUS 7 : Squeeze + Solid (Jarang Dibanting)
            cond_v7 = (cond_squeeze & (df_hasil.get('Karakter Gorengan', '') == 'Solid (Jarang Dibanting)'))
            df_v7 = df_hasil[cond_v7].copy() if not df_hasil.empty else pd.DataFrame()

            # RUMUS 8 : Squeeze + Accumulation (Wyckoff)
            cond_v8 = (cond_squeeze & (df_hasil.get('Fase Siklus Bandar', '') == 'Accumulation (Kumpul Barang)'))
            df_v8 = df_hasil[cond_v8].copy() if not df_hasil.empty else pd.DataFrame()

            # RUMUS 9 : Squeeze + Risk/Reward Menarik
            cond_v9 = (cond_squeeze & (df_hasil.get('Risk/Reward Ratio', '') == 'Sangat Menarik (> 1:3)'))
            df_v9 = df_hasil[cond_v9].copy() if not df_hasil.empty else pd.DataFrame()

            tab_screener, tab_ai = st.tabs(["🎯 Screener Spesial", "🧠 Asisten AI"])
            
            with tab_screener:
                pilihan_v = st.selectbox(
                    "Pilih Rumus Screener (Wajib Squeeze):",
                    [
                        "RUMUS 1 : Squeeze + Supply Kering (Siap Pump) 🏜️", 
                        "RUMUS 2 : Squeeze + 🔥 ANOMALI BANDAR (Siap Ledakan)", 
                        "RUMUS 3 : Squeeze + Golden Rebound Fibo 61.8% (Golden Ratio) 🎯", 
                        "RUMUS 4 : Squeeze + Golden Cross", 
                        "RUMUS 5 : Squeeze + Hammer (Potensi Reversal)",
                        "RUMUS 6 : Squeeze + 🕵️ Status Bandar ( Akumulasi Kuat )",
                        "RUMUS 7 : Squeeze + Solid (Jarang Dibanting)",
                        "RUMUS 8 : Squeeze + 🔄 Siklus Wyckoff ( Accumulation (Kumpul Barang) )",
                        "RUMUS 9 : Squeeze + Sangat Menarik (> 1:3)"
                    ]
                )
                
                st.markdown("---")
                if "RUMUS 1" in pilihan_v:
                    render_strategy_table(df_v1, "Screener_Rumus_1")
                elif "RUMUS 2" in pilihan_v:
                    render_strategy_table(df_v2, "Screener_Rumus_2")
                elif "RUMUS 3" in pilihan_v:
                    render_strategy_table(df_v3, "Screener_Rumus_3")
                elif "RUMUS 4" in pilihan_v:
                    render_strategy_table(df_v4, "Screener_Rumus_4")
                elif "RUMUS 5" in pilihan_v:
                    render_strategy_table(df_v5, "Screener_Rumus_5")
                elif "RUMUS 6" in pilihan_v:
                    render_strategy_table(df_v6, "Screener_Rumus_6")
                elif "RUMUS 7" in pilihan_v:
                    render_strategy_table(df_v7, "Screener_Rumus_7")
                elif "RUMUS 8" in pilihan_v:
                    render_strategy_table(df_v8, "Screener_Rumus_8")
                elif "RUMUS 9" in pilihan_v:
                    render_strategy_table(df_v9, "Screener_Rumus_9")

            with tab_ai:
                pilihan_ai = st.selectbox(
                    "Pilih Mode Analisis AI:",
                    [
                        "🤖 AI Bandar (Persiapan BSJP)", 
                        "🔎 Forensik Bandar (Bongkar DNA ARA)", 
                        "🎯 Pemburu ARA (Spesialis DNA Ledakan)"
                    ]
                )
                st.markdown("---")
                
                if "AI Bandar" in pilihan_ai:
                    st.subheader("🤖 AI Bandar (Persiapan BSJP Besok)")
                    
                    # MEMBAGI AI BANDAR MENJADI 2 TAB AGAR RAPI
                    tab_otomatis, tab_manual = st.tabs(["🛸 Auto-Pilot 9 Rumus (Spreadsheet)", "✍️ Mode Manual (Paste Saham)"])
                    
                    with tab_otomatis:
                        st.markdown("Sistem akan menyeleksi 15 saham terbaik per rumus secara global, lalu AI akan memilih Top 5 untuk dicetak ke tabel Spreadsheet.")
                        GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
                        
                        # Saya tambahkan key="autopilot_utama" agar tidak bentrok dengan tombol duplikat
                        if st.button("🛸 Jalankan Auto-Pilot Ultimate", type="primary", key="autopilot_utama"):
                            if not GEMINI_API_KEY:
                                st.error("❌ Kunci API GEMINI belum dipasang!")
                            else:
                                daftar_rumus = {
                                    1: df_v1, 2: df_v2, 3: df_v3, 
                                    4: df_v4, 5: df_v5, 6: df_v6, 
                                    7: df_v7, 8: df_v8, 9: df_v9
                                }
                                
                                progress_bar = st.progress(0)
                                status_teks = st.empty()
                                
                                # Siapkan keranjang untuk membuat tabel spreadsheet di akhir
                                keranjang_spreadsheet = {f"RUMUS {i}": [] for i in range(1, 10)}
                                
                                for i in range(1, 10):
                                    df_target = daftar_rumus[i]
                                    progress_bar.progress(i / 9.0)
                                    
                                    if len(df_target) == 0:
                                        status_teks.warning(f"⏭️ Rumus {i} kosong. Dilewati.")
                                        time.sleep(1)
                                        continue
                                        
                                    status_teks.info(f"🔄 **Algojo Python bekerja pada Rumus {i}**... (Mengekstrak data global)")
                                    
                                    saham_valid = df_target['Ticker'].tolist()
                                    df_seleksi = df_hasil[df_hasil['Ticker'].isin(saham_valid)].copy()
                                    
                                    df_seleksi['Score_Num'] = pd.to_numeric(df_seleksi['Total Score'], errors='coerce').fillna(0)
                                    
                                    # TAHAP 1: KLASEMEN GLOBAL (Pilih Top 15 berdasarkan Data Keras)
                                    df_sorted = df_seleksi.sort_values(by=['Score_Num', 'Volume', 'Change (%)'], ascending=[False, False, False])
                                    top_15 = df_sorted.head(15)
                                    
                                    data_kirim_ai = {}
                                    for _, row in top_15.iterrows():
                                        data_kirim_ai[row['Ticker']] = {
                                            'Harga': row.get('Harga (Rp)', 0),
                                            'Volume': row.get('Volume', 0),
                                            'Score': row.get('Score_Num', 0),
                                            'Change_Pct': row.get('Change (%)', 0),
                                            'Tekanan_Bandar': row.get('Tekanan Bandar', 'Normal'),
                                            'Broksum': row.get('Broksum', 'Normal')
                                        }
                                        
                                    status_teks.warning(f"🧠 Rumus {i} - Sidang Grand Final AI... (Menyaring 5 Jawara dari Top 15)")
                                    
                                    # TAHAP 2: HAKIM AI (Pilih Top 5 Mutlak)
                                    try:
                                        hasil_mentah = ai_hakim_klasemen(data_kirim_ai, GEMINI_API_KEY)
                                        
                                        # Jika AI menolak menjawab / Kena filter keamanan
                                        if "Error_AI:" in hasil_mentah:
                                            st.error(f"❌ API Error Rumus {i} (Terblokir Sistem Google): {hasil_mentah}")
                                            keranjang_spreadsheet[f"RUMUS {i}"] = ["", "", "", "", ""]
                                            continue
                                            
                                        # Teknik Ekstraksi JSON Anti-Gagal (String Slicing)
                                        awal = hasil_mentah.find('[')
                                        akhir = hasil_mentah.rfind(']')
                                        
                                        if awal != -1 and akhir != -1 and akhir > awal:
                                            teks_json = hasil_mentah[awal:akhir+1]
                                            import json
                                            hasil_json = json.loads(teks_json)
                                            df_tampil = pd.DataFrame(hasil_json)
                                            
                                            # Ambil ticker untuk masuk ke tabel spreadsheet
                                            if 'Ticker' in df_tampil.columns:
                                                jawara_tickers = df_tampil['Ticker'].tolist()
                                            else:
                                                jawara_tickers = []
                                                
                                            # Batasi maksimal 5, jika kurang tambahkan string kosong "" agar tabel rata
                                            jawara_tickers = (jawara_tickers + ["", "", "", "", ""])[:5] 
                                            keranjang_spreadsheet[f"RUMUS {i}"] = jawara_tickers
                                            
                                            # Simpan sinyal untuk dieksekusi bot malam ini
                                            if 'Target_TP' in df_tampil.columns and 'Target_CL' in df_tampil.columns:
                                                df_sinyal = df_tampil[['Ticker', 'Target_TP', 'Target_CL']]
                                                df_sinyal.to_csv(f"Database/sinyal_ai_rumus_{i}.csv", index=False)
                                                
                                        else:
                                            # Tampilkan balasan asli agar kita tahu kenapa AI ngeyel
                                            st.error(f"❌ Rumus {i} Gagal (AI tidak membalas format JSON):\n{hasil_mentah}")
                                            keranjang_spreadsheet[f"RUMUS {i}"] = ["", "", "", "", ""]
                                            
                                    except Exception as e:
                                        st.error(f"❌ Error Parsing Rumus {i}: {e}")
                                        keranjang_spreadsheet[f"RUMUS {i}"] = ["", "", "", "", ""]
                                    
                                    time.sleep(2.5) # Nafas panjang untuk API Google
                                
                                status_teks.success("🎉 MISSION ACCOMPLISHED! SELURUH RUMUS BERHASIL DISARING!")
                                st.balloons()
                                
                                # TAHAP 3: CETAK TABEL SPREADSHEET (Siap Copy-Paste)
                                st.markdown("### 📋 Tabel Master Portofolio (Siap Salin)")
                                df_spreadsheet = pd.DataFrame(keranjang_spreadsheet)
                                
                                st.data_editor(df_spreadsheet, use_container_width=True, hide_index=True)

                    with tab_manual:
                        st.markdown("Paste saham yang MASIH MERAH / SIDEWAYS. AI akan mencari siapa yang siap terbang besok.")
                        input_saham_massal = st.text_area("📋 Paste Daftar Saham (Pisahkan dengan Enter/Spasi):", placeholder="Contoh:\nDMAS\nINDF", height=200, key="input_ai_bandar")
                        
                        if st.button("🔮 Mulai Eksekusi AI Bandar"):
                            saham_bersih = [s.strip().upper() for s in re.split(r'[,\s\n]+', input_saham_massal) if s.strip()]
                            saham_unik = list(dict.fromkeys(saham_bersih))
                            saham_valid = [s for s in saham_unik if s in df_hasil['Ticker'].values]
                            
                            df_valid = df_hasil[df_hasil['Ticker'].isin(saham_valid)].copy()
                            if 'Change (%)' in df_valid.columns:
                                df_valid = df_valid[df_valid['Change (%)'] <= 5.0]
                                saham_valid = df_valid['Ticker'].tolist()

                            if not saham_valid:
                                st.error("❌ Saham yang Anda masukkan sudah terbang terlalu tinggi (>5%). Gunakan AI Bandar untuk mencari saham yang masih di bawah!")
                            else:
                                if len(saham_valid) > 19:
                                    st.info("🤖 Menyaring 19 saham terbaik untuk mencegah limit AI...")
                                    df_valid = df_valid.sort_values(by=['Total Score', 'Volume'], ascending=[False, False])
                                    saham_valid = df_valid['Ticker'].head(19).tolist()
                                
                                with st.spinner(f"Menganalisa {len(saham_valid)} saham untuk BSJP besok..."):
                                    data_kompilasi = {}
                                    for ticker in saham_valid:
                                        data_saham = df_hasil[df_hasil['Ticker'] == ticker].iloc[0]
                                        teks_ringkasan = get_historical_summary(ticker)
                                        data_kompilasi[ticker] = {
                                            'harga': data_saham.get('Harga (Rp)', 0),
                                            'change': data_saham.get('Change (%)', 0), 
                                            'broksum': data_saham.get('Broksum', 'Tidak Ada'),
                                            'status': data_saham.get('Fase Siklus Bandar', 'Normal'),
                                            'skor': data_saham.get('Total Score', 0),
                                            'histori': teks_ringkasan if teks_ringkasan else "Arsip belum tersedia."
                                        }
                                    hasil_ai = analisa_bandar_ai_multisaham(data_kompilasi, 'pilihan_ai')
                                    st.info(hasil_ai)

                elif "Forensik Bandar" in pilihan_ai:
                    st.subheader("📡 Radar Pencari Model Gemini Aktif (Live Server)")
                    st.markdown("Mesin ini akan bertanya langsung ke server Google AI Studio untuk mencari **semua nama model Gemini yang valid dan mendukung fitur Generate Content** untuk API Key Anda, lalu mengujinya satu per satu.")
                    
                    input_tester = st.text_area("📋 Paste Daftar Saham Uji Coba (Minimal 3 Saham):", placeholder="Contoh:\nVISI\nBBHI\nPANI", height=150, key="input_tester_gemini")
                    
                    if st.button("🚀 Tarik Daftar Server Google & Mulai Uji Coba"):
                        GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
                        if not GEMINI_API_KEY:
                            st.error("❌ Kunci API GEMINI belum dipasang di Secrets!")
                        else:
                            saham_bersih = [s.strip().upper() for s in re.split(r'[,\s\n]+', input_tester) if s.strip()]
                            saham_unik = list(dict.fromkeys(saham_bersih))
                            saham_valid = [s for s in saham_unik if s in df_hasil['Ticker'].values]
                            
                            if len(saham_valid) < 2:
                                st.error("❌ Masukkan minimal 2 kode saham yang valid di database hari ini.")
                            else:
                                st.info("🔄 Langkah 1: Meminta katalog model langsung dari server Google AI...")
                                
                                daftar_model_aktif = []
                                try:
                                    genai.configure(api_key=GEMINI_API_KEY)
                                    for m in genai.list_models():
                                        if 'generateContent' in m.supported_generation_methods:
                                            daftar_model_aktif.append(m.name)
                                except Exception as e:
                                    st.error(f"Gagal menarik data dari server Google. Error: {e}")
                                
                                if not daftar_model_aktif:
                                    st.warning("⚠️ Tidak ada model yang ditemukan untuk API Key ini.")
                                else:
                                    st.success(f"✅ Ditemukan {len(daftar_model_aktif)} model Gemini yang online untuk Anda! Memulai pengujian...")
                                    
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    
                                    payload_text = ""
                                    for ticker in saham_valid:
                                        data_saham = df_hasil[df_hasil['Ticker'] == ticker].iloc[0]
                                        payload_text += f"\n- {ticker}: Harga {data_saham.get('Harga (Rp)', 0)}, Vol {data_saham.get('Volume', 0)}"

                                    prompt_test = f"""
                                    CRITICAL INSTRUCTION: You are an automated data filter. 
                                    Read this data:
                                    {payload_text}
                                    
                                    MISSION: Pick EXACTLY 1 best ticker based on volume.
                                    STRICT RULE: Output ONLY the 4-letter ticker code (e.g., BBCA). DO NOT add any other words, punctuation, explanations, or formatting.
                                    """
                                    
                                    hasil_rekap = []
                                    
                                    for i, nama_model in enumerate(daftar_model_aktif):
                                        model_id_bersih = nama_model.replace("models/", "")
                                        status_text.text(f"⏳ Sedang menguji: {model_id_bersih} ({i+1}/{len(daftar_model_aktif)})")
                                        
                                        try:
                                            model_uji = genai.GenerativeModel(model_id_bersih)
                                            response = model_uji.generate_content(prompt_test)
                                            raw_content = response.text or ""
                                            bersih = raw_content.replace('`', '').replace('.', '').replace('\n', '').strip().upper()
                                            
                                            if bersih in saham_valid:
                                                status = "✅ Lulus & Patuh (Sangat Cocok!)"
                                            else:
                                                status = f"⚠️ Aktif tapi Bawel (Jawab: {raw_content.strip()[:25]}...)"
                                                
                                            hasil_rekap.append({"Nama Model": model_id_bersih, "Status": status})
                                            
                                        except Exception as e:
                                            pesan_error = str(e)
                                            hasil_rekap.append({"Nama Model": model_id_bersih, "Status": f"❌ Gagal: {pesan_error[:30]}..."})
                                        
                                        progress_bar.progress((i + 1) / len(daftar_model_aktif))
                                        time.sleep(2)
                                    
                                    status_text.success("🎉 Pengecekan Server Google Selesai!")
                                    
                                    df_rekap = pd.DataFrame(hasil_rekap)
                                    st.markdown("### 🏆 Hasil Uji Coba Model Gemini (Live Server)")
                                    st.dataframe(df_rekap, use_container_width=True)
                                    
                                    st.info("💡 **TUGAS ANDA:** Salin nama model yang berstatus '✅ Lulus & Patuh', dan kita gunakan nama pasti itu untuk skrip turnamen!")

                elif "Pemburu ARA" in pilihan_ai:
                    st.subheader("🎯 Pemburu ARA (Sistem Kualifikasi Lama)")
                    st.info("💡 **Fitur Auto-Pilot 9 Rumus (Klasemen Global) telah dipindahkan ke menu '🤖 AI Bandar'.** Silakan buka menu tersebut untuk menggunakan mode pencetak Tabel Spreadsheet secara otomatis!")

                    # ==============================================================
                    # 🛸 TOMBOL AUTO-PILOT ULTIMATE (KLASEMEN GLOBAL)
                    # ==============================================================
                    st.markdown("### 🛸 Mode Auto-Pilot (Super AI & Klasemen)")
                    st.markdown("Sistem akan menyeleksi 15 saham terbaik per rumus secara global, lalu AI akan memilih Top 5 untuk dicetak ke tabel Spreadsheet.")
                    
                    if st.button("🛸 Jalankan Auto-Pilot Ultimate", type="primary"):
                        if not GEMINI_API_KEY:
                            st.error("❌ Kunci API GEMINI belum dipasang!")
                        else:
                            daftar_rumus = {
                                1: df_v1, 2: df_v2, 3: df_v3, 
                                4: df_v4, 5: df_v5, 6: df_v6, 
                                7: df_v7, 8: df_v8, 9: df_v9
                            }
                            
                            progress_bar = st.progress(0)
                            status_teks = st.empty()
                            
                            # Siapkan keranjang untuk membuat tabel spreadsheet di akhir
                            keranjang_spreadsheet = {f"RUMUS {i}": [] for i in range(1, 10)}
                            
                            for i in range(1, 10):
                                df_target = daftar_rumus[i]
                                progress_bar.progress(i / 9.0)
                                
                                if len(df_target) == 0:
                                    status_teks.warning(f"⏭️ Rumus {i} kosong. Dilewati.")
                                    time.sleep(1)
                                    continue
                                    
                                status_teks.info(f"🔄 **Algojo Python bekerja pada Rumus {i}**... (Mengekstrak data global)")
                                
                                saham_valid = df_target['Ticker'].tolist()
                                df_seleksi = df_hasil[df_hasil['Ticker'].isin(saham_valid)].copy()
                                
                                df_seleksi['Score_Num'] = pd.to_numeric(df_seleksi['Total Score'], errors='coerce').fillna(0)
                                
                                # TAHAP 1: KLASEMEN GLOBAL (Pilih Top 15 berdasarkan Data Keras)
                                df_sorted = df_seleksi.sort_values(by=['Score_Num', 'Volume', 'Change (%)'], ascending=[False, False, False])
                                top_15 = df_sorted.head(15)
                                
                                data_kirim_ai = {}
                                for _, row in top_15.iterrows():
                                    data_kirim_ai[row['Ticker']] = {
                                        'Harga': row.get('Harga (Rp)', 0),
                                        'Volume': row.get('Volume', 0),
                                        'Score': row.get('Score_Num', 0),
                                        'Change_Pct': row.get('Change (%)', 0),
                                        'Tekanan_Bandar': row.get('Tekanan Bandar', 'Normal'),
                                        'Broksum': row.get('Broksum', 'Normal')
                                    }
                                    
                                status_teks.warning(f"🧠 Rumus {i} - Sidang Grand Final AI... (Menyaring 5 Jawara dari Top 15)")
                                
                                # TAHAP 2: HAKIM AI (Pilih Top 5 Mutlak)
                                try:
                                    hasil_mentah = ai_hakim_klasemen(data_kirim_ai, GEMINI_API_KEY)
                                    teks_bersih = hasil_mentah.replace('```json', '').replace('```', '').strip()
                                    pencarian_json = re.search(r'\[\s*\{.*?\}\s*\]', teks_bersih, re.DOTALL)
                                    
                                    if pencarian_json:
                                        hasil_json = json.loads(pencarian_json.group(0))
                                        df_tampil = pd.DataFrame(hasil_json)
                                        
                                        # Ambil ticker untuk masuk ke tabel spreadsheet
                                        if 'Ticker' in df_tampil.columns:
                                            jawara_tickers = df_tampil['Ticker'].tolist()
                                        else:
                                            jawara_tickers = []
                                            
                                        # Batasi maksimal 5, jika kurang tambahkan string kosong "" agar tabel rata
                                        jawara_tickers = (jawara_tickers + ["", "", "", "", ""])[:5] 
                                        keranjang_spreadsheet[f"RUMUS {i}"] = jawara_tickers
                                        
                                        # Simpan sinyal untuk dieksekusi bot malam ini
                                        if 'Target_TP' in df_tampil.columns and 'Target_CL' in df_tampil.columns:
                                            df_sinyal = df_tampil[['Ticker', 'Target_TP', 'Target_CL']]
                                            df_sinyal.to_csv(f"Database/sinyal_ai_rumus_{i}.csv", index=False)
                                            
                                    else:
                                        st.error(f"❌ Rumus {i} Gagal (AI tidak merespon JSON yang benar).")
                                        keranjang_spreadsheet[f"RUMUS {i}"] = ["", "", "", "", ""]
                                        
                                except Exception as e:
                                    st.error(f"❌ Error pada Rumus {i}: {e}")
                                    keranjang_spreadsheet[f"RUMUS {i}"] = ["", "", "", "", ""]
                                
                                time.sleep(2) # Nafas untuk API Google
                            
                            status_teks.success("🎉 MISSION ACCOMPLISHED! SELURUH RUMUS BERHASIL DISARING!")
                            st.balloons()
                            
                            # TAHAP 3: CETAK TABEL SPREADSHEET (Siap Copy-Paste)
                            st.markdown("### 📋 Tabel Master Portofolio (Siap Salin)")
                            df_spreadsheet = pd.DataFrame(keranjang_spreadsheet)
                            
                            st.data_editor(df_spreadsheet, use_container_width=True, hide_index=True)

    # ==========================================
    # TAB 4: PORTOFOLIO & BOT
    # ==========================================
    with tab4:
        st.markdown("## 🤖 Monitor Bot Simulator")
        
        # --- TOMBOL PEMICU BOT ---
        if st.button("🛒 Eksekusi Pembelian Bot Sekarang!", type="primary", use_container_width=True):
            with st.spinner("Bot sedang membaca sinyal dan mengeksekusi pembelian..."):
                import subprocess
                import sys  
                
                try:
                    proses_bot = subprocess.run([sys.executable, "bot_simulator.py"], capture_output=True, text=True)
                    
                    if proses_bot.returncode != 0:
                        st.error("❌ Bot gagal dijalankan. Berikut adalah log error dari sistem:")
                        st.code(proses_bot.stderr, language="bash")
                    else:
                        st.success("✅ Bot selesai berbelanja! Memuat ulang halaman...")
                        time.sleep(2)
                        st.rerun()
                except Exception as e:
                    st.error(f"Sistem web gagal memanggil file bot: {e}")
        
        st.markdown("---")
        
        # =========================================================
        # 📊 LAPORAN PERFORMA (SISTEM BRANKAS 3 LAPIS)
        # =========================================================
        st.markdown("## 📊 Dashboard Performa AI (Live)")
        
        pilihan_arena = st.selectbox("📂 Pilih Arena untuk diinspeksi:", [f"Rumus {i}" for i in range(1, 10)])
        nomor_rumus = pilihan_arena.split(" ")[1]

        FILE_SINYAL = f"Database/sinyal_ai_rumus_{nomor_rumus}.csv"
        file_porto = f"Database/portofolio_aktif_rumus_{nomor_rumus}.csv"
        file_hist = f"Database/histori_transaksi_rumus_{nomor_rumus}.csv"

        MODAL_AWAL = 100000000.0 
        
        df_porto = pd.read_csv(file_porto) if os.path.exists(file_porto) else pd.DataFrame()
        df_hist = pd.read_csv(file_hist) if os.path.exists(file_hist) else pd.DataFrame()

        # ---------------------------------------------------------
        # 🏆 LAPIS 3: PAPAN SKOR WINRATE & SALDO KAS
        # ---------------------------------------------------------
        total_profit_rp = df_hist['Total_Return_Rp'].sum() if not df_hist.empty and 'Total_Return_Rp' in df_hist.columns else 0
        modal_terpakai = df_porto['Total_Modal'].sum() if not df_porto.empty and 'Total_Modal' in df_porto.columns else 0
        
        saldo_saat_ini = MODAL_AWAL + total_profit_rp - modal_terpakai
        total_aset = saldo_saat_ini + modal_terpakai
        
        total_trade = len(df_hist)
        if total_trade > 0 and 'Return_%' in df_hist.columns:
            win_trade = len(df_hist[df_hist['Return_%'] > 0])
            winrate = (win_trade / total_trade) * 100
        else:
            winrate = 0.0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="💰 Total Aset (Kas + Saham)", value=f"Rp {total_aset:,.0f}".replace(",", "."))
        with col2:
            st.metric(label="💵 Dana Kas Tersedia", value=f"Rp {saldo_saat_ini:,.0f}".replace(",", "."))
        with col3:
            st.metric(label="📈 Realized Profit/Loss", value=f"Rp {total_profit_rp:,.0f}".replace(",", "."), delta=f"Rp {total_profit_rp:,.0f}".replace(",", "."))
        with col4:
            st.metric(label="🎯 Winrate AI", value=f"{winrate:.1f}%", delta=f"{total_trade} Selesai", delta_color="off")

        st.markdown("---")
        
        # ---------------------------------------------------------
        # MENUNJUKKAN 3 TABEL (ANTREAN, AKTIF, HISTORI)
        # ---------------------------------------------------------
        sub1, sub2, sub3 = st.tabs(["📝 Sinyal Antrean", "🟢 Lapis 1: Portofolio Aktif", "📚 Lapis 2: Histori Transaksi"])
        
        with sub1:
            if os.path.exists(FILE_SINYAL):
                df_sinyal = pd.read_csv(FILE_SINYAL)
                st.success("🔥 Sinyal AI (Kertas Belanja) telah diterima! Bot akan mengeksekusi pembelian pada jam bursa.")
                st.dataframe(df_sinyal, use_container_width=True, hide_index=True)
            else:
                st.info(f"KOSONG. Belum ada sinyal masuk untuk {pilihan_arena}, atau bot sudah membelinya dan membakar kertas belanja.")
        
        with sub2:
            if not df_porto.empty:
                df_porto_tampil = df_porto.copy()
                df_porto_tampil['Harga_Beli'] = df_porto_tampil['Harga_Beli'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                df_porto_tampil['Target_TP'] = df_porto_tampil['Target_TP'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                df_porto_tampil['Target_CL'] = df_porto_tampil['Target_CL'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                df_porto_tampil['Total_Modal'] = df_porto_tampil['Total_Modal'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                st.dataframe(df_porto_tampil, use_container_width=True, hide_index=True)
            else:
                st.info("📦 Gudang kosong. Belum ada saham yang dibeli atau semua sudah terjual (Masuk ke Lapis 2).")
        
        with sub3:
            if not df_hist.empty:
                def warnai_profit(val):
                    if isinstance(val, (int, float)):
                        color = '#166534' if val > 0 else '#991b1b' if val < 0 else ''
                        return f'background-color: {color}'
                    return ''
                    
                if 'Tanggal_Jual' in df_hist.columns:
                    df_hist_tampil = df_hist.sort_values(by='Tanggal_Jual', ascending=False).reset_index(drop=True)
                else:
                    df_hist_tampil = df_hist.copy()
                    
                st.dataframe(
                    df_hist_tampil.style.applymap(warnai_profit, subset=['Total_Return_Rp', 'Return_%']).format({
                        'Harga_Beli': "Rp {:,.0f}",
                        'Harga_Jual': "Rp {:,.0f}",
                        'Total_Return_Rp': "Rp {:,.0f}",
                        'Return_%': "{:.2f}%"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(f"📭 Belum ada riwayat penjualan saham untuk {pilihan_arena}.")