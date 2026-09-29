"""
AlphaScan Pro - Fitur Canggih
Tidak mengubah kode lama, hanya menambah.
"""
import os, re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone


def _wb_now():
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=7)


# ==========================================
# 1. MARKET BREADTH (A/D LINE)
# ==========================================
def market_breadth(df_hasil):
    if df_hasil.empty or "Change (%)" not in df_hasil.columns:
        return None
    chg = pd.to_numeric(df_hasil["Change (%)"], errors="coerce").dropna()
    adv = int((chg > 0).sum())
    dec = int((chg < 0).sum())
    unc = int((chg == 0).sum())
    ad_line = adv - dec
    ratio = (adv / dec) if dec > 0 else (float("inf") if adv > 0 else 0.0)
    if ratio > 2.0: status = "Sangat Bullish"
    elif ratio > 1.2: status = "Bullish"
    elif ratio < 0.5: status = "Sangat Bearish"
    elif ratio < 0.83: status = "Bearish"
    else: status = "Konsolidasi"
    return {"advance": adv, "decline": dec, "unchanged": unc,
            "ad_line": ad_line, "ratio": round(ratio, 2), "status": status}


# ==========================================
# 2. SECTOR ROTATION
# ==========================================
def sector_rotation(df_hasil):
    if df_hasil.empty or "Kategori" not in df_hasil.columns:
        return None
    df = df_hasil.copy()
    if "Value Transaksi" not in df.columns:
        df["Value Transaksi"] = pd.to_numeric(df.get("Harga (Rp)", 0), errors="coerce") * pd.to_numeric(df.get("Volume", 0), errors="coerce") * 100
    df["Value Transaksi"] = pd.to_numeric(df["Value Transaksi"], errors="coerce").fillna(0)
    agg = df.groupby("Kategori")["Value Transaksi"].sum().sort_values(ascending=False)
    total = agg.sum() or 1
    return [(kat, round(val/total*100, 1)) for kat, val in agg.items()]


# ==========================================
# 3. PRE-MARKET GAP SCANNER
# ==========================================
def premarket_gap_scanner(df_hasil, threshold_pct=2.0):
    if df_hasil.empty or "Status Gap" not in df_hasil.columns:
        return None
    df = df_hasil.copy()
    def _pct(s):
        if pd.isna(s): return 0.0
        match = re.search(r'\(([+-]?\\d+\\.?\\d*)', str(s))
        if match:
            try: return float(match.group(1))
            except: return 0.0
        return 0.0
    df["gap_pct"] = df["Status Gap"].apply(_pct)
    cols = [c for c in ["Ticker", "Harga (Rp)", "Change (%)", "gap_pct"] if c in df.columns]
    up = df[df["gap_pct"] >= threshold_pct][cols].sort_values("gap_pct", ascending=False).head(10)
    dn = df[df["gap_pct"] <= -threshold_pct][cols].sort_values("gap_pct").head(10)
    return {"gap_up": up, "gap_down": dn}


# ==========================================
# 4. POSITION SIZING CALCULATOR
# ==========================================
def position_sizing(modal_rp, risk_pct, entry_price, atr_value):
    if entry_price <= 0 or atr_value <= 0:
        return None
    risk_rp = modal_rp * (risk_pct / 100)
    sl_price = entry_price - atr_value
    risk_per_lot = (entry_price - sl_price) * 100
    if risk_per_lot <= 0:
        return None
    lot = int(risk_rp // risk_per_lot)
    return {"modal": modal_rp, "risk_rp": risk_rp, "entry": entry_price,
            "sl": sl_price, "tp_atr15": entry_price + (atr_value * 1.5),
            "lot": lot, "modal_keluar": lot * entry_price * 100}


# ==========================================
# 5. STRATEGY LEADERBOARD
# ==========================================
def strategy_leaderboard():
    """Ranking 9 rumus BSJP berdasarkan win-rate."""
    rows = []
    for i in range(1, 10):
        fh = os.path.join("Database", f"histori_transaksi_rumus_{i}.csv")
        if not os.path.exists(fh):
            continue
        try:
            h = pd.read_csv(fh)
        except Exception:
            continue
        if h.empty or "Return_%" not in h.columns:
            continue
        ret = pd.to_numeric(h["Return_%"], errors="coerce").dropna()
        n = len(ret)
        if n == 0:
            continue
        win = int((ret > 0).sum())
        total_rp = float(pd.to_numeric(h["Total_Return_Rp"], errors="coerce").fillna(0).sum())
        # longest losing streak
        won_arr = (ret > 0).astype(int)
        max_streak = cur = 0
        for v in won_arr:
            cur = cur + 1 if v == 0 else 0
            max_streak = max(max_streak, cur)
        rows.append({
            "Rumus": f"R{i}",
            "Trade": n,
            "Win": win,
            "WR%": round(win/n*100, 1),
            "Profit Rp": round(total_rp, 0),
            "Max Loss Streak": max_streak,
        })
    if not rows:
        return None
    return pd.DataFrame(rows).sort_values("WR%", ascending=False)


# ==========================================
# 6. DRAWDOWN ANALYSIS
# ==========================================
def drawdown_analysis(rumus_id):
    fh = os.path.join("Database", f"1histori_transaksi_rumus_{rumus_id}.csv")
    fh = os.path.join("Database", f"histori_transaksi_rumus_{rumus_id}.csv")
    if not os.path.exists(fh):
        return None
    try:
        h = pd.read_csv(fh)
    except Exception:
        return None
    if h.empty or "Total_Return_Rp" not in h.columns:
        return None
    h = h.copy()
    h["Total_Return_Rp"] = pd.to_numeric(h["Total_Return_Rp"], errors="coerce").fillna(0)
    h["equity"] = h["Total_Return_Rp"].cumsum() + 100000000
    h["peak"] = h["equity"].cummax()
    h["drawdown"] = (h["equity"] - h["peak"]) / h["peak"] * 100
    max_dd = float(h["drawdown"].min())
    return {"max_drawdown_pct": round(max_dd, 2),
            "equity_now": round(float(h["equity"].iloc[-1]), 0),
            "peak": round(float(h["peak"].max()), 0)}


# ==========================================
# 8. ALERT WATCHLIST
# ==========================================
def add_to_watchlist(st, ticker):
    if "alpha_watchlist" not in st.session_state:
        st.session_state.alpha_watchlist = []
    t = ticker.strip().upper()
    if t and t not in st.session_state.alpha_watchlist:
        st.session_state.alpha_watchlist.append(t)


def remove_from_watchlist(st, ticker):
    if "alpha_watchlist" in st.session_state:
        t = ticker.strip().upper()
        if t in st.session_state.alpha_watchlist:
            st.session_state.alpha_watchlist.remove(t)


def check_watchlist_alerts(df_hasil, st):
    if "alpha_watchlist" not in st.session_state or not st.session_state.alpha_watchlist:
        return []
    wl = st.session_state.alpha_watchlist
    df = df_hasil[df_hasil["Ticker"].isin(wl)].copy()
    alerts = []
    for _, r in df.iterrows():
        ticker = r["Ticker"]
        rvol = str(r.get("RVOL (Anomali Vol)", ""))
        if "Ledakan" in rvol or "Anomali Tinggi" in rvol:
            alerts.append(f"🌋 {ticker}: RVOL {rvol}")
        auto = str(r.get("Auto Trading Plan", ""))
        if "TP" in auto and "CL" in auto:
            alerts.append(f"🎯 {ticker}: plan {auto}")
    return alerts