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
# 2. DEFINISI MASTER INDIKATOR (UNTUK SINKRONISASI OTOMATIS)
# ==========================================
# Jika di kemudian hari Anda ingin menambah filter baru, CUKUP TAMBAHKAN di dalam dictionary MASTER_FILTERS ini.
# Sidebar dan Panel Utama akan otomatis mendeteksi dan menambahkannya ke layar.
MASTER_FILTERS = {
    "Vol Breakout": {"label": "🔊 Volume", "options": ["Semua", "Tembus MA20", "Normal"]},
    "RSI (14D)": {"label": "📊 RSI (14D)", "options": ["Semua", "> 50 (Bullish)", "<= 50 (Bearish)"]},
    "MA Signal": {"label": "📈 Tren (MA20)", "options": ["Semua", "Uptrend", "Downtrend"]},
    "Momentum": {"label": "⚡ Momentum", "options": ["Semua", "Positif", "Negatif"]},
    "Total Score": {"label": "⭐ Total Score", "options": ["Semua", 6, 5, 4, 3, 2, 1, 0]},
    "Rekomendasi": {"label": "🎯 Rekomendasi", "options": ["Semua", "BELI", "WAIT & SEE"]},
    "Likuiditas": {"label": "💧 Likuiditas", "options": ["Semua", "> 1 Miliar", "< 1 Miliar"]},
    "Status BB": {"label": "🌐 Bollinger Bands", "options": ["Semua", "Squeeze", "Bottom Rebound", "Breakout Upper", "Normal"]},
    "MA Cross": {"label": "🔀 MA Cross (5/20)", "options": ["Semua", "Golden Cross", "Bullish", "Death Cross", "Bearish"]},
    "Risiko": {"label": "⚠️ Risiko Volatilitas", "options": ["Semua", "Tinggi", "Sedang", "Rendah"]},
    "Status Akuisisi": {"label": "🤝 Sentimen Akuisisi", "options": ["Semua", "TIDAK ADA", "RENCANA AKUISISI", "DALAM AKUISISI"]},
    "MACD": {"label": "📈 MACD", "options": ["Semua", "Strong Bullish", "Bullish MACD", "Strong Bearish", "Bearish MACD"]}
}

# ==========================================
# 3. SIDEBAR - SISTEM PRESET FILTER CEPAT CUSTOM DINAMIS
# ==========================================
st.sidebar.title("⚙️ Preset Filter Cepat")
st.sidebar.markdown("Pilih preset kriteria bawaan atau aktifkan kriteria kustom Anda sendiri.")

# Inisialisasi session state untuk menyimpan preset bawaan (Default)
if 'custom_presets' not in st.session_state:
    # Membuat preset bawaan yang otomatis mengisi semua komponen di MASTER_FILTERS dengan "Semua"
    base_default = {k: "Semua" for k in MASTER_FILTERS.keys()}
    
    # Customisasi nilai spesifik untuk preset bawaan
    preset_super_ketat = base_default.copy()
    preset_super_ketat.update({"Vol Breakout": "Tembus MA20", "RSI (14D)": "> 50 (Bullish)", "MA Signal": "Uptrend", "Status BB": "Breakout Upper"})
    
    preset_uptrend_likuid = base_default.copy()
    preset_uptrend_likuid.update({"MA Signal": "Uptrend", "Likuiditas": "> 1 Miliar"})

    st.session_state.custom_presets = {
        "🔥 Super Ketat (Swing Trading)": preset_super_ketat,
        "🟢 Hanya Saham Uptrend & Likuid": preset_uptrend_likuid
    }

opsi_preset = ["Matikan Preset (Manual)"] + list(st.session_state.custom_presets.keys())
preset_terpilih = st.sidebar.selectbox("🎯 Pilih Preset Aktif:", opsi_preset)

st.sidebar.markdown("---")

# AUTOMATED FILTER CREATOR (Mengikuti MASTER_FILTERS secara otomatis)
with st.sidebar.expander("➕ Buat Preset Sendiri Kustom"):
    st.caption("Atur kombinasi kriteria di bawah ini lalu simpan ke sistem.")
    nama_preset_baru = st.text_input("Nama Preset Anda:", placeholder="Contoh: Akumulasi Uang Besar")
    
    # Loop otomatis memunculkan pilihan dropdown di sidebar berdasarkan MASTER_FILTERS
    kustom_input_user = {}
    for key, info in MASTER_FILTERS.items():
        kustom_input_user[key] = st.selectbox(f"P-{info['label']}", info['options'], key=f"sidebar_{key}")
    
    if st.button("💾 Simpan Jadi Preset Cepat"):
        if nama_preset_baru.strip():
            st.session_state.custom_presets[nama_preset_baru.strip()] = kustom_input_user
            st.success(f"Preset '{nama_preset_baru}' disimpan! Silakan pilih di menu atas.")
        else:
            st.error("Nama preset tidak boleh kosong!")

st.sidebar.markdown("---")
st.sidebar.caption("© AlgoTrade Screener")

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
    
    tab1, tab2, tab3 = st.tabs(["📊 Ringkasan Pasar", "🎯 Screener Utama", "💡 Insight & Edukasi"])
    
    # ----------------------------------------
    # ISI TAB 1: RINGKASAN PASAR
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
                height=450 
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_chart2:
            df_top15 = df_hasil.nlargest(15, 'Change (%)').iloc[::-1]
            
            fig_bar = px.bar(
                df_top15, 
                x='Change (%)', 
                y='Ticker', 
                orientation='h', 
                color='Change (%)', 
                color_continuous_scale=['#86efac', '#22c55e', '#166534']
            )
            fig_bar.update_traces(
                texttemplate='%{x:.0f}%',
                textposition='outside'
            )
            fig_bar.update_layout(
                title_text='Top 15 Saham Gainers Hari Ini (Stockbit Style)', 
                margin=dict(t=40, b=20, l=40, r=40), 
                showlegend=False,
                xaxis_title="Perubahan (%)",
                yaxis_title="Kode Saham",
                height=450 
            )
            if not df_top15.empty:
                fig_bar.update_xaxes(range=[0, df_top15['Change (%)'].max() * 1.2]) 
                
            st.plotly_chart(fig_bar, use_container_width=True)

    # ----------------------------------------
    # ISI TAB 2: SCREENER UTAMA (FILTER & TABEL)
    # ----------------------------------------
    with tab2:
        use_preset = preset_terpilih != "Matikan Preset (Manual)"
        vals = st.session_state.custom_presets[preset_terpilih] if use_preset else None

        # RENDER PANEL FILTER SECARA DINAMIS & OTOMATIS BERDASARKAN MASTER_FILTERS
        with st.expander("🎛️ Buka Panel Filter Lengkap (Klik untuk menyesuaikan kriteria)", expanded=False):
            # Membagi area filter menjadi susunan 3 kolom seimbang
            col_f1, col_f2, col_f3 = st.columns(3)
            
            filter_terpilih_tabel = {}
            
            # Mendistribusikan ke-12 filter secara merata ke dalam 3 kolom layout
            for idx, (db_key, info) in enumerate(MASTER_FILTERS.items()):
                target_col = col_f1 if idx % 3 == 0 else (col_f2 if idx % 3 == 1 else col_f3)
                
                with target_col:
                    default_idx = info["options"].index(vals[db_key]) if use_preset else 0
                    filter_terpilih_tabel[db_key] = st.selectbox(
                        info["label"], 
                        info["options"], 
                        index=default_idx, 
                        key=f"main_{db_key}"
                    )

        st.markdown("### 📋 Tabel Data Saham")
        col_search, col_empty = st.columns([1, 2])
        with col_search:
            search_ticker = st.text_input("🔍 Cari Kode Saham Spesifik (Contoh: BBCA, BMRI)", "", placeholder="Ketik kode...")

        # LOGIKA FILTERING DATA OTOMATIS BERDASARKAN SELECTION USER
        df_filtered = df_hasil.copy()
        
        if search_ticker: 
            df_filtered = df_filtered[df_filtered["Ticker"].str.contains(search_ticker.upper(), na=False)]
            
        for db_key, nilai_filter in filter_terpilih_tabel.items():
            if nilai_filter != "Semua":
                if db_key == "RSI (14D)":
                    if nilai_filter == "> 50 (Bullish)": df_filtered = df_filtered[df_filtered["RSI (14D)"] > 50]
                    elif nilai_filter == "<= 50 (Bearish)": df_filtered = df_filtered[df_filtered["RSI (14D)"] <= 50]
                elif db_key == "Total Score":
                    df_filtered = df_filtered[df_filtered["Total Score"] == int(nilai_filter)]
                else:
                    if db_key in df_filtered.columns:
                        df_filtered = df_filtered[df_filtered[db_key] == nilai_filter]

        # PAGINASI & FORMAT TABEL
        if not df_filtered.empty:
            col_pg1, col_pg2, col_pg3 = st.columns([1, 1, 2])
            with col_pg1: saham_per_halaman = st.selectbox("Tampilkan baris:", [20, 50, 100])
            total_halaman = int(np.ceil(len(df_filtered) / saham_per_halaman))
            with col_pg2:
                halaman_aktif = st.selectbox("Pilih Halaman:", range(1, total_halaman + 1)) if total_halaman > 0 else 1
                    
            indeks_awal = (halaman_aktif - 1) * saham_per_halaman
            indeks_akhir = indeks_awal + saham_per_halaman
            df_tampil = df_filtered.iloc[indeks_awal:indeks_akhir].copy()
            
            def format_skor_bintang_bersih(score):
                if pd.isna(score) or int(score) == 0: return "-"
                return "⭐" * int(score)

            def format_persen_ikon(val):
                if pd.isna(val): return "-"
                ikon = "🔺 " if val > 0 else ("🔻 " if val < 0 else "")
                return f"{ikon}{val:+.2f}%"

            def format_momentum_ikon(val):
                if val == "Positif": return "🔺 Positif"
                if val == "Negatif": return "🔻 Negatif"
                return val

            df_tampil["Total Score"] = df_tampil["Total Score"].apply(format_skor_bintang_bersih)
            
            def format_angka(val): 
                if pd.isna(val): return "-"
                return f"{int(val):,}".replace(",", ".")
            
            def warna_tabel(val):
                style = '' 
                if isinstance(val, str):
                    if any(x in val for x in ["Positif", "Uptrend", "BELI", "Breakout Upper", "Bottom Rebound", "DALAM AKUISISI", "Rendah", "🔺", "Golden Cross", "Bullish", "Tembus MA20"]): 
                        style = 'color: #22c55e; font-weight: 600;'
                    elif any(x in val for x in ["Negatif", "Downtrend", "WAIT & SEE", "Tinggi", "🔻", "Death Cross", "Bearish"]): 
                        style = 'color: #ef4444; font-weight: 600;'
                    elif val == "> 1 Miliar": 
                        style = 'color: #3b82f6; font-weight: 600;'
                    elif val in ["Squeeze", "RENCANA AKUISISI", "Sedang"]: 
                        style = 'color: #eab308; font-weight: 600;'
                    elif "⭐" in val:
                        if len(val) >= 4: style = 'color: #22c55e;'
                        else: style = 'color: #ef4444;'
                return style

            kolom_berwarna = ["Change (%)", "Momentum", "MA Signal", "MA Cross", "MACD", "Rekomendasi", "Likuiditas", "Status BB", "Status Akuisisi", "Risiko", "Total Score", "Vol Breakout"]
            kolom_berwarna_aktual = [col for col in kolom_berwarna if col in df_tampil.columns]

            tabel_akhir = df_tampil.style.format({
                "Harga (Rp)": format_angka,
                "Harga MA20": format_angka,
                "Support": format_angka,
                "Resistance": format_angka,
                "Volume": format_angka,
                "Change (%)": format_persen_ikon,
                "Momentum": format_momentum_ikon,
                "RSI (14D)": "{:.0f}"
            }).map(warna_tabel, subset=kolom_berwarna_aktual)

            urutan_kolom_tetap = [
                "Ticker", "Harga (Rp)", "Harga MA20", "Support", "Resistance", "Change (%)", 
                "Volume", "Vol Breakout", "RSI (14D)", "Momentum", "MA Signal", "MA Cross", "MACD",
                "Status BB", "Risiko", "Likuiditas", "Total Score", "Rekomendasi", "Status Akuisisi", "Terakhir Update"
            ]
            kolom_tersedia = [col for col in urutan_kolom_tetap if col in df_tampil.columns]

            st.dataframe(
                tabel_akhir, 
                use_container_width=True, 
                hide_index=True,
                column_order=kolom_tersedia
            )
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
        * **MA Cross (5/20):** 
          * **Golden Cross:** Rata-rata harga 5 hari memotong ke atas 20 hari. Sinyal kuat untuk mulai mengakumulasi (beli).
          * **Death Cross:** Rata-rata harga 5 hari memotong ke bawah 20 hari. Sinyal untuk waspada atau jual.
        * **MACD (Moving Average Convergence Divergence):**
          * **Strong Bullish / Bullish MACD:** Histogram MACD berada di atas garis sinyal, mengonfirmasi tren naik (*uptrend*) memiliki tenaga yang kuat.
        * **Support & Resistance:** 
          * **Support:** Area batas bawah historis (20 hari terakhir). Sering digunakan sebagai acuan titik pantul atau area *cutloss*.
          * **Resistance:** Area batas atas historis (20 hari terakhir). Sering digunakan sebagai target *Take Profit*.
        * **Risiko (Tingkat Volatilitas):** Diukur menggunakan lebar pita *Bollinger Bands*.
          * **Tinggi (Merah):** Pergerakan harga liar dan cepat.
          * **Rendah (Hijau):** Pergerakan harga sempit, berisiko rendah namun cenderung lambat (konsolidasi).
        * **Vol Breakout (Tembus MA20):** 
          * **Tembus MA20 (Hijau):** **SANGAT BAIK.** Menandakan volume transaksi melonjak tajam melampaui rata-rata bulanan, mengonfirmasi saham digerakkan oleh akumulasi dana besar (*Smart Money*).
          * **Normal (Putih):** Aktivitas transaksi berjalan wajar seperti biasa.
        * **Total Score (Maks 6 ⭐):** Saham dengan skor 5 ke atas mendapatkan rekomendasi **BELI**.
        """)