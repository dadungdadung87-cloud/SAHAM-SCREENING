# =====================================================================
# 🗺️  PETA PART app.py v5.0
# ---------------------------------------------------------------------
# PART 01 : IMPOR MODUL (+ autorefresh)
# PART 02 : FUNGSI AI KLASIK
# PART 03 : MESIN AUTO-PILOT CEPAT + narasi bersama
# PART 04 : SISTEM ARSIP CERDAS
# PART 05 : PENGATURAN UI/UX & CSS
# PART 06 : LOAD KONFIGURASI JSON
# PART 07 : PRESET & LOAD DATA SAHAM
# PART 08 : HEADER & SIDEBAR
# PART 09 : FORMATTER & PEWARNAAN TABEL
# PART 10 : TAB 1 - MARKET OVERVIEW
# PART 11 : TAB 2 - SCREENER UTAMA
# PART 12 : TAB 3 - ASISTEN AI (RUMUS v5.0 + RADAR LIVE)
# PART 13 : TAB 4 - PORTOFOLIO BOT (+ KURASI)
# PART 14 : TAB 5 - DETEKTIF LEDAKAN
# =====================================================================


# =====================================================================
# >>> PART 01 : IMPOR MODUL <<<
# =====================================================================
import io
import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import glob
import time
import re
import random
from datetime import datetime

# IMPORT UNTUK AI OPENROUTER & GOOGLE
from openai import OpenAI
import google.generativeai as genai

# REFRESH OTOMATIS UNTUK RADAR LIVE (TAB 3)
try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_OK = True
except Exception:
    AUTOREFRESH_OK = False


# =====================================================================
# >>> PART 02 : FUNGSI AI KLASIK (Hakim, OpenRouter, Turnamen) <<<
# =====================================================================
def ai_hakim_klasemen(data_top15, api_key):
    import google.generativeai as genai
    import time
    genai.configure(api_key=api_key)
    
    prompt = f"""
    Select EXACTLY 5 Tickers that have the highest combination of 'Score' and 'Volume' from the data below.
    Calculate 'Target_TP' (+5% from Harga) and 'Target_CL' (-3% from Harga).
    
    DATA:
    {data_top15}
    
    Output a JSON array containing objects with EXACTLY 3 keys: "Ticker", "Target_TP", "Target_CL".
    """
    
    daftar_model_aktif = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                nama_bersih = m.name.replace("models/", "")
                if "1.5" in nama_bersih:
                    daftar_model_aktif.insert(0, nama_bersih)
                else:
                    daftar_model_aktif.append(nama_bersih)
    except Exception as e:
        return f"Error_AI (Gagal menyalakan radar): {e}"

    if not daftar_model_aktif:
        return "Error_AI: Tidak ada satupun model Gemini yang online untuk API Key ini."

    pesan_error_terakhir = ""
    for nama_model in daftar_model_aktif:
        try:
            model = genai.GenerativeModel(
                nama_model,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0, 
                    response_mime_type="application/json"
                )
            )
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            pesan_error_terakhir = str(e)
            time.sleep(1) 
            continue 
            
    return f"Error_AI (Semua model aktif gagal eksekusi): {pesan_error_terakhir}"

# AI BANDAR (V6)
def analisa_bandar_ai_multisaham(data_saham_dict, pilihan_ai):
    try:
        OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY"))
    except:
        OPENROUTER_API_KEY = None
    if not OPENROUTER_API_KEY: return "❌ Kunci API OpenRouter belum dipasang!"

    model_andalan = "openrouter/free" 

    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
        
        payload_text = ""
        for ticker, data in data_saham_dict.items():
            payload_text += f"\n--- STOCK: {ticker} ---\n"
            payload_text += f"Current Price: Rp {data['harga']}\n"
            payload_text += f"Today's Change: {data['change']}%\n"
            payload_text += f"Broker Summary: {data['broksum']}\n"
            payload_text += f"Wyckoff Phase: {data['status']}\n"
            payload_text += f"Technical Score: {data['skor']}/10\n"
            payload_text += f"Historical Trace (Daily):\n{data['histori']}\n"

        prompt = f"""
        You are the mastermind of an elite Indonesian stock market syndicate (Mega Bandar). 
        Your specialty is 'Gorengan' (highly volatile) stocks. You DO NOT buy stocks that have already pumped today. You look for "Stealth Accumulation"—stocks that are currently sideways or slightly up (Change is <= 5%), but have massive hidden accumulation in the historical intraday data, indicating they are ready to EXPLODE to top gainers tomorrow.

        I have filtered and provided {len(data_saham_dict)} candidate stocks that haven't pumped yet today.

        YOUR TASK:
        Analyze the 'Historical Trace' and 'Broker Summary' carefully. Select ONLY THE TOP 5 STOCKS that have completed their stealth accumulation phase today (by 15:00) and are 100% ready for a massive Mark-Up tomorrow morning (BSJP strategy).

        STOCK DATA TO ANALYZE:
        {payload_text}

        STRICT RULES:
        1. OUTPUT LANGUAGE: MUST be in Indonesian.
        2. DO NOT list all stocks. ONLY output your Top 5 selections.
        3. Create a Markdown table: [Peringkat, Ticker, Skor Ledakan (0-100%), Status Saat Ini].
        4. Below the table, provide a brutally analytical explanation for each stock. Prove why the pump is imminent by citing specific anomalies from the 'Historical Trace' and 'Broker Summary'.
        5. Provide a realistic Trading Plan (Buy Area near Current Price, Target Price for a massive pump >10%, and a tight Cut Loss). 
        6. Act like a ruthless market maker. No pleasantries. Start immediately with the table.
        """
        completion = client.chat.completions.create(
            model=model_andalan, messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=3000, top_p=1, stream=False,
        )
        
        hasil_mentah = completion.choices[0].message.content
        model_terpakai = completion.model
        
        if not hasil_mentah:
            return f"⚠️ Server AI (Model: {model_terpakai}) gagal memberikan jawaban. Silakan coba lagi."
            
        return hasil_mentah + f"\n\n---\n⚡ *Dianalisa otomatis menggunakan mesin: **{model_terpakai}** via OpenRouter*"
    except Exception as e: return f"❌ Gagal memproses data dengan OpenRouter menggunakan auto-model. Error: {e}"

# AI FORENSIK BANDAR (V7)
def analisa_forensik_ai(data_saham_dict, master_filters_keys):
    try:
        OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY"))
    except:
        OPENROUTER_API_KEY = None
    if not OPENROUTER_API_KEY: return "❌ Kunci API OpenRouter belum dipasang!"

    model_andalan = "openrouter/free" 

    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
        payload_text = ""
        for ticker, data in data_saham_dict.items():
            payload_text += f"\n--- STOCK: {ticker} ---\n"
            payload_text += f"Broker Summary (Hari H): {data['broksum']}\n"
            payload_text += f"{data['histori']}\n"

        prompt = f"""
        You are a legendary Quantitative Analyst and Stock Market Forensic Expert in Indonesia.
        I am giving you the historical data of {len(data_saham_dict)} stocks from EXACTLY 1 TO 3 DAYS BEFORE they skyrocketed to Top Gainers / ARA (>10%). This is their condition BEFORE the pump.

        YOUR OBJECTIVE:
        1. Reverse engineer the 'Bandar' strategy. Find the exact common "DNA" or hidden patterns that occurred in these stocks during the 3 days BEFORE they exploded, including their Broker Summary activity.
        2. Cross-reference your findings with the EXISTING WEB FILTERS in my application.
        3. Suggest new metrics if my existing filters are missing the secret sauce.

        DATA STOCKS (H-3 to H-1 before pump):
        {payload_text}

        MY EXISTING WEB FILTERS (Categories you can use):
        {master_filters_keys}

        STRICT RULES:
        1. OUTPUT LANGUAGE: MUST be in Indonesian.
        2. Format your response into 3 sections using Markdown:
           - "### 🧬 DNA & Pola Tersembunyi Sebelum Ledakan": Explain exactly what similarities these stocks shared (e.g., "Ketiga saham ini mengalami penurunan harga, namun OBV terus naik dan volume ditahan...").
           - "### 🎛️ Resep Filter Web Saat Ini": Tell me EXACTLY how to set my existing filters (based on the provided list) to catch this pattern tomorrow.
           - "### 💡 Rekomendasi Rumus/Kategori Baru": If there is a pattern not covered by my filters, explicitly suggest what new filter/indicator I should code into my web application.
        3. Be highly analytical, specific, and brutally honest. Do not hallucinate.
        """
        completion = client.chat.completions.create(
            model=model_andalan, messages=[{"role": "user", "content": prompt}],
            temperature=0.2, max_tokens=3000, top_p=1, stream=False,
        )
        
        hasil_mentah = completion.choices[0].message.content
        model_terpakai = completion.model
        
        if not hasil_mentah:
            return f"⚠️ Server AI (Model: {model_terpakai}) gagal memberikan jawaban. Silakan coba lagi."
            
        return hasil_mentah + f"\n\n---\n🔬 *Lab Forensik AI menggunakan: **{model_terpakai}** via OpenRouter*"
    except Exception as e: return f"❌ Gagal memproses data dengan OpenRouter. Error: {e}"

def ai_penyisihan_turnamen(data_grup_dict, api_key):
    saham_grup_ini = list(data_grup_dict.keys())
    daftar_model_estafet = [
        'gemini-3.7-flash', 
        'gemini-3.6-flash',
        'gemini-3.5-flash',
        'gemini-flash-latest',
        'gemini-3.5-flash-lite',
        'gemini-3.1-flash-lite',
        'gemini-flash-lite-latest'
    ]
    genai.configure(api_key=api_key)
    payload_text = ""
    for ticker, data in data_grup_dict.items():
        payload_text += f"\n- {ticker}: Harga {data['harga']}, Vol {data['volume']}, Tekanan {data['tekanan_bandar']}, Supply {data['supply']}"
        
    prompt = f"""
    Act as a simple data sorter for a mathematical simulation.
    Here is a list of items and their stats:
    {payload_text}
    
    Your ONLY task is to pick the 3 best items based on Volume and Tekanan. 
    Even if all data is bad, you MUST pick exactly 3.
    Output ONLY a comma-separated list of the 3 items (e.g., BBCA,GOTO,PANI).
    DO NOT add any conversational text or markdown.
    """
    
    for nama_model in daftar_model_estafet:
        try:
            model = genai.GenerativeModel(nama_model)
            response = model.generate_content(prompt)
            raw_content = response.text.upper()
            
            semua_kata = re.findall(r'[A-Z]+', raw_content)
            lolos = []
            for kata in semua_kata:
                if kata in saham_grup_ini and kata not in lolos:
                    lolos.append(kata)
            
            if len(lolos) == 0:
                lolos = saham_grup_ini[:3]
                
            lolos_final = lolos[:3]
            return ",".join(lolos_final)
            
        except Exception as e:
            time.sleep(2)
            continue
            
    return ",".join(saham_grup_ini[:3])


def ai_grand_final_top5(data_saham_dict, api_key):
    import json
    daftar_model_estafet = [
        'gemini-3.7-flash', 
        'gemini-3.6-flash',
        'gemini-3.5-flash',
        'gemini-flash-latest',
        'gemini-3.5-flash-lite',
        'gemini-3.1-flash-lite',
        'gemini-flash-lite-latest'
    ]
    genai.configure(api_key=api_key)
    
    payload_text = ""
    for ticker, data in data_saham_dict.items():
        payload_text += f"\n--- {ticker} ---\n Harga: {data['harga']} | Vol: {data['volume']} | Broksum: {data['broksum']} | Tekanan: {data['tekanan_bandar']} | Supply: {data['supply']} | OBV: {data['obv']} | Fibo: {data['fibo']} | VWAP: {data['vwap']} | Candle: {data['pola_candle']}\n"

    prompt = f"""
    Act as an objective data formatting tool for a hypothetical academic simulation. THIS DOES NOT CONSTITUTE FINANCIAL ADVICE.
    Evaluate these fictionalized mathematical metrics:
    
    {payload_text}
    
    MISSION: Select EXACTLY 5 items that show the strongest theoretical accumulation score. Provide a theoretical 'Target_TP' and 'Target_CL' purely for simulation testing.
    
    CRITICAL INSTRUCTION: You are an automated JSON API endpoint. 
    You MUST output ONLY a raw, valid JSON array.
    DO NOT output any safety warnings, disclaimers, explanations, or conversational text.
    DO NOT wrap your response in markdown code blocks (DO NOT use ```json or ```).
    Your response must start exactly with '[' and end exactly with ']'.
    
    VERY IMPORTANT: The text inside the "Alasan" key MUST be written in fluent Bahasa Indonesia.
    
    Format EXACTLY like this:
    [
      {{"Peringkat": 1, "Ticker": "GOTO", "Alasan": "Akumulasi volume sangat tinggi dengan tekanan beli dominan", "Target_TP": 60, "Target_CL": 50}}
    ]
    """
    
    for nama_model in daftar_model_estafet:
        try:
            model = genai.GenerativeModel(nama_model)
            response = model.generate_content(prompt)
            raw_content = response.text or ""
            
            clean_content = raw_content.replace('```json', '').replace('```', '').strip()
            return clean_content, nama_model
            
        except Exception as e:
            time.sleep(3)
            continue
            
    raise Exception("🚨 KRITIS: Semua 7 model AI Gemini sedang mengalami limit maksimal atau server sibuk. Mohon jeda turnamen 1-2 menit sebelum mencoba lagi.")


# =====================================================================
# >>> PART 03 : MESIN AUTO-PILOT CEPAT & PARALEL (+ REM CERDAS) + 9 RONDE <<<
# =====================================================================
def radar_model_gemini_cepat(api_key):
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

def panggil_ai_teks(prompt):
    """Mesin narasi gratis: Gemini flash dulu, fallback OpenRouter free."""
    try:
        GK = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
        if GK:
            genai.configure(api_key=GK)
            for mn in ["gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-1.0-pro"]:
                try:
                    r = genai.GenerativeModel(mn).generate_content(prompt)
                    if r.text: return r.text, f"Gemini ({mn})"
                except Exception:
                    continue
    except Exception:
        pass
    try:
        OK_ = st.secrets.get("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY"))
        if OK_:
            cp = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OK_).chat.completions.create(
                model="openrouter/free", messages=[{"role": "user", "content": prompt}], temperature=0.4, max_tokens=1200)
            isi = cp.choices[0].message.content
            if isi: return isi, "OpenRouter"
    except Exception as e:
        return f"❌ AI gagal: {e}", "error"
    return "❌ Tidak ada mesin AI gratis tersedia.", "error"

def ai_hakim_klasemen_cepat(data_top15, api_key, daftar_model):
    genai.configure(api_key=api_key)
    prompt = f"""
    Select EXACTLY 5 Tickers that have the highest combination of 'Score' and 'Volume' from the data below.

    DATA:
    {data_top15}

    CRITICAL: Output ONLY a raw JSON array with EXACTLY 5 objects, each with EXACTLY 1 key: "Ticker".
    DO NOT add explanations, markdown, or any other text. Keep the output as short as possible.
    """
    pesan_error_terakhir = ""
    for nama_model in daftar_model:
        try:
            model = genai.GenerativeModel(
                nama_model,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                    max_output_tokens=1024,
                )
            )
            response = model.generate_content(prompt)
            teks = response.text or ""
            if not teks.strip():
                pesan_error_terakhir = "Respons kosong dari model"
                continue
            return teks
        except Exception as e:
            pesan_error_terakhir = str(e)
            if any(k in str(e) for k in ["429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]):
                time.sleep(5)
            else:
                time.sleep(1)
            continue
    return f"Error_AI (Semua model aktif gagal eksekusi): {pesan_error_terakhir}"

# =====================================================================
# 🎲 FUNGSI UNTUK UJI KONSISTENSI 9 RONDE (BARU)
# =====================================================================
def ai_top5_dari_daftar(data_dict, api_key, daftar_model, suhu=0.4):
    """AI memilih Top 5 dari daftar saham dengan JSON murni (tanpa penjelasan)."""
    genai.configure(api_key=api_key)
    payload_text = ""
    for ticker, d in data_dict.items():
        payload_text += (f"\n- {ticker}: Harga {d['harga']} | Change {d['change']}% | Vol {d['volume']} | Score {d['skor']} | "
                         f"Tekanan {d['tekanan']} | A/D {d['ad']} | VWAP {d['vwap']} | Supply {d['supply']} | Siklus {d['siklus']} | RVOL {d['rvol']}")
    prompt = f"""
    You are an elite Indonesian stock analyst for BSJP strategy (buy at close, sell at morning gap).
    Candidate stocks with today's metrics (list order is RANDOMIZED; judge purely by data quality):
    {payload_text}

    MISSION: Select EXACTLY 5 DIFFERENT tickers (NO duplicates, NO repeats) from the candidate list above, with the strongest accumulation & readiness for tomorrow morning's upward move.
    CRITICAL: Output ONLY a raw JSON array of 5 objects, each with EXACTLY 1 key: "Ticker".
    DO NOT add explanations, markdown, or any other text.
    """
    pesan_terakhir = ""
    for nama_model in daftar_model:
        try:
            model = genai.GenerativeModel(
                nama_model,
                generation_config=genai.types.GenerationConfig(
                    temperature=suhu,
                    response_mime_type="application/json",
                    max_output_tokens=512,
                )
            )
            response = model.generate_content(prompt)
            teks = response.text or ""
            if not teks.strip():
                pesan_terakhir = "Respons kosong"
                continue
            return teks
        except Exception as e:
            pesan_terakhir = str(e)
            time.sleep(2)
            continue
    return f"Error_AI: {pesan_terakhir}"

def _parse_ticker_top5(mentah, valid_set):
    hasil = []
    # Lapis 1: parse blok JSON
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
    # Lapis 2: penyelamat regex jika masih <5 (menyelamatkan ticker dari respons terpotong)
    if len(hasil) < 5:
        for m in re.finditer(r'\b([A-Z]{4})\b', mentah):
            t = m.group(1)
            if t in valid_set and t not in hasil:
                hasil.append(t)
            if len(hasil) >= 5:
                break
    return hasil[:5]

def jalankan_9_ronde_acak(df_data, daftar_ticker, api_key, progress_bar=None, status_teks=None):
    """Menjalankan 9 ronde pemilihan Top 5 dengan urutan acak setiap ronde."""
    df_seleksi = df_data[df_data['Ticker'].isin(daftar_ticker)].copy()
    if df_seleksi.empty:
        return None, "❌ Tidak ada ticker valid di database hari ini."
    # Batasi max 50 saham untuk mencegah konteks AI overflow
    if len(df_seleksi) > 50:
        df_seleksi['Score_Num'] = pd.to_numeric(df_seleksi['Total Score'], errors='coerce').fillna(0)
        df_seleksi = df_seleksi.sort_values('Score_Num', ascending=False).head(50)
    daftar_model = radar_model_gemini_cepat(api_key)
    if not daftar_model:
        return None, "❌ Tidak ada model Gemini yang online untuk API Key ini."
    
    hasil_ronde = {}
    urutan_sebelumnya = []
    for ronde in range(1, 10):
        if status_teks: status_teks.info(f"🎲 Ronde {ronde}/9: mengacak urutan & menggelar sidang AI...")
        acak = df_seleksi['Ticker'].tolist()
        # Jaminan urutan berbeda dari ronde sebelumnya
        while acak == urutan_sebelumnya and len(acak) > 1:
            random.shuffle(acak)
        urutan_sebelumnya = acak
        
        data_dict = {}
        for t in acak:
            row = df_seleksi[df_seleksi['Ticker'] == t].iloc[0]
            data_dict[t] = {
                'harga': row.get('Harga (Rp)', 0), 'change': row.get('Change (%)', 0),
                'volume': row.get('Volume', 0), 'skor': row.get('Total Score', 0),
                'tekanan': row.get('Tekanan Bandar', 'Normal'), 'ad': row.get('Kekuatan A/D', 'Normal'),
                'vwap': row.get('Posisi VWAP', 'Normal'), 'supply': row.get('Kondisi Supply', 'Normal'),
                'siklus': row.get('Fase Siklus Bandar', 'Normal'), 'rvol': row.get('RVOL (Anomali Vol)', 'Normal'),
            }
        top5 = []
        pesan_terakhir = ""
        for percobaan in range(1, 3):  # maksimal 2x percobaan per ronde
            mentah = ai_top5_dari_daftar(data_dict, api_key, daftar_model)
            if "Error_AI" in mentah:
                pesan_terakhir = mentah
                continue
            top5 = _parse_ticker_top5(mentah, set(acak))
            if len(top5) >= 5 or len(acak) < 5:
                break
        if not top5:
            hasil_ronde[ronde] = []
            if status_teks: status_teks.warning(f"⚠️ Ronde {ronde} gagal: {pesan_terakhir[:80] if pesan_terakhir else 'kurang dari 5 setelah 2 percobaan'}")
        else:
            hasil_ronde[ronde] = top5
            if status_teks: status_teks.success(f"✅ Ronde {ronde} selesai: {', '.join(top5)}")
        if progress_bar: progress_bar.progress(ronde / 9.0)
    return hasil_ronde, None
# =====================================================================

def jalankan_sidang_autopilot(daftar_rumus, df_data, api_key, progress_bar=None, status_teks=None):
    import concurrent.futures

    keranjang = {f"RUMUS {i}": ["", "", "", "", ""] for i in range(1, 10)}
    laporan = {i: {"status": "⏭️ Kosong", "detail": "Tidak ada saham yang lolos rumus ini"} for i in range(1, 10)}

    if status_teks: status_teks.info("📡 Radar model: menarik daftar model Gemini online (cukup sekali)...")
    daftar_model = radar_model_gemini_cepat(api_key)
    if not daftar_model:
        return keranjang, "❌ Tidak ada model Gemini yang online untuk API Key ini.", laporan

    def sidang_satu_rumus(i):
        try:
            df_target = daftar_rumus[i]
            n_kandidat = len(df_target)
            saham_valid = df_target['Ticker'].tolist()
            df_seleksi = df_data[df_data['Ticker'].isin(saham_valid)].copy()
            df_seleksi['Score_Num'] = pd.to_numeric(df_seleksi['Total Score'], errors='coerce').fillna(0)
            df_sorted = df_seleksi.sort_values(by=['Score_Num', 'Volume', 'Change (%)'], ascending=[False, False, False])

            if n_kandidat <= 5:
                tickers_ai = df_sorted['Ticker'].tolist()[:5]
            else:
                top_15 = df_sorted.head(15)
                data_kirim_ai = {}
                for _, row in top_15.iterrows():
                    data_kirim_ai[row['Ticker']] = {
                        'Harga': row.get('Harga (Rp)', 0),
                        'Volume': row.get('Volume', 0),
                        'Score': row.get('Score_Num', 0),
                        'Change_Pct': row.get('Change (%)', 0),
                        'Tekanan_Bandar': row.get('Tekanan Bandar', 'Normal'),
                        'Broksum': row.get('Broksum', 'Normal')
                    }

                hasil_mentah = ai_hakim_klasemen_cepat(data_kirim_ai, api_key, daftar_model)
                if "Error_AI" in hasil_mentah:
                    return i, n_kandidat, None, hasil_mentah

                hasil_json = None
                semua_blok_kurung = re.findall(r'\[.*\]', hasil_mentah, re.DOTALL)
                for blok in reversed(semua_blok_kurung):
                    try:
                        blok_bersih = blok.replace("'", '"')
                        blok_bersih = re.sub(r',\s*\]', ']', blok_bersih)
                        calon = json.loads(blok_bersih)
                        if isinstance(calon, list):
                            hasil_json = calon
                            break
                    except:
                        continue

                tickers_ai = []
                if hasil_json is not None:
                    for item in hasil_json:
                        t = (item.get("Ticker", "") if isinstance(item, dict) else str(item)).strip().upper()
                        if t and t in data_kirim_ai and t not in tickers_ai:
                            tickers_ai.append(t)
                else:
                    for m in re.finditer(r'Ticker"\s*:\s*"([A-Za-z0-9]+)', hasil_mentah):
                        t = m.group(1).strip().upper()
                        if t and t in data_kirim_ai and t not in tickers_ai:
                            tickers_ai.append(t)
                tickers_ai = tickers_ai[:5]

                if not tickers_ai:
                    return i, n_kandidat, None, f"AI tidak mengembalikan ticker valid. Respons: {hasil_mentah[:120]}"

            baris_sinyal = []
            for t in tickers_ai:
                row = df_sorted[df_sorted['Ticker'] == t]
                if row.empty: continue
                harga = float(row.iloc[0]['Harga (Rp)'])
                baris_sinyal.append({
                    "Ticker": t,
                    "Target_TP": int(round(harga * 1.05)),
                    "Target_CL": int(round(harga * 0.97)),
                })
            if baris_sinyal:
                pd.DataFrame(baris_sinyal).to_csv(f"Database/sinyal_ai_rumus_{i}.csv", index=False)

            jawara = [b["Ticker"] for b in baris_sinyal]
            return i, n_kandidat, (jawara + ["", "", "", "", ""])[:5], None
        except Exception as e:
            return i, len(daftar_rumus[i]), None, str(e)

    rumus_aktif = [i for i in range(1, 10) if len(daftar_rumus[i]) > 0]
    for i in range(1, 10):
        if len(daftar_rumus[i]) == 0 and status_teks:
            status_teks.warning(f"⏭️ Rumus {i} kosong. Dilewati.")

    if status_teks: status_teks.info(f"🚀 Sidang paralel dimulai: {len(rumus_aktif)} rumus aktif, 2 hakim bekerja bersamaan...")

    selesai = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(sidang_satu_rumus, i) for i in rumus_aktif]
        for fut in concurrent.futures.as_completed(futures):
            i, n_kandidat, jawara, err = fut.result()
            selesai += 1
            if progress_bar: progress_bar.progress(min(selesai / 9.0, 1.0))
            if err:
                laporan[i] = {"status": "❌ Gagal", "detail": f"{n_kandidat} kandidat | {err[:120]}"}
                keranjang[f"RUMUS {i}"] = ["", "", "", "", ""]
                if status_teks: status_teks.error(f"❌ Rumus {i} gagal: {err[:120]}")
            else:
                n_jawara = len([t for t in jawara if t])
                catatan = "≤5 kandidat: urut skor (tanpa AI)" if n_kandidat <= 5 else f"{n_kandidat} kandidat → sidang AI"
                laporan[i] = {"status": "✅ Sukses", "detail": f"{catatan} → {n_jawara} jawara"}
                keranjang[f"RUMUS {i}"] = jawara
                if status_teks: status_teks.success(f"✅ Rumus {i} selesai ({selesai}/{len(rumus_aktif)}).")

    if progress_bar: progress_bar.progress(1.0)

    try:
        import r2_client
        for i in range(1, 10):
            f_sinyal = f"Database/sinyal_ai_rumus_{i}.csv"
            if os.path.exists(f_sinyal):
                r2_client.upload_arsip(f_sinyal, f"Database/sinyal_ai_rumus_{i}.csv")
    except Exception:
        pass

    return keranjang, None, laporan


# =====================================================================
# >>> PART 04 : SISTEM ARSIP CERDAS (DATA HARIAN) — R2 + LOKAL <<<
# =====================================================================
import r2_client
import tempfile

@st.cache_data(ttl=60)
def _muat_arsip_r2():
    keys = r2_client.list_arsip()
    keys.sort(reverse=True)
    hasil = []
    for key in keys[:5]:
        date_str = key.split("_")[-1].replace(".csv", "")
        tmp = os.path.join(tempfile.gettempdir(), f"arsip_r2_{date_str}.csv")
        if r2_client.download_arsip(key, tmp):
            try:
                hasil.append((date_str, pd.read_csv(tmp)))
            except Exception:
                pass
    return hasil

def _muat_arsip_lokal():
    arsip_files = glob.glob("Arsip_Data_Harian/screener_*.csv")
    arsip_files.sort(reverse=True)
    hasil = []
    for file in arsip_files[:5]:
        date_str = file.split("_")[-1].replace(".csv", "")
        try:
            hasil.append((date_str, pd.read_csv(file)))
        except Exception:
            pass
    return hasil

def muat_arsip():
    data = _muat_arsip_r2()
    if not data:
        data = _muat_arsip_lokal()
    return data

def get_historical_summary(ticker):
    cols = ["Waktu Update", "Ticker", "Harga (Rp)", "Volume", "Posisi VWAP", "OBV Trend", "Tekanan Bandar", "Fase Siklus Bandar", "Trend MA (5,20,50)"]
    df_list = []
    for date_str, df in muat_arsip():
        try:
            ada_cols = [c for c in cols if c in df.columns]
            temp_df = df[ada_cols]
            temp_df = temp_df[temp_df["Ticker"] == ticker]
            if not temp_df.empty:
                temp_df = temp_df.copy()
                temp_df["Tanggal"] = date_str
                df_list.append(temp_df)
        except Exception:
            pass
    
    if not df_list: return None
    df_history = pd.concat(df_list, ignore_index=True)
    df_history = df_history.sort_values(by=["Tanggal", "Waktu Update"])
    
    summary_text = f"REKAM JEJAK ARSIP HARIAN SAHAM {ticker}:\n\n"
    for date, group in df_history.groupby("Tanggal"):
        open_price = group.iloc[0]["Harga (Rp)"]
        close_price = group.iloc[-1]["Harga (Rp)"]
        max_vol = group["Volume"].max()
        tekanan_akhir = group.iloc[-1]["Tekanan Bandar"]
        siklus = group.iloc[-1]["Fase Siklus Bandar"]
        summary_text += f"📅 {date} | Buka: {open_price} | Tutup: {close_price} | Max Vol Harian: {max_vol} | Tekanan Akhir: {tekanan_akhir} | Siklus Wyckoff: {siklus}\n"
    return summary_text

def get_forensic_data(ticker):
    cols = ["Waktu Update", "Ticker", "Harga (Rp)", "Volume", "Posisi VWAP", "OBV Trend", "Tekanan Bandar", "Fase Siklus Bandar", "Trend MA (5,20,50)", "Status BB", "RVOL (Anomali Vol)"]
    df_list = []
    for date_str, df in muat_arsip():
        try:
            ada_cols = [c for c in cols if c in df.columns]
            temp_df = df[ada_cols]
            temp_df = temp_df[temp_df["Ticker"] == ticker]
            if not temp_df.empty:
                temp_df = temp_df.copy()
                temp_df["Tanggal"] = date_str
                df_list.append(temp_df)
        except Exception:
            pass
    
    if not df_list: return None
    df_history = pd.concat(df_list, ignore_index=True)
    df_history = df_history.sort_values(by=["Tanggal", "Waktu Update"])
    
    tanggal_unik = sorted(df_history["Tanggal"].unique())
    if len(tanggal_unik) > 1:
        tanggal_unik = tanggal_unik[:-1] 
        tanggal_unik = tanggal_unik[-3:] 
    else:
        return "Data historis sebelum hari ini belum tersedia di arsip."
        
    df_history = df_history[df_history["Tanggal"].isin(tanggal_unik)]
    
    summary_text = f"REKAM JEJAK H-3 SEBELUM MELEDAK SAHAM {ticker}:\n"
    for date, group in df_history.groupby("Tanggal"):
        close_price = group.iloc[-1]["Harga (Rp)"]
        max_vol = group["Volume"].max()
        tekanan_akhir = group.iloc[-1]["Tekanan Bandar"]
        siklus = group.iloc[-1]["Fase Siklus Bandar"]
        obv = group.iloc[-1]["OBV Trend"] if "OBV Trend" in group.columns else "N/A"
        rvol = group.iloc[-1]["RVOL (Anomali Vol)"] if "RVOL (Anomali Vol)" in group.columns else "N/A"
        bb = group.iloc[-1]["Status BB"] if "Status BB" in group.columns else "N/A"
        
        summary_text += f"📅 {date} | Tutup: {close_price} | Vol: {max_vol} | Tekanan: {tekanan_akhir} | Siklus: {siklus} | OBV: {obv} | RVOL: {rvol} | BB: {bb}\n"
    return summary_text

# ==========================================
# 📖 HELPER BUKU BESAR & ARSIP HARIAN (TAB 5)
# ==========================================
KEY_LEDGER = "Buku_Besar/ringkasan_harian.csv.gz"

@st.cache_data(ttl=3600)
def muat_buku_besar():
    try:
        import r2_client
        tmp = os.path.join(tempfile.gettempdir(), "ringkasan_harian_web.csv.gz")
        if r2_client.download_arsip(KEY_LEDGER, tmp):
            return pd.read_csv(tmp)
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def muat_arsip_harian(tanggal):
    try:
        import r2_client
        tmp = os.path.join(tempfile.gettempdir(), f"arsip_web_{tanggal}.csv")
        if r2_client.download_arsip(f"Arsip_Data_Harian/screener_{tanggal}.csv", tmp):
            return pd.read_csv(tmp)
    except Exception:
        pass
    return pd.DataFrame()

# =====================================================================
# >>> PART 05 : PENGATURAN UI/UX & CSS <<<
# =====================================================================
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
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: 600; }
    .view-mode-container { background-color: #0f172a; padding: 10px 20px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #334155; }
    </style>
""", unsafe_allow_html=True)


# =====================================================================
# >>> PART 06 : LOAD KONFIGURASI JSON (MASTER FILTERS) <<<
# =====================================================================
FILE_CONFIG = "config_web.json"
FILE_PRESET = "preset_kustom.json"
FILE_HASIL = "Database/hasil_screener.csv"
FILE_AKUISISI = "Database/data_akuisisi.csv"

DEFAULT_CONFIG = {
    "MASTER_FILTERS": {
        "Kategori": {"label": "🏢 Kategori Saham", "options": ["Semua", "Big Cap (Lapis 1)", "Mid Cap (Lapis 2)", "Small Cap (Lapis 3)", "Mid Cap (Lapis 2) + Small Cap (Lapis 3)"]},
        "Status Open": {"label": "🌅 Sinyal Open", "options": ["Semua", "Open = Low (Bullish Kuat)", "Open = High (Tekanan Jual)", "Normal"]},
        "Risk/Reward Ratio": {"label": "⚖️ Risk/Reward", "options": ["Semua", "Sangat Menarik (> 1:3)", "Ideal (1:2)", "Menengah (1:1)", "Tidak Ideal (< 1:1)", "Di Area Support"]},
        "Kelas Transaksi": {"label": "💸 Kelas Transaksi", "options": ["Semua", "Sultan (> 50M/hari)", "Ritel Aktif (5M - 50M)", "Gorengan Sepi (< 5M)"]},
        "Sinyal Cuci Barang": {"label": "🧹 Sinyal Shakeout", "options": ["Semua", "Jarum Bawah (Sinyal Pantulan Kuat)", "Normal"]},
        "Valuasi": {"label": "💎 Valuasi Fundamental", "options": ["Semua", "Undervalued (Murah)", "Fair Value (Wajar)", "Overvalued (Mahal)"]},
        "Posisi VWAP": {"label": "⚖️ Posisi thd VWAP", "options": ["Semua", "Di Atas VWAP (Kuat)", "Di Bawah VWAP (Lemah)", "Persis di VWAP"]},
        "Fase Siklus Bandar": {"label": "🔄 Siklus Wyckoff", "options": ["Semua", "Accumulation (Kumpul Barang)", "Mark-Up (Fase Pesta)", "Distribution (Fase Jualan)", "Mark-Down (Fase Runtuh)", "Sideways"]},
        "RVOL (Anomali Vol)": {"label": "🌋 Ledakan Volume", "options": ["Semua", "Ledakan Ekstrem (> 300%)", "Anomali Tinggi (150-300%)", "Normal (50-150%)", "Sepi (< 50%)"]},
        "Karakter Gorengan": {"label": "🕵️ Karakter Saham", "options": ["Semua", "Spesialis Tiang Jemuran (Banting Pucuk)", "Solid (Jarang Dibanting)", "Normal"]},
        "Status Bandar": {"label": "🕵️ Status Bandar", "options": ["Semua", "Akumulasi Kuat", "Distribusi Kuat", "Normal"]},
        "Tekanan Bandar": {"label": "⚔️ Tekanan Harian", "options": ["Semua", "Dominan Beli (Hajar Kanan)", "Dominan Jual (Guyur)", "Seimbang / Adu Mekanik"]},
        "Kekuatan A/D": {"label": "🧠 Smart Money (A/D)", "options": ["Semua", "Akumulasi Pro (Smart Money)", "Distribusi Pro (Guyuran)", "Netral"]},
        "OBV Trend": {"label": "🌊 Tren Uang (OBV)", "options": ["Semua", "Akumulasi (Naik)", "Distribusi (Turun)", "Netral"]},
        "Pola Candle": {"label": "🕯️ Price Action", "options": ["Semua", "Marubozu (Strong Bullish)", "Hammer (Potensi Reversal)", "Doji (Ragu-ragu)", "Normal"]},
        "Posisi Entry": {"label": "🎯 Jarak ke Support", "options": ["Semua", "Dekat Support (Low Risk)", "Area Tengah", "Rawan Pucuk (High Risk)"]},
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
        "MACD": {"label": "📈 MACD", "options": ["Semua", "Strong Bullish", "Bullish MACD", "Strong Bearish", "Bearish MACD"]},
        "Status Stochastic": {"label": "🌊 Stochastic", "options": ["Semua", "Oversold (Jenuh Jual - Peluang)", "Golden Cross (Awal Bullish)", "Overbought (Jenuh Beli - Rawan)", "Death Cross (Awal Bearish)", "Netral / Sideways"]},
        "Status Sentimen": {"label": "📰 Sentimen Berita", "options": ["Semua", "Sentimen Positif 📰", "Sentimen Negatif ⚠️", "Netral / Sepi Berita"]},
        "Prediksi Machine Learning": {"label": "🧠 AI Machine Learning", "options": ["Semua", "🔥 ANOMALI BANDAR (Siap Ledakan)", "⚠️ Anomali (Sudah Terbang)", "Biasa / Mengikuti Pasar"]},
        "Kondisi Supply": {"label": "🏜️ Supply & Demand", "options": ["Semua", "Supply Kering (Siap Pump) 🏜️", "Supply Banjir (Distribusi) 🌊", "Normal / Sedang Transisi"]},
        "Status Fibonacci": {"label": "📏 Level Fibonacci", "options": ["Semua", "Golden Rebound Fibo 61.8% (Golden Ratio) 🎯", "Dekat Support Fibo 61.8% (Golden Ratio)", "Golden Rebound Fibo 50.0% 🎯", "Golden Rebound Fibo 38.2% 🎯", "Mengambang (Jauh dari Fibo)"]}
    }
}

if not os.path.exists(FILE_CONFIG):
    with open(FILE_CONFIG, "w") as f: json.dump(DEFAULT_CONFIG, f, indent=4)
else:
    with open(FILE_CONFIG, "r") as f: cek_config = json.load(f)
    if "Status Fibonacci" not in cek_config.get("MASTER_FILTERS", {}):
        with open(FILE_CONFIG, "w") as f: json.dump(DEFAULT_CONFIG, f, indent=4)

with open(FILE_CONFIG, "r") as f: WEB_CONFIG = json.load(f)

if "Mid Cap (Lapis 2) + Small Cap (Lapis 3)" not in WEB_CONFIG["MASTER_FILTERS"]["Kategori"]["options"]:
    WEB_CONFIG["MASTER_FILTERS"]["Kategori"]["options"] = ["Semua", "Big Cap (Lapis 1)", "Mid Cap (Lapis 2)", "Small Cap (Lapis 3)", "Mid Cap (Lapis 2) + Small Cap (Lapis 3)"]
    with open(FILE_CONFIG, "w") as f: json.dump(WEB_CONFIG, f, indent=4)

MASTER_FILTERS = WEB_CONFIG["MASTER_FILTERS"]


# =====================================================================
# >>> PART 07 : PRESET & LOAD DATA SAHAM <<<
# =====================================================================
def muat_preset():
    preset_bawaan = {
        "🌙 BSJP (Beli Sore 15:30)": {k: "Semua" for k in MASTER_FILTERS},
        "⚡ HAKA Sesi Pagi (Open=Low)": {k: "Semua" for k in MASTER_FILTERS},
        "🚀 Gorengan Aktif (High Risk)": {k: "Semua" for k in MASTER_FILTERS},
        "🎣 Pantulan Reversal Emas": {k: "Semua" for k in MASTER_FILTERS},
        "🔥 Bluechip Terakumulasi": {k: "Semua" for k in MASTER_FILTERS}
    }
    preset_bawaan["🌙 BSJP (Beli Sore 15:30)"].update({"Tekanan Bandar": "Dominan Beli (Hajar Kanan)", "Karakter Gorengan": "Solid (Jarang Dibanting)", "Status Bandar": "Akumulasi Kuat", "MA Signal": "Uptrend", "Rekomendasi": "BELI"})
    preset_bawaan["⚡ HAKA Sesi Pagi (Open=Low)"].update({"Status Open": "Open = Low (Bullish Kuat)", "Risk/Reward Ratio": "Sangat Menarik (> 1:3)"})
    preset_bawaan["🚀 Gorengan Aktif (High Risk)"].update({"Kategori": "Small Cap (Lapis 3)", "RVOL (Anomali Vol)": "Ledakan Ekstrem (> 300%)", "Posisi VWAP": "Di Atas VWAP (Kuat)"})
    preset_bawaan["🎣 Pantulan Reversal Emas"].update({"Sinyal Cuci Barang": "Jarum Bawah (Sinyal Pantulan Kuat)", "Kekuatan A/D": "Akumulasi Pro (Smart Money)"})
    preset_bawaan["🔥 Bluechip Terakumulasi"].update({"Status Bandar": "Akumulasi Kuat", "Kategori": "Big Cap (Lapis 1)", "MA Signal": "Uptrend"})

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

SUMBER_DATA = "❓"

@st.cache_data(ttl=10)
def load_data_saham():
    global SUMBER_DATA
    df = None
    try:
        import r2_client
        tmp = os.path.join(tempfile.gettempdir(), "hasil_screener_r2.csv")
        if r2_client.download_arsip("Database/hasil_screener.csv", tmp):
            df = pd.read_csv(tmp)
            SUMBER_DATA = "☁️ R2 (real-time)"
    except Exception:
        df = None
    if df is None or df.empty:
        SUMBER_DATA = "📁 Lokal/Git (cadangan) — R2 GAGAL"
        if not os.path.exists(FILE_HASIL): return pd.DataFrame()
        df = pd.read_csv(FILE_HASIL)

    if os.path.exists(FILE_AKUISISI):
        df_akuisisi = pd.read_csv(FILE_AKUISISI)
        if "Status Akuisisi" in df.columns: df = df.drop(columns=["Status Akuisisi"])
        df = df.merge(df_akuisisi, on="Ticker", how="left")
        df["Status Akuisisi"] = df["Status Akuisisi"].fillna("TIDAK ADA")
    else: df["Status Akuisisi"] = "TIDAK ADA"
    return df

df_hasil = load_data_saham()

if not df_hasil.empty and 'Volume' in df_hasil.columns and 'Harga (Rp)' in df_hasil.columns:
    df_hasil['Value Transaksi'] = df_hasil['Harga (Rp)'] * df_hasil['Volume'] * 100


# =====================================================================
# >>> PART 08 : HEADER & SIDEBAR <<<
# =====================================================================
if not df_hasil.empty and "Terakhir Update" in df_hasil.columns:
    waktu_update = str(df_hasil["Terakhir Update"].iloc[0]) + " WIB"
    st.sidebar.markdown(f"""
        <div style="border: 2px solid #06b6d4; padding: 10px; border-radius: 4px; text-align: center; margin-bottom: 15px; background-color: #0f172a; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
            <span style="font-size: 12px; color: #94a3b8; font-weight: 600;">Waktu Terakhir Update:</span><br>
            <strong style="color: #06b6d4; font-size: 14px;">{waktu_update}</strong>
        </div>
    """, unsafe_allow_html=True)

st.sidebar.caption(f"📡 Sumber Data: {SUMBER_DATA}")

if st.sidebar.button("🔃 Sync & Muat Ulang Data Server", use_container_width=True):
    with st.spinner("Menarik data terbaru dari Cloudflare R2..."):
        time.sleep(1)
    st.cache_data.clear()
    st.rerun()

st.sidebar.title("⚙️ Preset Filter Cepat")
st.sidebar.info("Gunakan **'BSJP (Beli Sore 15:30)'** untuk mencari saham yang mantap dibeli sebelum penutupan bursa!")

opsi_preset = ["Matikan Preset (Manual)"] + list(daftar_preset_aktif.keys())
idx_default = opsi_preset.index(st.session_state.preset_selector) if st.session_state.preset_selector in opsi_preset else 0
st.sidebar.selectbox("📌 Pilih Preset Aktif:", opsi_preset, index=idx_default, key="preset_selector", on_change=apply_preset)

kustom_presets = {}
if os.path.exists(FILE_PRESET):
    try:
        with open(FILE_PRESET, "r") as f: kustom_presets = json.load(f)
    except: pass

with st.sidebar.expander("🛠️ Manajemen Preset Kustom"):
    tab_edit, tab_hapus = st.tabs(["📝 Buat/Edit", "🗑️ Hapus"])
    with tab_edit:
        opsi_edit = ["-- Buat Baru --"] + list(kustom_presets.keys())
        pilih_edit = st.selectbox("Pilih Preset:", opsi_edit, key="select_edit")
        if pilih_edit == "-- Buat Baru --":
            nama_preset_baru = st.text_input("Nama Preset Baru:", placeholder="Contoh: Strategi X", key="nama_baru")
            nilai_awal = {k: info['options'][0] for k, info in MASTER_FILTERS.items()}
        else:
            nama_preset_baru = st.text_input("Simpan sebagai:", value=pilih_edit, key="nama_edit")
            nilai_awal = kustom_presets[pilih_edit]

        kustom_input = {}
        for k, info in MASTER_FILTERS.items():
            val_awal = nilai_awal.get(k, info['options'][0])
            idx_awal = info['options'].index(val_awal) if val_awal in info['options'] else 0
            kustom_input[k] = st.selectbox(f"P-{info['label']}", info['options'], index=idx_awal, key=f"edit_{k}")

        if st.button("💾 Simpan Preset"):
            if nama_preset_baru.strip():
                if pilih_edit != "-- Buat Baru --" and pilih_edit != nama_preset_baru.strip(): del kustom_presets[pilih_edit]
                kustom_presets[nama_preset_baru.strip()] = kustom_input
                with open(FILE_PRESET, "w") as f: json.dump(kustom_presets, f, indent=4)
                st.session_state.preset_selector = nama_preset_baru.strip()
                st.success("Preset berhasil disimpan!")
                st.rerun()
    with tab_hapus:
        if kustom_presets:
            pilih_hapus = st.selectbox("Pilih Preset untuk Dihapus:", list(kustom_presets.keys()))
            if st.button("🗑️ Hapus Preset"):
                del kustom_presets[pilih_hapus]
                with open(FILE_PRESET, "w") as f: json.dump(kustom_presets, f, indent=4)
                if st.session_state.preset_selector == pilih_hapus: st.session_state.preset_selector = "Matikan Preset (Manual)"
                st.success("Preset dihapus!")
                st.rerun()
        else: st.info("Belum ada preset kustom.")

st.title("⚡ AlgoTrade Screener - IHSG Ultimate")
st.markdown("Detektor Jejak Bandar, Anomali Volume, & Strategi BSJP.")
st.markdown("---")


# =====================================================================
# >>> PART 09 : FORMATTER & PEWARNAAN TABEL + TABEL STRATEGI <<<
# =====================================================================
def format_skor(s): return "⭐" * int(s) if pd.notna(s) and int(s) > 0 else "-"
def format_pct(v): return f"{'▲ ' if v > 0 else '▼ '}{v:+.2f}%" if pd.notna(v) and v != 0 else "0.00%"
def format_mom(v): return "▲ Positif" if v == "Positif" else ("▼ Negatif" if v == "Negatif" else v)
def format_desimal(v): return f"{v:.2f}" if pd.notna(v) and v != 0 else "-"
def format_angka(v): return f"{int(v):,}".replace(",", ".") if pd.notna(v) else "-"

def format_singkat_vol(v):
    if pd.isna(v): return "-"
    if v >= 1_000_000: return f"{v/1_000_000:.2f} M Lot"
    elif v >= 1_000: return f"{v/1_000:.2f} K Lot"
    return f"{v:.0f} Lot"

def format_singkat_rp(v):
    if pd.isna(v) or v == 0: return "-"
    if v >= 1_000_000_000_000: return f"🔥 Rp {v/1_000_000_000_000:.2f} T"
    elif v >= 1_000_000_000: return f"💰 Rp {v/1_000_000_000:.2f} M"
    elif v >= 1_000_000: return f"🪙 Rp {v/1_000_000:.2f} Jt"
    return f"Rp {v:,.0f}".replace(",", ".")

def warna_tabel(val):
    if isinstance(val, (int, float)): 
        return 'color: #22c55e; font-weight: 600;' if val > 0 else ('color: #ef4444; font-weight: 600;' if val < 0 else '')
    elif isinstance(val, str):
        if any(x in val for x in ["Positif", "Uptrend", "BELI", "Breakout Upper", "Bottom Rebound", "DALAM AKUISISI", "Rendah", "▲", "Golden Cross", "Bullish", "Tembus MA20", "Akumulasi", "Big Cap", "Gap Up", "Dominan Beli", "Undervalued", "Marubozu", "Dekat Support", "Hammer", "Di Atas VWAP", "Sultan", "Ledakan Ekstrem", "Solid", "Mark-Up", "Jarum Bawah", "Naik", "Open = Low", "Sangat Menarik", "Perfect Uptrend", "Awal Reversal", "Acc"]): return 'color: #22c55e; font-weight: 600;'
        elif any(x in val for x in ["Negatif", "Downtrend", "WAIT & SEE", "Tinggi", "▼", "Death Cross", "Bearish", "Distribusi", "Small Cap", "Gap Down", "Dominan Jual", "Overvalued", "Rawan Pucuk", "Di Bawah VWAP", "Gorengan Sepi", "Sepi", "Tiang Jemuran", "Mark-Down", "Turun", "Open = High", "Tidak Ideal", "Strong Downtrend", "Dist", "Token Mati", "Gagal", "Timeout"]): return 'color: #ef4444; font-weight: 600;'
        elif val == "> 1 Miliar": return 'color: #3b82f6; font-weight: 600;'
        elif any(x in val for x in ["Squeeze", "RENCANA AKUISISI", "Sedang", "Mid Cap", "Seimbang", "Fair Value", "Area Tengah", "Doji", "Ritel Aktif", "Anomali", "Accumulation", "Sideways", "Ideal", "Menengah", "Konsolidasi / Transisi", "Neutral"]): return 'color: #eab308; font-weight: 600;'
        elif "⭐" in val: return 'color: #22c55e;' if len(val) >= 6 else 'color: #ef4444;'
    return ''

def _render_salin_dengan_acak(daftar_ticker, key_state, key_btn):
    sumber = "|".join(daftar_ticker)
    key_sumber = f"{key_state}_sumber"
    if st.session_state.get(key_sumber) != sumber:
        st.session_state[key_state] = daftar_ticker[:]
        st.session_state[key_sumber] = sumber
    
    def _acak():
        urutan_lama = st.session_state.get(key_state, [])
        urutan_baru = urutan_lama[:]
        if len(urutan_baru) > 1:
            while urutan_baru == urutan_lama:
                random.shuffle(urutan_baru)
        st.session_state[key_state] = urutan_baru
    
    st.markdown("**📋 Salin Daftar Saham:**")
    col_kode, col_btn = st.columns([12, 1])
    with col_kode:
        st.code("\n".join(st.session_state.get(key_state, daftar_ticker)), language="text")
    with col_btn:
        st.button("🔀", key=key_btn, on_click=_acak,
                  use_container_width=True,
                  help="Acak urutan — dijamin berbeda setiap klik")

def render_strategy_table(df_subset, file_name):
    if not df_subset.empty:
        sort_cols = [c for c in ['Total Score', 'Volume'] if c in df_subset.columns]
        if sort_cols: df_subset = df_subset.sort_values(by=sort_cols, ascending=[False, False]).reset_index(drop=True)
        if "Total Score" in df_subset.columns: df_subset["Total Score"] = df_subset["Total Score"].apply(format_skor)

        kolom_utama = ["Ticker", "Harga (Rp)", "Change (%)", "Value Transaksi", "Volume", "Total Score", "Auto Trading Plan"]
        kolom_tambahan = ["Kelas Transaksi", "Broksum", "Trend MA (5,20,50)", "RVOL (Anomali Vol)", "Tekanan Bandar", "Status Bandar", "Kekuatan A/D", "Sinyal Cuci Barang", "Status BB", "MA Signal"]
        kolom_tampil = [c for c in kolom_utama + kolom_tambahan if c in df_subset.columns]

        styler = df_subset[kolom_tampil].style.format({
            "Harga (Rp)": format_angka, 
            "Volume": format_angka, 
            "Change (%)": format_pct,
            "Value Transaksi": format_singkat_rp
        })
        subset_warna = [c for c in kolom_tampil if c not in ["Ticker", "Auto Trading Plan"]]
        tabel_jadi = styler.map(warna_tabel, subset=subset_warna) if hasattr(styler, 'map') else styler.applymap(warna_tabel, subset=subset_warna)

        st.dataframe(tabel_jadi, use_container_width=True, hide_index=True)

        c1, c2 = st.columns([1, 1])
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer: tabel_jadi.to_excel(writer, index=False, sheet_name='Screener')
        c1.download_button(label=f"📥 Download {file_name} (Excel)", data=buffer.getvalue(), file_name=f"{file_name}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_{file_name}")
        with c2:
            _render_salin_dengan_acak(
                df_subset["Ticker"].tolist(),
                key_state=f"acak_{file_name}",
                key_btn=f"btn_acak_{file_name}"
            )
            st.caption("Klik icon 'Copy' untuk paste ke Tab AI — atau 🔀 untuk acak urutan.")
    else: st.info("🔍 Belum ada pergerakan saham yang memenuhi kriteria strategi ini pada sesi saat ini.")


# =====================================================================
# >>> PART 10 : TAB 1 - MARKET OVERVIEW <<<
# =====================================================================
if not df_hasil.empty:
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Market Overview", 
        "📌 Screener Utama", 
        "🤖 Asisten AI Spesial", 
        "💼 Portofolio Bot",
        "🕵️ Detektif Ledakan & Chat"
    ])
    
    with tab1:
        st.markdown("### 📊 Ringkasan Pasar IHSG")
        
        total_saham = len(df_hasil)
        saham_naik = len(df_hasil[df_hasil['Change (%)'] > 0]) if 'Change (%)' in df_hasil.columns else 0
        saham_turun = len(df_hasil[df_hasil['Change (%)'] < 0]) if 'Change (%)' in df_hasil.columns else 0
        saham_stagnan = total_saham - saham_naik - saham_turun
        
        if 'Turnover' not in df_hasil.columns:
            if 'Volume' in df_hasil.columns and 'Harga (Rp)' in df_hasil.columns:
                df_hasil['Turnover'] = df_hasil['Harga (Rp)'] * df_hasil['Volume'] * 100
            else:
                df_hasil['Turnover'] = 0

        if saham_naik > (saham_turun * 1.5): sentimen_teks, warna_sentimen = "🔥 Sangat Bullish", "#4ade80"
        elif saham_turun > (saham_naik * 1.5): sentimen_teks, warna_sentimen = "🩸 Sangat Bearish", "#f87171"
        else: sentimen_teks, warna_sentimen = "⚖️ Konsolidasi (Ragu)", "#facc15"
                
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.markdown(f"<div class='metric-container'><h3>🔍 Total Saham</h3><h2>{total_saham}</h2></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-container'><h3>🟢 Menguat</h3><h2 style='color: #4ade80;'>{saham_naik}</h2></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-container'><h3>🔴 Melemah</h3><h2 style='color: #f87171;'>{saham_turun}</h2></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='metric-container'><h3>⚪ Stagnan</h3><h2 style='color: #94a3b8;'>{saham_stagnan}</h2></div>", unsafe_allow_html=True)
        m5.markdown(f"<div class='metric-container'><h3>🧭 Sentimen Pasar</h3><h3 style='color: {warna_sentimen}; margin-top:5px;'>{sentimen_teks}</h3></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)

        def render_top_table(df_top, cols, format_dict):
            styler = df_top[cols].style.format(format_dict)
            tabel_warna = styler.map(warna_tabel, subset=['Change (%)']) if hasattr(styler, 'map') else styler.applymap(warna_tabel, subset=['Change (%)'])
            st.dataframe(tabel_warna, use_container_width=True, hide_index=True)

        with c1:
            st.markdown("#### 🔥 Top Gainers")
            if 'Change (%)' in df_hasil.columns:
                df_gainer = df_hasil.nlargest(10, 'Change (%)')
                render_top_table(df_gainer, ['Ticker', 'Harga (Rp)', 'Change (%)'], {'Harga (Rp)': format_angka, 'Change (%)': format_pct})
            
        with c2:
            st.markdown("#### 🩸 Top Losers")
            if 'Change (%)' in df_hasil.columns:
                df_loser = df_hasil.nsmallest(10, 'Change (%)')
                render_top_table(df_loser, ['Ticker', 'Harga (Rp)', 'Change (%)'], {'Harga (Rp)': format_angka, 'Change (%)': format_pct})
            
        st.markdown("<br>", unsafe_allow_html=True)
            
        with c3:
            st.markdown("#### 🌊 Top Volume")
            if 'Volume' in df_hasil.columns:
                df_vol = df_hasil.nlargest(10, 'Volume')
                render_top_table(df_vol, ['Ticker', 'Harga (Rp)', 'Volume', 'Change (%)'], {'Harga (Rp)': format_angka, 'Volume': format_singkat_vol, 'Change (%)': format_pct})
            
        with c4:
            st.markdown("#### 💰 Top Value (Turnover)")
            if 'Turnover' in df_hasil.columns:
                df_val = df_hasil.nlargest(10, 'Turnover')
                render_top_table(df_val, ['Ticker', 'Harga (Rp)', 'Turnover', 'Change (%)'], {'Harga (Rp)': format_angka, 'Turnover': format_singkat_rp, 'Change (%)': format_pct})


# =====================================================================
# >>> PART 11 : TAB 2 - SCREENER UTAMA <<<
# =====================================================================
    with tab2:
        def reset_semua_filter():
            for k, info in MASTER_FILTERS.items():
                if f"main_{k}" in st.session_state:
                    st.session_state[f"main_{k}"] = info["options"][0]
            st.session_state["pencarian_ticker"] = ""
            st.session_state["pencarian_broker"] = ""
            st.session_state["batas_harga_min"] = 0
            st.session_state["batas_harga_max"] = 0

        with st.expander("🛠️ Buka Panel Filter Lengkap", expanded=False):
            st.button("🔄 Reset Semua Filter ke Bawaan (Semua)", on_click=reset_semua_filter, use_container_width=True)
            st.markdown("---")
            
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            filter_terpilih = {}
            for idx, (db_key, info) in enumerate(MASTER_FILTERS.items()):
                target_col = col_f1 if idx % 4 == 0 else (col_f2 if idx % 4 == 1 else (col_f3 if idx % 4 == 2 else col_f4))
                with target_col:
                    val_sekarang = st.session_state.get(f"main_{db_key}", info["options"][0])
                    idx_opsi = info["options"].index(val_sekarang) if val_sekarang in info["options"] else 0
                    filter_terpilih[db_key] = st.selectbox(info["label"], info["options"], index=idx_opsi, key=f"main_{db_key}", on_change=manual_override)

        col_search, col_broker, col_min, col_max = st.columns([1.5, 1.5, 1, 1])
        with col_search: 
            search_ticker = st.text_input("🔍 Cari Kode Saham", "", placeholder="Contoh: BBCA", key="pencarian_ticker")
        with col_broker: 
            search_broker = st.text_input("👤 Cari Kode Broker", "", placeholder="Contoh: MG / YP", key="pencarian_broker")
        with col_min: 
            min_price = st.number_input("⬇️ Harga Minimal (Rp)", min_value=0, value=0, step=10, key="batas_harga_min")
        with col_max: 
            max_price = st.number_input("⬆️ Harga Maksimal (Rp)", min_value=0, value=0, step=10, key="batas_harga_max")

        df_filtered = df_hasil.copy()
        
        if search_ticker: 
            df_filtered = df_filtered[df_filtered["Ticker"].astype(str).str.contains(search_ticker.upper(), na=False)]
            
        if search_broker and "Broksum" in df_filtered.columns: 
            df_filtered = df_filtered[df_filtered["Broksum"].astype(str).str.contains(search_broker.upper(), na=False)]
            
        if min_price > 0:
            df_filtered = df_filtered[df_filtered["Harga (Rp)"] >= min_price]
        if max_price > 0:
            df_filtered = df_filtered[df_filtered["Harga (Rp)"] <= max_price]
        
        for db_key, nilai in filter_terpilih.items():
            if nilai != "Semua":
                if db_key == "RSI (14D)":
                    if "RSI (14D)" in df_filtered.columns: df_filtered = df_filtered[df_filtered["RSI (14D)"] > 50] if "Bullish" in nilai else df_filtered[df_filtered["RSI (14D)"] <= 50]
                elif db_key == "Total Score":
                    if "Total Score" in df_filtered.columns: df_filtered = df_filtered[df_filtered["Total Score"] == int(nilai)]
                elif db_key == "Kategori" and nilai == "Mid Cap (Lapis 2) + Small Cap (Lapis 3)":
                    if "Kategori" in df_filtered.columns:
                        df_filtered = df_filtered[df_filtered["Kategori"].isin(["Mid Cap (Lapis 2)", "Small Cap (Lapis 3)"])]
                elif db_key in df_filtered.columns: 
                    df_filtered = df_filtered[df_filtered[db_key] == nilai]

        if not df_filtered.empty:
            st.caption(f"Menampilkan **{len(df_filtered)}** saham yang lolos filter dari total **{len(df_hasil)}** saham.")
            st.markdown("<div class='view-mode-container'>", unsafe_allow_html=True)
            mode_tampilan = st.radio("👁️ Pilih Mode Tampilan Tabel:", ["🚀 Ringkasan Cepat", "👤 Bandarmologi & Wyckoff", "📈 Teknikal & Support", "💎 Fundamental & Likuiditas", "🌌 Tampilkan Semua Kolom"], horizontal=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            cp1, cp2, cp3 = st.columns([1, 1, 2])
            with cp1: per_hal = st.selectbox("Tampilkan baris:", [20, 50, 100])
            tot_hal = int(np.ceil(len(df_filtered) / per_hal))
            with cp2: hal_aktif = st.selectbox("Halaman:", range(1, tot_hal + 1)) if tot_hal > 0 else 1
                    
            idx_awal = (hal_aktif - 1) * per_hal
            df_tampil = df_filtered.iloc[idx_awal : idx_awal + per_hal].copy()
            if "Total Score" in df_tampil.columns: df_tampil["Total Score"] = df_tampil["Total Score"].apply(format_skor)
            
            kolom_ringkasan = ["Ticker", "Harga (Rp)", "Change (%)", "Value Transaksi", "Volume", "Broksum", "Rekomendasi", "Status Open", "Posisi VWAP", "Total Score", "Auto Trading Plan"]
            kolom_bandar = ["Ticker", "Harga (Rp)", "Change (%)", "Value Transaksi", "Broksum", "Fase Siklus Bandar", "Kekuatan A/D", "Status Bandar", "RVOL (Anomali Vol)", "Karakter Gorengan", "Tekanan Bandar", "OBV Trend", "Kondisi Supply", "Prediksi Machine Learning"]
            kolom_teknikal = ["Ticker", "Harga (Rp)", "Change (%)", "Value Transaksi", "Auto Trading Plan", "Risk/Reward Ratio", "Status Fibonacci", "Sinyal Cuci Barang", "Posisi Entry", "Pola Candle", "Trend MA (5,20,50)", "MA Signal", "Status BB", "RSI (14D)", "MACD", "Status Stochastic"]
            kolom_fundamental = ["Ticker", "Harga (Rp)", "Value Transaksi", "Kategori", "Valuasi", "PER (x)", "PBV (x)", "Kelas Transaksi", "Likuiditas", "Status Sentimen"]
            kolom_semua = ["Ticker", "Value Transaksi", "Broksum", "Status Open", "Risk/Reward Ratio", "Status Fibonacci", "Auto Trading Plan", "Streak Harian", "Sinyal Cuci Barang", "Kategori", "Kelas Transaksi", "Valuasi", "Harga (Rp)", "PER (x)", "PBV (x)", "Harga MA20", "Posisi VWAP", "Support", "Resistance", "Posisi Entry", "Pola Candle", "Change (%)", "Volume", "RVOL (Anomali Vol)", "Vol Breakout", "Status Gap", "Fase Siklus Bandar", "Karakter Gorengan", "Tekanan Bandar", "Kekuatan A/D", "Status Bandar", "OBV Trend", "RSI (14D)", "Momentum", "Trend MA (5,20,50)", "MA Signal", "MA Cross", "MACD", "Status Stochastic", "Status BB", "Risiko", "Likuiditas", "Status Sentimen", "Prediksi Machine Learning", "Kondisi Supply", "Total Score", "Rekomendasi"]
            
            if "Ringkasan" in mode_tampilan: kolom_pilih = kolom_ringkasan
            elif "Bandarmologi" in mode_tampilan: kolom_pilih = kolom_bandar
            elif "Teknikal" in mode_tampilan: kolom_pilih = kolom_teknikal
            elif "Fundamental" in mode_tampilan: kolom_pilih = kolom_fundamental
            else: kolom_pilih = kolom_semua

            kolom_ada = [c for c in kolom_pilih if c in df_tampil.columns]
            format_dict = {}
            for col in ["Harga (Rp)", "Harga MA20", "Support", "Resistance", "Volume"]:
                if col in df_tampil.columns: format_dict[col] = format_angka
            if "Change (%)" in df_tampil.columns: format_dict["Change (%)"] = format_pct
            if "Momentum" in df_tampil.columns: format_dict["Momentum"] = format_mom
            if "Value Transaksi" in df_tampil.columns: format_dict["Value Transaksi"] = format_singkat_rp
            for col in ["PER (x)", "PBV (x)"]:
                if col in df_tampil.columns: format_dict[col] = format_desimal
            if "RSI (14D)" in df_tampil.columns: format_dict["RSI (14D)"] = "{:.0f}"

            styler_obj = df_tampil[kolom_ada].style.format(format_dict)
            subset_warna = [c for c in kolom_ada if c not in ["Ticker", "Auto Trading Plan"]]
            tabel_akhir = styler_obj.map(warna_tabel, subset=subset_warna) if hasattr(styler_obj, 'map') else styler_obj.applymap(warna_tabel, subset=subset_warna)
            st.dataframe(tabel_akhir, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            col_dl, col_wl = st.columns([1, 1])
            with col_dl:
                csv_filter = df_filtered[kolom_ada].to_csv(index=False).encode('utf-8')
                st.download_button(label=f"📥 Download Data Tabel CSV", data=csv_filter, file_name=f"Screener_View_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv", key="dl_tab2")
            with col_wl:
                _render_salin_dengan_acak(
                    df_filtered["Ticker"].tolist(),
                    key_state="acak_tab2",
                    key_btn="btn_acak_tab2"
                )
                st.caption("Klik icon 'Copy' untuk paste massal ke Tab AI — atau 🔀 untuk acak urutan.")
        else: st.warning("Tidak ada data sesuai filter.")


# =====================================================================
# >>> PART 12 : TAB 3 - ASISTEN AI SPESIAL (RUMUS v5.0 + RADAR LIVE + TELEGRAM SNAPSHOT) <<<
# =====================================================================
    VERSI_SIDANG = "v5.0"
    MAX_CHANGE_BELI = 20.0  # saringan keras BSJP (sinkron dengan sidang_lib.py)
    FILE_CACHE_AUTOPILOT = "Database/cache_autopilot.json"

    # S1 — Helper simpan snapshot sidang ke R2 (dipakai Radar Live + bot Telegram)
    def simpan_snapshot_radar(keranjang, stempel_data):
        try:
            snap = {"stempel_data": stempel_data, "versi": VERSI_SIDANG, "keranjang": keranjang,
                    "waktu": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}
            path = os.path.join("Database", "radar_snapshot.json")
            with open(path, "w") as f: json.dump(snap, f)
            import r2_client
            r2_client.upload_arsip(path, "Database/radar_snapshot.json")
        except Exception:
            pass

    with tab3:
        st.markdown("## 🦅 Radar BSJP & Laboratorium Forensik AI")
        st.markdown("<div class='bandar-box-green'><b>💡 INFO:</b> Gunakan kotak pilihan (Dropdown) di bawah ini untuk beralih antar strategi atau mode AI agar tampilan lebih rapi.</div>", unsafe_allow_html=True)
        
        if 'Tekanan Bandar' not in df_hasil.columns:
            st.warning("⏳ **Fitur Radar belum menerima data terbaru.** Harap jalankan 'update_data.py'.")
        else:
            # --- SUSUNAN RUMUS v5.0: 1-5 remap, 6-9 rumus baru ---
            df_v1 = df_v2 = df_v3 = df_v4 = df_v5 = df_v6 = df_v7 = df_v8 = df_v9 = pd.DataFrame()
            if not df_hasil.empty:
                vwap_ok = (df_hasil.get('Posisi VWAP', '') != 'Di Bawah VWAP (Lemah)')
                vwap_kuat = (df_hasil.get('Posisi VWAP', '') == 'Di Atas VWAP (Kuat)')
                akumulasi_pro = (df_hasil.get('Kekuatan A/D', '') == 'Akumulasi Pro (Smart Money)')
                change_num = pd.to_numeric(df_hasil.get('Change (%)', 0), errors='coerce')

                # RUMUS 1: Smart Money Menyelam (eks R2)
                cond_v1 = (akumulasi_pro &
                           (df_hasil.get('Status Bandar', '') == 'Akumulasi Kuat') &
                           vwap_ok)
                df_v1 = df_hasil[cond_v1].copy()

                # RUMUS 2: Pantulan Jarum Bawah (eks R3)
                cond_v2 = (((df_hasil.get('Pola Candle', '') == 'Hammer (Potensi Reversal)') |
                            (df_hasil.get('Sinyal Cuci Barang', '') == 'Jarum Bawah (Sinyal Pantulan Kuat)')) &
                           vwap_kuat &
                           akumulasi_pro)
                df_v2 = df_hasil[cond_v2].copy()

                # RUMUS 3: Tutup Kuat, Bandar Hajar (eks R1)
                cond_v3 = (vwap_kuat &
                           (df_hasil.get('Tekanan Bandar', '') == 'Dominan Beli (Hajar Kanan)') &
                           (df_hasil.get('Status Open', '') == 'Open = Low (Bullish Kuat)') &
                           (df_hasil.get('Rekomendasi', '') == 'BELI'))
                df_v3 = df_hasil[cond_v3].copy()

                # RUMUS 4: Golden Cross Muda (tetap)
                cond_v4 = ((df_hasil.get('MA Cross', '') == 'Golden Cross') &
                           (df_hasil.get('Vol Breakout', '') == 'Tembus MA20') &
                           (df_hasil.get('MA Signal', '') == 'Uptrend') &
                           vwap_kuat)
                df_v4 = df_hasil[cond_v4].copy()

                # RUMUS 5: Momentum Likuid Sehat (eks R6)
                cond_v5 = ((df_hasil.get('Kelas Transaksi', '') == 'Ritel Aktif (5M - 50M)') &
                           (df_hasil.get('Vol Breakout', '') == 'Tembus MA20') &
                           vwap_kuat &
                           (df_hasil.get('MA Signal', '') == 'Uptrend'))
                df_v5 = df_hasil[cond_v5].copy()

                # RUMUS 6: BARU — Ledakan Volume Senyap
                cond_v6 = ((df_hasil.get('RVOL (Anomali Vol)', '').isin(['Anomali Tinggi (150-300%)', 'Ledakan Ekstrem (> 300%)'])) &
                           (df_hasil.get('OBV Trend', '') == 'Akumulasi (Naik)') &
                           (change_num <= 5.0) &
                           (df_hasil.get('Tekanan Bandar', '') == 'Dominan Beli (Hajar Kanan)'))
                df_v6 = df_hasil[cond_v6].copy()

                # RUMUS 7: BARU — Anomali Machine Learning
                cond_v7 = ((df_hasil.get('Prediksi Machine Learning', '') == '🔥 ANOMALI BANDAR (Siap Ledakan)') &
                           (df_hasil.get('Status Stochastic', '').isin(['Oversold (Jenuh Jual - Peluang)', 'Golden Cross (Awal Bullish)'])) &
                           vwap_ok)
                df_v7 = df_hasil[cond_v7].copy()

                # RUMUS 8: BARU — Katalis Sentimen & Akuisisi
                cond_v8 = (((df_hasil.get('Status Sentimen', '') == 'Sentimen Positif 📰') |
                            (df_hasil.get('Status Akuisisi', '').isin(['RENCANA AKUISISI', 'DALAM AKUISISI']))) &
                           (df_hasil.get('MA Signal', '') == 'Uptrend') &
                           (df_hasil.get('Rekomendasi', '') == 'BELI'))
                df_v8 = df_hasil[cond_v8].copy()

                # RUMUS 9: BARU — MACD Momentum Terukur
                cond_v9 = ((df_hasil.get('MACD', '').isin(['Strong Bullish', 'Bullish MACD'])) &
                           (df_hasil.get('Risk/Reward Ratio', '').isin(['Sangat Menarik (> 1:3)', 'Ideal (1:2)'])) &
                           (df_hasil.get('Posisi Entry', '') == 'Dekat Support (Low Risk)') &
                           (df_hasil.get('Momentum', '') == 'Positif'))
                df_v9 = df_hasil[cond_v9].copy()

            tab_screener, tab_ai = st.tabs(["🎯 Screener Spesial", "🧠 Asisten AI"])
            
            with tab_screener:
                pilihan_v = st.selectbox(
                    "Pilih Rumus Screener BSJP:",
                    [
                        "RUMUS 1 : Smart Money Menyelam 🕵️",
                        "RUMUS 2 : Pantulan Jarum Bawah 📌",
                        "RUMUS 3 : Tutup Kuat, Bandar Hajar ⚡",
                        "RUMUS 4 : Golden Cross Muda 🌱",
                        "RUMUS 5 : Momentum Likuid Sehat 💧",
                        "RUMUS 6 : Ledakan Volume Senyap 🌋",
                        "RUMUS 7 : Anomali Machine Learning 🧠",
                        "RUMUS 8 : Katalis Sentimen & Akuisisi 📰",
                        "RUMUS 9 : MACD Momentum Terukur 🎯"
                    ]
                )
                
                st.markdown("---")
                if "RUMUS 1" in pilihan_v:
                    render_strategy_table(df_v1, "Screener_Rumus_1")
                elif "RUMUS 2" in pilihan_v:
                    render_strategy_table(df_v2, "Screener_Rumus_2")
                elif "RUMUS 3" in pilihan_v:
                    render_strategy_table(df_v3, "Screener_Rumus_3")
                elif "RUMUS 4" in pilihan_v:
                    render_strategy_table(df_v4, "Screener_Rumus_4")
                elif "RUMUS 5" in pilihan_v:
                    render_strategy_table(df_v5, "Screener_Rumus_5")
                elif "RUMUS 6" in pilihan_v:
                    render_strategy_table(df_v6, "Screener_Rumus_6")
                elif "RUMUS 7" in pilihan_v:
                    render_strategy_table(df_v7, "Screener_Rumus_7")
                elif "RUMUS 8" in pilihan_v:
                    render_strategy_table(df_v8, "Screener_Rumus_8")
                elif "RUMUS 9" in pilihan_v:
                    render_strategy_table(df_v9, "Screener_Rumus_9")

            with tab_ai:
                pilihan_ai = st.selectbox(
                    "Pilih Mode Analisis AI:",
                    [
                        "🤖 AI Bandar (Persiapan BSJP)", 
                        "🔎 Forensik Bandar (Bongkar DNA ARA)", 
                        "🎯 Pemburu ARA (Spesialis DNA Ledakan)"
                    ]
                )
                st.markdown("---")
                
                if "AI Bandar" in pilihan_ai:
                    st.subheader("🤖 AI Bandar (Persiapan BSJP Besok)")
                    
                    tab_otomatis, tab_manual, tab_acak = st.tabs(["🛸 Auto-Pilot 9 Rumus (Spreadsheet)", "✍️ Mode Manual (Paste Saham)", "🎲 Uji Konsistensi 9 Ronde"])
                    
                    with tab_otomatis:
                        st.markdown("Sistem akan menyeleksi 15 saham terbaik per rumus secara global, lalu AI akan memilih Top 5 untuk dicetak ke tabel Spreadsheet.")
                        
                        paksa_sidang = st.checkbox("🔄 Paksa Sidang Ulang (abaikan cache Mode Kilat)", key="paksa_sidang_ulang")

                        if st.button("🗑️ Hapus Cache Sidang", key="hapus_cache_sidang"):
                            try:
                                if os.path.exists(FILE_CACHE_AUTOPILOT):
                                    os.remove(FILE_CACHE_AUTOPILOT)
                                    st.success("✅ Cache sidang dihapus. Sidang berikutnya mulai dari awal.")
                                else:
                                    st.info("Tidak ada cache tersimpan.")
                            except Exception as e:
                                st.error(f"Gagal hapus cache: {e}")

                        if st.button("🛸 Jalankan Auto-Pilot Ultimate", type="primary", key="autopilot_utama"):
                            
                            GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
                            
                            if not GEMINI_API_KEY:
                                st.error("❌ Kunci API GEMINI belum dipasang!")
                            else:
                                daftar_rumus = {
                                    1: df_v1, 2: df_v2, 3: df_v3, 
                                    4: df_v4, 5: df_v5, 6: df_v6, 
                                    7: df_v7, 8: df_v8, 9: df_v9
                                }
                                
                                stempel_data = str(df_hasil["Terakhir Update"].iloc[0]) if "Terakhir Update" in df_hasil.columns else "tanpa_stempel"
                                FILE_CACHE_AUTOPILOT = "Database/cache_autopilot.json"
                                
                                keranjang_spreadsheet = None
                                if not paksa_sidang and os.path.exists(FILE_CACHE_AUTOPILOT):
                                    try:
                                        with open(FILE_CACHE_AUTOPILOT, "r") as f: cache_muat = json.load(f)
                                        if cache_muat.get("stempel_data") == stempel_data and cache_muat.get("versi") == VERSI_SIDANG and cache_muat.get("keranjang"):
                                            ada_isi_cache = any(len([t for t in cache_muat["keranjang"].get(f"RUMUS {i}", []) if t]) > 0 for i in range(1, 10))
                                            if ada_isi_cache:
                                                keranjang_spreadsheet = cache_muat["keranjang"]
                                                st.info("⚡ **Mode Kilat Aktif:** Data belum berubah sejak sidang terakhir — hasil ditampilkan instan dari cache.")
                                    except: pass
                                
                                if keranjang_spreadsheet is None:
                                    progress_bar = st.progress(0)
                                    status_teks = st.empty()
                                    
                                    keranjang_spreadsheet, err_global, laporan_sidang = jalankan_sidang_autopilot(daftar_rumus, df_hasil, GEMINI_API_KEY, progress_bar, status_teks)
                                    
                                    if err_global:
                                        st.error(err_global)
                                    else:
                                        df_laporan = pd.DataFrame([{
                                            "Rumus": f"RUMUS {i}",
                                            "Status": laporan_sidang[i]["status"],
                                            "Keterangan": laporan_sidang[i]["detail"]
                                        } for i in range(1, 10)])
                                        st.markdown("### 🧾 Laporan Sidang (Transparan)")
                                        st.dataframe(df_laporan, use_container_width=True, hide_index=True)
                                        
                                        ada_isi = any(laporan_sidang[i]["status"] == "✅ Sukses" for i in range(1, 10))
                                        if ada_isi:
                                            try:
                                                with open(FILE_CACHE_AUTOPILOT, "w") as f:
                                                    json.dump({"stempel_data": stempel_data, "versi": VERSI_SIDANG, "keranjang": keranjang_spreadsheet}, f, indent=4)
                                            except: pass
                                            # S2a — simpan snapshot untuk Telegram
                                            simpan_snapshot_radar(keranjang_spreadsheet, stempel_data)
                                            status_teks.success("🎉 MISSION ACCOMPLISHED! SELURUH RUMUS BERHASIL DISARING!")
                                            st.balloons()
                                        else:
                                            status_teks.warning("⚠️ Sidang selesai tetapi tidak ada jawara. Baca Laporan Sidang untuk tahu penyebab pastinya.")
                                
                                st.markdown("### 📋 Tabel Master Portofolio (Siap Salin)")
                                
                                for kunci in keranjang_spreadsheet:
                                    keranjang_spreadsheet[kunci] = (keranjang_spreadsheet[kunci] + ["", "", "", "", ""])[:5]
                                
                                df_spreadsheet = pd.DataFrame(keranjang_spreadsheet)
                                
                                st.data_editor(df_spreadsheet, use_container_width=True, hide_index=True)

                    with tab_manual:
                        st.markdown("Paste saham yang MASIH MERAH / SIDEWAYS. AI akan mencari siapa yang siap terbang besok.")
                        input_saham_massal = st.text_area("📋 Paste Daftar Saham (Pisahkan dengan Enter/Spasi):", placeholder="Contoh:\nDMAS\nINDF", height=200, key="input_ai_bandar")
                        
                        if st.button("🔮 Mulai Eksekusi AI Bandar"):
                            saham_bersih = [s.strip().upper() for s in re.split(r'[,\s\n]+', input_saham_massal) if s.strip()]
                            saham_unik = list(dict.fromkeys(saham_bersih))
                            saham_valid = [s for s in saham_unik if s in df_hasil['Ticker'].values]
                            
                            df_valid = df_hasil[df_hasil['Ticker'].isin(saham_valid)].copy()
                            if 'Change (%)' in df_valid.columns:
                                df_valid = df_valid[df_valid['Change (%)'] <= 5.0]
                                saham_valid = df_valid['Ticker'].tolist()

                            if not saham_valid:
                                st.error("❌ Saham yang Anda masukkan sudah terbang terlalu tinggi (>5%). Gunakan AI Bandar untuk mencari saham yang masih di bawah!")
                            else:
                                if len(saham_valid) > 19:
                                    st.info("🤖 Menyaring 19 saham terbaik untuk mencegah limit AI...")
                                    df_valid = df_valid.sort_values(by=['Total Score', 'Volume'], ascending=[False, False])
                                    saham_valid = df_valid['Ticker'].head(19).tolist()
                                
                                with st.spinner(f"Menganalisa {len(saham_valid)} saham untuk BSJP besok..."):
                                    data_kompilasi = {}
                                    for ticker in saham_valid:
                                        data_saham = df_hasil[df_hasil['Ticker'] == ticker].iloc[0]
                                        teks_ringkasan = get_historical_summary(ticker)
                                        data_kompilasi[ticker] = {
                                            'harga': data_saham.get('Harga (Rp)', 0),
                                            'change': data_saham.get('Change (%)', 0), 
                                            'broksum': data_saham.get('Broksum', 'Tidak Ada'),
                                            'status': data_saham.get('Fase Siklus Bandar', 'Normal'),
                                            'skor': data_saham.get('Total Score', 0),
                                            'histori': teks_ringkasan if teks_ringkasan else "Arsip belum tersedia."
                                        }
                                    hasil_ai = analisa_bandar_ai_multisaham(data_kompilasi, 'pilihan_ai')
                                    st.info(hasil_ai)

                    # >>> Tab 9 Ronde Uji Konsistensi
                    with tab_acak:
                        st.markdown("Paste puluhan saham → AI memilih Top 5 → urutan diacak otomatis → diulang sampai **9 ronde**. Hasil dicetak sebagai spreadsheet murni, tanpa penjelasan.")
                        input_acak = st.text_area("📋 Paste Daftar Saham (Enter/Spasi):", height=200, key="input_acak_9ronde", placeholder="Contoh:\nBBCA\nTLKM\nASII\nGOTO\nBUKA\n...")
                        if st.button("🎲 Jalankan 9 Ronde Top-5", type="primary", key="btn_9ronde"):
                            GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
                            if not GEMINI_API_KEY:
                                st.error("❌ Kunci API GEMINI belum dipasang!")
                            else:
                                saham_bersih = [s.strip().upper() for s in re.split(r'[,\s\n]+', input_acak) if s.strip()]
                                saham_unik = list(dict.fromkeys(saham_bersih))
                                if len(saham_unik) < 5:
                                    st.error("❌ Minimal 5 kode saham valid untuk menggelar 9 ronde.")
                                else:
                                    progress_bar = st.progress(0)
                                    status_teks = st.empty()
                                    hasil_ronde, err = jalankan_9_ronde_acak(df_hasil, saham_unik, GEMINI_API_KEY, progress_bar, status_teks)
                                    if err:
                                        st.error(err)
                                    else:
                                        df_spread = pd.DataFrame({f"RONDE {i}": (hasil_ronde.get(i, []) + ["", "", "", "", ""])[:5] for i in range(1, 10)})
                                        st.markdown("### 📋 Spreadsheet Top-5 per Ronde (Siap Salin)")
                                        st.data_editor(df_spread, use_container_width=True, hide_index=True)
                                        from collections import Counter
                                        freq = Counter()
                                        for i in range(1, 10):
                                            freq.update(hasil_ronde.get(i, []))
                                        if freq:
                                            df_freq = pd.DataFrame([(t, c) for t, c in freq.most_common()], columns=["Ticker", "Muncul (dari 9 Ronde)"])
                                            st.markdown("### 🏆 Rekap Konsistensi (semakin sering muncul = semakin dipercaya AI)")
                                            st.dataframe(df_freq, use_container_width=True, hide_index=True)

                elif "Forensik Bandar" in pilihan_ai:
                    st.subheader("📡 Radar Pencari Model Gemini Aktif (Live Server)")
                    st.markdown("Mesin ini akan bertanya langsung ke server Google AI Studio untuk mencari **semua nama model Gemini yang valid dan mendukung fitur Generate Content** untuk API Key Anda, lalu mengujinya satu per satu.")
                    
                    input_tester = st.text_area("📋 Paste Daftar Saham Uji Coba (Minimal 3 Saham):", placeholder="Contoh:\nVISI\nBBHI\nPANI", height=150, key="input_tester_gemini")
                    
                    if st.button("🚀 Tarik Daftar Server Google & Mulai Uji Coba"):
                        GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
                        if not GEMINI_API_KEY:
                            st.error("❌ Kunci API GEMINI belum dipasang di Secrets!")
                        else:
                            saham_bersih = [s.strip().upper() for s in re.split(r'[,\s\n]+', input_tester) if s.strip()]
                            saham_unik = list(dict.fromkeys(saham_bersih))
                            saham_valid = [s for s in saham_unik if s in df_hasil['Ticker'].values]
                            
                            if len(saham_valid) < 2:
                                st.error("❌ Masukkan minimal 2 kode saham yang valid di database hari ini.")
                            else:
                                st.info("🔄 Langkah 1: Meminta katalog model langsung dari server Google AI...")
                                
                                daftar_model_aktif = []
                                try:
                                    genai.configure(api_key=GEMINI_API_KEY)
                                    for m in genai.list_models():
                                        if 'generateContent' in m.supported_generation_methods:
                                            daftar_model_aktif.append(m.name)
                                except Exception as e:
                                    st.error(f"Gagal menarik data dari server Google. Error: {e}")
                                
                                if not daftar_model_aktif:
                                    st.warning("⚠️ Tidak ada model yang ditemukan untuk API Key ini.")
                                else:
                                    st.success(f"✅ Ditemukan {len(daftar_model_aktif)} model Gemini yang online untuk Anda! Memulai pengujian...")
                                    
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    
                                    payload_text = ""
                                    for ticker in saham_valid:
                                        data_saham = df_hasil[df_hasil['Ticker'] == ticker].iloc[0]
                                        payload_text += f"\n- {ticker}: Harga {data_saham.get('Harga (Rp)', 0)}, Vol {data_saham.get('Volume', 0)}"

                                    prompt_test = f"""
                                    CRITICAL INSTRUCTION: You are an automated data filter. 
                                    Read this data:
                                    {payload_text}
                                    
                                    MISSION: Pick EXACTLY 1 best ticker based on volume.
                                    STRICT RULE: Output ONLY the 4-letter ticker code (e.g., BBCA). DO NOT add any other words, punctuation, explanations, or formatting.
                                    """
                                    
                                    hasil_rekap = []
                                    
                                    for i, nama_model in enumerate(daftar_model_aktif):
                                        model_id_bersih = nama_model.replace("models/", "")
                                        status_text.text(f"⏳ Sedang menguji: {model_id_bersih} ({i+1}/{len(daftar_model_aktif)})")
                                        
                                        try:
                                            model_uji = genai.GenerativeModel(model_id_bersih)
                                            response = model_uji.generate_content(prompt_test)
                                            raw_content = response.text or ""
                                            bersih = raw_content.replace('`', '').replace('.', '').replace('\n', '').strip().upper()
                                            
                                            if bersih in saham_valid:
                                                status = "✅ Lulus & Patuh (Sangat Cocok!)"
                                            else:
                                                status = f"⚠️ Aktif tapi Bawel (Jawab: {raw_content.strip()[:25]}...)"
                                                
                                            hasil_rekap.append({"Nama Model": model_id_bersih, "Status": status})
                                            
                                        except Exception as e:
                                            pesan_error = str(e)
                                            hasil_rekap.append({"Nama Model": model_id_bersih, "Status": f"❌ Gagal: {pesan_error[:30]}..."})
                                        
                                        progress_bar.progress((i + 1) / len(daftar_model_aktif))
                                        time.sleep(2)
                                    
                                    status_text.success("🎉 Pengecekan Server Google Selesai!")
                                    
                                    df_rekap = pd.DataFrame(hasil_rekap)
                                    st.markdown("### 🏆 Hasil Uji Coba Model Gemini (Live Server)")
                                    st.dataframe(df_rekap, use_container_width=True)
                                    
                                    st.info("💡 **TUGAS ANDA:** Salin nama model yang berstatus '✅ Lulus & Patuh', dan kita gunakan nama pasti itu untuk skrip turnamen!")

                elif "Pemburu ARA" in pilihan_ai:
                    st.subheader("🎯 Pemburu ARA — 2 Bagian")
                    st.caption("**Bagian 1** mencetak daftar belanja simulator. **Bagian 2** radar referensi uang asli (tidak menulis apa pun).")

                    # ========== BAGIAN 1: PEMBUAT DAFTAR BELANJA (SIMULATOR) ==========
                    st.markdown("### 🛸 Bagian 1 — Auto-Pilot Pembuat Daftar Belanja")
                    st.caption("Menyeleksi 15 saham terbaik per rumus → AI sidang Top 5 → **menulis kertas belanja** ke simulator (Tab 4).")
                    paksa_sidang_ara = st.checkbox("🔄 Paksa Sidang Ulang (abaikan cache Mode Kilat)", key="paksa_sidang_ara")
                    if st.button("🛸 Jalankan Auto-Pilot (Buat Daftar Belanja)", type="primary", key="autopilot_ara"):
                        GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
                        if not GEMINI_API_KEY:
                            st.error("❌ Kunci API GEMINI belum dipasang!")
                        else:
                            daftar_rumus = {1: df_v1, 2: df_v2, 3: df_v3, 4: df_v4, 5: df_v5, 6: df_v6, 7: df_v7, 8: df_v8, 9: df_v9}
                            stempel_data = str(df_hasil["Terakhir Update"].iloc[0]) if "Terakhir Update" in df_hasil.columns else "tanpa_stempel"
                            keranjang_spreadsheet = None
                            if not paksa_sidang_ara and os.path.exists(FILE_CACHE_AUTOPILOT):
                                try:
                                    with open(FILE_CACHE_AUTOPILOT, "r") as f: cache_muat = json.load(f)
                                    if cache_muat.get("stempel_data") == stempel_data and cache_muat.get("versi") == VERSI_SIDANG and cache_muat.get("keranjang"):
                                        ada_isi_cache = any(len([t for t in cache_muat["keranjang"].get(f"RUMUS {i}", []) if t]) > 0 for i in range(1, 10))
                                        if ada_isi_cache:
                                            keranjang_spreadsheet = cache_muat["keranjang"]
                                            st.info("⚡ **Mode Kilat Aktif:** hasil sidang sebelumnya ditampilkan instan dari cache.")
                                except: pass
                            if keranjang_spreadsheet is None:
                                progress_bar = st.progress(0)
                                status_teks = st.empty()
                                keranjang_spreadsheet, err_global, laporan_sidang = jalankan_sidang_autopilot(daftar_rumus, df_hasil, GEMINI_API_KEY, progress_bar, status_teks)
                                if err_global:
                                    st.error(err_global)
                                else:
                                    df_laporan = pd.DataFrame([{
                                        "Rumus": f"RUMUS {i}",
                                        "Status": laporan_sidang[i]["status"],
                                        "Keterangan": laporan_sidang[i]["detail"]
                                    } for i in range(1, 10)])
                                    st.markdown("#### 🧾 Laporan Sidang (Transparan)")
                                    st.dataframe(df_laporan, use_container_width=True, hide_index=True)
                                    ada_isi = any(laporan_sidang[i]["status"] == "✅ Sukses" for i in range(1, 10))
                                    if ada_isi:
                                        try:
                                            with open(FILE_CACHE_AUTOPILOT, "w") as f:
                                                json.dump({"stempel_data": stempel_data, "versi": VERSI_SIDANG, "keranjang": keranjang_spreadsheet}, f, indent=4)
                                        except: pass
                                        # S2b — simpan snapshot untuk Telegram
                                        simpan_snapshot_radar(keranjang_spreadsheet, stempel_data)
                                        status_teks.success("🎉 MISSION ACCOMPLISHED! Daftar belanja baru tercetak & ter-upload ke R2.")
                                        st.balloons()
                                    else:
                                        status_teks.warning("⚠️ Sidang selesai tetapi tidak ada jawara. Baca Laporan Sidang untuk tahu penyebab pastinya.")
                            st.markdown("#### 📋 Tabel Master Portofolio (Siap Salin)")
                            for kunci in keranjang_spreadsheet:
                                keranjang_spreadsheet[kunci] = (keranjang_spreadsheet[kunci] + ["", "", "", "", ""])[:5]
                            df_spreadsheet = pd.DataFrame(keranjang_spreadsheet)
                            st.data_editor(df_spreadsheet, use_container_width=True, hide_index=True)

                    st.markdown("---")

                    # ========== BAGIAN 2: RADAR LIVE (SUMBER AI YANG SAMA) ==========
                    st.markdown("### 📡 Bagian 2 — Radar Live Top-5 (Sumber AI yang Sama)")
                    st.caption("Menampilkan **hasil sidang AI yang sama persis** dengan Daftar Belanja (Bagian 1). Tidak ada AI kedua → hasil dijamin identik & hemat kuota. Refresh ±5 menit hanya memuat ulang hasil.")
                    if AUTOREFRESH_OK:
                        st_autorefresh(interval=5 * 60 * 1000, key="radar_live_autorefresh")
                    _now = datetime.utcnow() + pd.Timedelta(hours=7)
                    _jam = _now.time()
                    live = (_now.weekday() < 5) and (pd.Timestamp("08:45").time() <= _jam <= pd.Timestamp("16:05").time())
                    st.caption("🟢 DATA LIVE (jam bursa)" if live else "📴 Data penutupan terakhir (di luar jam bursa)")

                    stempel_now = str(df_hasil["Terakhir Update"].iloc[0]) if (not df_hasil.empty and "Terakhir Update" in df_hasil.columns) else "tanpa_stempel"

                    def _muat_keranjang_ai():
                        try:
                            if os.path.exists(FILE_CACHE_AUTOPILOT):
                                with open(FILE_CACHE_AUTOPILOT) as f:
                                    cm = json.load(f)
                                if cm.get("versi") == VERSI_SIDANG and cm.get("keranjang") and cm.get("stempel_data") == stempel_now:
                                    return cm["keranjang"], "cache_cocok"
                        except Exception:
                            pass
                        ker, ada = {}, False
                        for i in range(1, 10):
                            fs = f"Database/sinyal_ai_rumus_{i}.csv"
                            if os.path.exists(fs):
                                try:
                                    ds = pd.read_csv(fs)
                                    ker[f"RUMUS {i}"] = (ds["Ticker"].tolist() + ["", "", "", "", ""])[:5]
                                    ada = True
                                except Exception:
                                    ker[f"RUMUS {i}"] = ["", "", "", "", ""]
                            else:
                                ker[f"RUMUS {i}"] = ["", "", "", "", ""]
                        return (ker if ada else None), "sinyal"

                    auto_sidang_radar = st.checkbox("🤖 Auto-sidang ulang saat data berubah (pakai kuota AI)", key="auto_sidang_radar")
                    keranjang_radar, sumber_radar = _muat_keranjang_ai()

                    if auto_sidang_radar and sumber_radar != "cache_cocok":
                        GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
                        if GEMINI_API_KEY:
                            with st.spinner("Data berubah — sidang AI ulang agar Radar & Daftar Belanja tetap identik..."):
                                daftar_rumus_r = {1: df_v1, 2: df_v2, 3: df_v3, 4: df_v4, 5: df_v5, 6: df_v6, 7: df_v7, 8: df_v8, 9: df_v9}
                                keranjang_radar, err_r, lap_r = jalankan_sidang_autopilot(daftar_rumus_r, df_hasil, GEMINI_API_KEY)
                                if not err_r and keranjang_radar:
                                    try:
                                        with open(FILE_CACHE_AUTOPILOT, "w") as f:
                                            json.dump({"stempel_data": stempel_now, "versi": VERSI_SIDANG, "keranjang": keranjang_radar}, f, indent=4)
                                    except Exception:
                                        pass
                                    # S3 — simpan snapshot untuk Telegram
                                    simpan_snapshot_radar(keranjang_radar, stempel_now)
                                    sumber_radar = "sidang_baru"

                    if keranjang_radar:
                        df_radar = pd.DataFrame({k: (v + ["", "", "", "", ""])[:5] for k, v in keranjang_radar.items()})
                        st.markdown("#### 🏆 Top-5 per Rumus (hasil sidang AI — identik dengan Daftar Belanja)")
                        st.dataframe(df_radar, use_container_width=True, hide_index=True)
                        lbl = {"cache_cocok": "⚡ cache sidang (data belum berubah)",
                               "sinyal": "📄 file sinyal aktif",
                               "sidang_baru": "🤖 sidang AI baru saja dijalankan"}.get(sumber_radar, sumber_radar)
                        st.caption(f"Sumber: {lbl}.")
                    else:
                        st.info("📭 Belum ada hasil sidang AI. Jalankan **Bagian 1** sekali, atau centang Auto-sidang di atas.")
                        df_radar = None
                    if df_radar is not None and st.button("🧠 Mintakan opini AI sekarang (hemat kuota: hanya saat diklik)", key="btn_opini_radar"):
                        prompt_radar = f"""Berikut hasil radar top-5 per rumus screener IHSG saat ini:
{df_radar.to_string(index=False)}
Berikan opini singkat (maks 150 kata) dalam Bahasa Indonesia: rumus mana yang paling layak dieksekusi uang asli sore ini dan mana yang sebaiknya dihindari, beserta alasan teknikal singkat."""
                        with st.spinner("AI menyusun opini..."):
                            jawab_r, mesin_r = panggil_ai_teks(prompt_radar)
                        st.markdown(jawab_r)
                        st.caption(f"⚡ via {mesin_r}")


# =====================================================================
# >>> PART 13 : TAB 4 - PORTOFOLIO BOT (+ KURASI DAFTAR BELANJA) <<<
# =====================================================================
    with tab4:
        @st.cache_data(ttl=60)
        def _sedot_porto_r2():
            try:
                import r2_client
                return r2_client.download_database()
            except Exception:
                return False
        _sedot_porto_r2()

        st.markdown("## 🤖 Monitor Bot Simulator")
        
        # >>> PAGAR STRATEGI: beli = manual saja, jual = otomatis
        st.info("🔒 **Pagar strategi:** BELI hanya lewat tombol di bawah ini (manual). Cron laptop TIDAK pernah membeli — ia hanya mengurus JUAL (TP/CL/square-off) saat jam bursa. Daftar belanja yang tidak Anda inginkan bisa disapu bersih di bagian **Kurasi** bawah.")
        if st.button("🛒 Eksekusi Pembelian Bot Sekarang!", type="primary", use_container_width=True):
            with st.spinner("Bot mengeksekusi pembelian dengan harga terakhir..."):
                import subprocess
                import sys
                try:
                    proses_bot = subprocess.run([sys.executable, "bot_simulator.py", "--manual"], capture_output=True, text=True)
                    if proses_bot.returncode != 0:
                        st.error("❌ Bot gagal dijalankan. Log error:")
                        st.code(proses_bot.stderr, language="bash")
                    else:
                        st.success("✅ Bot selesai! Berikut log eksekusinya:")
                        st.code(proses_bot.stdout[-2500:], language="bash")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"Sistem web gagal memanggil file bot: {e}")
        
        col_backup, col_restore = st.columns(2)
        with col_backup:
            if st.button("💾 Backup Portofolio ke R2", use_container_width=True):
                with st.spinner("Mengunggah seluruh Database ke Cloudflare R2..."):
                    import r2_client
                    ok = r2_client.upload_database()
                if ok:
                    st.success("✅ Portofolio, histori & sinyal AMAN di R2 (tidak akan hilang meski reboot)!")
                else:
                    st.error("❌ Gagal backup ke R2.")
        with col_restore:
            if st.button("⬇️ Tarik Portofolio dari R2", use_container_width=True):
                with st.spinner("Menarik data portofolio terbaru dari R2..."):
                    import r2_client
                    ok = r2_client.download_database()
                if ok:
                    st.success("✅ Data portofolio terbaru berhasil ditarik!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Gagal menarik dari R2.")
        
        # >>> BARU: KURASI DAFTAR BELANJA — sapu bersih 9 rumus (lokal + R2)
        st.markdown("---")
        st.markdown("### 🗑️ Kurasi Daftar Belanja")
        st.caption("Buang kertas belanja yang tidak ingin Anda beli — terhapus di web DAN di R2, sehingga cron laptop & tombol Eksekusi tidak akan menyentuhnya. Posisi yang sudah dibeli TIDAK tersentuh.")
        if st.session_state.get("konfirmasi_sapu_sinyal"):
            st.warning("️ Seluruh daftar belanja di 9 arena akan dihapus (lokal & R2). Lanjutkan?")
            col_ya, col_batal = st.columns(2)
            with col_ya:
                if st.button("✅ YA, SAPU BERSIH SEMUA", type="primary", key="sapu_ya"):
                    terhapus = 0
                    for i in range(1, 10):
                        f_local = f"Database/sinyal_ai_rumus_{i}.csv"
                        if os.path.exists(f_local):
                            try:
                                os.remove(f_local); terhapus += 1
                            except Exception: pass
                        try:
                            r2_client.hapus_objek(f"Database/sinyal_ai_rumus_{i}.csv")
                        except Exception: pass
                    st.session_state["konfirmasi_sapu_sinyal"] = False
                    st.success(f"🧹 Selesai: {terhapus} file lokal dibuang + seluruh objek sinyal di R2 dihapus. Daftar belanja kini kosong.")
                    time.sleep(1)
                    st.rerun()
            with col_batal:
                if st.button("↩️ Batal", key="sapu_batal"):
                    st.session_state["konfirmasi_sapu_sinyal"] = False
                    st.rerun()
        else:
            if st.button("🗑️ Kosongkan Semua Daftar Belanja (9 Rumus)", use_container_width=True,
                         help="Hapus kertas belanja yang tidak ingin Anda beli — lokal & R2 sekaligus"):
                st.session_state["konfirmasi_sapu_sinyal"] = True
                st.rerun()
        
        st.markdown("---")
        
        st.markdown("## 📊 Dashboard Performa AI (Live)")
        
        pilihan_arena = st.selectbox("📂 Pilih Arena untuk diinspeksi:", [f"Rumus {i}" for i in range(1, 10)])
        nomor_rumus = pilihan_arena.split(" ")[1]

        FILE_SINYAL = f"Database/sinyal_ai_rumus_{nomor_rumus}.csv"
        file_porto = f"Database/portofolio_aktif_rumus_{nomor_rumus}.csv"
        file_hist = f"Database/histori_transaksi_rumus_{nomor_rumus}.csv"

        MODAL_AWAL = 100000000.0 
        
        df_porto = pd.read_csv(file_porto) if os.path.exists(file_porto) else pd.DataFrame()
        df_hist = pd.read_csv(file_hist) if os.path.exists(file_hist) else pd.DataFrame()

        total_profit_rp = df_hist['Total_Return_Rp'].sum() if not df_hist.empty and 'Total_Return_Rp' in df_hist.columns else 0
        modal_terpakai = df_porto['Total_Modal'].sum() if not df_porto.empty and 'Total_Modal' in df_porto.columns else 0
        
        saldo_saat_ini = MODAL_AWAL + total_profit_rp - modal_terpakai
        total_aset = saldo_saat_ini + modal_terpakai
        
        total_trade = len(df_hist)
        win_trade = loss_trade = be_trade = 0
        winrate = 0.0
        profit_factor = 0.0
        avg_return = 0.0
        if total_trade > 0 and 'Return_%' in df_hist.columns:
            win_trade = int((df_hist['Return_%'] > 0).sum())
            loss_trade = int((df_hist['Return_%'] < 0).sum())
            be_trade = total_trade - win_trade - loss_trade
            winrate = (win_trade / total_trade) * 100
            gross_profit = df_hist.loc[df_hist['Total_Return_Rp'] > 0, 'Total_Return_Rp'].sum()
            gross_loss = abs(df_hist.loc[df_hist['Total_Return_Rp'] < 0, 'Total_Return_Rp'].sum())
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
            avg_return = df_hist['Return_%'].mean()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="💰 Total Aset (Kas + Saham)", value=f"Rp {total_aset:,.0f}".replace(",", "."))
        with col2:
            st.metric(label="💵 Dana Kas Tersedia", value=f"Rp {saldo_saat_ini:,.0f}".replace(",", "."))
        with col3:
            tanda = "+" if total_profit_rp >= 0 else "-"
            st.metric(label="📈 Realized Profit/Loss",
                      value=f"Rp {total_profit_rp:,.0f}".replace(",", "."),
                      delta=f"{tanda} Rp {abs(total_profit_rp):,.0f}".replace(",", "."),
                      delta_color="normal")
        with col4:
            st.metric(label="🎯 Winrate AI", value=f"{winrate:.1f}%",
                      delta=f"✅ {win_trade} Win | ❌ {loss_trade} Loss | ➖ {be_trade} BE",
                      delta_color="off")

        m1, m2 = st.columns(2)
        with m1:
            pf_txt = "∞" if profit_factor == float('inf') else f"{profit_factor:.2f}"
            st.metric(label="⚖️ Profit Factor (ideal > 1.5)", value=pf_txt)
        with m2:
            st.metric(label="📊 Rata-rata Return/Trade", value=f"{avg_return:.2f}%")

        st.markdown("---")
        
        sub1, sub2, sub3 = st.tabs(["📝 Sinyal Antrean", "🟢 Lapis 1: Portofolio Aktif", "📚 Lapis 2: Histori Transaksi"])
        
        with sub1:
            if os.path.exists(FILE_SINYAL):
                df_sinyal = pd.read_csv(FILE_SINYAL)
                st.success("🔥 Sinyal AI (Kertas Belanja) diterima! Menunggu eksekusi MANUAL Anda lewat tombol 🛒 di atas — cron tidak akan membelinya.")
                st.dataframe(df_sinyal, use_container_width=True, hide_index=True)
            else:
                st.info(f"KOSONG. Belum ada sinyal masuk untuk {pilihan_arena}, atau bot sudah membelinya dan membakar kertas belanja.")
        
        with sub2:
            if not df_porto.empty:
                df_porto_tampil = df_porto.copy()
                df_porto_tampil['Harga_Beli'] = df_porto_tampil['Harga_Beli'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                df_porto_tampil['Target_TP'] = df_porto_tampil['Target_TP'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                df_porto_tampil['Target_CL'] = df_porto_tampil['Target_CL'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                df_porto_tampil['Total_Modal'] = df_porto_tampil['Total_Modal'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                st.dataframe(df_porto_tampil, use_container_width=True, hide_index=True)
            else:
                st.info("📦 Gudang kosong. Belum ada saham yang dibeli atau semua sudah terjual (Masuk ke Lapis 2).")
        
        with sub3:
            if not df_hist.empty:
                def warnai_profit(val):
                    if isinstance(val, (int, float)):
                        color = '#166534' if val > 0 else '#991b1b' if val < 0 else ''
                        return f'background-color: {color}'
                    return ''
                    
                if 'Tanggal_Jual' in df_hist.columns:
                    df_hist_tampil = df_hist.sort_values(by='Tanggal_Jual', ascending=False).reset_index(drop=True)
                else:
                    df_hist_tampil = df_hist.copy()
                    
                styler = df_hist_tampil.style
                kolom_warna = [c for c in ['Total_Return_Rp', 'Return_%'] if c in df_hist_tampil.columns]
                if kolom_warna:
                    if hasattr(styler, "map"):
                        styler = styler.map(warnai_profit, subset=kolom_warna)
                    else:
                        styler = styler.applymap(warnai_profit, subset=kolom_warna)
                
                fmt = {}
                for c, f in [('Harga_Beli', "Rp {:,.0f}"), ('Harga_Jual', "Rp {:,.0f}"),
                             ('Total_Return_Rp', "Rp {:,.0f}"), ('Return_%', "{:.2f}%")]:
                    if c in df_hist_tampil.columns:
                        fmt[c] = f
                
                st.dataframe(styler.format(fmt), use_container_width=True, hide_index=True)
            else:
                st.info(f"📭 Belum ada riwayat penjualan saham untuk {pilihan_arena}.")

# =====================================================================
# >>> PART 14 : TAB 5 - DETEKTIF LEDAKAN (HANYA BACA) + CHAT AI <<<
# =====================================================================
    with tab5:
        st.markdown("## 🕵️ Detektif Ledakan & Ruang Obrolan AI")
        st.caption("Angka dihitung LOKAL dari arsip intraday R2 (snapshot 5-menitan) + Buku Besar Harian (50 hari, gzip ±1MB). AI gratis hanya menyusun narasi — tidak berhitung.")
        st.caption("🔒 **Pagar keamanan:** Tab ini hanya MEMBACA & MENGANALISIS — tidak pernah membeli, menjual, atau mengubah portofolio/sinyal Anda.")

        HARI_INI = (datetime.utcnow() + pd.Timedelta(hours=7)).strftime("%Y-%m-%d")
        lb = muat_buku_besar()
        tgl_opsi = sorted(lb["Tanggal"].astype(str).unique(), reverse=True) if not lb.empty else []
        arsip_hari_ini = muat_arsip_harian(HARI_INI)
        if not arsip_hari_ini.empty and HARI_INI not in tgl_opsi:
            tgl_opsi = [HARI_INI] + tgl_opsi

        def _set_otopsi(t, tgl):
            st.session_state["otopsi_ticker"] = t
            st.session_state["otopsi_tanggal"] = tgl

        # ---------- Mesin hitung lokal ----------
        def anomali_intraday(df_day, ticker):
            g = df_day[df_day["Ticker"] == ticker].copy()
            if g.empty: return [], None
            cw = next((c for c in ["Waktu Update", "Terakhir Update"] if c in g.columns), g.columns[0])
            g["_jam"] = g[cw].astype(str).str.split(" ").str[-1].str[:5]
            g = g.sort_values("_jam")
            h = pd.to_numeric(g["Harga (Rp)"], errors="coerce")
            v = pd.to_numeric(g["Volume"], errors="coerce")
            c = pd.to_numeric(g["Change (%)"], errors="coerce")
            swing = (h.max() - h.min()) / h.min() * 100 if h.min() else 0.0
            ringkas = {"Open": h.iloc[0], "High": h.max(), "Low": h.min(), "Close": h.iloc[-1],
                       "Swing_%": round(swing, 2), "Puncak_Change_%": round(c.max(), 2) if not c.isna().all() else 0.0,
                       "Slot": len(g)}
            ciri = []
            dv = v.diff().fillna(0)
            if len(dv) > 9:
                rata = dv.iloc[1:-6].mean()
                akhir = dv.tail(6).sum()
                if rata and rata > 0 and akhir / (rata * 6) >= 2.5:
                    ciri.append(f"🌋 Ledakan volume sesi akhir: 30 menit terakhir ≈{akhir / (rata * 6):.1f}x rata-rata slot")
            ta, tk = str(g.iloc[0].get("Tekanan Bandar", "")), str(g.iloc[-1].get("Tekanan Bandar", ""))
            if "Jual" in ta and "Beli" in tk:
                ciri.append(f"🔄 Pressure flip: {ta} → {tk}")
            bbs = g["Status BB"].astype(str).tolist() if "Status BB" in g.columns else []
            if "Squeeze" in bbs and any("Breakout" in b for b in bbs[bbs.index("Squeeze"):]):
                ciri.append("🌐 Squeeze → Breakout Upper dalam satu hari")
            if swing < 3 and "Beli" in tk and "Akumulasi" in str(g.iloc[-1].get("Kekuatan A/D", "")):
                ciri.append(f"🤫 Silent accumulation: harga flat (swing {swing:.1f}%) tapi {tk} + {g.iloc[-1].get('Kekuatan A/D')}")
            p15 = g[g["_jam"] >= "15:00"]
            if len(p15) > 0 and len(h) > len(p15):
                dasar = h.iloc[-len(p15) - 1]
                if dasar:
                    jump = (h.iloc[-1] - dasar) / dasar * 100
                    if jump >= 1.5: ciri.append(f"⏰ Closing jump: {jump:+.1f}% setelah 15:00")
            if not c.isna().all() and abs(c.iloc[0]) >= 2:
                ciri.append(f"🚪 Gap open: {c.iloc[0]:+.1f}% di snapshot pertama")
            if "Posisi VWAP" in g.columns:
                rk = (g["Posisi VWAP"].astype(str) == "Di Atas VWAP (Kuat)").mean()
                if rk >= 0.7: ciri.append(f"🛡️ Ditahan di atas VWAP {rk * 100:.0f}% waktu perdagangan")
            return ciri, ringkas

        def kenapa_lolos(r):
            get = lambda k: str(r.get(k, ""))
            vk = get("Posisi VWAP") == "Di Atas VWAP (Kuat)"
            vo = get("Posisi VWAP") != "Di Bawah VWAP (Lemah)"
            ap = get("Kekuatan A/D") == "Akumulasi Pro (Smart Money)"
            _ch = pd.to_numeric(r.get("Change (%)", 0), errors="coerce")
            _ch = 0.0 if pd.isna(_ch) else float(_ch)
            cek = {
                1: [("Smart Money A/D", ap), ("Bandar Akumulasi Kuat", get("Status Bandar") == "Akumulasi Kuat"), ("VWAP tidak lemah", vo)],
                2: [("Hammer/Jarum Bawah", get("Pola Candle") == "Hammer (Potensi Reversal)" or get("Sinyal Cuci Barang") == "Jarum Bawah (Sinyal Pantulan Kuat)"), ("VWAP kuat", vk), ("Smart Money A/D", ap)],
                3: [("VWAP kuat", vk), ("Tekanan HAKA", get("Tekanan Bandar") == "Dominan Beli (Hajar Kanan)"), ("Open=Low", get("Status Open") == "Open = Low (Bullish Kuat)"), ("Rekomendasi BELI", get("Rekomendasi") == "BELI")],
                4: [("Golden Cross", get("MA Cross") == "Golden Cross"), ("Tembus MA20", get("Vol Breakout") == "Tembus MA20"), ("Uptrend", get("MA Signal") == "Uptrend"), ("VWAP kuat", vk)],
                5: [("Ritel Aktif", get("Kelas Transaksi") == "Ritel Aktif (5M - 50M)"), ("Tembus MA20", get("Vol Breakout") == "Tembus MA20"), ("VWAP kuat", vk), ("Uptrend", get("MA Signal") == "Uptrend")],
                6: [("RVOL anomali tinggi", get("RVOL (Anomali Vol)") in ("Anomali Tinggi (150-300%)", "Ledakan Ekstrem (> 300%)")), ("OBV Akumulasi", get("OBV Trend") == "Akumulasi (Naik)"), ("Change ≤ 5%", _ch <= 5.0), ("Tekanan HAKA", get("Tekanan Bandar") == "Dominan Beli (Hajar Kanan)")],
                7: [("ML Anomali Bandar", get("Prediksi Machine Learning") == "🔥 ANOMALI BANDAR (Siap Ledakan)"), ("Stochastic peluang", get("Status Stochastic") in ("Oversold (Jenuh Jual - Peluang)", "Golden Cross (Awal Bullish)")), ("VWAP tidak lemah", vo)],
                8: [("Katalis sentimen/akuisisi", get("Status Sentimen") == "Sentimen Positif 📰" or get("Status Akuisisi") in ("RENCANA AKUISISI", "DALAM AKUISISI")), ("Uptrend", get("MA Signal") == "Uptrend"), ("Rekomendasi BELI", get("Rekomendasi") == "BELI")],
                9: [("MACD bullish", get("MACD") in ("Strong Bullish", "Bullish MACD")), ("R/R menarik", get("Risk/Reward Ratio") in ("Sangat Menarik (> 1:3)", "Ideal (1:2)")), ("Dekat Support", get("Posisi Entry") == "Dekat Support (Low Risk)"), ("Momentum Positif", get("Momentum") == "Positif")],
            }
            return {i: [lab for lab, ok in pairs if not ok] for i, pairs in cek.items() if any(not ok for _, ok in pairs)}

        def tren_50h(ticker):
            if lb.empty: return None
            g = lb[lb["Ticker"] == ticker].sort_values("Tanggal").tail(50).copy()
            if g.empty: return None
            for kol in ["Volume", "Close"]:
                g[kol] = pd.to_numeric(g[kol], errors="coerce")
            g["MA5_vol"] = g["Volume"].rolling(5).mean()
            g["MA20_vol"] = g["Volume"].rolling(20).mean()
            g["MA50_vol"] = g["Volume"].rolling(50).mean()
            g["MA20_close"] = g["Close"].rolling(20).mean()
            return g

        def narasi_ai(konteks, pertanyaan):
            prompt = f"""Kamu analis detektif pasar saham Indonesia. FAKTA hanya dari BLOK DATA di bawah; untuk edukasi/konsep gunakan pengetahuan umum. Jika fakta tidak ada, katakan jujur. Jawab Bahasa Indonesia, analitis, tanpa basa-basi.
            BLOK DATA:
            {konteks}
            PERTANYAAN: {pertanyaan}"""
            
            error_log = []
            
            # 1. Coba Gemini (Langsung tembak model flash, skip list_models agar tidak kena rate limit)
            try:
                GK = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
                if GK:
                    genai.configure(api_key=GK)
                    for model_nama in ["gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-1.0-pro"]:
                        try:
                            r = genai.GenerativeModel(model_nama).generate_content(prompt)
                            if r.text: return r.text, f"Gemini ({model_nama})"
                        except Exception:
                            continue
                    error_log.append("Gemini: Semua model flash/pro limit atau gagal.")
                else:
                    error_log.append("Gemini: API Key tidak ada di secrets.")
            except Exception as e:
                error_log.append(f"Gemini error: {str(e)[:80]}")

            # 2. Coba OpenRouter
            try:
                OK_ = st.secrets.get("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY"))
                if OK_:
                    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OK_)
                    cp = client.chat.completions.create(
                        model="openrouter/free", 
                        messages=[{"role": "user", "content": prompt}], 
                        temperature=0.4, 
                        max_tokens=1500
                    )
                    isi = cp.choices[0].message.content
                    if isi: return isi, "OpenRouter"
                    else: error_log.append("OpenRouter: Respons kosong dari server.")
                else:
                    error_log.append("OpenRouter: API Key tidak ada di secrets.")
            except Exception as e:
                error_log.append(f"OpenRouter error: {str(e)[:80]}")

            return f"❌ Kedua mesin AI gagal. Detail: {' | '.join(error_log)}", "error"

        def simpan_kasus(entry):
            try:
                import r2_client
                tmp = os.path.join(tempfile.gettempdir(), "kasus_web.json")
                data = []
                if r2_client.download_arsip("Buku_Besar/kasus_ledakan.json", tmp):
                    try: data = json.load(open(tmp))
                    except Exception: data = []
                data.append(entry); data = data[-200:]
                json.dump(data, open(tmp, "w"), indent=2)
                r2_client.upload_arsip(tmp, "Buku_Besar/kasus_ledakan.json")
            except Exception: pass

        # ---------- Panel kontrol ----------
        if not tgl_opsi:
            st.info("📖 Buku Besar belum ada. Jalankan sekali di laptop: `./.venv/bin/python bangun_buku_besar.py --backfill`")
        c1, c2 = st.columns([1, 1])
        with c1:
            ticker_inp = st.text_input("Kode saham:", placeholder="Contoh: LAPD", key="otopsi_ticker").strip().upper()
        with c2:
            tanggal_inp = st.selectbox("Tanggal otopsi:", tgl_opsi if tgl_opsi else [HARI_INI], key="otopsi_tanggal")

        # ---------- Chip ledakan (swing low→high ≥10%) ----------
        if not lb.empty and tgl_opsi:
            tgl_chip = HARI_INI if HARI_INI in tgl_opsi else tgl_opsi[0]
            dfx = lb[lb["Tanggal"].astype(str) == tgl_chip]
            df_ledakan = dfx[(pd.to_numeric(dfx["Swing_%"], errors="coerce") >= 10) | (pd.to_numeric(dfx["Puncak_Change_%"], errors="coerce") >= 10)]
            df_ledakan = df_ledakan.sort_values("Swing_%", ascending=False).head(12)
            if not df_ledakan.empty:
                st.markdown(f"**🔥 Terdeteksi swing low→high ≥10% pada {tgl_chip}** *(saham yang pagi terbang lalu sore turun TETAP tertangkap)*:")
                n_col = min(len(df_ledakan), 6)
                chips = st.columns(n_col)
                for i, (_, r) in enumerate(df_ledakan.head(n_col).iterrows()):
                    with chips[i]:
                        st.button(f"{r.Ticker} ⤴{float(r['Swing_%']):.0f}%", key=f"chip_{r.Ticker}_{tgl_chip}",
                                  on_click=_set_otopsi, args=(r.Ticker, tgl_chip))

        # ---------- Tombol template ----------
        st.markdown("---")
        tpl = st.columns(4)
        aksi = None
        with tpl[0]:
            if st.button("🩺 Otopsi H-1", use_container_width=True): aksi = "otopsi"
            if st.button("🚫 Kenapa lolos radar?", use_container_width=True): aksi = "lolos"
        with tpl[1]:
            if st.button("📈 Tren 50H (MA5/20/50)", use_container_width=True): aksi = "tren"
            if st.button("🎯 Checklist siap gap-up", use_container_width=True): aksi = "gapup"
        with tpl[2]:
            if st.button("🧬 Ciri ledakan (naratif)", use_container_width=True): aksi = "dna"
            if st.button("⏱️ Fokus sesi akhir 14:00+", use_container_width=True): aksi = "sesi"
        with tpl[3]:
            if st.button("💡 Usulan rumus baru", use_container_width=True): aksi = "rumus"
            if st.button("🗑️ Bersihkan chat", use_container_width=True):
                st.session_state["chat_detektif"] = []
                st.rerun()

        # ---------- Eksekusi template ----------
        if aksi and ticker_inp and tanggal_inp:
            df_day = muat_arsip_harian(tanggal_inp)
            ciri, ringkas = anomali_intraday(df_day, ticker_inp) if not df_day.empty else ([], None)
            row_h1 = None
            if not df_day.empty and not df_day[df_day["Ticker"] == ticker_inp].empty:
                row_h1 = df_day[df_day["Ticker"] == ticker_inp].iloc[-1]
            elif not lb.empty:
                lbb = lb[(lb["Ticker"] == ticker_inp) & (lb["Tanggal"].astype(str) == tanggal_inp)]
                if not lbb.empty: row_h1 = lbb.iloc[-1]
            if row_h1 is None:
                st.warning(f"❌ Tidak ada data {ticker_inp} pada {tanggal_inp}.")
            else:
                konteks = f"SAHAM {ticker_inp} TANGGAL {tanggal_inp}\n"
                if ringkas: konteks += f"OHLC intraday: Open {ringkas['Open']} High {ringkas['High']} Low {ringkas['Low']} Close {ringkas['Close']} | Swing {ringkas['Swing_%']}% | Puncak change {ringkas['Puncak_Change_%']}%\n"
                konteks += f"Baris penutup hari: Tekanan {row_h1.get('Tekanan Bandar', row_h1.get('Tekanan'))} | Siklus {row_h1.get('Fase Siklus Bandar', row_h1.get('Siklus'))} | A/D {row_h1.get('Kekuatan A/D', row_h1.get('AD'))} | BB {row_h1.get('Status BB', row_h1.get('BB'))} | RVOL {row_h1.get('RVOL (Anomali Vol)', row_h1.get('RVOL'))} | Supply {row_h1.get('Kondisi Supply', row_h1.get('Supply'))} | Score {row_h1.get('Total Score', row_h1.get('Score'))} | Rekomendasi {row_h1.get('Rekomendasi')}\n"
                if ciri: konteks += "ANOMALI TERDETEKSI:\n- " + "\n- ".join(ciri) + "\n"
                gt = tren_50h(ticker_inp)
                if gt is not None and len(gt) > 1:
                    l = gt.iloc[-1]
                    konteks += f"TREN 50H: hari ke-{len(gt)} | Close {l['Close']} vs MA20 {l['MA20_close']:.0f} | Vol terakhir {l['Volume']:.0f} vs MA5 {l['MA5_vol']:.0f} / MA20 {l['MA20_vol']:.0f} / MA50 {l['MA50_vol']:.0f}\n"

                if aksi == "otopsi":
                    st.markdown(f"### 🩺 Otopsi {ticker_inp} — {tanggal_inp}")
                    if ringkas:
                        st.dataframe(pd.DataFrame([ringkas]), use_container_width=True, hide_index=True)
                    st.markdown("**Ciri anomali yang terdeteksi mesin:**")
                    st.markdown("\n".join(f"- {x}" for x in ciri) if ciri else "- Tidak ada anomali besar; hari itu tenang.")
                    pertanyaan = f"Jelaskan secara naratif mengapa pergerakan {ticker_inp} pada {tanggal_inp} penting/tidak sebagai persiapan ledakan hari berikutnya."
                elif aksi == "lolos":
                    gagal = kenapa_lolos(row_h1)
                    st.markdown(f"### 🚫 Kenapa {ticker_inp} tidak masuk screener pada {tanggal_inp}?")
                    for i, buruk in gagal.items():
                        st.markdown(f"- **Rumus {i} gagal:** " + ", ".join(buruk))
                    konteks += f"SYARAT RUMUS YANG GAGAL: {gagal}\n"
                    pertanyaan = f"Berdasarkan syarat yang gagal ini, jelaskan kenapa radar melewatkan {ticker_inp} dan ciri mana yang sebenarnya sudah memberi petunjuk."
                elif aksi == "tren":
                    st.markdown(f"### 📈 Tren 50H {ticker_inp}")
                    if gt is None: st.warning("Buku Besar belum punya riwayat saham ini.")
                    else:
                        st.line_chart(gt.set_index("Tanggal")[["Close", "MA20_close"]])
                        st.bar_chart(gt.set_index("Tanggal")[["Volume"]])
                        pertanyaan = f"Interpretasikan tren 50 hari {ticker_inp}: ada build-up senyap atau tidak?"
                elif aksi == "gapup":
                    cek = [
                        ("Tutup dekat high intraday (≥98%)", ringkas and ringkas["Close"] >= 0.98 * ringkas["High"]),
                        ("Swing intraday ≥5%", ringkas and ringkas["Swing_%"] >= 5),
                        ("Volume >2x MA20 volume", gt is not None and len(gt) > 1 and gt['Volume'].iloc[-1] > 2 * gt['MA20_vol'].iloc[-1]),
                        ("Tekanan akhir Dominan Beli", "Beli" in str(row_h1.get("Tekanan Bandar", row_h1.get("Tekanan")))),
                        ("A/D Akumulasi", "Akumulasi" in str(row_h1.get("Kekuatan A/D", row_h1.get("AD")))),
                        ("Supply tidak banjir", "Banjir" not in str(row_h1.get("Kondisi Supply", row_h1.get("Supply")))),
                    ]
                    skor = sum(1 for _, ok in cek if ok)
                    st.markdown(f"### 🎯 Checklist siap gap-up {ticker_inp} — skor {skor}/{len(cek)}")
                    for lab, ok in cek: st.markdown(f"- {'✅' if ok else '❌'} {lab}")
                    st.markdown(f"**Kesimpulan mesin:** {'SIAP GAP-UP' if skor >= 4 else 'MERAGUKAN' if skor >= 2 else 'TIDAK SIAP'} (angka oleh mesin, bukan AI)")
                    konteks += f"CHECKLIST GAPUP: skor {skor}/{len(cek)}\n"
                    pertanyaan = "Beri opini singkat atas checklist gap-up ini."
                elif aksi == "dna":
                    pertanyaan = f"Sebut dan jelaskan ciri-ciri ledakan yang terlihat pada {ticker_inp} tanggal {tanggal_inp} berdasarkan BLOK DATA, dalam bentuk daftar ciri TERLIHAT vs TIDAK TERLIHAT. Jangan bergantung pada skor."
                elif aksi == "sesi":
                    if df_day.empty: st.warning("Arsip intraday tanggal itu tidak tersedia.")
                    else:
                        gs = df_day[df_day["Ticker"] == ticker_inp].copy()
                        cw = next((c for c in ["Waktu Update", "Terakhir Update"] if c in gs.columns), gs.columns[0])
                        gs["_jam"] = gs[cw].astype(str).str.split(" ").str[-1].str[:5]
                        gs = gs[gs["_jam"] >= "14:00"]
                        st.dataframe(gs[["_jam", "Harga (Rp)", "Volume", "Change (%)", "Tekanan Bandar"]].tail(20), use_container_width=True, hide_index=True)
                    pertanyaan = f"Analisis sesi akhir (14:00-tutup) {ticker_inp} pada {tanggal_inp}: ada persiapan mark-up apa?"
                else:  # rumus
                    pertanyaan = f"Berdasarkan kasus {ticker_inp} {tanggal_inp} yang lolos radar, usulkan 1 rumus/filter BARU yang konkret (sebutkan nama kolom dan nilainya) agar pola serupa tertangkap besok."

                with st.spinner("Mesin menghitung + AI menyusun narasi..."):
                    jawab, mesin = narasi_ai(konteks, pertanyaan)
                st.markdown(jawab)
                st.caption(f"⚡ Narasi via {mesin} | angka dihitung lokal.")
                simpan_kasus({"tanggal_otopsi": str(datetime.utcnow() + pd.Timedelta(hours=7))[:19],
                              "ticker": ticker_inp, "tanggal_data": tanggal_inp, "mode": aksi,
                              "ciri": ciri, "ringkas": ringkas})

        # ---------- Chat bebas ----------
        st.markdown("---")
        st.markdown("### 🗨️ Obrolan bebas (konteks: data lokal Anda)")
        if "chat_detektif" not in st.session_state: st.session_state["chat_detektif"] = []
        for m in st.session_state["chat_detektif"]:
            with st.chat_message(m["role"]): st.markdown(m["content"])
        if pesan := st.chat_input("Tanya apa saja: analisa, edukasi, atau lanjutan otopsi di atas..."):
            st.session_state["chat_detektif"].append({"role": "user", "content": pesan})
            with st.chat_message("user"): st.markdown(pesan)
            with st.chat_message("assistant"):
                with st.spinner("Berpikir..."):
                    ctx = ""
                    tk = re.findall(r"\b[A-Z]{4}\b", pesan.upper())
                    tk = [t for t in tk if not lb.empty and t in set(lb["Ticker"])] or (tk[:1] if tk else [])
                    for t in tk[:2]:
                        gt = tren_50h(t)
                        if gt is not None and len(gt):
                            l = gt.iloc[-1]
                            ctx += f"{t}: close {l['Close']} swing terakhir {l['Swing_%']}% vol {l['Volume']:.0f} (MA20 {l['MA20_vol']:.0f})\n"
                    jawab, mesin = narasi_ai(ctx or "(tidak ada data lokal relevan)", pesan)
                st.markdown(jawab)
                st.caption(f"⚡ via {mesin}")
            st.session_state["chat_detektif"].append({"role": "assistant", "content": jawab})