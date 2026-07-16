import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import plotly.express as px

# ==========================================
# 1. PENGATURAN UI/UX
# ==========================================
st.set_page_config(page_title="Screener Saham IHSG", layout="wide", initial_sidebar_state="expanded")

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
        margin-bottom: 20px;
    }
    /* Mempercantik tampilan Tab */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 16px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SIDEBAR (BILAH SAMPING)
# ==========================================
st.sidebar.title("⚙️ Pengaturan Cepat")
st.sidebar.markdown("Gunakan panel ini untuk pencarian instan.")

search_ticker = st.sidebar.text_input("🔍 Cari Kode Saham (Cth: BBCA)", "")
mode_ketat = st.sidebar.checkbox("🔥 Aktifkan Filter Super Ketat", value=False, help="Otomatis menyetel filter ke mode paling ketat untuk Swing Trading.")

st.sidebar.markdown("---")
st.sidebar.caption("© AlgoTrade Screener")

# ==========================================
# 3. KONTEN UTAMA (HEADER)
# ==========================================
st.title("⚡ AlgoTrade Screener - IHSG")
st.markdown("Analisis Tren, Momentum, Volume, dan Sentimen Akuisisi.")
st.markdown("---")

# ==========================================
# 4. MEMUAT DATA LOKAL
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
        df_hasil["Status Akuisisi"] = df_hasil["Status Akuisisi"].fillna("TIDAK ADA")
    else:
        df_hasil["Status Akuisisi"] = "TIDAK ADA"
else:
    st.error(f"❌ File '{FILE_HASIL}' belum ditemukan! Silakan jalankan script `update_data.py` terlebih dahulu di terminal.")
    df_hasil = pd.DataFrame()

# ==========================================
# 5. PEMBAGIAN SISTEM TAB & KONTEN
# ==========================================
if not df_hasil.empty:
    
    # Membuat 3 Tab
    tab1, tab2, tab3 = st.tabs(["📊 Ringkasan Pasar", "🎯 Screener Utama", "💡 Insight & Edukasi"])
    
    # ----------------------------------------
    # ISI TAB 1: RINGKASAN PASAR (METRIK & GRAFIK)
    # ----------------------------------------
    with tab1:
        st.markdown("### Performa Pasar Keseluruhan")
        
        total_dianalisis = len(df_hasil)
        total_beli = len(df_hasil[df_hasil['Rekomendasi'] == 'BELI'])
        total_uptrend = len(df_hasil[df_hasil['MA Signal'] == 'Uptrend'])

        met1, met2, met3 = st.columns(3)
        met1.markdown(f"<div class='metric-container'><h3>🔍 Total Dianalisis</h3><h2>{total_dianalisis} Saham</h2></div>", unsafe_allow_html=True)
        met2.markdown(f"<div class='metric-container'><h3>🎯 Sinyal BELI</h3><h2 style='color: #4ade80;'>{total_beli} Saham</h2></div>", unsafe_allow_html=True)
        met3.markdown(f"<div class='metric-container'><h3>📈 Fase Uptrend</h3><h2 style='color: #60a5fa;'>{total_uptrend} Saham</h2></div>", unsafe_allow_html=True)
        
        persentase_uptrend = (total_uptrend / total_dianalisis) * 100 if total_dianalisis > 0 else 0
        st.markdown(f"**📈 Indeks Kesehatan Pasar (Saham Fase Uptrend): {persentase_uptrend:.1f}%**")
        st.progress(persentase_uptrend / 100.0)
        
        if persentase_uptrend > 50:
            st.caption("🟢 Mayoritas saham sedang Uptrend. Momentum pasar secara umum mendukung untuk Swing Trading.")
        else:
            st.caption("🔴 Mayoritas saham sedang Downtrend. Waspada, pasar sedang lesu atau distribusi.")
        
        st.markdown("---")
        
        col_chart1, col_chart2 = st.columns([1, 2]) 
        
        with col_chart1:
            df_rekomendasi = df_hasil['Rekomendasi'].value_counts().reset_index()
            df_rekomendasi.columns = ['Rekomendasi', 'Jumlah']
            
            fig_pie = px.pie(
                df_rekomendasi, 
                names='Rekomendasi', 
                values='Jumlah', 
                hole=0.5,
                color='Rekomendasi', 
                color_discrete_map={'BELI': '#22c55e', 'WAIT & SEE': '#ef4444'}
            )
            fig_pie.update_layout(
                title_text='Rasio Sinyal Rekomendasi', 
                margin=dict(t=40, b=20, l=20, r=20),
                showlegend=True,
                height=380 
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_chart2:
            df_top15 = df_hasil.nlargest(15, 'Change (%)')
            
            fig_bar = px.bar(
                df_top15, 
                x='Ticker', 
                y='Change (%)', 
                color='Change (%)', 
                color_continuous_scale=['#86efac', '#22c55e', '#166534']
            )
            fig_bar.update_traces(
                texttemplate='%{y:.0f}%', 
                textposition='outside'
            )
            fig_bar.update_layout(
                title_text='Top 15 Saham Gainers Hari Ini', 
                margin=dict(t=40, b=20, l=20, r=20), 
                showlegend=False,
                xaxis_title="Kode Saham",
                yaxis_title="Perubahan (%)",
                height=380 
            )
            if not df_top15.empty:
                fig_bar.update_yaxes(range=[0, df_top15['Change (%)'].max() * 1.2]) 
                
            st.plotly_chart(fig_bar, use_container_width=True)

    # ----------------------------------------
    # ISI TAB 2: SCREENER UTAMA (FILTER & TABEL)
    # ----------------------------------------
    with tab2:
        with st.expander("🎛️ Buka Panel Filter Lengkap (Klik untuk menyesuaikan kriteria)", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filter_vol = st.selectbox("🔊 Volume", ["Semua", "Tembus MA20", "Normal"], index=1 if mode_ketat else 0)
                filter_momentum = st.selectbox("⚡ Momentum", ["Semua", "Positif", "Negatif"], index=1 if mode_ketat else 0)
                filter_likuiditas = st.selectbox("💧 Likuiditas", ["Semua", "> 1 Miliar", "< 1 Miliar"])
                # --- TAMBAHAN FILTER RISIKO ---
                filter_risiko = st.selectbox("⚠️ Risiko Volatilitas", ["Semua", "Tinggi", "Sedang", "Rendah"])
                
            with col2:
                filter_rsi = st.selectbox("📊 RSI (14D)", ["Semua", "> 50 (Bullish)", "<= 50 (Bearish)"], index=1 if mode_ketat else 0)
                filter_score = st.selectbox("⭐ Total Score", ["Semua", 4, 3, 2, 1, 0])
                filter_bb = st.selectbox("🌐 Bollinger Bands", ["Semua", "Squeeze", "Bottom Rebound", "Breakout Upper", "Normal"], index=3 if mode_ketat else 0)
                
            with col3:
                filter_trend = st.selectbox("📈 Tren (MA20)", ["Semua", "Uptrend", "Downtrend"], index=1 if mode_ketat else 0)
                filter_rekomendasi = st.selectbox("🎯 Rekomendasi", ["Semua", "BELI", "WAIT & SEE"])
                filter_akuisisi = st.selectbox("🤝 Sentimen Akuisisi", ["Semua", "TIDAK ADA", "RENCANA AKUISISI", "DALAM AKUISISI"])

        # LOGIKA FILTERING DATA
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
                
        if filter_akuisisi != "Semua": 
            if "Status Akuisisi" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["Status Akuisisi"] == filter_akuisisi]
                
        # --- LOGIKA FILTER RISIKO ---
        if filter_risiko != "Semua":
            if "Risiko" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["Risiko"] == filter_risiko]

        # PAGINASI & FORMAT TABEL
        if not df_filtered.empty:
            st.markdown("### 📋 Tabel Data Saham")
            
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
            
            def format_angka(val): 
                if pd.isna(val): return "-"
                return f"{int(val):,}".replace(",", ".")
                
            def format_persen(val): 
                if pd.isna(val): return "-"
                return f"{val:+.2f}%"
            
            def warna_tabel(val):
                style = '' 
                if isinstance(val, (int, float)):
                    if val > 0: style = 'color: #22c55e; font-weight: 600;' 
                    elif val < 0: style = 'color: #ef4444; font-weight: 600;' 
                elif isinstance(val, str):
                    # --- MENAMBAHKAN PEWARNAAN UNTUK STATUS RISIKO ---
                    if val in ["Positif", "Uptrend", "BELI", "Breakout Upper", "Bottom Rebound", "DALAM AKUISISI", "Rendah"]: style = 'color: #22c55e; font-weight: 600;'
                    elif val in ["Negatif", "Downtrend", "WAIT & SEE", "Tinggi"]: style = 'color: #ef4444; font-weight: 600;'
                    elif val == "> 1 Miliar": style = 'color: #3b82f6; font-weight: 600;'
                    elif val in ["Squeeze", "RENCANA AKUISISI", "Sedang"]: style = 'color: #eab308; font-weight: 600;'
                return style

            def warna_skor(val):
                if val in [3, 4]: return 'color: #22c55e; font-weight: 600;'
                elif val in [0, 1, 2]: return 'color: #ef4444; font-weight: 600;'
                return ''

            # --- MENAMBAHKAN "Risiko" KE DALAM DAFTAR KOLOM YANG DIWARNAI ---
            kolom_berwarna = ["Change (%)", "Momentum", "MA Signal", "Rekomendasi", "Likuiditas", "Status BB", "Status Akuisisi", "Risiko"]
            kolom_berwarna_aktual = [col for col in kolom_berwarna if col in df_tampil.columns]

            # --- MENAMBAHKAN SUPPORT DAN RESISTANCE KE FORMAT ANGKA ---
            tabel_akhir = df_tampil.style.format({
                "Harga (Rp)": format_angka,
                "Harga MA20": format_angka,
                "Support": format_angka,
                "Resistance": format_angka,
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

    # ----------------------------------------
    # ISI TAB 3: INSIGHT & EDUKASI
    # ----------------------------------------
    with tab3:
        st.markdown("### 📚 Panduan Membaca Screener")
        st.info("Gunakan panduan di bawah ini untuk memahami setiap metrik yang digunakan dalam AlgoTrade Screener.")
        
        st.markdown("""
        * **Support & Resistance:** 
          * **Support:** Area batas bawah historis (20 hari terakhir). Sering digunakan sebagai acuan titik pantul atau area *cutloss*.
          * **Resistance:** Area batas atas historis (20 hari terakhir). Sering digunakan sebagai target *Take Profit*.
        * **Risiko (Tingkat Volatilitas):** Diukur menggunakan lebar pita *Bollinger Bands*.
          * **Tinggi (Merah):** Pergerakan harga sangat liar dan cepat (berisiko tinggi namun potensi cuan besar).
          * **Sedang (Kuning):** Pergerakan harga normal dan stabil.
          * **Rendah (Hijau):** Pergerakan harga sangat sempit, berisiko rendah namun cenderung lambat (konsolidasi).
        * **RSI (14D) - Relative Strength Index:** Mengukur kecepatan dan perubahan pergerakan harga. 
          * **> 50 (Bullish):** Momentum sedang naik, bagus untuk mencari peluang beli.
          * **<= 50 (Bearish):** Momentum sedang turun atau lemah.
        * **Tren (MA20):** Membandingkan harga saat ini dengan harga rata-rata 20 hari ke belakang. 
          * **Uptrend:** Harga saat ini di atas MA20. Tren secara umum positif.
          * **Downtrend:** Harga saat ini di bawah MA20. Sebaiknya dihindari.
        * **Bollinger Bands:** Mengukur volatilitas pasar.
          * **Squeeze:** Pita menyempit. Sering kali menjadi pertanda akan ada pergerakan harga yang sangat besar (breakout).
          * **Breakout Upper:** Harga menembus pita atas. Menandakan pergerakan *bullish* yang sangat kuat.
          * **Bottom Rebound:** Harga memantul dari pita bawah. Peluang untuk *buy on weakness*.
        * **Vol Breakout (Tembus MA20):** Menandakan volume transaksi hari ini lebih tinggi daripada rata-rata volume 20 hari terakhir. Ini adalah konfirmasi penting bahwa kenaikan harga didukung oleh minat beli (uang) yang riil.
        * **Total Score:** Skor penilaian dari algoritma (Maksimal 4). Saham yang mendapat skor 4 memiliki momentum, tren, volume, dan RSI yang positif secara bersamaan (Sinyal BELI).
        """)