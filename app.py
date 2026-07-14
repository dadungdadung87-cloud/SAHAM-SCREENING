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
st.markdown("Analisis Tren, Momentum, Volume, dan Sentimen Akuisisi.")
st.markdown("---")

# ==========================================
# 2. MEMUAT DATA LOKAL
# ==========================================
FILE_HASIL = "hasil_screener.csv"
FILE_AKUISISI = "data_akuisisi.csv"

if os.path.exists(FILE_HASIL):
    waktu_modifikasi = os.path.getmtime(FILE_HASIL)
    waktu_terakhir = datetime.fromtimestamp(waktu_modifikasi).strftime('%Y-%m-%d %H:%M:%S')
    
    st.success(f"💾 Data berhasil dimuat secara instan! Terakhir diperbarui pada: **{waktu_terakhir}**")
    df_hasil = pd.read_csv(FILE_HASIL)
    
    # --- PENGGABUNGAN DATA AKUISISI ---
    if os.path.exists(FILE_AKUISISI):
        df_akuisisi = pd.read_csv(FILE_AKUISISI)
        df_hasil = pd.merge(df_hasil, df_akuisisi, on="Ticker", how="left")
        # Jika ada saham yang kosong beritanya, jadikan "TIDAK ADA"
        df_hasil["Status Akuisisi"] = df_hasil["Status Akuisisi"].fillna("TIDAK ADA")
    else:
        df_hasil["Status Akuisisi"] = "TIDAK ADA"
else:
    st.error(f"❌ File '{FILE_HASIL}' belum ditemukan! Silakan jalankan script `update_data.py` terlebih dahulu di terminal.")
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
    
    st.markdown("---")
    persentase_uptrend = (total_uptrend / total_dianalisis) * 100 if total_dianalisis > 0 else 0
    st.markdown(f"**📈 Indeks Kesehatan Pasar (Saham Fase Uptrend): {persentase_uptrend:.1f}%**")
    st.progress(persentase_uptrend / 100.0)
    
    if persentase_uptrend > 50:
        st.caption("🟢 Mayoritas saham sedang Uptrend. Momentum pasar secara umum mendukung untuk Swing Trading.")
    else:
        st.caption("🔴 Mayoritas saham sedang Downtrend. Waspada, pasar sedang lesu atau distribusi.")
    st.markdown("---")

    st.markdown("### 🎛️ Panel Filter Lengkap")
    
    mode_ketat = st.checkbox("🔥 Aktifkan Preset Kriteria Super (Saring Ketat)")
    search_ticker = st.text_input("🔍 Cari Kode Saham Spesifik (Contoh: BBCA, BMRI)", "")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: filter_vol = st.selectbox("🔊 1. Volume", ["Semua", "Tembus MA20", "Normal"], index=1 if mode_ketat else 0)
    with col2: filter_rsi = st.selectbox("📊 2. RSI (14D)", ["Semua", "> 50 (Bullish)", "<= 50 (Bearish)"], index=1 if mode_ketat else 0)
    with col3: filter_trend = st.selectbox("📈 3. Tren (MA20)", ["Semua", "Uptrend", "Downtrend"], index=1 if mode_ketat else 0)
    with col4: filter_momentum = st.selectbox("⚡ 4. Momentum", ["Semua", "Positif", "Negatif"], index=1 if mode_ketat else 0)

    st.write("") 
    
    # --- FILTER BARU: MENJADI 5 KOLOM UNTUK AKUISISI ---
    col5, col6, col7, col8, col9 = st.columns(5)
    with col5: filter_score = st.selectbox("⭐ Total Score", ["Semua", 4, 3, 2, 1, 0])
    with col6: filter_rekomendasi = st.selectbox("🎯 Rekomendasi", ["Semua", "BELI", "WAIT & SEE"])
    with col7: filter_likuiditas = st.selectbox("💧 Likuiditas", ["Semua", "> 1 Miliar", "< 1 Miliar"])
    with col8: filter_bb = st.selectbox("🌐 Bollinger Bands", ["Semua", "Squeeze", "Bottom Rebound", "Breakout Upper", "Normal"], index=3 if mode_ketat else 0)
    with col9: filter_akuisisi = st.selectbox("🤝 Akuisisi", ["Semua", "TIDAK ADA", "RENCANA AKUISISI", "DALAM AKUISISI"])

    df_filtered = df_hasil.copy()
    if search_ticker: df_filtered = df_filtered[df_filtered["Ticker"].str.contains(search_ticker.upper(), na=False)]
    if filter_vol != "Semua": df_filtered = df_filtered[df_filtered["Vol Breakout"] == filter_vol]
    if filter_rsi == "> 50 (Bullish)": df_filtered = df_filtered[df_filtered["RSI (14D)"] > 50]
    elif filter_rsi == "<= 50 (Bearish)": df_filtered = df_filtered[df_filtered["RSI (14D)"] <= 50]
    if filter_trend != "Semua": df_filtered = df_filtered[df_filtered["MA Signal"] == filter_trend]
    if filter_momentum != "Semua": df_filtered = df_filtered[df_filtered["Momentum"] == filter_momentum]
    
    if filter_score != "Semua": df_filtered = df_filtered[df_filtered["Total Score"] == int(filter_score)]
    if filter_rekomendasi != "Semua": df_filtered = df_filtered[df_filtered["Rekomendasi"] == filter_rekomendasi]
    if filter_likuiditas != "Semua": df_filtered = df_filtered[df_filtered["Likuiditas"] == filter_likuiditas]
    
    if filter_bb != "Semua":
        if "Status BB" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Status BB"] == filter_bb]
            
    # LOGIKA FILTER AKUISISI
    if filter_akuisisi != "Semua": 
        if "Status Akuisisi" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Status Akuisisi"] == filter_akuisisi]

    # ==========================================
    # 4. PAGINASI & FORMAT TABEL
    # ==========================================
    if not df_filtered.empty:
        st.markdown("### Hasil Penapisan (Screener)")
        
        col_pg1, col_pg2, col_pg3 = st.columns([1, 1, 2])
        with col_pg1: saham_per_halaman = st.selectbox("Tampilkan baris:", [20, 50, 100])
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
                if val in ["Positif", "Uptrend", "BELI", "Breakout Upper", "Bottom Rebound", "DALAM AKUISISI"]: style = 'color: #22c55e; font-weight: 600;'
                elif val in ["Negatif", "Downtrend", "WAIT & SEE"]: style = 'color: #ef4444; font-weight: 600;'
                elif val == "> 1 Miliar": style = 'color: #3b82f6; font-weight: 600;'
                elif val in ["Squeeze", "RENCANA AKUISISI"]: style = 'color: #eab308; font-weight: 600;'
            return style

        def warna_skor(val):
            if val in [3, 4]: return 'color: #22c55e; font-weight: 600;'
            elif val in [0, 1, 2]: return 'color: #ef4444; font-weight: 600;'
            return ''

        # --- TAMBAHAN KOLOM "Status Akuisisi" KE LIST WARNA ---
        kolom_berwarna = ["Change (%)", "Momentum", "MA Signal", "Rekomendasi", "Likuiditas", "Status BB", "Status Akuisisi"]
        kolom_berwarna_aktual = [col for col in kolom_berwarna if col in df_tampil.columns]

        tabel_akhir = df_tampil.style.format({
            "Harga (Rp)": format_angka,
            "Volume": format_angka,
            "Change (%)": format_persen,
            "RSI (14D)": "{:.0f}"
        }).map(warna_tabel, subset=kolom_berwarna_aktual)

        if "Total Score" in df_tampil.columns:
            tabel_akhir = tabel_akhir.map(warna_skor, subset=['Total Score'])

        st.dataframe(tabel_akhir, use_container_width=True, hide_index=True)
        st.caption(f"Menampilkan urutan {(indeks_awal + 1)} - {min(indeks_akhir, len(df_filtered))} dari total {len(df_filtered)} saham yang lolos filter.")
        
        st.markdown("---")
        @st.cache_data
        def convert_df(df):
            return df.to_csv(index=False).encode('utf-8')
        
        csv_data = convert_df(df_filtered)
        st.download_button(
            label="📥 Unduh Hasil Screener (CSV)",
            data=csv_data,
            file_name=f'screener_ihsg_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv',
        )
    else:
        st.warning("Tidak ada saham yang memenuhi kriteria filter Anda saat ini.")