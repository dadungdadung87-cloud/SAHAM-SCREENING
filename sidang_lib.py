# ==========================================
# 🧠 SIDANG LIB — sidang autopilot headless (cron laptop)
# Aturan IDENTIK dengan app.py web: rumus v5.2.
# Jika ubah rumus/ambang: ubah DI SINI dan DI app.py.
# ==========================================
import os, json, re, time
import pandas as pd

VERSI_SIDANG = "v5.2"
DIR_DB = "Database"

def _wb_now():
    from datetime import datetime, timedelta, timezone
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)

def radar_model_gemini_cepat(api_key):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    cepat, cadangan = [], []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                nama = m.name.replace("models/", "")
                if ("flash" in nama.lower()) or ("lite" in nama.lower()):
                    cepat.append(nama)
                else:
                    cadangan.append(nama)
    except Exception:
        pass
    return cepat + cadangan

def ai_hakim_klasemen_cepat(data_top15, api_key, daftar_model):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    prompt = f"""
    Select EXACTLY 5 Tickers that have the highest combination of 'Score' and 'Volume' from the data below.

    DATA:
    {data_top15}

    CRITICAL: Output ONLY a raw JSON array with EXACTLY 5 objects, each with EXACTLY 1 key: "Ticker".
    DO NOT add explanations, markdown, or any other text. Keep the output as short as possible.
    """
    pesan = ""
    for nama_model in daftar_model:
        try:
            model = genai.GenerativeModel(
                nama_model,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0, response_mime_type="application/json", max_output_tokens=1024))
            response = model.generate_content(prompt)
            teks = response.text or ""
            if not teks.strip():
                pesan = "Respons kosong"; continue
            return teks
        except Exception as e:
            pesan = str(e)
            time.sleep(5 if any(k in str(e) for k in ["429", "503", "RESOURCE_EXHAUSTED"]) else 1)
            continue
    return f"Error_AI: {pesan}"

def _parse_top5(mentah, valid_set):
    hasil = []
    for blok in re.findall(r'\[.*\]', mentah, re.DOTALL):
        try:
            calon = json.loads(blok.replace("'", '"'))
            if isinstance(calon, list):
                for item in calon:
                    t = (item.get("Ticker", "") if isinstance(item, dict) else str(item)).strip().upper()
                    if t in valid_set and t not in hasil:
                        hasil.append(t)
        except Exception:
            continue
    if len(hasil) < 5:
        for m in re.finditer(r'\b([A-Z]{4})\b', mentah):
            t = m.group(1)
            if t in valid_set and t not in hasil:
                hasil.append(t)
            if len(hasil) >= 5:
                break
    return hasil[:5]

def muat_momentum_30m(base_dir=None):
    """Set ticker yang HARGA NAIK dalam 30 menit terakhir AKTIF (arsip intraday hari ini).
    Basis: snapshot terakhir yang harga-nya benar-benar berubah (menghindari snapshot
    statis pasca-tutup yang membuat perbandingan selalu sama → 0 hasil).
    Return set ticker; set kosong jika arsip belum tersedia (graceful)."""
    import glob as _glob
    from datetime import datetime as _dt, timedelta as _td
    base = base_dir or os.path.dirname(os.path.abspath(__file__))
    files = sorted(_glob.glob(os.path.join(base, "Arsip_Data_Harian", "screener_*.csv")))
    if not files:
        return set()
    try:
        df = pd.read_csv(files[-1], usecols=["Waktu Update", "Ticker", "Harga (Rp)"])
        df["_jam"] = df["Waktu Update"].astype(str).str[:5]
        naik = set()
        for t, x in df.groupby("Ticker"):
            x = x.sort_values("_jam")
            bergerak = x[x["Harga (Rp)"].diff().fillna(1) != 0]
            if bergerak.empty:
                continue
            last_h = bergerak["_jam"].iloc[-1]
            last_p = float(bergerak["Harga (Rp)"].iloc[-1])
            hh, mm = int(last_h[:2]), int(last_h[3:])
            target = (_dt(2000, 1, 1, hh, mm) - _td(minutes=30)).strftime("%H:%M")
            kand = x[x["_jam"] <= target]
            if kand.empty:
                continue
            if last_p > float(kand.iloc[-1]["Harga (Rp)"]):
                naik.add(t)
        return naik
    except Exception:
        return set()


def hitung_rumus(df, momentum_30m=None):
    """Rumus v5.2 — identik dengan app.py PART 12."""
    out = {i: pd.DataFrame() for i in range(1, 10)}
    if df is None or df.empty or 'Tekanan Bandar' not in df.columns:
        return out
    # --- FILTER SAHAM SUSPEND (beku / tidak diperdagangkan / delisted) ---
    try:
        delisted = set()
        _fd = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "DATA-CENTER", "Konfigurasi", "saham_delisted.txt")
        if os.path.exists(_fd):
            delisted = {l.strip().upper() for l in open(_fd) if l.strip()}
    except Exception:
        delisted = set()
    try:
        from suspend_helper import muat_suspended_hari_ini
        _susp = muat_suspended_hari_ini(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        _susp = set()
    _h = pd.to_numeric(df.get('Harga (Rp)', 0), errors='coerce')
    _s = pd.to_numeric(df.get('Support', 0), errors='coerce')
    _r = pd.to_numeric(df.get('Resistance', 0), errors='coerce')
    _ma = pd.to_numeric(df.get('Harga MA20', 0), errors='coerce')
    beku = (_h > 0) & (_h == _ma) & (_s == _r) & (_h == _s)
    mask_aktif = ~(beku | df['Ticker'].astype(str).str.upper().isin(delisted | _susp))
    df = df[mask_aktif].copy()
    vwap_ok = (df.get('Posisi VWAP', '') != 'Di Bawah VWAP (Lemah)')
    vwap_kuat = (df.get('Posisi VWAP', '') == 'Di Atas VWAP (Kuat)')
    akumulasi_pro = (df.get('Kekuatan A/D', '') == 'Akumulasi Pro (Smart Money)')
    change_num = pd.to_numeric(df.get('Change (%)', 0), errors='coerce')
    score_num = pd.to_numeric(df.get('Total Score', 0), errors='coerce')
    supply_banjir = df['Kondisi Supply'].astype(str).str.contains('Banjir', na=False) if 'Kondisi Supply' in df.columns else False
    # Pagar zona mati (bukti 122 trade: change 10-20% winrate 0%): RUMUS 1-5 hanya < 7%
    pagar_7 = (change_num < 7.0)
    pola_sisir_aktif = df.get('Pola Sisir', '').astype(str).str.contains('Pola Sisir', na=False) if 'Pola Sisir' in df.columns else pd.Series(False, index=df.index)
    vol_tembus = (df.get('Vol Breakout', '') == 'Tembus MA20')
    haka = (df.get('Tekanan Bandar', '') == 'Dominan Beli (Hajar Kanan)')
    mark_up = (df.get('Fase Siklus Bandar', '') == 'Mark-Up (Fase Pesta)')
    macd_bull = (df.get('MACD', '') == 'Strong Bullish')
    # MOMENTUM 30 MENIT (RUMUS 1-3): saham sedang NAIK dalam 30 menit terakhir.
    # Jika data arsip belum tersedia (set kosong), filter otomatis dilewati (graceful).
    if momentum_30m is None:
        momentum_30m = set()
    mom30 = df['Ticker'].astype(str).str.upper().isin(set(momentum_30m)) if momentum_30m else pd.Series(True, index=df.index)
    # RUMUS 1 = dasar R7 (Mark-Up Pesta) + Momentum 30M Naik
    out[1] = df[mark_up & (df.get('Trend MA (5,20,50)', '') == 'Perfect Uptrend (5>20>50)') &
                vol_tembus & ~supply_banjir & (haka | akumulasi_pro | macd_bull) & mom30 & pagar_7].copy()
    # RUMUS 2 = dasar R8 (MACD Breakout Volume) + Momentum 30M Naik
    out[2] = df[macd_bull & vol_tembus & (df.get('MA Signal', '') == 'Uptrend') & ~supply_banjir &
                (haka | akumulasi_pro) & mom30 & pagar_7].copy()
    # RUMUS 3 = dasar R9 (AD Akumulasi Skor Tinggi) + Momentum 30M Naik
    out[3] = df[akumulasi_pro & (df.get('MA Signal', '') == 'Uptrend') & (score_num >= 5) &
                vol_tembus & (mark_up | macd_bull) & mom30 & pagar_7].copy()
    out[4] = df[((df.get('MA Cross', '') == 'Golden Cross') |
                 (df.get('MACD', '').isin(['Strong Bullish', 'Bullish MACD']))) &
                vol_tembus & (df.get('MA Signal', '') == 'Uptrend') & vwap_kuat &
                (haka | akumulasi_pro) & pagar_7].copy()
    # RUMUS 5 — Pola Sisir Naik (spike berulang, struktur masih utuh) + pagar 7%
    out[5] = df[pola_sisir_aktif & (df.get('MA Signal', '') == 'Uptrend') & vwap_ok & pagar_7].copy()
    # RUMUS 6 — Uptrend Akumulasi (bebas, diperkuat: vol + supply + konfirmasi)
    out[6] = df[(df.get('MA Signal', '') == 'Uptrend') & (score_num >= 5) &
                (df.get('Likuiditas', '') == '> 1 Miliar') & vol_tembus & ~supply_banjir &
                (haka | akumulasi_pro)].copy()
    # RUMUS 7 — Mark-Up Pesta diperkuat (bebas, wajib vol + supply sehat)
    out[7] = df[mark_up & (df.get('Trend MA (5,20,50)', '') == 'Perfect Uptrend (5>20>50)') &
                vol_tembus & ~supply_banjir & (haka | akumulasi_pro | macd_bull)].copy()
    # RUMUS 8 — MACD Breakout Volume diperkuat (bebas, wajib supply sehat + konfirmasi)
    out[8] = df[macd_bull & vol_tembus & (df.get('MA Signal', '') == 'Uptrend') & ~supply_banjir &
                (haka | akumulasi_pro)].copy()
    # RUMUS 9 — AD Akumulasi Skor Tinggi diperkuat (bebas, wajib vol + konfirmasi momentum)
    out[9] = df[akumulasi_pro & (df.get('MA Signal', '') == 'Uptrend') & (score_num >= 5) &
                vol_tembus & (mark_up | macd_bull)].copy()
    return out

def jalankan_sidang(daftar_rumus, df_data, api_key, log=print, mode_tulis=True):
    """Sidang headless: tulis sinyal (+kolom Stempel), cache, snapshot; upload R2.
    Kembalikan (keranjang, error atau None)."""
    import concurrent.futures
    keranjang = {f"RUMUS {i}": ["", "", "", "", ""] for i in range(1, 10)}
    stempel_data = str(df_data["Terakhir Update"].iloc[0]) if (not df_data.empty and "Terakhir Update" in df_data.columns) else "tanpa_stempel"
    stempel_beli = _wb_now().strftime("%Y-%m-%d")
    daftar_model = radar_model_gemini_cepat(api_key)
    if not daftar_model:
        return keranjang, "Tidak ada model Gemini online untuk key ini."

    def sidang_satu(i):
        df_target = daftar_rumus[i]
        n = len(df_target)
        if n == 0:
            return i, [], n
        df_seleksi = df_data[df_data['Ticker'].isin(df_target['Ticker'].tolist())].copy()
        df_seleksi['Score_Num'] = pd.to_numeric(df_seleksi['Total Score'], errors='coerce').fillna(0)
        df_sorted = df_seleksi.sort_values(by=['Score_Num', 'Volume', 'Change (%)'], ascending=[False, False, False])
        if n <= 5:
            tickers = df_sorted['Ticker'].tolist()[:5]
        else:
            top15 = df_sorted.head(15)
            data_ai = {}
            for _, row in top15.iterrows():
                data_ai[row['Ticker']] = {
                    'Harga': row.get('Harga (Rp)', 0), 'Volume': row.get('Volume', 0),
                    'Score': row.get('Score_Num', 0), 'Change_Pct': row.get('Change (%)', 0),
                    'Tekanan_Bandar': row.get('Tekanan Bandar', 'Normal'), 'Broksum': row.get('Broksum', 'Normal')}
            mentah = ai_hakim_klasemen_cepat(data_ai, api_key, daftar_model)
            if "Error_AI" in mentah:
                return i, [], n
            tickers = _parse_top5(mentah, set(data_ai.keys()))
        baris = []
        for t in tickers:
            row = df_sorted[df_sorted['Ticker'] == t]
            if row.empty:
                continue
            harga = float(row.iloc[0]['Harga (Rp)'])
            baris.append({"Ticker": t, "Target_TP": int(round(harga * 1.05)),
                          "Target_CL": int(round(harga * 0.97)), "Stempel": stempel_beli})
        if baris:
            if mode_tulis:
                fs = os.path.join(DIR_DB, f"sinyal_ai_rumus_{i}.csv")
                pd.DataFrame(baris).to_csv(fs, index=False)
                try:
                    import r2_client
                    r2_client.upload_arsip(fs, f"Database/sinyal_ai_rumus_{i}.csv")
                except Exception:
                    pass
        return i, [b["Ticker"] for b in baris], n

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        futs = [ex.submit(sidang_satu, i) for i in range(1, 10)]
        for f in concurrent.futures.as_completed(futs):
            i, jawara, n = f.result()
            keranjang[f"RUMUS {i}"] = (jawara + ["", "", "", "", ""])[:5]
            log(f"   RUMUS {i}: {n} kandidat -> {len(jawara)} jawara {jawara}")

    try:
        with open(os.path.join(DIR_DB, "cache_autopilot.json"), "w") as f:
            json.dump({"stempel_data": stempel_data, "versi": VERSI_SIDANG, "keranjang": keranjang}, f, indent=4)
        snap = {"stempel_data": stempel_data, "versi": VERSI_SIDANG, "keranjang": keranjang,
                "waktu": _wb_now().strftime("%Y-%m-%d %H:%M:%S"), "mode": "sore" if not mode_tulis else "pagi"}
        nama_snap = "radar_snapshot_sore.json" if not mode_tulis else "radar_snapshot.json"
        ps = os.path.join(DIR_DB, nama_snap)
        with open(ps, "w") as f:
            json.dump(snap, f)
        log(f"✅ {nama_snap} ditulis lokal")
        try:
            import r2_client
            r2_client.upload_arsip(ps, f"Database/{nama_snap}")
            log(f"✅ {nama_snap} ter-upload ke R2")
        except Exception as e2:
            log(f"⚠️ upload R2 gagal (file lokal tetap ada): {e2}")
    except Exception as e:
        log(f"❌ GAGAL tulis snapshot: {e}")
        import traceback
        log(traceback.format_exc())
    return keranjang, None
