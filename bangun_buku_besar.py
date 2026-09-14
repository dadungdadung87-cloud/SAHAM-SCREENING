# ==========================================
# 📖 BUKU BESAR HARIAN — ringkasan 1 baris/saham/hari
# Disimpan HANYA di R2: Buku_Besar/ringkasan_harian.csv.gz (gzip, ringan)
# Mode malam: cron | Mode pertama: --backfill
# ==========================================
import pandas as pd, os, glob, sys, tempfile
import r2_client

KEY_LEDGER = "Buku_Besar/ringkasan_harian.csv.gz"
KOLOM = ["Tanggal","Ticker","Open","High","Low","Close","Volume","Swing_%","Puncak_Change_%",
         "Tekanan","Siklus","Supply","AD","BB","RVOL","Score","Rekomendasi"]

def muat_ledger():
    tmp = os.path.join(tempfile.gettempdir(), "ringkasan_harian_in.csv.gz")
    if r2_client.download_arsip(KEY_LEDGER, tmp):
        try: return pd.read_csv(tmp)
        except Exception: pass
    return pd.DataFrame(columns=KOLOM)

def ringkas_hari(file_csv, tanggal):
    df = pd.read_csv(file_csv)
    if df.empty or "Ticker" not in df.columns: return []
    for k in ["Harga (Rp)", "Volume", "Change (%)"]:
        if k in df.columns: df[k] = pd.to_numeric(df[k], errors="coerce")
    baris = []
    for t, g in df.groupby("Ticker"):
        g = g.dropna(subset=["Harga (Rp)"]) if "Harga (Rp)" in g else g
        if g.empty: continue
        low, high = g["Harga (Rp)"].min(), g["Harga (Rp)"].max()
        last = g.iloc[-1]
        swing = (high - low) / low * 100 if low else 0.0
        puncak = g["Change (%)"].max() if "Change (%)" in g.columns else 0.0
        baris.append({"Tanggal": tanggal, "Ticker": t,
            "Open": g["Harga (Rp)"].iloc[0], "High": high, "Low": low, "Close": last["Harga (Rp)"],
            "Volume": last.get("Volume", 0), "Swing_%": round(swing, 2), "Puncak_Change_%": round(puncak, 2),
            "Tekanan": last.get("Tekanan Bandar", "Normal"), "Siklus": last.get("Fase Siklus Bandar", "Normal"),
            "Supply": last.get("Kondisi Supply", "Normal"), "AD": last.get("Kekuatan A/D", "Normal"),
            "BB": last.get("Status BB", "Normal"), "RVOL": last.get("RVOL (Anomali Vol)", "Normal"),
            "Score": last.get("Total Score", 0), "Rekomendasi": last.get("Rekomendasi", "WAIT & SEE")})
    return baris

def main():
    backfill = "--backfill" in sys.argv
    ledger = muat_ledger()
    punya = set(ledger["Tanggal"].astype(str)) if not ledger.empty else set()
    sumber = []
    if backfill:
        for k in r2_client.list_arsip():
            tgl = k.split("_")[-1].replace(".csv", "")
            if tgl not in punya: sumber.append((tgl, ("R2", k)))
    else:
        for f in glob.glob("Arsip_Data_Harian/screener_*.csv"):
            tgl = f.split("_")[-1].replace(".csv", "")
            if tgl not in punya: sumber.append((tgl, ("LOKAL", f)))
    if not sumber:
        print("📖 Buku besar sudah mutakhir.")
    else:
        sumber.sort()
        tambahan = []
        for tgl, (jenis, src) in sumber:
            if jenis == "LOKAL":
                tambahan += ringkas_hari(src, tgl)
            else:
                tmp = os.path.join(tempfile.gettempdir(), f"arsip_bb_{tgl}.csv")
                if r2_client.download_arsip(src, tmp):
                    tambahan += ringkas_hari(tmp, tgl)
            print(f"📖 {tgl} diringkas (total sementara +{len(tambahan)} baris)")
        if tambahan:
            df_baru = pd.DataFrame(tambahan, columns=KOLOM)
            ledger = pd.concat([ledger, df_baru], ignore_index=True) if not ledger.empty else df_baru
            ledger = ledger.drop_duplicates(subset=["Tanggal", "Ticker"], keep="last")
            tgl_unik = sorted(ledger["Tanggal"].astype(str).unique())
            if len(tgl_unik) > 60:
                ledger = ledger[~ledger["Tanggal"].astype(str).isin(tgl_unik[:-60])]
            out = os.path.join(tempfile.gettempdir(), "ringkasan_harian_out.csv.gz")
            ledger.to_csv(out, index=False, compression="gzip")
            if r2_client.upload_arsip(out, KEY_LEDGER):
                print(f"✅ Buku besar R2: {len(ledger)} baris / {ledger['Tanggal'].nunique()} hari.")
    r2_client.prune_r2_jika_penuh(9.0)

if __name__ == "__main__":
    main()