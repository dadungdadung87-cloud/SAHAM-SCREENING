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
        "Status Bandar": {"label": "🕵️ Status Bandar", "options": ["Semua", "Akumulasi Kuat", "Distribusi Kuat", "Normal"]},
        "Tekanan Bandar": {"label": "⚔️ Tekanan Harian", "options": ["Semua", "Dominan Beli (Hajar Kanan)", "Dominan Jual (Guyur)", "Seimbang / Adu Mekanik"]},
        "OBV Trend": {"label": "🌊 Tren Uang (OBV)", "options": ["Semua", "Akumulasi (Naik)", "Distribusi (Turun)", "Netral"]},
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
        "MACD": {"label": "📈 MACD", "options": ["Semua", "Strong Bullish", "Bullish MACD", "Strong Bearish", "Bearish MACD"]}
    },
    "KAMUS_EDUKASI": {
        "Ticker": "Kode unik perusahaan.",
        "Kategori": "Pengelompokan saham berdasarkan Kapitalisasi Pasar. Lapis 1 (>10T), Lapis 2 (1-10T), Lapis 3 (<1T).",
        "Harga (Rp)": "Harga penutupan terakhir.",
        "PER (x)": "Price to Earnings Ratio. < 15x = murah.",
        "PBV (x)": "Price to Book Value. < 1x = diskon dari nilai asli.",
        "Harga MA20": "Harga rata-rata pergerakan saham 20 hari terakhir.",
        "Support": "Area batas pantul bawah.",
        "Resistance": "Area batas atap atas.",
        "Change (%)": "Persentase pergerakan harga hari ini.",
        "Volume": "Jumlah lembar saham yang diperdagangkan.",
        "Vol Breakout": "Tembus MA20 = volume melonjak di atas rata-rata.",
        "Status Bandar": "Deteksi pergerakan uang berdasarkan anomali volume. 'Akumulasi' = Bandar beli, 'Distribusi' = Bandar jualan.",
        "Status Gap": "Manipulasi Pre-Opening. 'Gap Up' = harga dibuka langsung loncat di atas penutupan kemarin (FOMO).",
        "Tekanan Bandar": "Analisis anatomi Candlestick harian. 'Dominan Beli' = harga ditutup dekat batas atas (bandar Hajar Kanan). 'Dominan Jual' = harga ditutup jauh di bawah batas atas (ekor panjang di atas = diguyur).",
        "OBV Trend": "Jika 'Akumulasi (Naik)', arus volume uang masuk lebih besar daripada uang keluar dalam 5 hari.",
        "RSI (14D)": "Momentum kecepatan harga.",
        "Momentum": "Arah pergerakan harga harian murni.",
        "MA Signal": "Uptrend jika harga > MA20.",
        "MA Cross": "Golden Cross (Sinyal Beli).",
        "MACD": "Konfirmasi tren.",
        "Status BB": "Squeeze = harga konsolidasi/diam bersiap meledak.",
        "Risiko": "Tingkat Volatilitas. Tinggi = pergerakan liar.",
        "Likuiditas": "Total nilai transaksi.",
        "Total Score": "Akumulasi skor (Maksimal 10 Bintang).",
        "Rekomendasi": "Kesimpulan algoritma. BELI jika skor >= 7.",
        "Status Akuisisi": "Sentimen M&A.",
        "Terakhir Update": "Waktu sinkronisasi data."
    },
    "STRATEGI": {
        "1. Fast Trade & Scalping (Copet)": "Gunakan Tab 5 (Radar Bandar). Cari saham Squeeze dengan Tekanan Bandar 'Dominan Beli'. Beli sore hari, jual besok pagi saat harga Gap Up.",
        "2. Swing Trading (Follow the Trend)": "Gunakan filter: Tren = Uptrend, RSI = > 50, Kategori = Big/Mid Cap.",
        "3. Value Investing (Beli Diskon)": "Cari saham dengan PER < 15, PBV < 1, Kategori = Big Cap.",
        "4. Menghindari Guyuran Bandar": "Jika saham naik kencang (Breakout Upper) TAPI Tekanan Bandar 'Dominan Jual' (ekor panjang di atas), itu artinya bandar sedang take profit. Segera jual!"
    }
}

if not os.path.exists(FILE_CONFIG):
    with open(FILE_CONFIG, "w") as f: json.dump(DEFAULT_CONFIG, f, indent=4)
else:
    with open(FILE_CONFIG, "r") as f:
        cek_config = json.load(f)
    if "Tekanan Bandar" not in cek_config.get("MASTER_FILTERS", {}):
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
        "🔥 Bluechip Terakumulasi": {k: "Semua" for k in MASTER_FILTERS},
        "🟢 Uptrend Aman": {k: "Semua" for k in MASTER_FILTERS}
    }
    preset_bawaan["🔥 Bluechip Terakumulasi"].update({"Status Bandar": "Akumulasi Kuat", "Kategori": "Big Cap (Lapis 1)", "MA Signal": "Uptrend"})
    preset_bawaan["🟢 Uptrend Aman"].update({"MA Signal": "Uptrend", "Likuiditas": "> 1 Miliar", "Risiko": "Sedang"})

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

@st.cache_data(ttl=10) # Memori cache otomatis dihapus setiap 10 detik
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
# TOMBOL SAKTI PEMBERSH CACHE MANUAL
if st.sidebar.button("🔄 Muat Ulang Data Server", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.title("⚙️ Preset Filter Cepat")
opsi_preset = ["Matikan Preset (Manual)"] + list(daftar_preset_aktif.keys())
idx_default = opsi_preset.index(st.session_state.preset_selector) if st.session_state.preset_selector in opsi_preset else 0
st.sidebar.selectbox("🎯 Pilih Preset Aktif:", opsi_preset, index=idx_default, key="preset_selector", on_change=apply_preset)

with st.sidebar.expander("➕ Buat Preset Sendiri Kustom"):
    nama_preset_baru = st.text_input("Nama Preset Anda:", placeholder="Contoh: Akumulasi Uang Besar")
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
st.title("⚡ AlgoTrade Screener - IHSG")
st.markdown("Analisis Tren, Momentum, Bandarmologi, dan Fundamental Ringan.")
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
    if isinstance(val, (int, float)): return 'color: #22c55e; font-weight: 600;' if val > 0 else ('color: #ef4444; font-weight: 600;' if val < 0 else '')
    elif isinstance(val, str):
        if any(x in val for x in ["Positif", "Uptrend", "BELI", "Breakout Upper", "Bottom Rebound", "DALAM AKUISISI", "Rendah", "▲", "Golden Cross", "Bullish", "Tembus MA20", "Akumulasi", "Big Cap", "Gap Up", "Dominan Beli"]): return 'color: #22c55e; font-weight: 600;'
        elif any(x in val for x in ["Negatif", "Downtrend", "WAIT & SEE", "Tinggi", "▼", "Death Cross", "Bearish", "Distribusi", "Small Cap", "Gap Down", "Dominan Jual"]): return 'color: #ef4444; font-weight: 600;'
        elif val == "> 1 Miliar": return 'color: #3b82f6; font-weight: 600;'
        elif any(x in val for x in ["Squeeze", "RENCANA AKUISISI", "Sedang", "Mid Cap", "Seimbang"]): return 'color: #eab308; font-weight: 600;'
        elif "⭐" in val: return 'color: #22c55e;' if len(val) >= 6 else 'color: #ef4444;'
    return ''

# ==========================================
# SECTION 6: RENDER TABS
# ==========================================
if not df_hasil.empty:
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
            st.caption(f"Menampilkan **{len(df_filtered)}** saham yang lolos filter dari total **{len(df_hasil)}** saham.")
            
            cp1, cp2, cp3 = st.columns([1, 1, 2])
            with cp1: per_hal = st.selectbox("Tampilkan baris:", [20, 50, 100])
            tot_hal = int(np.ceil(len(df_filtered) / per_hal))
            with cp2: hal_aktif = st.selectbox("Halaman:", range(1, tot_hal + 1)) if tot_hal > 0 else 1
                    
            idx_awal = (hal_aktif - 1) * per_hal
            df_tampil = df_filtered.iloc[idx_awal : idx_awal + per_hal].copy()
            df_tampil["Total Score"] = df_tampil["Total Score"].apply(format_skor)
            
            urutan = ["Ticker", "Kategori", "Harga (Rp)", "PER (x)", "PBV (x)", "Harga MA20", "Support", "Resistance", "Change (%)", "Volume", "Vol Breakout", "Status Gap", "Tekanan Bandar", "Status Bandar", "OBV Trend", "RSI (14D)", "Momentum", "MA Signal", "MA Cross", "MACD", "Status BB", "Risiko", "Likuiditas", "Total Score", "Rekomendasi", "Status Akuisisi", "Terakhir Update"]
            kolom_ada = [c for c in urutan if c in df_tampil.columns]

            tabel_akhir = df_tampil.style.format({"Harga (Rp)": format_angka, "Harga MA20": format_angka, "Support": format_angka, "Resistance": format_angka, "Volume": format_angka, "Change (%)": format_pct, "Momentum": format_mom, "PER (x)": format_desimal, "PBV (x)": format_desimal, "RSI (14D)": "{:.0f}"}).map(warna_tabel, subset=[c for c in kolom_ada if c not in ["Ticker"]])
            
            st.dataframe(tabel_akhir, use_container_width=True, hide_index=True, column_order=kolom_ada)
            
            # ================= FITUR DOWNLOAD & COPY TAB 2 =================
            st.markdown("---")
            col_dl, col_wl = st.columns([1, 1])
            with col_dl:
                # Mengubah dataframe yang sudah difilter menjadi format CSV
                csv_filter = df_filtered[kolom_ada].to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Hasil Filter (CSV)",
                    data=csv_filter,
                    file_name=f"Screener_Hasil_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="dl_tab2"
                )
            with col_wl:
                # Membuat format daftar ticker dengan koma
                daftar_ticker = ", ".join(df_filtered["Ticker"].tolist())
                st.code(daftar_ticker, language="text")
                st.caption("📋 Klik icon 'Copy' di pojok kanan atas kotak untuk paste massal ke TradingView/Broker.")
        else: 
            st.warning("Tidak ada data sesuai filter.")

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
                
        st.markdown("---")
        st.markdown("#### 🛠️ Analisis Status Pasar Saat Ini")
        if 'Status Bandar' in df_hasil.columns:
            dominasi_bandar = len(df_hasil[df_hasil['Status Bandar'] == 'Akumulasi Kuat'])
            if dominasi_bandar > (len(df_hasil) * 0.1): st.info("🔥 **SIMULASI:** Saat ini banyak saham (>10% pasar) sedang diakumulasi bandar. Fokus pada strategi **Bandarmologi Ride**.")
            else: st.warning("⚖️ **SIMULASI:** Pasar sedang sepi dari pergerakan bandar masif. Disarankan menggunakan strategi **Value Investing** (cicil saham murah) atau **Buy on Squeeze**.")

    with tab5:
        st.markdown("## 🦅 Radar Copet Bandar (Fast Trade)")
        st.markdown("<div class='bandar-box'><b>⚠️ PERINGATAN RISIKO TINGGI:</b> Tab ini murni mendeteksi anomali volume dan volatilitas ekstrem pada saham Lapis 3 (Small Cap/Gorengan). Kecepatan eksekusi sangat dibutuhkan!</div>", unsafe_allow_html=True)
        
        if 'Tekanan Bandar' not in df_hasil.columns:
            st.warning("⏳ **Fitur Radar Bandar belum menerima data terbaru.** Harap klik tombol 'Muat Ulang Data Server' di sidebar sebelah kiri.")
        else:
            df_lapis3 = df_hasil[df_hasil['Kategori'].str.contains("Small Cap", na=False)]
            
            df_markup = df_lapis3[(df_lapis3['Status Bandar'] == 'Akumulasi Kuat') & (df_lapis3['Tekanan Bandar'] == 'Dominan Beli (Hajar Kanan)')].copy()
            df_senyap = df_lapis3[(df_lapis3['OBV Trend'] == 'Akumulasi (Naik)') & (df_lapis3['Status BB'] == 'Squeeze')].copy()
            df_guyur = df_lapis3[(df_lapis3['Status Bandar'] == 'Distribusi Kuat') | (df_lapis3['Tekanan Bandar'] == 'Dominan Jual (Guyur)')].copy()

            st.markdown("---")
            st.markdown("### 🔥 Fase Mark-Up (Sedang Digoreng Naik)")
            st.caption("Algoritma: Saham Lapis 3 + Volume Akumulasi Kuat + Ditutup dengan Tekanan Beli (Hajar Kanan).")
            if not df_markup.empty:
                df_markup["Total Score"] = df_markup["Total Score"].apply(format_skor)
                kolom_b = ["Ticker", "Harga (Rp)", "Change (%)", "Status Gap", "Volume", "Vol Breakout", "Tekanan Bandar", "Status Bandar", "OBV Trend", "Status BB", "Total Score"]
                tabel_markup = df_markup.style.format({"Harga (Rp)": format_angka, "Volume": format_angka, "Change (%)": format_pct}).map(warna_tabel, subset=[c for c in kolom_b if c not in ["Ticker"]])
                st.dataframe(tabel_markup, use_container_width=True, hide_index=True, column_order=kolom_b)
                
                # Fitur Download & Copy
                c1, c2 = st.columns([1, 1])
                c1.download_button("📥 Download Mark-Up (CSV)", df_markup[kolom_b].to_csv(index=False).encode('utf-8'), "Fase_MarkUp.csv", "text/csv", key="dl_markup")
                c2.code(", ".join(df_markup["Ticker"].tolist()), language="text")
            else: st.info("Belum ada saham gorengan yang ditarik kuat oleh Bandar hari ini.")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 🤫 Fase Akumulasi Senyap (Curi Start)")
            st.caption("Algoritma: Saham Lapis 3 + Pergerakan Sempit (Squeeze) + Uang Masuk Diam-diam (OBV Naik). Diurutkan berdasarkan Skor Teknikal dan Volume.")
            if not df_senyap.empty:
                df_senyap = df_senyap.sort_values(by=['Total Score', 'Volume'], ascending=[False, False]).reset_index(drop=True)
                df_senyap.insert(0, 'Prioritas', ['🏆 #1'] + [f'#{i+1}' for i in range(1, len(df_senyap))])
                df_senyap["Total Score"] = df_senyap["Total Score"].apply(format_skor)
                
                kolom_senyap = ["Prioritas", "Ticker", "Harga (Rp)", "Change (%)", "Status Gap", "Volume", "Vol Breakout", "Tekanan Bandar", "Status Bandar", "OBV Trend", "Status BB", "Total Score"]
                tabel_senyap = df_senyap.style.format({"Harga (Rp)": format_angka, "Volume": format_angka, "Change (%)": format_pct}).map(warna_tabel, subset=[c for c in kolom_senyap if c not in ["Ticker", "Prioritas"]])
                st.dataframe(tabel_senyap, use_container_width=True, hide_index=True, column_order=kolom_senyap)
                
                # Fitur Download & Copy
                c1, c2 = st.columns([1, 1])
                c1.download_button("📥 Download Curi Start (CSV)", df_senyap[kolom_senyap].to_csv(index=False).encode('utf-8'), "Fase_CuriStart.csv", "text/csv", key="dl_senyap")
                c2.code(", ".join(df_senyap["Ticker"].tolist()), language="text")
            else: st.info("Belum ada saham yang terpantau masuk fase persiapan.")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### ☠️ Fase Guyuran / Distribusi (HINDARI!)")
            if not df_guyur.empty:
                df_guyur["Total Score"] = df_guyur["Total Score"].apply(format_skor)
                kolom_b = ["Ticker", "Harga (Rp)", "Change (%)", "Status Gap", "Volume", "Vol Breakout", "Tekanan Bandar", "Status Bandar", "OBV Trend", "Status BB", "Total Score"]
                tabel_guyur = df_guyur.style.format({"Harga (Rp)": format_angka, "Volume": format_angka, "Change (%)": format_pct}).map(warna_tabel, subset=[c for c in kolom_b if c not in ["Ticker"]])
                st.dataframe(tabel_guyur, use_container_width=True, hide_index=True, column_order=kolom_b)
                
                # Fitur Download & Copy
                c1, c2 = st.columns([1, 1])
                c1.download_button("📥 Download Guyuran (CSV)", df_guyur[kolom_b].to_csv(index=False).encode('utf-8'), "Fase_Guyuran.csv", "text/csv", key="dl_guyur")
                c2.code(", ".join(df_guyur["Ticker"].tolist()), language="text")
            else: st.success("Pasar Lapis 3 terpantau bersih dari aksi guyuran berat Bandar hari ini.")
else:
    st.error("Silakan jalankan `update_data.py` terlebih dahulu di terminal untuk memuat data!")