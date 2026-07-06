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
# FITUR TAMBAHAN: SIDEBAR WATCHLIST PRIBADI
# ==========================================
FILE_WATCHLIST = "watchlist_pribadi.txt"

def baca_watchlist():
    if not os.path.exists(FILE_WATCHLIST):
        with open(FILE_WATCHLIST, "w") as f:
            pass
        return []
    with open(FILE_WATCHLIST, "r") as f:
        return [baris.strip().upper() for baris in f if baris.strip()]

def simpan_watchlist(daftar_saham):
    with open(FILE_WATCHLIST, "w") as f:
        for saham in set(daftar_saham): 
            f.write(saham + "\n")

# Membangun antarmuka di Sidebar
st.sidebar.markdown("### 📌 Watchlist Anda")
watchlist_saat_ini = baca_watchlist()

saham_baru = st.sidebar.text_input("Tambah Saham (Cth: BBCA):").upper()
if st.sidebar.button("➕ Tambah"):
    if saham_baru and saham_baru not in watchlist_saat_ini:
        watchlist_saat_ini.append(saham_baru)
        simpan_watchlist(watchlist_saat_ini)
        st.sidebar.success("Masuk daftar!")
        st.rerun()

st.sidebar.markdown("---")

if watchlist_saat_ini:
    st.sidebar.write("Saham Tersimpan:")
    for saham in watchlist_saat_ini:
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            st.sidebar.write(f"**{saham}**")
        with col2:
            if st.sidebar.button("❌", key=f"hapus_{saham}", help="Hapus dari watchlist"):
                watchlist_saat_ini.remove(saham)
                simpan_watchlist(watchlist_saat_ini)
                st.rerun()
else:
    st.sidebar.info("Belum ada saham.")

# ==========================================
# 2. MEMUAT DATA LOKAL (DENGAN LIVE MARKET UPDATER)
# ==========================================
FILE_HASIL = "hasil_screener.csv"
SCRIPT_UPDATER = "update_data.py" # Sesuaikan dengan nama script backend Anda

import subprocess

# Fungsi untuk menjalankan script update_data.py dan membaca hasilnya
def muat_ulang_data(jalankan_script=False):
    # Jika dipicu tombol refresh, jalankan script backend terlebih dahulu
    if jalankan_script:
        with st.spinner("🔄 Mengambil data live market terbaru... Mohon tunggu..."):
            try:
                # Menjalankan script update_data.py secara otomatis di background
                subprocess.run(["python", SCRIPT_UPDATER], check=True)
                st.toast("Data live market berhasil diperbarui!", icon="✅")
            except Exception as e:
                st.error(f"⚠️ Gagal memperbarui data otomatis: {e}")
    
    # Baca file CSV hasil update
    if os.path.exists(FILE_HASIL):
        st.session_state['df_hasil'] = pd.read_csv(FILE_HASIL)
        waktu_modifikasi = os.path.getmtime(FILE_HASIL)
        st.session_state['waktu_terakhir'] = datetime.fromtimestamp(waktu_modifikasi).strftime('%Y-%m-%d %H:%M:%S')
    else:
        st.session_state['df_hasil'] = pd.DataFrame()
        st.session_state['waktu_terakhir'] = None

# Inisialisasi data saat aplikasi pertama kali dibuka (tanpa jalankan script biar cepat)
if 'df_hasil' not in st.session_state:
    muat_ulang_data(jalankan_script=False)

# Membuat layout info data dan tombol refresh
col_info, col_btn = st.columns([4, 1])

with col_info:
    if st.session_state['df_hasil'] is not None and not st.session_state['df_hasil'].empty:
        st.success(f"💾 Data saat ini: **{st.session_state['waktu_terakhir']}** (Gunakan tombol di samping untuk fetch data live market terbaru)")
    else:
        st.error(f"❌ File '{FILE_HASIL}' belum ditemukan! Silakan jalankan script `{SCRIPT_UPDATER}` terlebih dahulu.")

with col_btn:
    # Tombol refresh sekarang akan memicu jalankan_script=True
    if st.button("🔄 Refresh Data", use_container_width=True):
        muat_ulang_data(jalankan_script=True)
        st.rerun()

# Menghubungkan ke variabel utama Anda
df_hasil = st.session_state['df_hasil']

# ==========================================
# 4. DASHBOARD RINGKASAN & FILTER 
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
    search_ticker = st.text_input("🔍 Cari Kode Saham Spesifik (Contoh: BBCA, BMRI)", "")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: filter_vol = st.selectbox("🔊 1. Volume", ["Semua", "Tembus MA20", "Normal"])
    with col2: filter_rsi = st.selectbox("📊 2. RSI (14D)", ["Semua", "> 50 (Bullish)", "<= 50 (Bearish)"])
    with col3: filter_trend = st.selectbox("📈 3. Tren (MA20)", ["Semua", "Uptrend", "Downtrend"])
    with col4: filter_momentum = st.selectbox("⚡ 4. Momentum", ["Semua", "Positif", "Negatif"])

    st.write("") 
    col5, col6, col7 = st.columns(3)
    with col5: filter_score = st.selectbox("⭐ Total Score", ["Semua", 4, 3, 2, 1, 0])
    with col6: filter_rekomendasi = st.selectbox("🎯 Rekomendasi", ["Semua", "BELI", "WAIT & SEE"])
    with col7: filter_likuiditas = st.selectbox("💧 Likuiditas", ["Semua", "> 1 Miliar", "< 1 Miliar"])

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

    # ==========================================
    # 5. PAGINASI & FORMAT TABEL
    # ==========================================
    if not df_filtered.empty:
        st.markdown("### Hasil Penapisan (Screener)")
        
        # Fitur Baru: Dropdown jumlah baris dan pilihan halaman disejajarkan
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
                if val in ["Positif", "Uptrend", "BELI"]: style = 'color: #22c55e; font-weight: 600;'
                elif val in ["Negatif", "Downtrend", "WAIT & SEE"]: style = 'color: #ef4444; font-weight: 600;'
                elif val == "> 1 Miliar": style = 'color: #3b82f6; font-weight: 600;'
            return style

        kolom_berwarna = ["Change (%)", "Momentum", "MA Signal", "Rekomendasi", "Likuiditas"]

        tabel_akhir = df_tampil.style.format({
            "Harga (Rp)": format_angka,
            "Volume": format_angka,
            "Change (%)": format_persen,
            "RSI (14D)": "{:.0f}"
        }).map(warna_tabel, subset=kolom_berwarna)

        # Menghapus height=750 agar tinggi tabel dinamis menyesuaikan baris
        st.dataframe(tabel_akhir, use_container_width=True, hide_index=True)

        # ==========================================
        # FITUR: SIMPAN CEPAT KE WATCHLIST
        # ==========================================
        st.markdown("---")
        st.markdown("#### ⭐ Simpan Cepat ke Watchlist")
        
        pilihan_saham = st.selectbox("Pilih saham dari tabel di atas untuk dipantau:", ["- Pilih Saham -"] + list(df_filtered["Ticker"]))
        
        if st.button("Simpan ke Watchlist 📌"):
            if pilihan_saham != "- Pilih Saham -":
                watchlist_sekarang = baca_watchlist()
                if pilihan_saham not in watchlist_sekarang:
                    watchlist_sekarang.append(pilihan_saham)
                    simpan_watchlist(watchlist_sekarang)
                    st.success(f"Berhasil! {pilihan_saham} sudah ditambahkan ke menu Sidebar.")
                else:
                    st.warning(f"{pilihan_saham} sudah ada di Watchlist Anda.")
                    
        st.caption(f"Menampilkan urutan {(indeks_awal + 1)} - {min(indeks_akhir, len(df_filtered))} dari total {len(df_filtered)} saham yang lolos filter.")
    else:
        st.warning("Tidak ada saham yang memenuhi kriteria filter Anda saat ini.")

# ==========================================
# 6. TABEL KHUSUS WATCHLIST (DATA LENGKAP & BERWARNA)
# ==========================================
st.markdown("---")
st.markdown("### 🌟 Data Lengkap Watchlist Pribadi Anda")

watchlist_terbaru = baca_watchlist()

if len(watchlist_terbaru) > 0 and not df_hasil.empty:
    df_watchlist = df_hasil[df_hasil['Ticker'].isin(watchlist_terbaru)]
    
    def pewarnaan_tabel_watchlist(val):
        if isinstance(val, str):
            if val in ["Uptrend", "Positif", "BELI", "Tembus MA20"]:
                return "color: #4ade80; font-weight: bold;" 
            elif val in ["Downtrend", "Negatif"]:
                return "color: #f87171; font-weight: bold;" 
            elif val == "WAIT & SEE":
                return "color: #fbbf24; font-weight: bold;" 
        elif isinstance(val, (int, float)) and val < 0:
            return "color: #f87171; font-weight: bold;" 
        return "" 

    try:
        tabel_watchlist_cantik = df_watchlist.style.map(pewarnaan_tabel_watchlist).format({
            "Harga (Rp)": "{:,.0f}",
            "Volume": "{:,.0f}",
            "Change (%)": "{:.2f}%",
            "RSI (14D)": "{:.0f}"
        })
    except AttributeError:
        tabel_watchlist_cantik = df_watchlist.style.applymap(pewarnaan_tabel_watchlist).format({
            "Harga (Rp)": "{:,.0f}",
            "Volume": "{:,.0f}",
            "Change (%)": "{:.2f}%",
            "RSI (14D)": "{:.0f}"
        })

    st.dataframe(tabel_watchlist_cantik, use_container_width=True, hide_index=True)
else:
    st.info("📌 Watchlist Anda masih kosong. Silakan tambahkan saham melalui panel di atas atau dari menu samping (Sidebar).")