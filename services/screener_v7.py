# ==========================================
# TAB 7 — SCREENER BSJP TEPAT SASARAN v7
# Lapisan penyaringan tambahan DI ATAS rumus v6.1 lama (tidak mengubah tab lain).
# Sumber data: Database/hasil_screener.csv (teknikal) + Database/fundamental_exodus.csv
# Semua kolom fundamental opsional — kalau file tidak ada, skor komposit tetap jalan.
# ==========================================
import os
import pandas as pd

DIR_DB = "Database"
VERSI_V7 = "v7.0"

# Bobot skor komposit (total 100)
BOBOT = {
    "teknikal": 40,      # Total Score + rekomendasi + momentum intraday
    "fundamental": 30,   # PER, PBV, Piotroski, EPS
    "likuiditas": 20,    # nilai transaksi + kelas transaksi
    "asing": 10,         # net foreign
}


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def muat_fundamental():
    fp = os.path.join(DIR_DB, "fundamental_exodus.csv")
    if not os.path.exists(fp):
        return pd.DataFrame()
    try:
        df = pd.read_csv(fp)
        df["Ticker"] = df["Ticker"].astype(str).str.upper()
        return df.drop_duplicates(subset="Ticker")
    except Exception:
        return pd.DataFrame()


def skor_fundamental(row_f):
    """0-100 dari baris fundamental. Nilai 0/kosong dianggap tidak tersedia (netral 50)."""
    if row_f is None:
        return 50.0, {}
    rincian = {}
    pe = row_f.get("Current PE Ratio (TTM)", 0) or 0
    pbv = row_f.get("Current Price to Book Value", 0) or 0
    pio = row_f.get("Piotroski F-Score", 0) or 0
    eps = row_f.get("EPS Rating", 0) or 0
    rs = row_f.get("Relative Strength Rating", 0) or 0
    div = row_f.get("Dividend Yield", 0) or 0

    # PER: 0<PE<=12 bagus; negatif (rugi) buruk; >30 buruk
    if pe <= 0:
        rincian["PER"] = 20
    elif pe <= 12:
        rincian["PER"] = 100
    elif pe <= 20:
        rincian["PER"] = 70
    elif pe <= 30:
        rincian["PER"] = 45
    else:
        rincian["PER"] = 20

    # PBV: <=1 sangat murah; 1-2 ok; >3 mahal
    if pbv <= 0:
        rincian["PBV"] = 25
    elif pbv <= 1.0:
        rincian["PBV"] = 100
    elif pbv <= 2.0:
        rincian["PBV"] = 75
    elif pbv <= 3.0:
        rincian["PBV"] = 50
    else:
        rincian["PBV"] = 25

    # Piotroski 0-9
    rincian["Piotroski"] = min(100.0, max(0.0, (pio / 9.0) * 100))
    # EPS rating 0-100 (langsung)
    rincian["EPS"] = min(100.0, max(0.0, float(eps)))
    # Relative strength 0-100
    rincian["RS"] = min(100.0, max(0.0, float(rs)))
    # Dividend yield: >=3% bagus
    rincian["Div"] = min(100.0, (div / 5.0) * 100) if div > 0 else 30.0

    skor = (rincian["PER"] * 0.25 + rincian["PBV"] * 0.20 + rincian["Piotroski"] * 0.25
            + rincian["EPS"] * 0.10 + rincian["RS"] * 0.15 + rincian["Div"] * 0.05)
    return round(skor, 1), rincian


def skor_teknikal(row):
    """0-100 dari kolom teknikal hasil_screener."""
    skor = 0.0
    ts = pd.to_numeric(row.get("Total Score", 0), errors="coerce")
    ts = 0 if pd.isna(ts) else float(ts)
    skor += min(30.0, ts * 3.0)  # max 30 dari Total Score (10 -> 30)

    rek = str(row.get("Rekomendasi", ""))
    if "BELI" in rek:
        skor += 15
    elif "WATCH" in rek.upper() or "PANTAU" in rek.upper():
        skor += 7

    if str(row.get("Tekanan Bandar", "")) == "Dominan Beli (Hajar Kanan)":
        skor += 10
    if str(row.get("Posisi VWAP", "")) == "Di Atas VWAP (Kuat)":
        skor += 8
    if str(row.get("Kekuatan A/D", "")) == "Akumulasi Pro (Smart Money)":
        skor += 8
    if str(row.get("Fase Siklus Bandar", "")) == "Mark-Up (Fase Pesta)":
        skor += 7
    if str(row.get("MACD", "")) == "Strong Bullish":
        skor += 6
    if "Banjir" in str(row.get("Kondisi Supply", "")):
        skor -= 10
    if "Guyur" in str(row.get("Tekanan Bandar", "")):
        skor -= 8
    return round(min(100.0, max(0.0, skor)), 1)


def skor_likuiditas(row):
    """0-100 dari likuiditas & kelas transaksi."""
    skor = 0.0
    if str(row.get("Likuiditas", "")) == "> 1 Miliar":
        skor += 50
    kelas = str(row.get("Kelas Transaksi", ""))
    if "Sultan" in kelas:
        skor += 50
    elif "Ritel Aktif" in kelas:
        skor += 30
    else:
        skor += 5
    if "Solid" in str(row.get("Karakter Gorengan", "")):
        skor += 10
    elif "Tiang Jemuran" in str(row.get("Karakter Gorengan", "")):
        skor -= 10
    return round(min(100.0, max(0.0, skor)), 1)


def skor_asing(nilai_rp):
    """0-100 dari net foreign (Rp). >= 1M bagus, negatif besar buruk."""
    try:
        v = float(nilai_rp or 0)
    except (TypeError, ValueError):
        return 50.0
    if v >= 1_000_000_000:
        return 100.0
    if v >= 100_000_000:
        return 75.0
    if v > 0:
        return 60.0
    if v == 0:
        return 50.0
    if v >= -100_000_000:
        return 35.0
    if v >= -1_000_000_000:
        return 20.0
    return 5.0


def hitung_tab7(df_hasil, df_net_foreign=None):
    """Kembalikan DataFrame kandidat v7 lengkap dengan skor komposit & rincian."""
    if df_hasil is None or df_hasil.empty:
        return pd.DataFrame()
    df_f = muat_fundamental()
    fmap = {r["Ticker"]: r for _, r in df_f.iterrows()} if not df_f.empty else {}
    nf = {}
    sumber_nf = "tidak ada"
    # Prioritas 1: kolom Net Asing (Rp) di hasil_screener itu sendiri
    if "Net Asing (Rp)" in df_hasil.columns:
        s = pd.to_numeric(df_hasil["Net Asing (Rp)"], errors="coerce").fillna(0)
        if (s != 0).any():
            nf = dict(zip(df_hasil["Ticker"].astype(str).str.upper(), s))
            sumber_nf = "hasil_screener"
    # Prioritas 2: file net_foreign.csv
    if not nf and df_net_foreign is not None and not df_net_foreign.empty and "Net_Asing_Rp" in df_net_foreign.columns:
        s = pd.to_numeric(df_net_foreign["Net_Asing_Rp"], errors="coerce").fillna(0)
        if (s != 0).any():
            nf = dict(zip(df_net_foreign["Ticker"].astype(str).str.upper(), s))
            sumber_nf = "net_foreign.csv"

    baris = []
    for _, r in df_hasil.iterrows():
        t = str(r.get("Ticker", "")).upper()
        if not t:
            continue
        s_tek = skor_teknikal(r)
        s_liq = skor_likuiditas(r)
        s_nf = skor_asing(nf.get(t, 0))
        row_f = fmap.get(t)
        s_fun, rincian_f = skor_fundamental(row_f)
        total = (s_tek * BOBOT["teknikal"] + s_fun * BOBOT["fundamental"]
                 + s_liq * BOBOT["likuiditas"] + s_nf * BOBOT["asing"]) / 100.0
        harga = pd.to_numeric(r.get("Harga (Rp)", 0), errors="coerce")
        vol = pd.to_numeric(r.get("Volume", 0), errors="coerce")
        nilai_tx = float(harga) * float(vol) if pd.notna(harga) and pd.notna(vol) else 0.0
        baris.append({
            "Ticker": t,
            "Harga (Rp)": harga,
            "Change (%)": pd.to_numeric(r.get("Change (%)", 0), errors="coerce"),
            "Skor Komposit": round(total, 1),
            "Skor Teknikal": s_tek,
            "Skor Fundamental": s_fun,
            "Skor Likuiditas": s_liq,
            "Net Asing": s_nf,
            "PER": rincian_f.get("PER", "-") if rincian_f else "-",
            "PBV": rincian_f.get("PBV", "-") if rincian_f else "-",
            "Piotroski": (row_f.get("Piotroski F-Score") if row_f is not None else "-"),
            "PER (x)": r.get("PER (x)", ""),
            "PBV (x)": r.get("PBV (x)", ""),
            "Kategori": r.get("Kategori", ""),
            "Valuasi": r.get("Valuasi", ""),
            "Likuiditas": r.get("Likuiditas", ""),
            "Kelas Transaksi": r.get("Kelas Transaksi", ""),
            "Rekomendasi": r.get("Rekomendasi", ""),
            "Total Score": r.get("Total Score", ""),
            "Nilai Tx (Rp)": nilai_tx,
            "Net Asing (Rp)": nf.get(t, 0),
        })
    return pd.DataFrame(baris)


def filter_tepat_sasaran(df_v7, min_skor=60, min_harga=50, max_harga=0,
                         minta_likuid=True, tolak_gorengan=True,
                         per_maks=30, pbv_maks=5, min_piotroski=0):
    """Filter keras opsional di atas skor komposit."""
    if df_v7 is None or df_v7.empty:
        return pd.DataFrame()
    d = df_v7.copy()
    d["Harga (Rp)"] = pd.to_numeric(d["Harga (Rp)"], errors="coerce")
    d = d[d["Harga (Rp)"] >= min_harga]
    if max_harga > 0:
        d = d[d["Harga (Rp)"] <= max_harga]
    d = d[d["Skor Komposit"] >= min_skor]
    if minta_likuid:
        d = d[d["Likuiditas"] == "> 1 Miliar"]
    if tolak_gorengan:
        d = d[~d["Kelas Transaksi"].astype(str).str.contains("Gorengan Sepi", na=False)]
    if per_maks > 0:
        per_num = pd.to_numeric(d["PER (x)"], errors="coerce")
        # PER negatif (rugi) boleh lolos hanya jika skor komposit tinggi (>=70)
        ok_per = (per_num <= per_maks) & (per_num > 0)
        ok_rugi = per_num.isna() | ((per_num <= 0) & (d["Skor Komposit"] >= 70))
        d = d[ok_per | ok_rugi]
    if pbv_maks > 0:
        pbv_num = pd.to_numeric(d["PBV (x)"], errors="coerce")
        d = d[pbv_num.isna() | (pbv_num <= pbv_maks)]
    if min_piotroski > 0:
        pio = pd.to_numeric(d["Piotroski"], errors="coerce")
        d = d[pio.isna() | (pio >= min_piotroski)]
    return d.sort_values("Skor Komposit", ascending=False).reset_index(drop=True)
