import pandas as pd
import os
from datetime import datetime

# ==========================================
# ⚙️ KONFIGURASI BOT SIMULATOR BSJP (9 ARENA)
# ==========================================
MODAL_AWAL = 100000000.0  # Rp 100 Juta per Rumus
FEE_BELI = 0.0015         # 0.15%
FEE_JUAL = 0.0025         # 0.25%
FILE_MARKET = "Database/hasil_screener.csv"
DIR_DB = "Database"       

# ==========================================
# 🛠️ FUNGSI PEMBANTU
# ==========================================
def inisialisasi_database(rumus_id):
    file_porto = os.path.join(DIR_DB, f"portofolio_virtual_rumus_{rumus_id}.csv")
    file_hist = os.path.join(DIR_DB, f"history_trade_rumus_{rumus_id}.csv")
    
    if not os.path.exists(file_porto):
        df_porto = pd.DataFrame(columns=['Tanggal_Beli', 'Ticker', 'Harga_Beli', 'Lot', 'Total_Modal', 'Target_TP', 'Target_CL'])
        df_porto.to_csv(file_porto, index=False)
        
    if not os.path.exists(file_hist):
        df_hist = pd.DataFrame(columns=['Tanggal_Beli', 'Tanggal_Jual', 'Ticker', 'Harga_Beli', 'Harga_Jual', 'Status', 'Total_Return_Rp', 'Return_%'])
        df_hist.to_csv(file_hist, index=False)
        
    return file_porto, file_hist

def cek_saldo_tersedia(df_porto):
    if df_porto.empty:
        return MODAL_AWAL
    modal_terpakai = df_porto['Total_Modal'].sum()
    return MODAL_AWAL - modal_terpakai

# ==========================================
# 🤖 MESIN EKSEKUSI UTAMA (MODE BSJP)
# ==========================================
def jalankan_bot():
    now = datetime.now()
    waktu_sekarang_str = now.strftime('%H:%M:%S')
    tanggal_hari_ini = now.strftime('%Y-%m-%d') # Untuk mengecek umur kepemilikan
    jam_sekarang = now.time()
    
    jam_square_off = datetime.strptime("15:30", "%H:%M").time()
    
    print(f"[{waktu_sekarang_str}] Membangunkan Bot Simulator AI (Mode BSJP)...")
    
    # Cek apakah ini jam kritis untuk Jual Paksa
    is_square_off_time = jam_sekarang >= jam_square_off
    if is_square_off_time:
        print("🧹 WAKTU SQUARE OFF / SORE HARI! Saham H+1 dijual paksa, Saham baru siap dibeli.")

    if not os.path.exists(FILE_MARKET):
        print("Mata bot buta: Data hasil_screener.csv tidak ditemukan.")
        return
    df_market = pd.read_csv(FILE_MARKET)

    for i in range(1, 10):
        file_porto, file_hist = inisialisasi_database(i)
        file_sinyal = os.path.join(DIR_DB, f"sinyal_ai_rumus_{i}.csv")
        
        df_porto = pd.read_csv(file_porto)
        df_history = pd.read_csv(file_hist)
        
        porto_baru = []
        
        # ==========================================
        # FASE A: MODE JUAL (PANTAU TP / CL / JUAL PAKSA H+1)
        # ==========================================
        for idx, posisi in df_porto.iterrows():
            ticker = posisi['Ticker']
            # Ambil tanggal belinya saja (YYYY-MM-DD)
            tgl_beli_saham = str(posisi['Tanggal_Beli']).split()[0]
            
            # 🛑 KUNCI BSJP: Jika saham baru dibeli hari ini, HOLD! (Kunci gembok untuk dijual besok)
            if tgl_beli_saham == tanggal_hari_ini:
                porto_baru.append(posisi)
                continue

            try:
                harga_sekarang = df_market[df_market['Ticker'] == ticker]['Harga (Rp)'].values[0]
            except:
                porto_baru.append(posisi) 
                continue
                
            harga_beli = posisi['Harga_Beli']
            tp = posisi['Target_TP']
            cl = posisi['Target_CL']
            lot = posisi['Lot']
            
            terjual = False
            status_jual = ""
            harga_jual = 0
            
            # ATURAN 1: JUAL PAKSA SORE HARI (Hanya berlaku untuk saham H+1)
            if is_square_off_time:
                terjual = True
                status_jual = "AUTO_SQUARE_OFF (BSJP) 🧹"
                harga_jual = harga_sekarang
            # ATURAN 2: JUAL NORMAL DI PAGI/SIANG (Menyentuh TP / CL)
            elif harga_sekarang >= tp:
                terjual = True
                status_jual = "TAKE_PROFIT 🎯"
                harga_jual = harga_sekarang
            elif harga_sekarang <= cl:
                terjual = True
                status_jual = "CUT_LOSS ✂️"
                harga_jual = harga_sekarang
                
            if terjual:
                # Kalkulasi bersih dipotong fee
                nilai_jual_kotor = harga_jual * lot * 100
                potongan_fee = nilai_jual_kotor * FEE_JUAL
                nilai_jual_bersih = nilai_jual_kotor - potongan_fee
                
                profit_rp = nilai_jual_bersih - posisi['Total_Modal']
                profit_pct = (profit_rp / posisi['Total_Modal']) * 100
                
                catatan_baru = {
                    'Tanggal_Beli': posisi['Tanggal_Beli'],
                    'Tanggal_Jual': now.strftime("%Y-%m-%d %H:%M"),
                    'Ticker': ticker,
                    'Harga_Beli': harga_beli,
                    'Harga_Jual': harga_jual,
                    'Status': status_jual,
                    'Total_Return_Rp': round(profit_rp, 2),
                    'Return_%': round(profit_pct, 2)
                }
                df_history = pd.concat([df_history, pd.DataFrame([catatan_baru])], ignore_index=True)
                print(f"💰 [RUMUS {i}] JUAL H+1: {ticker} @ Rp {harga_jual} | Status: {status_jual} | PnL: {profit_pct:.2f}%")
            else:
                porto_baru.append(posisi)

        df_porto = pd.DataFrame(porto_baru)
        if df_porto.empty:
            df_porto = pd.DataFrame(columns=['Tanggal_Beli', 'Ticker', 'Harga_Beli', 'Lot', 'Total_Modal', 'Target_TP', 'Target_CL'])

        # ==========================================
        # FASE B: MODE BELI (Bebas Jam, Fokus Eksekusi Malam)
        # ==========================================
        if os.path.exists(file_sinyal):
            saldo_sekarang = cek_saldo_tersedia(df_porto)
            saham_dimiliki = df_porto['Ticker'].tolist() if not df_porto.empty else []
            df_sinyal = pd.read_csv(file_sinyal)
            
            for _, sinyal in df_sinyal.iterrows():
                ticker = sinyal['Ticker']
                if ticker in saham_dimiliki:
                    continue
                    
                try:
                    harga_beli = df_market[df_market['Ticker'] == ticker]['Harga (Rp)'].values[0]
                except:
                    continue
                
                # Alokasi Maksimal Rp 20 Juta per Saham
                alokasi_dana = min(20000000, saldo_sekarang)
                
                if alokasi_dana >= (harga_beli * 100 * 1.0015): 
                    harga_1_lot_plus_fee = (harga_beli * 100) * (1 + FEE_BELI)
                    jumlah_lot = int(alokasi_dana // harga_1_lot_plus_fee)
                    total_modal_dikeluarkan = jumlah_lot * harga_1_lot_plus_fee
                    
                    posisi_baru = {
                        'Tanggal_Beli': now.strftime("%Y-%m-%d %H:%M"),
                        'Ticker': ticker,
                        'Harga_Beli': harga_beli,
                        'Lot': jumlah_lot,
                        'Total_Modal': total_modal_dikeluarkan,
                        'Target_TP': sinyal['Target_TP'],
                        'Target_CL': sinyal['Target_CL']
                    }
                    df_porto = pd.concat([df_porto, pd.DataFrame([posisi_baru])], ignore_index=True)
                    saldo_sekarang -= total_modal_dikeluarkan
                    print(f"🛒 [RUMUS {i}] BELI SORE/MALAM: {ticker} @ Rp {harga_beli} | {jumlah_lot} Lot")

            # Kertas belanja WAJIB dihapus agar besok tidak dibeli lagi dobel
            try:
                os.remove(file_sinyal)
            except:
                pass

        # 4. SIMPAN PERUBAHAN KE DATABASE SECARA AMAN (Tanpa syarat ada_transaksi)
        df_porto.to_csv(file_porto, index=False)
        df_history.to_csv(file_hist, index=False)

    print("✅ Inspeksi 9 Arena (Mode BSJP) selesai.")

if __name__ == "__main__":
    jalankan_bot()