import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests # <--- TAMBAHKAN INI

# ==========================================
# 1. PENGATURAN UI/UX
# ==========================================
st.set_page_config(page_title="Screener Saham IHSG", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    h1 {
        font-weight: 800;
        background: -webkit-linear-gradient(#38bdf8, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 10px;
    }
    .metric-container {
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        border: 1px solid #334155;
        background-color: #1e293b;
        color: #f8fafc;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ AlgoTrade Screener - IHSG")
st.markdown("Analisis Tren, Momentum, dan Volume secara Real-Time.")
st.markdown("---")

# ==========================================
# 2. DAFTAR SAHAM (DARI FILE Teks)
# ==========================================
try:
    # Membaca daftar saham langsung dari file saham.txt
    with open("saham.txt", "r") as file:
        daftar_saham = [baris.strip().upper() for baris in file if baris.strip()]
    st.caption(f"📁 Berhasil memuat **{len(daftar_saham)}** saham dari file eksternal.")
except FileNotFoundError:
    st.error("File 'saham.txt' tidak ditemukan! Pastikan Anda sudah membuat file tersebut.")
    daftar_saham = [] # Kosongkan daftar jika file tidak ada

# ==========================================
# 3. MESIN KALKULASI ALGORITMA (VERSI TURBO - MULTITHREADING)
# ==========================================
@st.cache_data(ttl=300) 
def proses_screener_turbo(saham_list):
    hasil = []
    
    with st.spinner('Menerapkan Bulk Download untuk 500+ saham secara serentak...'):
        # 1. Menyiapkan daftar lengkap kode saham dengan .JK
        tickers_jk = [f"{t}.JK" for t in saham_list]
        tickers_str = " ".join(tickers_jk)
        
        # 2. BULK DOWNLOAD (Menarik semua data sekaligus)
        # Parameter threads=True membuat proses download berjalan paralel
        data_mentah = yf.download(tickers_str, period="2mo", interval="1d", group_by='ticker', threads=True, progress=False)
        
        progress_bar = st.progress(0)
        
        # 3. Mengolah data mentah yang sudah ditarik secara massal
        for i, ticker in enumerate(saham_list):
            try:
                t_jk = f"{ticker}.JK"
                
                # Mengisolasi data untuk 1 saham spesifik, buang data yang kosong
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
                        
                        ma_20 = df_saham['Close'].rolling(window=20).mean().iloc[-1].item()
                        vol_ma_20 = df_saham['Volume'].rolling(window=20).mean().iloc[-1].item()
                        ma_signal = "Uptrend" if close_today > ma_20 else "Downtrend"
                        
                        vol_breakout = "Tembus MA20" if vol_today > vol_ma_20 else "Normal"
                        
                        delta = df_saham['Close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi_raw = 100 - (100 / (1 + rs)).iloc[-1].item()
                        rsi = int(round(rsi_raw)) if not pd.isna(rsi_raw) else 0
                        
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
                            "Likuiditas": likuiditas,
                            "Total Score": score,
                            "Rekomendasi": rekomendasi
                        })
            except Exception:
                pass
                
            # Update progress bar agar visualisasi tetap responsif
            progress_bar.progress((i + 1) / len(saham_list))
            
        progress_bar.empty() 
        
    kolom = ["Ticker", "Harga (Rp)", "Change (%)", "Volume", "Vol Breakout", "RSI (14D)", "Momentum", "MA Signal", "Likuiditas", "Total Score", "Rekomendasi"]
    if not hasil: return pd.DataFrame(columns=kolom)
    return pd.DataFrame(hasil)

# Mengeksekusi mesin turbo
df_hasil = proses_screener_turbo(daftar_saham)

# ==========================================
# 4. DASHBOARD RINGKASAN & FILTER (UI BARU)
# ==========================================
if not df_hasil.empty:
    total_dianalisis = len(df_hasil)
    total_beli = len(df_hasil[df_hasil['Rekomendasi'] == 'BELI'])
    total_uptrend = len(df_hasil[df_hasil['MA Signal'] == 'Uptrend'])

    met1, met2, met3 = st.columns(3)
    met1.markdown(f"<div class='metric-container'><h3>🔍 Total Dianalisis</h3><h2>{total_dianalisis} Saham</h2></div>", unsafe_allow_html=True)
    met2.markdown(f"<div class='metric-container'><h3>🎯 Sinyal BELI</h3><h2 style='color: #4ade80;'>{total_beli} Saham</h2></div>", unsafe_allow_html=True)
    met3.markdown(f"<div class='metric-container'><h3>📈 Fase Uptrend</h3><h2 style='color: #60a5fa;'>{total_uptrend} Saham</h2></div>", unsafe_allow_html=True)
    
    st.markdown("### 🎛️ Panel Filter Lengkap")
    
    # Tombol untuk menarik data paling baru dari market
if st.button("🔄 Perbarui Data Market Sekarang"):
    st.cache_data.clear() # Menghapus ingatan lama
    st.rerun() # Memuat ulang web secara instan

    # FITUR BARU: Kolom Pencarian Saham
    search_ticker = st.text_input("🔍 Cari Kode Saham Spesifik (Contoh: BBCA, BMRI)", "")
    
    # Baris 1: Filter Indikator Dasar
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filter_vol = st.selectbox("🔊 1. Volume", ["Semua", "Tembus MA20", "Normal"])
    with col2:
        filter_rsi = st.selectbox("📊 2. RSI (14D)", ["Semua", "> 50 (Bullish)", "<= 50 (Bearish)"])
    with col3:
        filter_trend = st.selectbox("📈 3. Tren (MA20)", ["Semua", "Uptrend", "Downtrend"])
    with col4:
        filter_momentum = st.selectbox("⚡ 4. Momentum", ["Semua", "Positif", "Negatif"])

    # Baris 2: Filter Hasil Penilaian & Keamanan
    st.write("") # Spasi kecil agar rapi
    col5, col6, col7 = st.columns(3)
    with col5:
        filter_score = st.selectbox("⭐ Total Score", ["Semua", 4, 3, 2, 1, 0])
    with col6:
        filter_rekomendasi = st.selectbox("🎯 Rekomendasi", ["Semua", "BELI", "WAIT & SEE"])
    with col7:
        filter_likuiditas = st.selectbox("💧 Likuiditas", ["Semua", "> 1 Miliar", "< 1 Miliar"])

    # MESIN PENYARINGAN (FILTERING)
    df_filtered = df_hasil.copy()
    
    # Menyaring berdasarkan Pencarian Ticker (FITUR BARU)
    if search_ticker:
        # Menjadikan teks input selalu huruf besar agar cocok dengan data
        df_filtered = df_filtered[df_filtered["Ticker"].str.contains(search_ticker.upper(), na=False)]
        
    # Menyaring berdasarkan Indikator
    if filter_vol != "Semua":
        df_filtered = df_filtered[df_filtered["Vol Breakout"] == filter_vol]
    if filter_rsi == "> 50 (Bullish)":
        df_filtered = df_filtered[df_filtered["RSI (14D)"] > 50]
    elif filter_rsi == "<= 50 (Bearish)":
        df_filtered = df_filtered[df_filtered["RSI (14D)"] <= 50]
    if filter_trend != "Semua":
        df_filtered = df_filtered[df_filtered["MA Signal"] == filter_trend]
    if filter_momentum != "Semua":
        df_filtered = df_filtered[df_filtered["Momentum"] == filter_momentum]
        
    # Menyaring berdasarkan Penilaian Akhir
    if filter_score != "Semua":
        df_filtered = df_filtered[df_filtered["Total Score"] == filter_score]
    if filter_rekomendasi != "Semua":
        df_filtered = df_filtered[df_filtered["Rekomendasi"] == filter_rekomendasi]
    if filter_likuiditas != "Semua":
        df_filtered = df_filtered[df_filtered["Likuiditas"] == filter_likuiditas]

# ==========================================
# 5. PAGINASI & FORMAT TABEL
# ==========================================
    saham_per_halaman = 20
    total_halaman = int(np.ceil(len(df_filtered) / saham_per_halaman))

    if total_halaman > 0:
        st.markdown("### Hasil Penapisan (Screener)")
        
        halaman_aktif = st.selectbox("Pilih Halaman:", range(1, total_halaman + 1))
        
        indeks_awal = (halaman_aktif - 1) * saham_per_halaman
        indeks_akhir = indeks_awal + saham_per_halaman
        df_tampil = df_filtered.iloc[indeks_awal:indeks_akhir]
        
        # Fungsi Format Kustom untuk Angka & Persen
        def format_angka(val):
            return f"{int(val):,}".replace(",", ".")
            
        def format_persen(val):
            return f"{val:+.2f}%"
        
        # Fungsi Warna
        def warna_tabel(val):
            style = '' 
            if isinstance(val, (int, float)):
                if val > 0: style = 'color: #22c55e; font-weight: 600;' 
                elif val < 0: style = 'color: #ef4444; font-weight: 600;' 
            elif isinstance(val, str):
                if val in ["Positif", "Uptrend", "BELI"]: style = 'color: #22c55e; font-weight: 600;'
                elif val in ["Negatif", "Downtrend", "WAIT & SEE"]: style = 'color: #ef4444; font-weight: 600;'
                elif val == "> 1 Miliar": style = 'color: #3b82f6; font-weight: 600;'
            return style

        # MENGGUNAKAN SUBSET: Warna hanya diterapkan pada kolom-kolom ini
        kolom_berwarna = ["Change (%)", "Momentum", "MA Signal", "Rekomendasi", "Likuiditas"]

        tabel_akhir = df_tampil.style.format({
            "Harga (Rp)": format_angka,
            "Volume": format_angka,
            "Change (%)": format_persen,
            "RSI (14D)": "{:.0f}"
        }).map(warna_tabel, subset=kolom_berwarna)

        st.dataframe(
            tabel_akhir,
            use_container_width=True,
            hide_index=True,
            height=750 
        )
        st.caption(f"Menampilkan urutan {(indeks_awal + 1)} - {min(indeks_akhir, len(df_filtered))} dari total {len(df_filtered)} saham yang lolos filter.")
    else:
        st.warning("Tidak ada saham yang memenuhi kriteria filter Anda saat ini.")