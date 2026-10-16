
def muat_suspended_hari_ini(base_dir="."):
    """Deteksi saham suspend dari arsip intraday: High == Low sepanjang sesi (tidak ada pergerakan harga).
    Return set ticker. Jika arsip tidak ada, return set kosong."""
    import os, glob
    import pandas as pd
    try:
        files = sorted(glob.glob(os.path.join(base_dir, "Arsip_Data_Harian", "screener_*.csv")), reverse=True)
        if not files:
            return set()
        df = pd.read_csv(files[0], usecols=["Ticker", "Harga (Rp)", "Volume"])
        g = df.groupby("Ticker").agg(hi=("Harga (Rp)", "max"), lo=("Harga (Rp)", "min"), vol=("Volume", "sum"))
        beku = g[(g["hi"] == g["lo"]) | (pd.to_numeric(g["vol"], errors="coerce") == 0)]
        return set(beku.index.astype(str))
    except Exception:
        return set()
