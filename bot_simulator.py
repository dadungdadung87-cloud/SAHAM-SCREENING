import pandas as pd
import os
from datetime import datetime
import subprocess

# ==========================================
# ⚙️ KONFIGURASI BOT SIMULATOR BSJP (9 ARENA)
# ==========================================
MODAL_AWAL = 100000000.0  # Rp 100 Juta per Rumus
FEE_BELI = 0.0015         # 0.15%
FEE_JUAL = 0.0025         # 0.25%
FILE_MARKET = "Database/hasil_screener.csv"
DIR_DB = "Database"       

# ==========================================
# ☁️ FUNGSI SINKRON R2
# ==========================================
def sinkron_r2_masuk():
    """Tarik state portofolio terbaru dari R2 sebelum bot bekerja."""
    try:
        import r2_client
        if r2_client.download_database():
            print("☁️ State portofolio tersinkron dari R2.")
        else:
            print("⚠️ R2 kosong/belum ada data — pakai file lokal.")
        return True
    except Exception as e:
        print(f"⚠️ Gagal sinkron masuk R2: {e}")
        return False

def sinkron_r2_keluar():
    """Kirim state portofolio terbaru ke R2 (mode mirror: sinyal terbakar ikut terhapus)."""
    try:
        import r2_client
        if r2_client.upload_database(mirror=True):
            print("☁️ State portofolio ter-upload ke R2 (mirror).")
    except Exception as e:
        print(f"⚠️ Gagal sinkron keluar R2: {e}")

# ==========================================
# 🛠️ FUNGSI AUTO-SAVE KE GITHUB (ABADI)
# ==========================================
def auto_save_github():
    print("\n🔄 Memulai pencadangan (Auto-Save) permanen ke GitHub...")
    try:
        subprocess.run(["git", "add", "Database/*.csv"], check=True)
        waktu_sekarang = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        pesan_komit = f"🤖 Bot Update Portofolio: {waktu_sekarang}"
        commit_process = subprocess.run(["git", "commit", "-m", pesan_komit], capture_output=True, text=True)
        if "nothing to commit" in commit_process.stdout or "nothing to commit" in commit_process.stderr:
            print("✅ Data aman. Tidak ada transaksi baru.")
            return
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True, text=True)
        push_process = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
        if push_process.returncode != 0:
            subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True, text=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
        print("🚀 Pencadangan berhasil! Data portofolio Anda abadi.")
    except Exception as e:
        print(f"❌ Gagal melakukan Auto-Save. Error: {e}")

# ==========================================
# 🛠️ FUNGSI INISIALISASI (BRANKAS 3 LAPIS)
# ==========================================
def inisialisasi_database(rumus_id):
    file_porto = os.path.join(DIR_DB, f"portofolio_aktif_rumus_{rumus_id}.csv")
    file_hist = os.path.join(DIR_DB, f"histori_transaksi_rumus_{rumus_id}.csv")
    
    if not os.path.exists(file_porto):
        pd.DataFrame(columns=['Tanggal_Beli', 'Ticker', 'Harga_Beli', 'Lot', 'Total_Modal', 'Target_TP', 'Target_CL']).to_csv(file_porto, index=False)
        
    if not os.path.exists(file_hist):
        pd.DataFrame(columns=['Tanggal_Beli', 'Tanggal_Jual', 'Ticker', 'Harga_Beli', 'Harga_Jual', 'Status', 'Total_Return_Rp', 'Return_%']).to_csv(file_hist, index=False)
        
    return file_porto, file_hist

def cek_saldo_tersedia(df_porto):
    if df_porto.empty:
        return MODAL_AWAL
    return MODAL_AWAL - df_porto['Total_Modal'].sum()

# ==========================================
# 🤖 MESIN EKSEKUSI UTAMA (MODE BSJP)
# ==========================================
def jalankan_bot():
    now = datetime.now()
    tanggal_hari_ini = now.strftime('%Y-%m-%d')
    jam_sekarang = now.time()
    jam_square_off = datetime.strptime("15:30", "%H:%M").time()
    
    print(f"[{now.strftime('%H:%M:%S')}] Membangunkan Bot Simulator AI...")

    # ----------------------------------------------------
    # 😴 GEMBOK AKHIR PEKAN — bot libur total Sabtu-Minggu
    # ----------------------------------------------------
    if now.weekday() >= 5:
        print("😴 Akhir pekan terdeteksi. Bot libur — posisi aman sampai Senin.")
        return

    # ----------------------------------------------------
    # ☁️ SINKRON MASUK: tarik state terbaru dari R2
    # ----------------------------------------------------
    r2_ok = sinkron_r2_masuk()

    # ----------------------------------------------------
    # 🔒 GEMBOK PAGI: SISTEM PENGAMAN ANTI-HILANG DATA
    # ----------------------------------------------------
    if not os.path.exists(FILE_MARKET):
        print("🔒 GEMBOK AKTIF: File hasil_screener.csv tidak ditemukan. Bot menolak beroperasi agar portofolio aman!")
        return
        
    try:
        df_market = pd.read_csv(FILE_MARKET)
        if df_market.empty or 'Ticker' not in df_market.columns or 'Harga (Rp)' not in df_market.columns:
            print("🔒 GEMBOK AKTIF: Data market kosong atau cacat. Bot tidur kembali untuk melindungi data Anda.")
            return
    except Exception as e:
        print(f"🔒 GEMBOK AKTIF: Gagal membaca data market ({e}). Bot tidur kembali.")
        return
    # ----------------------------------------------------

    # ----------------------------------------------------
    # 🧓 GEMBOK DATA BASI: beli boleh malam hari (harga penutupan),
    # tetapi dilarang jika data market berusia > 3 hari
    # ----------------------------------------------------
    try:
        stempel_market = str(df_market['Terakhir Update'].iloc[0])[:10]
        usia_data = (now - datetime.strptime(stempel_market, '%Y-%m-%d')).days
    except Exception:
        usia_data = 0
    mode_beli_aktif = usia_data <= 3
    if not mode_beli_aktif:
        print(f"🔒 GEMBOK DATA BASI AKTIF: data market berusia {usia_data} hari — bot hanya evaluasi jual, tidak membeli.")

    is_square_off_time = jam_sekarang >= jam_square_off
    if is_square_off_time:
        print("🧹 WAKTU SQUARE OFF / SORE HARI! Evaluasi jual paksa diaktifkan.")

    # MENYAPU RUMUS 1 SAMPAI 9
    for i in range(1, 10):
        file_porto, file_hist = inisialisasi_database(i)
        file_sinyal = os.path.join(DIR_DB, f"sinyal_ai_rumus_{i}.csv")
        
        df_porto = pd.read_csv(file_porto)
        df_history = pd.read_csv(file_hist)
        
        porto_baru = []
        history_baru = []
        
        # ==========================================
        # FASE A: MODE JUAL (CABUT SAHAM DARI GUDANG)
        # ==========================================
        for idx, posisi in df_porto.iterrows():
            ticker = posisi['Ticker']
            tgl_beli_saham = str(posisi['Tanggal_Beli']).split()[0]
            
            # BSJP: Jika beli hari ini, TAHAN! (Tidak Boleh Dijual)
            if tgl_beli_saham == tanggal_hari_ini:
                porto_baru.append(posisi)
                continue

            try:
                harga_sekarang = df_market[df_market['Ticker'] == ticker]['Harga (Rp)'].values[0]
            except:
                porto_baru.append(posisi) 
                continue
                
            terjual = False
            status_jual = ""
            harga_jual = 0
            
            if is_square_off_time:
                terjual = True
                status_jual = "AUTO_SQUARE_OFF 🧹"
                harga_jual = harga_sekarang
            elif harga_sekarang >= posisi['Target_TP']:
                terjual = True
                status_jual = "TAKE_PROFIT 🎯"
                harga_jual = harga_sekarang
            elif harga_sekarang <= posisi['Target_CL']:
                terjual = True
                status_jual = "CUT_LOSS ✂️"
                harga_jual = harga_sekarang
                
            if terjual:
                nilai_jual_kotor = harga_jual * posisi['Lot'] * 100
                nilai_jual_bersih = nilai_jual_kotor - (nilai_jual_kotor * FEE_JUAL)
                profit_rp = nilai_jual_bersih - posisi['Total_Modal']
                profit_pct = (profit_rp / posisi['Total_Modal']) * 100
                
                history_baru.append({
                    'Tanggal_Beli': posisi['Tanggal_Beli'],
                    'Tanggal_Jual': now.strftime("%Y-%m-%d %H:%M"),
                    'Ticker': ticker,
                    'Harga_Beli': posisi['Harga_Beli'],
                    'Harga_Jual': harga_jual,
                    'Status': status_jual,
                    'Total_Return_Rp': round(profit_rp, 2),
                    'Return_%': round(profit_pct, 2)
                })
                print(f"💰 [RUMUS {i}] JUAL: {ticker} @ Rp {harga_jual} | {status_jual} | {profit_pct:.2f}%")
            else:
                porto_baru.append(posisi)

        df_porto = pd.DataFrame(porto_baru)
        if df_porto.empty:
            df_porto = pd.DataFrame(columns=['Tanggal_Beli', 'Ticker', 'Harga_Beli', 'Lot', 'Total_Modal', 'Target_TP', 'Target_CL'])
        
        if history_baru:
            df_history = pd.concat([df_history, pd.DataFrame(history_baru)], ignore_index=True)

        # ==========================================
        # FASE B: MODE BELI (MASUKKAN SAHAM KE GUDANG)
        # ==========================================
        if mode_beli_aktif and os.path.exists(file_sinyal):
            saldo_sekarang = cek_saldo_tersedia(df_porto)
            saham_dimiliki = df_porto['Ticker'].tolist() if not df_porto.empty else []
            try:
                df_sinyal = pd.read_csv(file_sinyal)
                for _, sinyal in df_sinyal.iterrows():
                    ticker = sinyal['Ticker']
                    if ticker in saham_dimiliki:
                        continue
                        
                    try:
                        harga_beli = df_market[df_market['Ticker'] == ticker]['Harga (Rp)'].values[0]
                    except:
                        continue
                    
                    alokasi_dana = min(20000000, saldo_sekarang)
                    harga_1_lot_plus_fee = (harga_beli * 100) * (1 + FEE_BELI)
                    
                    if alokasi_dana >= harga_1_lot_plus_fee: 
                        jumlah_lot = int(alokasi_dana // harga_1_lot_plus_fee)
                        total_modal_dikeluarkan = jumlah_lot * harga_1_lot_plus_fee
                        
                        df_porto = pd.concat([df_porto, pd.DataFrame([{
                            'Tanggal_Beli': now.strftime("%Y-%m-%d %H:%M"),
                            'Ticker': ticker,
                            'Harga_Beli': harga_beli,
                            'Lot': jumlah_lot,
                            'Total_Modal': total_modal_dikeluarkan,
                            'Target_TP': sinyal['Target_TP'],
                            'Target_CL': sinyal['Target_CL']
                        }])], ignore_index=True)
                        saldo_sekarang -= total_modal_dikeluarkan
                        print(f"🛒 [RUMUS {i}] BELI: {ticker} @ Rp {harga_beli} | {jumlah_lot} Lot")

                os.remove(file_sinyal)
            except Exception as e:
                print(f"⚠️ Gagal membaca sinyal Rumus {i}: {e}")
        elif os.path.exists(file_sinyal) and not mode_beli_aktif:
            print(f" [RUMUS {i}] Sinyal diterima tetapi ditahan (data basi) — akan dieksekusi saat data segar.")

        df_porto.to_csv(file_porto, index=False)
        df_history.to_csv(file_hist, index=False)

    print("✅ Inspeksi 9 Arena selesai.")
    
    # ----------------------------------------------------
    # ☁️ SINKRON KELUAR: kirim state terbaru ke R2 (mirror)
    # ----------------------------------------------------
    if r2_ok:
        sinkron_r2_keluar()

    # EKSEKUSI AUTO-SAVE KE GITHUB
    auto_save_github()

if __name__ == "__main__":
    jalankan_bot()