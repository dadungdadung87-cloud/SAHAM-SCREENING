import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

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
# 2. MEMUAT DATA LOKAL (SANGAT INSTAN)
# ==========================================
FILE_HASIL = "hasil_screener.csv"

if os.path.exists(FILE_HASIL):
    # Mengambil waktu pembaruan file CSV terakhir kali
    waktu_modifikasi = os.path.getmtime(FILE_HASIL)
    waktu_terakhir = datetime.fromtimestamp(waktu_modifikasi).strftime('%Y-%m-%d %H:%M:%S')
    
    st.success(f"💾 Data berhasil dimuat secara instan! Terakhir diperbarui pada: **{waktu_terakhir}**")
    df_hasil = pd.read_csv(FILE_HASIL)
else:
    st.error(f"❌ File '{FILE_HASIL}' belum ditemukan! Silakan jalankan script `update_data.py` terlebih dahulu di terminal untuk memproses data.")
    df_hasil = pd.DataFrame()

# ==========================================
# 3. DASHBOARD RINGKASAN & FILTER 
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
    
    # Menambahkan tombol centang filter ketat
    mode_ketat = st.checkbox("🔥 Aktifkan Preset Kriteria Super (Saring Ketat)")
    
    search_ticker = st.text_input("🔍 Cari Kode Saham Spesifik (Contoh: BBCA, BMRI)", "")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: filter_vol = st.selectbox("🔊 1. Volume", ["Semua", "Tembus MA20", "Normal"], index=1 if mode_ketat else 0)
    with col2: filter_rsi = st.selectbox("📊 2. RSI (14D)", ["Semua", "> 50 (Bullish)", "<= 50 (Bearish)"], index=1 if mode_ketat else 0)
    with col3: filter_trend = st.selectbox("📈 3. Tren (MA20)", ["Semua", "Uptrend", "Downtrend"], index=1 if mode_ketat else 0)
    with col4: filter_momentum = st.selectbox("⚡ 4. Momentum", ["Semua", "Positif", "Negatif"], index=1 if mode_ketat else 0)

    st.write("") 
    # Filter Bollinger Bands menjadi 4 kolom di baris kedua
    col5, col6, col7, col8 = st.columns(4)
    with col5: filter_score = st.selectbox("⭐ Total Score", ["Semua", 4, 3, 2, 1, 0])
    with col6: filter_rekomendasi = st.selectbox("🎯 Rekomendasi", ["Semua", "BELI", "WAIT & SEE"])
    with col7: filter_likuiditas = st.selectbox("💧 Likuiditas", ["Semua", "> 1 Miliar", "< 1 Miliar"])
    
    # 👇 Baris di bawah ini yang diperbarui (tambahkan index=3)
    with col8: filter_bb = st.selectbox("🌐 Bollinger Bands", ["Semua", "Squeeze", "Bottom Rebound", "Breakout Upper", "Normal"], index=3 if mode_ketat else 0)

    df_filtered = df_hasil.copy()
    if search_ticker: df_filtered = df_filtered[df_filtered["Ticker"].str.contains(search_ticker.upper(), na=False)]
    if filter_vol != "Semua": df_filtered = df_filtered[df_filtered["Vol Breakout"] == filter_vol]
    if filter_rsi == "> 50 (Bullish)": df_filtered = df_filtered[df_filtered["RSI (14D)"] > 50]
    elif filter_rsi == "<= 50 (Bearish)": df_filtered = df_filtered[df_filtered["RSI (14D)"] <= 50]
    if filter_trend != "Semua": df_filtered = df_filtered[df_filtered["MA Signal"] == filter_trend]
    if filter_momentum != "Semua": df_filtered = df_filtered[df_filtered["Momentum"] == filter_momentum]
    
    # Penyesuaian filter tipe numerik dari file CSV lokal
    if filter_score != "Semua": df_filtered = df_filtered[df_filtered["Total Score"] == int(filter_score)]
    if filter_rekomendasi != "Semua": df_filtered = df_filtered[df_filtered["Rekomendasi"] == filter_rekomendasi]
    if filter_likuiditas != "Semua": df_filtered = df_filtered[df_filtered["Likuiditas"] == filter_likuiditas]
    
    # Logika filter untuk Bollinger Bands
    if filter_bb != "Semua":
        if "Status BB" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Status BB"] == filter_bb]
        else:
            st.warning("⚠️ Kolom 'Status BB' belum ada di CSV. Silakan jalankan update_data.py terlebih dahulu.")

    # ==========================================
    # 4. PAGINASI & FORMAT TABEL
    # ==========================================
    if not df_filtered.empty:
        st.markdown("### Hasil Penapisan (Screener)")
        
        col_pg1, col_pg2, col_pg3 = st.columns([1, 1, 2])
        
        with col_pg1:
            saham_per_halaman = st.selectbox("Tampilkan baris:", [20, 50, 100])
            
        total_halaman = int(np.ceil(len(df_filtered) / saham_per_halaman))
        
        with col_pg2:
            if total_halaman > 0:
                halaman_aktif = st.selectbox("Pilih Halaman:", range(1, total_halaman + 1))
            else:
                halaman_aktif = 1
                
        indeks_awal = (halaman_aktif - 1) * saham_per_halaman
        indeks_akhir = indeks_awal + saham_per_halaman
        df_tampil = df_filtered.iloc[indeks_awal:indeks_akhir]
        
        def format_angka(val): return f"{int(val):,}".replace(",", ".")
        def format_persen(val): return f"{val:+.2f}%"
        
        def warna_tabel(val):
            style = '' 
            if isinstance(val, (int, float)):
                if val > 0: style = 'color: #22c55e; font-weight: 600;' 
                elif val < 0: style = 'color: #ef4444; font-weight: 600;' 
            elif isinstance(val, str):
                if val in ["Positif", "Uptrend", "BELI", "Breakout Upper", "Bottom Rebound"]: style = 'color: #22c55e; font-weight: 600;'
                elif val in ["Negatif", "Downtrend", "WAIT & SEE"]: style = 'color: #ef4444; font-weight: 600;'
                elif val == "> 1 Miliar": style = 'color: #3b82f6; font-weight: 600;'
                elif val == "Squeeze": style = 'color: #fbbf24; font-weight: 600;'
            return style

        kolom_berwarna = ["Change (%)", "Momentum", "MA Signal", "Rekomendasi", "Likuiditas", "Status BB"]
        
        # Memastikan hanya mewarnai kolom yang memang ada di dataframe
        kolom_berwarna_aktual = [col for col in kolom_berwarna if col in df_tampil.columns]

        tabel_akhir = df_tampil.style.format({
            "Harga (Rp)": format_angka,
            "Volume": format_angka,
            "Change (%)": format_persen,
            "RSI (14D)": "{:.0f}"
        }).map(warna_tabel, subset=kolom_berwarna_aktual)

        st.dataframe(tabel_akhir, use_container_width=True, hide_index=True)

        st.caption(f"Menampilkan urutan {(indeks_awal + 1)} - {min(indeks_akhir, len(df_filtered))} dari total {len(df_filtered)} saham yang lolos filter.")
    else:
        st.warning("Tidak ada saham yang memenuhi kriteria filter Anda saat ini.")