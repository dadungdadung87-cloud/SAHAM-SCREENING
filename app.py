import streamlit as st
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
import plotly.express as px

# ==========================================
# SECTION 1: PENGATURAN UI/UX AWAL
# ==========================================
st.set_page_config(page_title="Screener Saham IHSG", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stDataFrame { border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.15); }
    h1 { font-weight: 800; background: -webkit-linear-gradient(#38bdf8, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; padding-bottom: 10px; }
    .metric-container { border-radius: 10px; padding: 15px; text-align: center; border: 1px solid #334155; background-color: #1e293b; color: #f8fafc; margin-bottom: 20px; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0px 0px; padding: 10px 16px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# SECTION 2: DEFINISI MASTER INDIKATOR & FILTER
# ==========================================
# PENTING: Tambahkan filter baru Anda HANYA di dalam dictionary ini.
MASTER_FILTERS = {
    "Kategori": {"label": "🏢 Kategori Saham", "options": ["Semua", "Big Cap (Lapis 1)", "Mid Cap (Lapis 2)", "Small Cap (Lapis 3)"]},
    "Status Bandar": {"label": "🕵️ Status Bandar", "options": ["Semua", "Akumulasi Kuat", "Distribusi Kuat", "Normal"]},
    "OBV Trend": {"label": "🌊 Tren Uang (OBV)", "options": ["Semua", "Akumulasi (Naik)", "Distribusi (Turun)", "Netral"]},
    "Vol Breakout": {"label": "🔊 Volume", "options": ["Semua", "Tembus MA20", "Normal"]},
    "RSI (14D)": {"label": "📊 RSI (14D)", "options": ["Semua", "> 50 (Bullish)", "<= 50 (Bearish)"]},
    "MA Signal": {"label": "📈 Tren (MA20)", "options": ["Semua", "Uptrend", "Downtrend"]},
    "Momentum": {"label": "⚡ Momentum", "options": ["Semua", "Positif", "Negatif"]},
    "Total Score": {"label": "⭐ Total Score", "options": ["Semua", 8, 7, 6, 5, 4, 3, 2, 1, 0]},
    "Rekomendasi": {"label": "🎯 Rekomendasi", "options": ["Semua", "BELI", "WAIT & SEE"]},
    "Likuiditas": {"label": "💧 Likuiditas", "options": ["Semua", "> 1 Miliar", "< 1 Miliar"]},
    "Status BB": {"label": "🌐 Bollinger Bands", "options": ["Semua", "Squeeze", "Bottom Rebound", "Breakout Upper", "Normal"]},
    "MA Cross": {"label": "🔀 MA Cross (5/20)", "options": ["Semua", "Golden Cross", "Bullish", "Death Cross", "Bearish"]},
    "Risiko": {"label": "⚠️ Risiko Volatilitas", "options": ["Semua", "Tinggi", "Sedang", "Rendah"]},
    "Status Akuisisi": {"label": "🤝 Sentimen Akuisisi", "options": ["Semua", "TIDAK ADA", "RENCANA AKUISISI", "DALAM AKUISISI"]},
    "MACD": {"label": "📈 MACD", "options": ["Semua", "Strong Bullish", "Bullish MACD", "Strong Bearish", "Bearish MACD"]}
}

# ==========================================
# SECTION 3: MANAJEMEN DATABASE PRESET (JSON) & CALLBACK
# ==========================================
FILE_PRESET = "preset_kustom.json"

base_default = {k: "Semua" for k in MASTER_FILTERS.keys()}
preset_super_ketat = base_default.copy()
preset_super_ketat.update({"Vol Breakout": "Tembus MA20", "RSI (14D)": "> 50 (Bullish)", "MA Signal": "Uptrend", "Status BB": "Breakout Upper", "Status Bandar": "Akumulasi Kuat", "Kategori": "Big Cap (Lapis 1)"})
preset_uptrend_likuid = base_default.copy()
preset_uptrend_likuid.update({"MA Signal": "Uptrend", "Likuiditas": "> 1 Miliar"})

PRESET_BAWAAN = {
    "🔥 Aman & Akumulasi (Bluechip)": preset_super_ketat,
    "🟢 Hanya Saham Uptrend & Likuid": preset_uptrend_likuid
}

def muat_preset():
    if os.path.exists(FILE_PRESET):
        try:
            with open(FILE_PRESET, "r") as f:
                kustom = json.load(f)
                total = PRESET_BAWAAN.copy()
                total.update(kustom)
                return total
        except: return PRESET_BAWAAN
    return PRESET_BAWAAN

def simpan_preset_baru(nama, kriteria):
    data_kustom = {}
    if os.path.exists(FILE_PRESET):
        try:
            with open(FILE_PRESET, "r") as f: data_kustom = json.load(f)
        except: pass
    data_kustom[nama] = kriteria
    with open(FILE_PRESET, "w") as f: json.dump(data_kustom, f, indent=4)

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
# SECTION 4: HEADER & LOAD DATA LOKAL
# ==========================================
st.title("⚡ AlgoTrade Screener - IHSG")
st.markdown("Analisis Tren, Momentum, Bandarmologi, dan Fundamental Ringan.")
st.markdown("---")

FILE_HASIL = "hasil_screener.csv"
FILE_AKUISISI = "data_akuisisi.csv"

def load_data_saham():
    if not os.path.exists(FILE_HASIL): return pd.DataFrame()
    waktu_modifikasi = os.path.getmtime(FILE_HASIL)
    waktu_terakhir = datetime.fromtimestamp(waktu_modifikasi).strftime('%Y-%m-%d %H:%M:%S')
    st.success(f"💾 Data berhasil dimuat secara instan! Terakhir diperbarui pada: **{waktu_terakhir}**")
    
    df = pd.read_csv(FILE_HASIL)
    if os.path.exists(FILE_AKUISISI):
        df_akuisisi = pd.read_csv(FILE_AKUISISI)
        if "Status Akuisisi" in df.columns: df = df.drop(columns=["Status Akuisisi"])
        df = pd.merge(df, df_akuisisi, on="Ticker", how="left")
        df["Status Akuisisi"] = df["Status Akuisisi"].fillna("TIDAK ADA")
    else:
        df["Status Akuisisi"] = "TIDAK ADA"
    return df

df_hasil = load_data_saham()

# ==========================================
# SECTION 5: RENDER SIDEBAR KIRI
# ==========================================
st.sidebar.title("⚙️ Preset Filter Cepat")
opsi_preset = ["Matikan Preset (Manual)"] + list(daftar_preset_aktif.keys())
idx_default = opsi_preset.index(st.session_state.preset_selector) if st.session_state.preset_selector in opsi_preset else 0
st.sidebar.selectbox("🎯 Pilih Preset Aktif:", opsi_preset, index=idx_default, key="preset_selector", on_change=apply_preset)

with st.sidebar.expander("➕ Buat Preset Sendiri Kustom"):
    nama_preset_baru = st.text_input("Nama Preset Anda:", placeholder="Contoh: Akumulasi Uang Besar")
    kustom_input_user = {}
    for key, info in MASTER_FILTERS.items():
        kustom_input_user[key] = st.selectbox(f"P-{info['label']}", info['options'], key=f"sidebar_{key}")
    
    if st.button("💾 Simpan Jadi Preset"):
        if nama_preset_baru.strip():
            simpan_preset_baru(nama_preset_baru.strip(), kustom_input_user)
            for k in MASTER_FILTERS.keys(): st.session_state[f"main_{k}"] = kustom_input_user[k]
            st.session_state.preset_selector = nama_preset_baru.strip()
            st.success(f"Preset Disimpan!")
            st.rerun()
        else: st.error("Nama tidak boleh kosong!")

st.sidebar.markdown("---")
st.sidebar.caption("© AlgoTrade Screener")

# ==========================================
# SECTION 6: FUNGSI PEWARNAAN & FORMATTING TABEL
# ==========================================
def format_skor_bintang_bersih(score):
    if pd.isna(score) or int(score) == 0: return "-"
    return "⭐" * int(score)

def format_persen_ikon(val):
    if pd.isna(val): return "-"
    if val == 0: return "0.00%"
    ikon = "▲ " if val > 0 else "▼ "
    return f"{ikon}{val:+.2f}%"

def format_momentum_ikon(val):
    if val == "Positif": return "▲ Positif"
    if val == "Negatif": return "▼ Negatif"
    return val
    
def format_desimal(val):
    if pd.isna(val) or val == 0: return "-"
    return f"{val:.2f}"

def format_angka(val): 
    if pd.isna(val): return "-"
    return f"{int(val):,}".replace(",", ".")

def warna_tabel(val):
    style = '' 
    if isinstance(val, (int, float)):
        if val > 0: style = 'color: #22c55e; font-weight: 600;' 
        elif val < 0: style = 'color: #ef4444; font-weight: 600;' 
    elif isinstance(val, str):
        if any(x in val for x in ["Positif", "Uptrend", "BELI", "Breakout Upper", "Bottom Rebound", "DALAM AKUISISI", "Rendah", "▲", "Golden Cross", "Bullish", "Tembus MA20", "Akumulasi", "Big Cap"]): 
            style = 'color: #22c55e; font-weight: 600;'
        elif any(x in val for x in ["Negatif", "Downtrend", "WAIT & SEE", "Tinggi", "▼", "Death Cross", "Bearish", "Distribusi", "Small Cap"]): 
            style = 'color: #ef4444; font-weight: 600;'
        elif val == "> 1 Miliar": 
            style = 'color: #3b82f6; font-weight: 600;'
        elif any(x in val for x in ["Squeeze", "RENCANA AKUISISI", "Sedang", "Mid Cap"]): 
            style = 'color: #eab308; font-weight: 600;'
        elif "⭐" in val:
            if len(val) >= 5: style = 'color: #22c55e;'
            else: style = 'color: #ef4444;'
    return style

# ==========================================
# SECTION 7: RENDER KONTEN UTAMA (TABS)
# ==========================================
if not df_hasil.empty:
    tab1, tab2, tab3 = st.tabs(["📊 Ringkasan Pasar", "🎯 Screener Utama", "💡 Insight & Edukasi"])
    
    # --- TAB 1: RINGKASAN ---
    with tab1:
        total_dianalisis = len(df_hasil)
        total_beli = len(df_hasil[df_hasil['Rekomendasi'] == 'BELI'])
        total_uptrend = len(df_hasil[df_hasil['MA Signal'] == 'Uptrend'])

        met1, met2, met3 = st.columns(3)
        met1.markdown(f"<div class='metric-container'><h3>🔍 Total Saham</h3><h2>{total_dianalisis}</h2></div>", unsafe_allow_html=True)
        met2.markdown(f"<div class='metric-container'><h3>🎯 Sinyal BELI</h3><h2 style='color: #4ade80;'>{total_beli}</h2></div>", unsafe_allow_html=True)
        met3.markdown(f"<div class='metric-container'><h3>📈 Fase Uptrend</h3><h2 style='color: #60a5fa;'>{total_uptrend}</h2></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        col_chart1, col_chart2 = st.columns([1, 2]) 
        with col_chart1:
            df_rekomendasi = df_hasil['Rekomendasi'].value_counts().reset_index()
            df_rekomendasi.columns = ['Rekomendasi', 'Jumlah']
            fig_pie = px.pie(df_rekomendasi, names='Rekomendasi', values='Jumlah', hole=0.5, color='Rekomendasi', color_discrete_map={'BELI': '#22c55e', 'WAIT & SEE': '#ef4444'})
            fig_pie.update_layout(title_text='Rasio Sinyal Rekomendasi', margin=dict(t=40, b=20, l=20, r=20), height=450)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_chart2:
            df_top15 = df_hasil.nlargest(15, 'Change (%)').iloc[::-1]
            fig_bar = px.bar(df_top15, x='Change (%)', y='Ticker', orientation='h', color='Change (%)', color_continuous_scale=['#86efac', '#22c55e', '#166534'])
            fig_bar.update_traces(texttemplate='%{x:.0f}%', textposition='outside')
            fig_bar.update_layout(title_text='Top 15 Saham Gainers (Stockbit Style)', margin=dict(t=40, b=20, l=40, r=40), xaxis_title="Perubahan (%)", yaxis_title="Kode Saham", height=450)
            if not df_top15.empty: fig_bar.update_xaxes(range=[0, df_top15['Change (%)'].max() * 1.2]) 
            st.plotly_chart(fig_bar, use_container_width=True)

    # --- TAB 2: SCREENER UTAMA ---
    with tab2:
        with st.expander("🎛️ Buka Panel Filter Lengkap", expanded=False):
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            filter_terpilih_tabel = {}
            for idx, (db_key, info) in enumerate(MASTER_FILTERS.items()):
                target_col = col_f1 if idx % 4 == 0 else (col_f2 if idx % 4 == 1 else (col_f3 if idx % 4 == 2 else col_f4))
                with target_col:
                    val_sekarang = st.session_state.get(f"main_{db_key}", info["options"][0])
                    idx_opsi = info["options"].index(val_sekarang) if val_sekarang in info["options"] else 0
                    filter_terpilih_tabel[db_key] = st.selectbox(info["label"], info["options"], index=idx_opsi, key=f"main_{db_key}", on_change=manual_override)

        st.markdown("### 📋 Tabel Data Saham")
        col_search, col_empty = st.columns([1, 2])
        with col_search: search_ticker = st.text_input("🔍 Cari Kode Saham", "", placeholder="Ketik kode (Contoh: BBCA)")

        # Logika Filter
        df_filtered = df_hasil.copy()
        if search_ticker: df_filtered = df_filtered[df_filtered["Ticker"].str.contains(search_ticker.upper(), na=False)]
        for db_key, nilai_filter in filter_terpilih_tabel.items():
            if nilai_filter != "Semua":
                if db_key == "RSI (14D)":
                    if nilai_filter == "> 50 (Bullish)": df_filtered = df_filtered[df_filtered["RSI (14D)"] > 50]
                    elif nilai_filter == "<= 50 (Bearish)": df_filtered = df_filtered[df_filtered["RSI (14D)"] <= 50]
                elif db_key == "Total Score":
                    df_filtered = df_filtered[df_filtered["Total Score"] == int(nilai_filter)]
                else:
                    if db_key in df_filtered.columns: df_filtered = df_filtered[df_filtered[db_key] == nilai_filter]

        if not df_filtered.empty:
            col_pg1, col_pg2, col_pg3 = st.columns([1, 1, 2])
            with col_pg1: saham_per_halaman = st.selectbox("Tampilkan baris:", [20, 50, 100])
            total_halaman = int(np.ceil(len(df_filtered) / saham_per_halaman))
            with col_pg2: halaman_aktif = st.selectbox("Pilih Halaman:", range(1, total_halaman + 1)) if total_halaman > 0 else 1
                    
            indeks_awal = (halaman_aktif - 1) * saham_per_halaman
            indeks_akhir = indeks_awal + saham_per_halaman
            df_tampil = df_filtered.iloc[indeks_awal:indeks_akhir].copy()
            
            df_tampil["Total Score"] = df_tampil["Total Score"].apply(format_skor_bintang_bersih)
            
            kolom_berwarna = ["Change (%)", "Momentum", "MA Signal", "MA Cross", "MACD", "Rekomendasi", "Likuiditas", "Status BB", "Status Akuisisi", "Risiko", "Total Score", "Vol Breakout", "Status Bandar", "OBV Trend", "Kategori"]
            kolom_berwarna_aktual = [col for col in kolom_berwarna if col in df_tampil.columns]

            tabel_akhir = df_tampil.style.format({
                "Harga (Rp)": format_angka, "Harga MA20": format_angka, "Support": format_angka, "Resistance": format_angka,
                "Volume": format_angka, "Change (%)": format_persen_ikon, "Momentum": format_momentum_ikon,
                "PER (x)": format_desimal, "PBV (x)": format_desimal, "RSI (14D)": "{:.0f}"
            }).map(warna_tabel, subset=kolom_berwarna_aktual)

            # --- JIKA INGIN MENAMBAH KOLOM KE TABEL, TAMBAHKAN DI BAWAH INI ---
            urutan_kolom_tetap = [
                "Ticker", "Kategori", "Harga (Rp)", "PER (x)", "PBV (x)", "Harga MA20", "Support", "Resistance", "Change (%)", 
                "Volume", "Vol Breakout", "Status Bandar", "OBV Trend", "RSI (14D)", "Momentum", "MA Signal", "MA Cross", "MACD",
                "Status BB", "Risiko", "Likuiditas", "Total Score", "Rekomendasi", "Status Akuisisi", "Terakhir Update"
            ]
            kolom_tersedia = [col for col in urutan_kolom_tetap if col in df_tampil.columns]

            st.dataframe(tabel_akhir, use_container_width=True, hide_index=True, column_order=kolom_tersedia)
            st.caption(f"Menampilkan urutan {(indeks_awal + 1)} - {min(indeks_akhir, len(df_filtered))} dari {len(df_filtered)} saham.")
            
            st.markdown("---")
            st.download_button(
                label="📥 Unduh Hasil (CSV)", 
                data=df_filtered.to_csv(index=False).encode('utf-8'),
                file_name=f'screener_ihsg_{datetime.now().strftime("%Y%m%d")}.csv', 
                mime='text/csv'
            )
        else: st.warning("Tidak ada saham yang memenuhi kriteria.")

    # --- TAB 3: EDUKASI ---
    with tab3:
        st.markdown("### 📚 Panduan Membaca Screener")
        st.markdown("""
        * **🏢 Kategori Saham:** Lapis 1 (Bluechip), Lapis 2 (Menengah), Lapis 3 (Gorengan).
        * **💰 Valuasi:** PER < 15x (Murah), PBV < 1x (Sangat Murah/Diskon).
        * **🕵️ Status Bandar:** Lonjakan volume ekstrem untuk membaca *Akumulasi* atau *Distribusi* uang besar.
        * **MA Cross & MACD:** Konfirmasi kuat dari perubahan arah tren jangka pendek ke menengah.
        * **Total Score (Maks 8 ⭐):** Saham dengan skor 6 ke atas (hijau) mendapatkan rekomendasi **BELI**.
        """)
else:
    st.error("Silakan jalankan `update_data.py` terlebih dahulu di terminal untuk memuat data!")