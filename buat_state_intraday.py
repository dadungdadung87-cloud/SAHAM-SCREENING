#!/usr/bin/env python
"""Buat Database/state_intraday.json — state intraday ringkas utk web cloud.
Dijalankan jalankan_bot.sh tiap siklus; file ikut auto-commit git sehingga
Streamlit Cloud mendapat data intraday tanpa R2 maupun arsip 60MB."""
import os, sys, json
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from sidang_lib import muat_rebound_state, muat_open_state, muat_skor_pembekal, VERSI_SIDANG

# Sumber arsip: lokal SAHAM dulu, lalu DATA-CENTER (producer)
KANDIDAT_DIR = [
    os.path.join(BASE, "Arsip_Data_Harian"),
    "/home/kaltaraid/Documents/DATA-CENTER/feed/arsip",
]
from datetime import datetime, timedelta
wib = datetime.utcnow() + timedelta(hours=7)
if wib.weekday() >= 5:
    wib = wib - timedelta(days=(wib.weekday() - 4))
d0 = wib.strftime("%Y-%m-%d")
d1 = (wib - timedelta(days=1)).strftime("%Y-%m-%d")


def cari_arsip(tgl):
    for d in KANDIDAT_DIR:
        p = os.path.join(d, f"screener_{tgl}.csv")
        if os.path.exists(p):
            return p
    return None


def hitung_reb_open(path):
    df = pd.read_csv(path, usecols=["Waktu Update", "Ticker", "Harga (Rp)"])
    p_last = df.pivot_table(index="Ticker", columns="Waktu Update", values="Harga (Rp)", aggfunc="last")
    p_first = df.pivot_table(index="Ticker", columns="Waktu Update", values="Harga (Rp)", aggfunc="first")
    akhir = p_last.ffill(axis=1).iloc[:, -1]
    low = p_last.min(axis=1)
    openp = p_first.bfill(axis=1).iloc[:, 0]
    reb = ((akhir - low) / low * 100).replace([float("inf"), float("-inf")], 0).fillna(0)
    opn = ((akhir - openp) / openp * 100).replace([float("inf"), float("-inf")], 0).fillna(0)
    reb_d = {t: round(float(reb[t]), 2) for t in reb.index if low[t] > 0}
    opn_d = {t: round(float(opn[t]), 2) for t in opn.index if openp[t] > 0}
    return reb_d, opn_d


def main():
    f0, f1 = cari_arsip(d0), cari_arsip(d1)
    reb, opn, bek = {}, {}, {}
    if f0:
        reb, opn = hitung_reb_open(f0)
    else:
        reb = {t: v[0] for t, v in muat_rebound_state(BASE).items()}
        opn = {t: v[0] for t, v in muat_open_state(BASE).items()}
    if f1:
        _r, _o = hitung_reb_open(f1)
        del _r, _o
        bek = muat_skor_pembekal(BASE)
    else:
        bek = muat_skor_pembekal(BASE)
    state = {"tgl": d0, "bekal_tgl": d1, "versi": VERSI_SIDANG, "reb": reb, "open": opn, "bekal": bek}
    out = os.path.join(BASE, "Database", "state_intraday.json")
    with open(out, "w") as f:
        json.dump(state, f, separators=(",", ":"))
    print(f"✅ state_intraday.json: {len(reb)} reb | {len(opn)} open | {len(bek)} bekal ({d0})")


if __name__ == "__main__":
    main()
