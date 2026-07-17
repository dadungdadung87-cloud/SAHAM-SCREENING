import streamlit as st
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
import plotly.express as px

# ==========================================
# SECTION 1: PENGATURAN UI/UX 
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
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0px 0px; padding: 10px 16px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# SECTION 2: MEMUAT DATA EKSTERNAL (JSON)
# ==========================================
FILE_CONFIG = "config_web.json"
FILE_PRESET = "preset_kustom.json"

if not os.path.exists(FILE_CONFIG):
    st.error(f"❌ File konfigurasi '{FILE_CONFIG}' tidak ditemukan! Harap buat file tersebut terlebih dahulu.")
    st.stop()

with open(FILE_CONFIG, "r") as f:
    WEB_CONFIG = json.load(f)

MASTER_FILTERS = WEB_CONFIG["MASTER_FILTERS"]
KAMUS_EDUKASI = WEB_CONFIG["KAMUS_EDUKASI"]
STRATEGI_SIMULASI = WEB_CONFIG["STRATEGI"]

# ==========================================
# SECTION 3: DATABASE PRESET CUSTOM (JSON)
# ==========================================
def muat_preset():
    preset_bawaan = {
        "🔥 Bluechip Terakumulasi": {k: "Semua" for k in MASTER_FILTERS},
        "🟢 Uptrend Aman": {k: "Semua" for k in MASTER_FILTERS}
    }
    preset_bawaan["🔥 Bluechip Terakumulasi"].update({"Status Bandar": "Akumulasi Kuat", "Kategori": "Big Cap (Lapis 1)", "MA Signal": "Uptrend"})
    preset_bawaan["🟢 Uptrend Aman"].update({"MA Signal": "Uptrend", "Likuiditas": "> 1 Miliar", "Risiko": "Sedang"})

    if os.path.exists(FILE_PRESET):
        try:
            with open(FILE_PRESET, "r") as f:
                kustom = json.load(f)
                preset_bawaan.update(kustom)
        except: pass
    return preset_bawaan

daftar_preset_aktif = muat_preset()
if "preset_selector" not in st.session_state: st.session_state.preset_selector = "Matikan Preset (Manual)"

def apply_preset():
    chosen = st.session_state.preset_selector
    if chosen != "Matikan Preset (Manual)":
        vals = daftar_preset_aktif[chosen]
        for k in MASTER_FILTERS.keys():
            if k in vals: st.session_state[f"main_{k}"] = vals[k]

def manual_override():
    st.session_state.preset_selector = "Matikan Preset (Manual)"

# ==========================================
# SECTION 4: HEADER & LOAD DATA SAHAM (CSV)
# ==========================================
st.sidebar.title("⚙️ Preset Filter Cepat")
opsi_preset = ["Matikan Preset (Manual)"] + list(daftar_preset_aktif.keys())
idx_default = opsi_preset.index(st.session_state.preset_selector) if st.session_state.preset_selector in opsi_preset else 0
st.sidebar.selectbox("🎯 Pilih Preset Aktif:", opsi_preset, index=idx_default, key="preset_selector", on_change=apply_preset)

with st.sidebar.expander("➕ Buat Preset Sendiri Kustom"):
    nama_preset_baru = st.text_input("Nama Preset Anda:", placeholder="Contoh: Akumulasi Uang Besar")
    kustom_input = {k: st.selectbox(f"P-{info['label']}", info['options'], key=f"sidebar_{k}") for k, info in MASTER_FILTERS.items()}
    
    if st.button("💾 Simpan Jadi Preset"):
        if nama_preset_baru.strip():
            kustom_lama = {}
            if os.path.exists(FILE_PRESET):
                with open(FILE_PRESET, "r") as f: kustom_lama = json.load(f)
            kustom_lama[nama_preset_baru.strip()] = kustom_input
            with open(FILE_PRESET, "w") as f: json.dump(kustom_lama, f, indent=4)
            
            for k in MASTER_FILTERS.keys(): st.session_state[f"main_{k}"] = kustom_input[k]
            st.session_state.preset_selector = nama_preset_baru.strip()
            st.success(f"Preset Disimpan!")
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("💡 Info: Edit isi file config_web.json untuk mengubah menu dan edukasi secara permanen tanpa koding.")

st.title("⚡ AlgoTrade Screener - IHSG")
st.markdown("Analisis Tren, Momentum, Bandarmologi, dan Fundamental Ringan.")
st.markdown("---")

def load_data_saham():
    if not os.path.exists("hasil_screener.csv"): return pd.DataFrame()
    df = pd.read_csv("hasil_screener.csv")
    if os.path.exists("data_akuisisi.csv"):
        df_akuisisi = pd.read_csv("data_akuisisi.csv")
        if "Status Akuisisi" in df.columns: df = df.drop(columns=["Status Akuisisi"])
        df = pd.merge(df, df_akuisisi, on="Ticker", how="left")
        df["Status Akuisisi"] = df["Status Akuisisi"].fillna("TIDAK ADA")
    else: df["Status Akuisisi"] = "TIDAK ADA"
    return df

df_hasil = load_data_saham()

# ==========================================
# SECTION 5: FUNGSI PEWARNAAN TABEL
# ==========================================
def format_skor(s): return "⭐" * int(s) if pd.notna(s) and int(s) > 0 else "-"
def format_pct(v): return f"{'▲ ' if v > 0 else '▼ '}{v:+.2f}%" if v != 0 else "0.00%"
def format_mom(v): return "▲ Positif" if v == "Positif" else ("▼ Negatif" if v == "Negatif" else v)
def format_desimal(v): return f"{v:.2f}" if pd.notna(v) and v != 0 else "-"
def format_angka(v): return f"{int(v):,}".replace(",", ".") if pd.notna(v) else "-"

def warna_tabel(val):
    if isinstance(val, (int, float)): return 'color: #22c55e; font-weight: 600;' if val > 0 else ('color: #ef4444; font-weight: 600;' if val < 0 else '')
    elif isinstance(val, str):
        if any(x in val for x in ["Positif", "Uptrend", "BELI", "Breakout Upper", "Bottom Rebound", "DALAM AKUISISI", "Rendah", "▲", "Golden Cross", "Bullish", "Tembus MA20", "Akumulasi", "Big Cap"]): return 'color: #22c55e; font-weight: 600;'
        elif any(x in val for x in ["Negatif", "Downtrend", "WAIT & SEE", "Tinggi", "▼", "Death Cross", "Bearish", "Distribusi", "Small Cap"]): return 'color: #ef4444; font-weight: 600;'
        elif val == "> 1 Miliar": return 'color: #3b82f6; font-weight: 600;'
        elif any(x in val for x in ["Squeeze", "RENCANA AKUISISI", "Sedang", "Mid Cap"]): return 'color: #eab308; font-weight: 600;'
        elif "⭐" in val: return 'color: #22c55e;' if len(val) >= 5 else 'color: #ef4444;'
    return ''

# ==========================================
# SECTION 6: RENDER KONTEN TAB UTAMA
# ==========================================
if not df_hasil.empty:
    # --- MENAMBAHKAN TAB 5: RADAR BANDAR ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Ringkasan Pasar", "🎯 Screener Utama", "💡 Insight & Edukasi", "📈 Simulasi & Strategi", "🦅 Radar Bandar (Fast Trade)"])
    
    with tab1:
        total = len(df_hasil)
        beli = len(df_hasil[df_hasil['Rekomendasi'] == 'BELI'])
        uptrend = len(df_hasil[df_hasil['MA Signal'] == 'Uptrend'])
        
        m1, m2, m3 = st.columns(3)
        m1.markdown(f"<div class='metric-container'><h3>🔍 Total Saham</h3><h2>{total}</h2></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-container'><h3>🎯 Sinyal BELI</h3><h2 style='color: #4ade80;'>{beli}</h2></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-container'><h3>📈 Fase Uptrend</h3><h2 style='color: #60a5fa;'>{uptrend}</h2></div>", unsafe_allow_html=True)
        
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
            cp1, cp2, cp3 = st.columns([1, 1, 2])
            with cp1: per_hal = st.selectbox("Tampilkan baris:", [20, 50, 100])
            tot_hal = int(np.ceil(len(df_filtered) / per_hal))
            with cp2: hal_aktif = st.selectbox("Halaman:", range(1, tot_hal + 1)) if tot_hal > 0 else 1
                    
            idx_awal = (hal_aktif - 1) * per_hal
            df_tampil = df_filtered.iloc[idx_awal : idx_awal + per_hal].copy()
            df_tampil["Total Score"] = df_tampil["Total Score"].apply(format_skor)
            
            urutan = ["Ticker", "Kategori", "Harga (Rp)", "PER (x)", "PBV (x)", "Harga MA20", "Support", "Resistance", "Change (%)", "Volume", "Vol Breakout", "Status Bandar", "OBV Trend", "RSI (14D)", "Momentum", "MA Signal", "MA Cross", "MACD", "Status BB", "Risiko", "Likuiditas", "Total Score", "Rekomendasi", "Status Akuisisi", "Terakhir Update"]
            kolom_ada = [c for c in urutan if c in df_tampil.columns]

            tabel_akhir = df_tampil.style.format({"Harga (Rp)": format_angka, "Harga MA20": format_angka, "Support": format_angka, "Resistance": format_angka, "Volume": format_angka, "Change (%)": format_pct, "Momentum": format_mom, "PER (x)": format_desimal, "PBV (x)": format_desimal, "RSI (14D)": "{:.0f}"}).map(warna_tabel, subset=[c for c in kolom_ada if c not in ["Ticker"]])
            
            st.dataframe(tabel_akhir, use_container_width=True, hide_index=True, column_order=kolom_ada)
        else: st.warning("Tidak ada data sesuai filter.")

    with tab3:
        st.markdown("### 📚 Kamus Istilah Kolom")
        st.info("Penjelasan di bawah ini otomatis membaca seluruh kolom yang ada di dalam Screener Anda.")
        for kolom in df_hasil.columns:
            if kolom in KAMUS_EDUKASI: st.markdown(f"🔹 **{kolom}**: {KAMUS_EDUKASI[kolom]}")
            else: st.markdown(f"🔹 **{kolom}**: *(Penjelasan belum ditambahkan di config_web.json)*")

    with tab4:
        st.markdown("### 📈 Strategi & Simulasi Trading Profesional")
        st.success("Terapkan kombinasi filter Screener Anda menggunakan pendekatan para ahli di bawah ini.")
        for judul, deskripsi in STRATEGI_SIMULASI.items():
            with st.expander(f"💼 {judul}", expanded=False): st.write(deskripsi)
                
        st.markdown("---")
        st.markdown("#### 🛠️ Analisis Status Pasar Saat Ini")
        if not df_hasil.empty:
            dominasi_bandar = len(df_hasil[df_hasil['Status Bandar'] == 'Akumulasi Kuat'])
            if dominasi_bandar > (len(df_hasil) * 0.1): st.info("🔥 **SIMULASI:** Saat ini banyak saham (>10% pasar) sedang diakumulasi bandar. Fokus pada strategi **Bandarmologi Ride**.")
            else: st.warning("⚖️ **SIMULASI:** Pasar sedang sepi dari pergerakan bandar masif. Disarankan menggunakan strategi **Value Investing** (cicil saham murah) atau **Buy on Squeeze**.")

    # --- TAB 5: RADAR BANDAR AGRESIF (IDE BARU) ---
    with tab5:
        st.markdown("## 🦅 Radar Copet Bandar (Fast Trade)")
        st.markdown("<div class='bandar-box'><b>⚠️ PERINGATAN RISIKO TINGGI:</b> Tab ini murni mendeteksi anomali volume dan volatilitas ekstrem pada saham Lapis 3 (Small Cap/Gorengan) untuk strategi Fast Trade (Hit & Run). Gunakan uang dingin dan batasi risiko dengan ketat!</div>", unsafe_allow_html=True)
        
        # Logika Inti Pola Pikir Bandar: Filter paksa dari dataframe utama
        # 1. Pastikan Lapis 3 (Barang Ringan)
        df_lapis3 = df_hasil[df_hasil['Kategori'].str.contains("Small Cap", na=False)]
        
        # 2. Deteksi Fase Mark-Up (Sedang Digoreng Keras)
        df_markup = df_lapis3[(df_lapis3['Status Bandar'] == 'Akumulasi Kuat') & (df_lapis3['Status BB'] == 'Breakout Upper')].copy()
        
        # 3. Deteksi Fase Akumulasi Senyap (Persiapan Terbang)
        df_senyap = df_lapis3[(df_lapis3['OBV Trend'] == 'Akumulasi (Naik)') & (df_lapis3['Status BB'] == 'Squeeze')].copy()

        st.markdown("---")
        st.markdown("### 🔥 Fase Mark-Up (Saham Sedang Digoreng)")
        st.caption("Algoritma mencari: Saham Lapis 3 + Breakout Atap (Upper BB) + Volume Terakumulasi Kuat.")
        if not df_markup.empty:
            df_markup["Total Score"] = df_markup["Total Score"].apply(format_skor)
            kolom_bandar = ["Ticker", "Harga (Rp)", "Change (%)", "Volume", "Vol Breakout", "Status Bandar", "OBV Trend", "Status BB", "Risiko", "Total Score"]
            tabel_markup = df_markup.style.format({"Harga (Rp)": format_angka, "Volume": format_angka, "Change (%)": format_pct}).map(warna_tabel, subset=[c for c in kolom_bandar if c not in ["Ticker"]])
            st.dataframe(tabel_markup, use_container_width=True, hide_index=True, column_order=kolom_bandar)
        else:
            st.info("Tidak ada saham gorengan yang sedang berada di fase mark-up ekstrem hari ini.")

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("### 🤫 Fase Akumulasi Senyap (Curi Start / Persiapan)")
        st.caption("Algoritma mencari: Saham Lapis 3 + Volatilitas Sempit (Squeeze) + Tren Uang Masuk (OBV Naik).")
        if not df_senyap.empty:
            df_senyap["Total Score"] = df_senyap["Total Score"].apply(format_skor)
            kolom_bandar = ["Ticker", "Harga (Rp)", "Change (%)", "Volume", "Vol Breakout", "Status Bandar", "OBV Trend", "Status BB", "Risiko", "Total Score"]
            tabel_senyap = df_senyap.style.format({"Harga (Rp)": format_angka, "Volume": format_angka, "Change (%)": format_pct}).map(warna_tabel, subset=[c for c in kolom_bandar if c not in ["Ticker"]])
            st.dataframe(tabel_senyap, use_container_width=True, hide_index=True, column_order=kolom_bandar)
        else:
            st.info("Tidak ada saham gorengan yang sedang diakumulasi diam-diam (Squeeze) hari ini.")
            
        st.markdown("---")
        with st.expander("🧠 Pelajari Pola Pikir Bandar Main Cepat"):
            st.markdown("""
            1. **Cari Barang Ringan (Fokus Lapis 3):** Bandar tidak membuang tenaga untuk menaikkan harga bank besar. Mereka mencari saham berkapitalisasi kecil agar dengan modal beberapa miliar saja harga bisa ditarik naik 20%.
            2. **Fase Akumulasi Senyap (Squeeze):** Bandar membeli sedikit demi sedikit agar harga tidak melonjak. Di grafik terlihat datar (Squeeze), tapi secara hitungan *On Balance Volume (OBV)*, uang terus masuk. Ini momen paling tepat bagi ritel untuk curi start.
            3. **Fase Mark-Up (Breakout Upper):** Bandar mulai melakukan pembelian agresif (Hajar Kanan). Harga meledak menembus atap, memancing indikator teknikal menyala, dan membuat *trader* ritel FOMO (Fear Of Missing Out) ikut membeli.
            4. **Fase Distribusi (Guyur):** Ketika ritel sedang antusias membeli di pucuk, Bandar perlahan menjual (membuang) barang mereka. Volume tetap tinggi, tapi harga mulai tertahan atau turun.
            """)

else:
    st.error("Silakan jalankan `update_data.py` terlebih dahulu di terminal untuk memuat data!")