# ==========================================
# 🧠 SIDANG LIB — sidang autopilot headless (cron laptop)
# Aturan IDENTIK dengan app.py web: rumus v5.1.
# Jika ubah rumus/ambang: ubah DI SINI dan DI app.py.
# ==========================================
import os, json, re, time
import pandas as pd

VERSI_SIDANG = "v5.1"
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

def hitung_rumus(df):
    """Rumus v5.1 — identik dengan app.py PART 12."""
    out = {i: pd.DataFrame() for i in range(1, 10)}
    if df is None or df.empty or 'Tekanan Bandar' not in df.columns:
        return out
    vwap_ok = (df.get('Posisi VWAP', '') != 'Di Bawah VWAP (Lemah)')
    vwap_kuat = (df.get('Posisi VWAP', '') == 'Di Atas VWAP (Kuat)')
    akumulasi_pro = (df.get('Kekuatan A/D', '') == 'Akumulasi Pro (Smart Money)')
    change_num = pd.to_numeric(df.get('Change (%)', 0), errors='coerce')
    supply_banjir = df['Kondisi Supply'].astype(str).str.contains('Banjir', na=False) if 'Kondisi Supply' in df.columns else False
    out[1] = df[akumulasi_pro & (df.get('Status Bandar', '') == 'Akumulasi Kuat') & vwap_kuat & ~supply_banjir].copy()
    out[2] = df[((df.get('Pola Candle', '') == 'Hammer (Potensi Reversal)') |
                 (df.get('Sinyal Cuci Barang', '') == 'Jarum Bawah (Sinyal Pantulan Kuat)')) & vwap_kuat & akumulasi_pro].copy()
    out[3] = df[vwap_kuat & (df.get('Tekanan Bandar', '') == 'Dominan Beli (Hajar Kanan)') &
                (df.get('Status Open', '') == 'Open = Low (Bullish Kuat)') & (df.get('Rekomendasi', '') == 'BELI')].copy()
    out[4] = df[(df.get('MA Cross', '') == 'Golden Cross') & (df.get('Vol Breakout', '') == 'Tembus MA20') &
                (df.get('MA Signal', '') == 'Uptrend') & vwap_kuat &
                (df.get('Tekanan Bandar', '') == 'Dominan Beli (Hajar Kanan)')].copy()
    out[5] = df[(df.get('Kelas Transaksi', '') == 'Ritel Aktif (5M - 50M)') & (df.get('Vol Breakout', '') == 'Tembus MA20') &
                vwap_kuat & (df.get('MA Signal', '') == 'Uptrend') &
                ((df.get('Tekanan Bandar', '') == 'Dominan Beli (Hajar Kanan)') | akumulasi_pro)].copy()
    out[6] = df[(df.get('RVOL (Anomali Vol)', '').isin(['Anomali Tinggi (150-300%)', 'Ledakan Ekstrem (> 300%)'])) &
                (df.get('OBV Trend', '') == 'Akumulasi (Naik)') & (change_num <= 5.0) &
                (df.get('Tekanan Bandar', '') == 'Dominan Beli (Hajar Kanan)')].copy()
    out[7] = df[(df.get('Prediksi Machine Learning', '') == '🔥 ANOMALI BANDAR (Siap Ledakan)') &
                (df.get('Status Stochastic', '').isin(['Oversold (Jenuh Jual - Peluang)', 'Golden Cross (Awal Bullish)'])) & vwap_kuat].copy()
    out[8] = df[((df.get('Status Sentimen', '') == 'Sentimen Positif 📰') |
                 (df.get('Status Akuisisi', '').isin(['RENCANA AKUISISI', 'DALAM AKUISISI']))) &
                (df.get('MA Signal', '') == 'Uptrend') & (df.get('Rekomendasi', '') == 'BELI')].copy()
    out[9] = df[(df.get('MACD', '').isin(['Strong Bullish', 'Bullish MACD'])) &
                (df.get('Risk/Reward Ratio', '').isin(['Sangat Menarik (> 1:3)', 'Ideal (1:2)'])) &
                (df.get('Posisi Entry', '') == 'Dekat Support (Low Risk)') & (df.get('Momentum', '') == 'Positif') & vwap_ok].copy()
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
