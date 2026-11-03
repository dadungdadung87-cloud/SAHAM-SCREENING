# ==========================================
# 🧠 SIDANG LIB — sidang autopilot headless (cron laptop)
# Aturan IDENTIK dengan app.py web: rumus v6.0 (rebound pembekal).
# Jika ubah rumus/ambang: ubah DI SINI dan DI app.py.
# ==========================================
import os, json, re, time
import pandas as pd

VERSI_SIDANG = "v6.0"
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


def _b64d(s):
    import base64
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def muat_rebound_state(base_dir=None):
    """Hitung state rebound intraday HARI INI per ticker dari arsip 5-menit.
    Return dict {ticker: (pct_dari_low, low_sejauh_ini)} atau {} jika arsip belum ada.
    pct_dari_low = (harga_snapshot_terakhir - low_intraday) / low * 100 —
    bukan kenaikan dari harga pembukaan (bukti 18 winner 03-11)."""
    import glob as _glob
    base = base_dir or os.path.dirname(os.path.abspath(__file__))
    files = sorted(_glob.glob(os.path.join(base, "Arsip_Data_Harian", "screener_*.csv")))
    if not files:
        return {}
    try:
        df = pd.read_csv(files[-1], usecols=["Waktu Update", "Ticker", "Harga (Rp)"])
        if df.empty:
            return {}
        p = df.pivot_table(index="Ticker", columns="Waktu Update", values="Harga (Rp)", aggfunc="last")
        if p.empty:
            return {}
        low = p.min(axis=1)
        akhir = p.ffill(axis=1).iloc[:, -1]
        pct = ((akhir - low) / low * 100).replace([float("inf"), float("-inf")], 0).fillna(0)
        return {t: (float(pct[t]), float(low[t])) for t in p.index if low[t] > 0}
    except Exception:
        return {}


def muat_skor_pembekal(base_dir=None):
    """Skor 'pembekal rebound' dari snapshot penutupan HARI SEBELUMNYA (bukti 03-11:
    sisir aktif 3.1x, markup 3.7x, uptrend 2.5x, chg-neg 1.6x; skor>=4 => 7.9% rebound>=10%).
    Skor 0-6 per ticker; {} jika arsip kemarin tidak ada (graceful)."""
    import glob as _glob
    base = base_dir or os.path.dirname(os.path.abspath(__file__))
    files = sorted(_glob.glob(os.path.join(base, "Arsip_Data_Harian", "screener_*.csv")))
    if len(files) < 2:
        return {}
    try:
        cols = ["Waktu Update", "Ticker", "Change (%)", "Tekanan Bandar", "Pola Sisir",
                "Fase Siklus Bandar", "Kekuatan A/D", "MA Signal"]
        df = pd.read_csv(files[-2], usecols=cols)
        if df.empty:
            return {}
        last = df["Waktu Update"].max()
        d = df[df["Waktu Update"] == last].set_index("Ticker")
        S = lambda s, pat, rx=False: s.astype(str).str.contains(pat, na=False, regex=rx)
        skor = (S(d["Pola Sisir"], "Pola Sisir (").astype(int)
                + S(d["Fase Siklus Bandar"], "Mark-Up").astype(int)
                + (d["MA Signal"].astype(str) == "Uptrend").astype(int)
                + S(d["Kekuatan A/D"], "Akumulasi").astype(int)
                + (pd.to_numeric(d["Change (%)"], errors="coerce") < 0).fillna(False).astype(int)
                + (~S(d["Tekanan Bandar"], "Guyur")).astype(int))
        return {t: int(skor[t]) for t in d.index}
    except Exception:
        return {}


def hitung_rumus(df, momentum_30m=None):
    """Rumus v6.0 — identik dengan app.py PART 12. Wajib argumen momentum_30m (dict rebound
    dari muat_rebound_state) dan skor_pembekal (dari muat_skor_pembekal)."""
    out = {i: pd.DataFrame() for i in range(1, 10)}
    if df is None or df.empty or 'Tekanan Bandar' not in df.columns:
        return out
    if momentum_30m is None:
        momentum_30m = muat_rebound_state()
    if isinstance(momentum_30m, (set, list)):
        momentum_30m = {}
    reb_pct = {t: v[0] for t, v in momentum_30m.items()} if isinstance(momentum_30m, dict) else {}
    skor_pembekal = muat_skor_pembekal()
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
    pola_sisir_aktif = df.get('Pola Sisir', '').astype(str).str.contains('Pola Sisir', na=False) if 'Pola Sisir' in df.columns else pd.Series(False, index=df.index)
    vol_tembus = (df.get('Vol Breakout', '') == 'Tembus MA20')
    haka = (df.get('Tekanan Bandar', '') == 'Dominan Beli (Hajar Kanan)')
    mark_up = (df.get('Fase Siklus Bandar', '') == 'Mark-Up (Fase Pesta)')
    macd_bull = (df.get('MACD', '') == 'Strong Bullish')
    # --- v6.0 INTI BARU: REBOUND DARI LOW INTRADAY (bukan dari open) ---
    # Bukti 03-11: 18 winner naik>=10%; mayoritas rebound dari low, bukan dari open.
    # Rebound dini (naik>=3% dari low) = prediktor terkuat antar-hari (Senin: 24.3%, Selasa: 11%).
    tk = df['Ticker'].astype(str).str.upper()
    _reb = tk.map(reb_pct).fillna(0).astype(float)
    reb_dini = (_reb >= 3.0)        # sudah memantul >=3% dari low intraday
    reb_besar = (_reb >= 8.0)       # rebound sudah besar (sarana trailing, bukan entry awal)
    # --- v6.0 SKOR PEMBEKAL dari penutupan kemarin (skor 0-6) ---
    _sk = tk.map(skor_pembekal).fillna(0).astype(int)
    bekal_kuat = (_sk >= 4)         # 7.9% jadi winner vs baseline 1.8% (bukti 03-11)
    bekal_min = (_sk >= 3)
    # MOMENTUM 30 MENIT legacy (tidak lagi dipakai wajib; dipertahankan utk kompatibilitas)
    if isinstance(momentum_30m, dict) and momentum_30m:
        mom_set = set(momentum_30m.keys())
    else:
        mom_set = set()
    mom30 = tk.isin(mom_set) if mom_set else pd.Series(True, index=df.index)

    # RUMUS 1 — Rebound Dini Pembekal (inti v6): pembekal kuat + mulai memantul dari low
    out[1] = df[bekal_kuat & reb_dini & ~supply_banjir & (haka | akumulasi_pro | vwap_kuat)].copy()
    # RUMUS 2 — Rebound Dini Luas (tanpa syarat pembekal, wajib konfirmasi teknikal)
    out[2] = df[reb_dini & vol_tembus & ~supply_banjir & (haka | akumulasi_pro | macd_bull)].copy()
    # RUMUS 3 — Rebound + Sisir Aktif (sisir = lift 3.1x kemarin, konfirmasi rebound)
    out[3] = df[reb_dini & pola_sisir_aktif & (vwap_ok | vwap_kuat) & ~supply_banjir].copy()
    # RUMUS 4 — Pantulan Jarum Bawah v6 (hammer/jarum bawah + rebound sudah jalan)
    out[4] = df[((df.get('Pola Candle', '') == 'Hammer (Potensi Reversal)') |
                 (df.get('Sinyal Cuci Barang', '') == 'Jarum Bawah (Sinyal Pantulan Kuat)')) &
                reb_dini & (vwap_ok | akumulasi_pro) & ~supply_banjir].copy()
    # RUMUS 5 — Rebound Mark-Up (fase pesta + rebound: lift markup 3.7x)
    out[5] = df[mark_up & reb_dini & ~supply_banjir & (haka | akumulasi_pro | vol_tembus)].copy()
    # RUMUS 6 — Uptrend Rebound (struktur uptrend + rebound dini, kandidat lanjutan)
    out[6] = df[(df.get('MA Signal', '') == 'Uptrend') & reb_dini & vol_tembus &
                ~supply_banjir & (akumulasi_pro | (score_num >= 5))].copy()
    # RUMUS 7 — Rebound Besar Momentum (reb>=8% + vol tembus: momentum kedua / pyramiding)
    out[7] = df[reb_besar & vol_tembus & (haka | akumulasi_pro | macd_bull) & ~supply_banjir].copy()
    # RUMUS 8 — MACD Bull Rebound (MACD kuat + rebound: tren + pantulan searah)
    out[8] = df[macd_bull & reb_dini & (df.get('MA Signal', '') == 'Uptrend') & ~supply_banjir].copy()
    # RUMUS 9 — AD Akumulasi Skor Tinggi v6 (akumulasi pro + skor tinggi + rebound)
    out[9] = df[akumulasi_pro & reb_dini & (score_num >= 5) & (mark_up | macd_bull | vol_tembus)].copy()
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
