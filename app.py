import streamlit as st
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
import plotly.express as px

# ==========================================
# SECTION 1: PENGATURAN UI/UX & FILE EKSTERNAL
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
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0px 0px; padding: 10px 16px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# SECTION 2: AUTO-HEALING KONFIGURASI JSON
# ==========================================
FILE_CONFIG = "config_web.json"
FILE_PRESET = "preset_kustom.json"
FILE_HASIL = "hasil_screener.csv"
FILE_AKUISISI = "data_akuisisi.csv"

DEFAULT_CONFIG = {
    "MASTER_FILTERS": {
        "Kategori": {"label": "🏢 Kategori Saham", "options": ["Semua", "Big Cap (Lapis 1)", "Mid Cap (Lapis 2)", "Small Cap (Lapis 3)"]},
        "Fase Siklus Bandar": {"label": "🔄 Siklus Wyckoff", "options": ["Semua", "Accumulation (Kumpul Barang)", "Mark-Up (Fase Pesta)", "Distribution (Fase Jualan)", "Mark-Down (Fase Runtuh)", "Sideways"]},
        "RVOL (Anomali Vol)": {"label": "🌋 Ledakan Volume", "options": ["Semua", "Ledakan Ekstrem (> 300%)", "Anomali Tinggi (150-300%)", "Normal (50-150%)", "Sepi (< 50%)"]},
        "Karakter Gorengan": {"label": "🕵️ Karakter Saham", "options": ["Semua", "Spesialis Tiang Jemuran (Banting Pucuk)", "Solid (Jarang Dibanting)", "Normal"]},
        "Kelas Transaksi": {"label": "💸 Kelas Transaksi", "options": ["Semua", "Sultan (> 50M/hari)", "Ritel Aktif (5M - 50M)", "Gorengan Sepi (< 5M)"]},
        "Posisi VWAP": {"label": "⚖️ Posisi thd VWAP", "options": ["Semua", "Di Atas VWAP (Kuat)", "Di Bawah VWAP (Lemah)", "Persis di VWAP"]},
        "Kekuatan A/D": {"label": "🧠 Smart Money (A/D)", "options": ["Semua", "Akumulasi Pro (Smart Money)", "Distribusi Pro (Guyuran)", "Netral"]},
        "Status Bandar": {"label": "🕵️ Status Bandar", "options": ["Semua", "Akumulasi Kuat", "Distribusi Kuat", "Normal"]},
        "Tekanan Bandar": {"label": "⚔️ Tekanan Harian", "options": ["Semua", "Dominan Beli (Hajar Kanan)", "Dominan Jual (Guyur)", "Seimbang / Adu Mekanik"]},
        "Valuasi": {"label": "💎 Valuasi", "options": ["Semua", "Undervalued (Murah)", "Fair Value (Wajar)", "Overvalued (Mahal)"]},
        "Posisi Entry": {"label": "🎯 Jarak ke Support", "options": ["Semua", "Dekat Support (Low Risk)", "Area Tengah", "Rawan Pucuk (High Risk)"]},
        "Total Score": {"label": "⭐ Total Score", "options": ["Semua", 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]},
        "Rekomendasi": {"label": "🎯 Rekomendasi", "options": ["Semua", "BELI", "WAIT & SEE"]},
        "MA Signal": {"label": "📈 Tren (MA20)", "options": ["Semua", "Uptrend", "Downtrend"]}
    },
    "KAMUS_EDUKASI": {
        "Fase Siklus Bandar": "Pendekatan Wyckoff (MA20 vs MA50). 'Accumulation' = fase persiapan naik. 'Mark-Up' = sedang uptrend kuat.",
        "RVOL (Anomali Vol)": "Relative Volume. Membandingkan volume hari ini terhadap rata-rata 10 hari. Angka ekstrem mengindikasikan aksi bandar masif.",
        "Karakter Gorengan": "Mendeteksi seberapa sering saham ini dibanting dari pucuk (membuat ekor atas panjang) dalam 20 hari terakhir. Jika sering, waspada jebakan batman.",
        "Kelas Transaksi": "Rata-rata nilai transaksi harian dalam 5 hari terakhir. Menghindari saham tidak likuid.",
        "Posisi VWAP": "Harga rata-rata bandar berdasar volume. Jika harga di atas VWAP, buyer memegang kendali.",
        "Kekuatan A/D": "Deteksi uang pintar dari bentuk candle. Menghitung apakah penutupan selalu ditarik ke atas (akumulasi)."
    },
    "STRATEGI": {
        "1. Pemburu Gorengan (Super Fast Trade)": "Gunakan tab Screener Utama, filter: RVOL = 'Ledakan Ekstrem (> 300%)', Karakter = 'Spesialis Tiang Jemuran'. Beli sangat pagi, pantau bid-offer, JUAL sebelum istirahat siang. Jangan serakah!",
        "2. Swing Trading Aman (Follow the Trend)": "Gunakan filter: Fase Siklus = 'Mark-Up', Kekuatan A/D = 'Akumulasi Pro', Posisi VWAP = 'Di Atas VWAP'.",
        "3. Early Reversal (Beli di Bawah)": "Filter Fase Siklus = 'Accumulation', dipadukan dengan Posisi Entry = 'Dekat Support (Low Risk)'."
    }
}

if not os.path.exists(FILE_CONFIG):
    with open(FILE_CONFIG, "w") as f: json.dump(DEFAULT_CONFIG, f, indent=4)
else:
    with open(FILE_CONFIG, "r") as f: cek_config = json.load(f)
    if "RVOL (Anomali Vol)" not in cek_config.get("MASTER_FILTERS", {}):
        with open(FILE_CONFIG, "w") as f: json.dump(DEFAULT_CONFIG, f, indent=4)

with open(FILE_CONFIG, "r") as f:
    WEB_CONFIG = json.load(f)

MASTER_FILTERS = WEB_CONFIG["MASTER_FILTERS"]
KAMUS_EDUKASI = WEB_CONFIG["KAMUS_EDUKASI"]
STRATEGI_SIMULASI = WEB_CONFIG["STRATEGI"]

# ==========================================
# SECTION 3: DATABASE PRESET & LOAD DATA
# ==========================================
def muat_preset():
    preset_bawaan = {
        "🔥 Gorengan Aktif (High Risk)": {k: "Semua" for k in MASTER_FILTERS},
        "🟢 Swing Wyckoff Cuan": {k: "Semua" for k in MASTER_FILTERS}
    }
    preset_bawaan["🔥 Gorengan Aktif (High Risk)"].update({"Kategori": "Small Cap (Lapis 3)", "RVOL (Anomali Vol)": "Ledakan Ekstrem (> 300%)", "Tekanan Bandar": "Dominan Beli (Hajar Kanan)"})
    preset_bawaan["🟢 Swing Wyckoff Cuan"].update({"Fase Siklus Bandar": "Mark-Up (Fase Pesta)", "Kekuatan A/D": "Akumulasi Pro (Smart Money)", "MA Signal": "Uptrend"})

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

# ==========================================
# SECTION 4: HEADER & SIDEBAR
# ==========================================
if st.sidebar.button("🔄 Muat Ulang Data Server", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.title("⚙️ Preset Filter Cepat")
opsi_preset = ["Matikan Preset (Manual)"] + list(daftar_preset_aktif.keys())
idx_default = opsi_preset.index(st.session_state.preset_selector) if st.session_state.preset_selector in opsi_preset else 0
st.sidebar.selectbox("🎯 Pilih Preset Aktif:", opsi_preset, index=idx_default, key="preset_selector", on_change=apply_preset)

with st.sidebar.expander("➕ Buat Preset Sendiri Kustom"):
    nama_preset_baru = st.text_input("Nama Preset Anda:", placeholder="Contoh: Pemburu Tiang Jemuran")
    kustom_input = {k: st.selectbox(f"P-{info['label']}", info['options'], key=f"sidebar_{k}") for k, info in MASTER_FILTERS.items()}
    if st.button("💾 Simpan Jadi Preset"):
        if nama_preset_baru.strip():
            k_lama = {}
            if os.path.exists(FILE_PRESET):
                with open(FILE_PRESET, "r") as f: k_lama = json.load(f)
            k_lama[nama_preset_baru.strip()] = kustom_input
            with open(FILE_PRESET, "w") as f: json.dump(k_lama, f, indent=4)
            for k in MASTER_FILTERS: st.session_state[f"main_{k}"] = kustom_input[k]
            st.session_state.preset_selector = nama_preset_baru.strip()
            st.success(f"Preset Disimpan!")
            st.rerun()

st.sidebar.markdown("---")
st.title("⚡ AlgoTrade Screener - IHSG Ultimate")
st.markdown("Detektor Jejak Bandar, Anomali Volume, & Strategi Fast Trade Pagi.")
st.markdown("---")

df_hasil = load_data_saham()

# ==========================================
# SECTION 5: FUNGSI PEWARNAAN
# ==========================================
def format_skor(s): return "⭐" * int(s) if pd.notna(s) and int(s) > 0 else "-"
def format_pct(v): return f"{'▲ ' if v > 0 else '▼ '}{v:+.2f}%" if v != 0 else "0.00%"
def format_mom(v): return "▲ Positif" if v == "Positif" else ("▼ Negatif" if v == "Negatif" else v)
def format_desimal(v): return f"{v:.2f}" if pd.notna(v) and v != 0 else "-"
def format_angka(v): return f"{int(v):,}".replace(",", ".") if pd.notna(v) else "-"

def warna_tabel(val):
    if isinstance(val, (int, float)): 
        return 'color: #22c55e; font-weight: 600;' if val > 0 else ('color: #ef4444; font-weight: 600;' if val < 0 else '')
    elif isinstance(val, str):
        if any(x in val for x in ["Positif", "Uptrend", "BELI", "Breakout Upper", "Bottom Rebound", "DALAM AKUISISI", "Rendah", "▲", "Golden Cross", "Bullish", "Tembus MA20", "Akumulasi", "Big Cap", "Gap Up", "Dominan Beli", "Undervalued", "Marubozu", "Dekat Support", "Hammer", "Di Atas VWAP", "Sultan", "Ledakan Ekstrem", "Solid", "Mark-Up"]): 
            return 'color: #22c55e; font-weight: 600;'
        elif any(x in val for x in ["Negatif", "Downtrend", "WAIT & SEE", "Tinggi", "▼", "Death Cross", "Bearish", "Distribusi", "Small Cap", "Gap Down", "Dominan Jual", "Overvalued", "Rawan Pucuk", "Di Bawah VWAP", "Gorengan Sepi", "Sepi", "Tiang Jemuran", "Mark-Down"]): 
            return 'color: #ef4444; font-weight: 600;'
        elif val == "> 1 Miliar": 
            return 'color: #3b82f6; font-weight: 600;'
        elif any(x in val for x in ["Squeeze", "RENCANA AKUISISI", "Sedang", "Mid Cap", "Seimbang", "Fair Value", "Area Tengah", "Doji", "Ritel Aktif", "Anomali", "Accumulation"]): 
            return 'color: #eab308; font-weight: 600;'
        elif "⭐" in val: 
            return 'color: #22c55e;' if len(val) >= 6 else 'color: #ef4444;'
    return ''

# ==========================================
# SECTION 6: RENDER TABS
# ==========================================
if not df_hasil.empty:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Ringkasan Pasar", "🎯 Screener Utama", "💡 Insight & Edukasi", "📈 Simulasi & Strategi", "🦅 Radar Bandar (Fast Trade)"])
    
    with tab1:
        total = len(df_hasil)
        beli = len(df_hasil[df_hasil['Rekomendasi'] == 'BELI'])
        uptrend = len(df_hasil[df_hasil['Fase Siklus Bandar'] == 'Mark-Up (Fase Pesta)']) if 'Fase Siklus Bandar' in df_hasil.columns else 0
        
        m1, m2, m3 = st.columns(3)
        m1.markdown(f"<div class='metric-container'><h3>🔍 Total Saham</h3><h2>{total}</h2></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-container'><h3>🎯 Sinyal BELI</h3><h2 style='color: #4ade80;'>{beli}</h2></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-container'><h3>🚀 Di Fase Pesta (Mark-Up)</h3><h2 style='color: #60a5fa;'>{uptrend}</h2></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        c1, c2 = st.columns([1, 2])
        with c1:
            df_rek = df_hasil['Rekomendasi'].value_counts().reset_index()
            df_rek.columns = ['Rekomendasi', 'Jumlah']
            fig_pie = px.pie(df_rek, names='Rekomendasi', values='Jumlah', hole=0.5, color='Rekomendasi', color_discrete_map={'BELI': '#22c55e', 'WAIT & SEE': '#ef4444'})
            st.plotly_chart(fig_pie, use_container_width=True)
        with c2:
            df_top = df_hasil.nlargest(15, 'Change (%)').iloc[::-1]
            fig_bar = px.bar(df_top, x='Change (%)', y='Ticker', orientation='h', color='Change (%)', color_continuous_scale=['#86efac', '#22c55e', '#166534'])
            fig_bar.update_traces(texttemplate='%{x:.0f}%', textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        with st.expander("🎛️ Buka Panel Filter Lengkap", expanded=False):
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            filter_terpilih = {}
            for idx, (db_key, info) in enumerate(MASTER_FILTERS.items()):
                target_col = col_f1 if idx % 4 == 0 else (col_f2 if idx % 4 == 1 else (col_f3 if idx % 4 == 2 else col_f4))
                with target_col:
                    val_sekarang = st.session_state.get(f"main_{db_key}", info["options"][0])
                    idx_opsi = info["options"].index(val_sekarang) if val_sekarang in info["options"] else 0
                    filter_terpilih[db_key] = st.selectbox(info["label"], info["options"], index=idx_opsi, key=f"main_{db_key}", on_change=manual_override)

        col_search, _ = st.columns([1, 2])
        with col_search: search_ticker = st.text_input("🔍 Cari Kode Saham", "", placeholder="Contoh: BBCA")

        df_filtered = df_hasil.copy()
        if search_ticker: df_filtered = df_filtered[df_filtered["Ticker"].str.contains(search_ticker.upper(), na=False)]
        
        for db_key, nilai in filter_terpilih.items():
            if nilai != "Semua":
                if db_key == "RSI (14D)":
                    df_filtered = df_filtered[df_filtered["RSI (14D)"] > 50] if "Bullish" in nilai else df_filtered[df_filtered["RSI (14D)"] <= 50]
                elif db_key == "Total Score":
                    df_filtered = df_filtered[df_filtered["Total Score"] == int(nilai)]
                elif db_key in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered[db_key] == nilai]

        if not df_filtered.empty:
            st.caption(f"Menampilkan **{len(df_filtered)}** saham yang lolos filter dari total **{len(df_hasil)}** saham.")
            
            cp1, cp2, cp3 = st.columns([1, 1, 2])
            with cp1: per_hal = st.selectbox("Tampilkan baris:", [20, 50, 100])
            tot_hal = int(np.ceil(len(df_filtered) / per_hal))
            with cp2: hal_aktif = st.selectbox("Halaman:", range(1, tot_hal + 1)) if tot_hal > 0 else 1
                    
            idx_awal = (hal_aktif - 1) * per_hal
            df_tampil = df_filtered.iloc[idx_awal : idx_awal + per_hal].copy()
            df_tampil["Total Score"] = df_tampil["Total Score"].apply(format_skor)
            
            # URUTAN KOLOM YANG DI-PRIORITASKAN UNTUK MEMANTAU AKSI BANDAR
            urutan = ["Ticker", "RVOL (Anomali Vol)", "Fase Siklus Bandar", "Karakter Gorengan", "Kategori", "Kelas Transaksi", "Harga (Rp)", "Posisi VWAP", "Tekanan Bandar", "Kekuatan A/D", "Status Bandar", "OBV Trend", "Posisi Entry", "Pola Candle", "Change (%)", "Volume", "Status Gap", "Valuasi", "Harga MA20", "RSI (14D)", "Total Score", "Rekomendasi"]
            kolom_ada = [c for c in urutan if c in df_tampil.columns]

            tabel_akhir = df_tampil.style.format({"Harga (Rp)": format_angka, "Harga MA20": format_angka, "Volume": format_angka, "Change (%)": format_pct, "RSI (14D)": "{:.0f}"}).map(warna_tabel, subset=[c for c in kolom_ada if c not in ["Ticker"]])
            
            st.dataframe(tabel_akhir, use_container_width=True, hide_index=True, column_order=kolom_ada)
            
            st.markdown("---")
            col_dl, col_wl = st.columns([1, 1])
            with col_dl:
                csv_filter = df_filtered[kolom_ada].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Hasil Filter (CSV)",
                    data=csv_filter,
                    file_name=f"Screener_Bandar_Hasil_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="dl_tab2"
                )
            with col_wl:
                daftar_ticker = ", ".join(df_filtered["Ticker"].tolist())
                st.code(daftar_ticker, language="text")
                st.caption("📋 Klik icon 'Copy' di pojok kanan atas kotak untuk paste massal ke TradingView/Broker.")
        else: 
            st.warning("Tidak ada data sesuai filter.")

    # ... Tab 3, 4, 5 sisanya sama (tidak saya tulis ulang secara penuh demi menyingkat tempat, cukup pertahankan yang lama karena sudah sesuai)
    with tab3:
        st.markdown("### 📚 Kamus Istilah Kolom")
        st.info("Penjelasan membaca kolom otomatis dari config_web.json")
        for kolom in df_hasil.columns:
            if kolom in KAMUS_EDUKASI: st.markdown(f"🔹 **{kolom}**: {KAMUS_EDUKASI[kolom]}")
            else: st.markdown(f"🔹 **{kolom}**: *(Penjelasan belum ditambahkan di config_web.json)*")

    with tab4:
        st.markdown("### 📈 Strategi & Simulasi Trading Profesional")
        st.success("Terapkan kombinasi filter Screener Anda menggunakan pendekatan para ahli di bawah ini.")
        for judul, deskripsi in STRATEGI_SIMULASI.items():
            with st.expander(f"💼 {judul}", expanded=False): st.write(deskripsi)
                
    with tab5:
        st.markdown("## 🦅 Radar Copet Bandar (Fast Trade)")
        st.info("Catatan: Tetap gunakan tab ini untuk melihat rangkuman fase cepat. Anda kini bisa validasi temuan di tab ini menggunakan filter 'RVOL' dan 'Karakter Gorengan' di Tab 2 Utama.")
else:
    st.error("Silakan jalankan `update_data.py` terlebih dahulu di terminal untuk memuat data!")