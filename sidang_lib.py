# ==========================================
# 🧠 SIDANG LIB — sidang autopilot headless (cron laptop)
# Aturan IDENTIK dengan app.py web: rumus v6.0 (rebound pembekal).
# Jika ubah rumus/ambang: ubah DI SINI dan DI app.py.
# ==========================================
import os, json, re, time
import pandas as pd

VERSI_SIDANG = "v6.1"
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


def _arsip_hari_ini(base_dir=None, hari_lalu=False):
    """Path arsip intraday terbaru, dengan fallback R2 untuk deployment cloud
    (Streamlit Cloud tidak punya arsip lokal — R2 di-refresh jalankan_bot.sh).
    hari_lalu=True mengambil arsip H-1 (untuk skor pembekal). Return path atau None."""
    from datetime import datetime, timedelta
    base = base_dir or os.path.dirname(os.path.abspath(__file__))
    wib = datetime.utcnow() + timedelta(hours=7)
    if wib.weekday() >= 5:  # Sabtu/Minggu: bursa tutup, pakai Jumat
        wib = wib - timedelta(days=(wib.weekday() - 4))
    target = (wib - timedelta(days=1 if hari_lalu else 0)).strftime("%Y-%m-%d")
    nama = f"screener_{target}.csv"
    lokal = os.path.join(base, "Arsip_Data_Harian", nama)
    if os.path.exists(lokal):
        return lokal
    # Fallback cloud: unduh dari R2 (cache lokal agar tidak download tiap rerun)
    cache = os.path.join(base, "Arsip_Data_Harian", f".r2_{nama}")
    if os.path.exists(cache):
        return cache
    try:
        import r2_client
        if r2_client.download_arsip(f"Arsip_Data_Harian/{nama}", cache):
            return cache
    except Exception:
        pass
    return None


def muat_open_state(base_dir=None):
    """Pct kenaikan dari HARGA PEMBUKAAN intraday HARI INI (snapshot pertama arsip).
    Return {ticker: (pct_dari_open, harga_open)}. Bukti 04-11: 20 winner naik>=10%
    dari open; rebound dari low saja buta sepanjang pagi (low pagi = harga pagi)."""
    f = _arsip_hari_ini(base_dir)
    if not f:
        return {}
    try:
        df = pd.read_csv(f, usecols=["Waktu Update", "Ticker", "Harga (Rp)"])
        if df.empty:
            return {}
        p = df.pivot_table(index="Ticker", columns="Waktu Update", values="Harga (Rp)", aggfunc="first")
        if p.empty:
            return {}
        openp = p.iloc[:, 0]
        akhir = p.ffill(axis=1).iloc[:, -1]
        pct = ((akhir - openp) / openp * 100).replace([float("inf"), float("-inf")], 0).fillna(0)
        return {t: (float(pct[t]), float(openp[t])) for t in p.index if openp[t] > 0}
    except Exception:
        return {}


def muat_rebound_state(base_dir=None):
    """Hitung state rebound intraday HARI INI per ticker dari arsip 5-menit.
    Return dict {ticker: (pct_dari_low, low_sejauh_ini)} atau {} jika arsip belum ada.
    pct_dari_low = (harga_snapshot_terakhir - low_intraday) / low * 100 —
    bukan kenaikan dari harga pembukaan (bukti 18 winner 03-11)."""
    f = _arsip_hari_ini(base_dir)
    if not f:
        return {}
    try:
        df = pd.read_csv(f, usecols=["Waktu Update", "Ticker", "Harga (Rp)"])
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
    f = _arsip_hari_ini(base_dir, hari_lalu=True)
    if not f:
        return {}
    try:
        cols = ["Waktu Update", "Ticker", "Change (%)", "Tekanan Bandar", "Pola Sisir",
                "Fase Siklus Bandar", "Kekuatan A/D", "MA Signal"]
        df = pd.read_csv(f, usecols=cols)
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
    """Rumus v6.1 — identik dengan app.py PART 12. Wajib argumen momentum_30m (gabungan
    rebound-dari-low + naik-dari-open dari muat_rebound_state & muat_open_state)."""
    out = {i: pd.DataFrame() for i in range(1, 10)}
    if df is None or df.empty or 'Tekanan Bandar' not in df.columns:
        return out
    if momentum_30m is None:
        _reb = muat_rebound_state()
        _opn = muat_open_state()
        momentum_30m = {t: (_reb.get(t, (0, 0))[0] if t in _reb else _opn.get(t, (0, 0))[0], 0)
                        for t in set(_reb) | set(_opn)}
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
    # --- v6.1 INTI BARU: GATE INTRADAY GANDA (rebound dari low ATAU naik dari open) ---
    # Bukti 04-11: 20 winner naik>=10% dari open; mayoritas Downtrend + bekal 1-2.
    # Konfirmasi intraday hari ini > struktur kemarin; rebate low buta sepanjang pagi.
    tk = df['Ticker'].astype(str).str.upper()
    _reb = tk.map(reb_pct).fillna(0).astype(float)
    reb_dini = (_reb >= 3.0)        # gate intraday: rebound dari low ATAU naik dari open
    reb_besar = (_reb >= 8.0)       # momentum kedua / pyramiding
    # --- v6.1: pembekal kemarin hanya PELUNAK (bukan syarat wajib) ---
    _sk = tk.map(skor_pembekal).fillna(0).astype(int)
    bekal_kuat = (_sk >= 4)
    bekal_min = (_sk >= 2)
    # MOMENTUM 30 MENIT legacy (tidak lagi dipakai wajib; dipertahankan utk kompatibilitas)
    if isinstance(momentum_30m, dict) and momentum_30m:
        mom_set = set(momentum_30m.keys())
    else:
        mom_set = set()
    mom30 = tk.isin(mom_set) if mom_set else pd.Series(True, index=df.index)

    # --- v6.1: kolom intraday hari ini (bukan struktur kemarin) ---
    supply_kering = df['Kondisi Supply'].astype(str).str.contains('Kering', na=False) if 'Kondisi Supply' in df.columns else pd.Series(False, index=df.index)
    marubozu = (df.get('Pola Candle', '') == 'Marubozu (Strong Bullish)')
    hammer = (df.get('Pola Candle', '') == 'Hammer (Potensi Reversal)') | \
             (df.get('Sinyal Cuci Barang', '') == 'Jarum Bawah (Sinyal Pantulan Kuat)')
    haka = (df.get('Tekanan Bandar', '') == 'Dominan Beli (Hajar Kanan)')
    # --- v6.1 PERBAIKAN BUG: sisir AKTIF hanya "spike 12H"; filter lama (contains) ikut
    # menangkap "Pola Sisir Lemah" sehingga tidak menyeleksi apa pun ---
    sisir_aktif = df.get('Pola Sisir', '').astype(str).str.contains('spike 12H', na=False) if 'Pola Sisir' in df.columns else pd.Series(False, index=df.index)

    # RUMUS 1 — Hajar Kanan Momentum (inti v6.1): beli dominan + gate intraday
    out[1] = df[haka & reb_dini & ~supply_banjir & (vwap_kuat | marubozu)].copy()
    # RUMUS 2 — Marubozu Breakout: candle kekuatan penuh + vol tembus MA20
    out[2] = df[marubozu & reb_dini & vol_tembus & ~supply_banjir].copy()
    # RUMUS 3 — Sisir Aktif Breakout (fix bug: benar-benar hanya sisir spike 12H)
    out[3] = df[sisir_aktif & reb_dini & ~supply_banjir].copy()
    # RUMUS 4 — Pantulan Hammer: jarum bawah/hammer + pembekal kemarin (pelunak)
    out[4] = df[hammer & reb_dini & (bekal_min | akumulasi_pro) & vwap_ok & ~supply_banjir].copy()
    # RUMUS 5 — Akumulasi Pro Turnaround: smart money naik walau fase masih jelek
    out[5] = df[akumulasi_pro & reb_dini & haka & ~supply_banjir].copy()
    # RUMUS 6 — Mark-Up Kontinu: fase pesta + gate intraday (struktur kemarin valid saat fase benar)
    out[6] = df[mark_up & reb_dini & ~supply_banjir & (haka | vol_tembus)].copy()
    # RUMUS 7 — Momentum Besar (reb>=8%): pyramiding, konfirmasi ganda
    out[7] = df[reb_besar & vol_tembus & (haka | akumulasi_pro | macd_bull) & ~supply_banjir].copy()
    # RUMUS 8 — MACD Bull Rebound: tren balik + gate intraday
    out[8] = df[macd_bull & reb_dini & (haka | akumulasi_pro) & ~supply_banjir].copy()
    # RUMUS 9 — Skor Tinggi Konfirmasi: total score tinggi + konfirmasi intraday
    out[9] = df[(score_num >= 5) & reb_dini & (haka | vol_tembus | macd_bull) & ~supply_banjir].copy()
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
