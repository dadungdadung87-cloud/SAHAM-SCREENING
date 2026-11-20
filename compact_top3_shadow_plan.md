# SAHAM-SCREENING — Session Handoff (2026-11-21) → NEXT SESSION: BUILD "TOP 3 SHADOW PORTFOLIO"

## USER'S NEXT TASK (main objective)
Build **OPTION 2: Shadow Portfolio "PORTO TOP 3 SAHAM"** — fully agreed plan, NOT yet implemented. This document is the complete handoff so a fresh chat can build it directly.

### What the user wants (confirmed understanding)
- Currently: each of the 9 formula arenas (rumus 1..9) holds ONE portfolio of max 5 stocks ("Top 5"), bought automatically at 15:50 WIB daily after an AI sidang (deliberation).
- New addition (stays inside Tab 4 "Portofolio Bot" in app.py): a SECOND, SEPARATE portfolio per rumus named **"PORTO TOP 3 SAHAM"** = the best 3 re-filtered FROM the already-selected Top 5.
- Process order when screening / making the shopping list: normal sidang AI forms Top 5 first → only after Top 5 exists → a second AI pass picks the best 3 of those 5 → shopping list for Top 3.
- **User chose OPTION 2 (shadow/simulation)**: Top 3 tracks P/L with virtual money only — NO second Rp100M real balance. Reason: zero financial risk while A/B testing whether "3-of-5" filtering is actually more profitable than Top 5. If after ~2-4 weeks shadow data shows Top 3 consistently better → user may upgrade it to a real portfolio later.
- P/L accounting for shadow (user asked how profit is measured without real capital): identical mechanics to real bot — record entry price at 15:50 from feed, standard lot (mirror existing per-stock allocation, e.g. ~Rp33M/stock), record sell on TP/CL hit with same fee model → `Total_Return_Rp`, `Return_%`, cumulative shadow P/L per rumus → comparison view "Top 5 profit vs Top 3 profit".

## CURRENT SYSTEM FACTS (verified this session, Nov 13-21 2026)

### Repo / environment
- Project root: `/home/kaltaraid/Documents/SAHAM-SCREENING` (git repo, remote origin = github.com:dadungdadung87-cloud/SAHAM-SCREENING). Producer: `/home/kaltaraid/Documents/DATA-CENTER` (NOT a git repo). WEB-SCREENING is OUT OF SCOPE (user explicitly said focus SAHAM-SCREENING only).
- Python venv: `SAHAM-SCREENING/.venv` (Python 3.14). DATA-CENTER has own `venv`.
- Recent commits this session: `8732647d` (--tp-sl-catchup mode), `445fe99d` (web TTL 120s + radar autorefresh 2m), `56c91bea` (new daily schedule), `ef6bcf09` (UI text updates). Later, another agent added Tab 7 screener_v7 (`services/screener_v7.py`), CDP token recovery (`jaga_token.py` + `ambil_token_cdp.py`), commit `121a81d4`+.
- Working tree is clean; all bot daily updates auto-commit as "Auto-update data dan bot simulator (arsip via R2)".

### Daily schedule (as of 2026-11-14, commit 56c91bea) — DO NOT BREAK
- Cron */5 9-17 Mon-Fri runs `jalankan_bot.sh`.
- 09:00-14:55 & 15:05-15:45: `bot_simulator.py --tp-sl-only` (auto-sell positions touching Target_TP/Target_CL).
- **15:00**: AUTO SELL (square-off) all unsold positions across 9 arenas — `jam_square_off = 15:00` in `bot_simulator.py:~217`. TP/CL fires regardless of position age (invariant at bot_simulator.py:331-334); square-off only sells positions bought before today.
- **15:50** (window 15:50-15:59, flag `/tmp/bsjp_beli_$(date +%F)` for idempotency): single session = `sidang_jadwal.py` (AI shopping list Top 5 for 9 rumus) → `kirim_telegram.py` (ONLY daily Telegram notification) → `bot_simulator.py --jadwal` (executes BUY of sinyal into 9 portfolios).
- Old 15:20 sidang and 16:00 sidang_sore/telegram_sore REMOVED from jalankan_bot.sh.
- KEY FILE: `sidang_lib.py` `jalankan_sidang()` (~line 354): per rumus → top15 by Score_Num/Volume/Change → Gemini AI (`ai_hakim_klasemen_cepat`) picks Top 5 (`_parse_top5`) → writes `Database/sinyal_ai_rumus_N.csv` with columns Ticker/Target_TP/Target_CL/Stempel (+uploads R2). TP=+5%, CL=-3% (sidang_lib.py:~394).
- `bot_simulator.py` FASE B buy (~line 536): mode jadwal only, filter `Stempel == today` (line ~543), checks `mode_beli_aktif` (feed age ≤3h, line ~301).
- Price source: producer pipeline. `DATA-CENTER/update_data.py`: cron */2 09:00-16:59 (paired hour ranges 9-10,11-12,13-14,15-16 + 20,50 at 16 for EOD), fetch 944 tickers last-bar intraday from Stockbit exodus (16-27s), then **ProcessPoolExecutor 3 workers** (GIL fix — was ThreadPool 60-90s), writes 52-col `feed/hasil_screener.csv` + `feed/status.json`, then jalankan_data_center.sh **uploads R2 directly** (Database/hasil_screener.csv, fundamental_exodus.csv, status.json, Arsip_Data_Harian/screener_DATE.csv). Broksum mode: process pool does NOT do HTTP broksum (placeholder "Paywall Broksum"); fallback thread mode exists via `SET_BROKSUM_THREAD=1` (marketdetectors currently HTTP 402 PAYWALL anyway).
- EOD crons (separate lines): 16:15 fetcher_exodus fundamental, 16:45 net_foreign.py, 16:50 skor_broker.py, 17:05 skor_sistem snapshot+evaluasi, Fri 17:40 backtest.
- Web: local Streamlit `http://localhost:8501` (jaga_web.sh keeper), cache TTL 120s, radar autorefresh 2m. Reads R2 `Database/hasil_screener.csv`. Data freshness now ~2-4 min end-to-end (was 5-15).
- Token Stockbit: canonical `SAHAM-SCREENING/token_stockbit.txt`, synced by `jaga_token.py` (cron */10 6-18) to DATA-CENTER & WEB-SCREENING. Recovery order: CDP browser cookie via Thorium (`ambil_token_cdp.py`) → HAR fallback. Last known state: token died Fri 19 Nov 22:51 WIB (laptop off Fri-Sun, cron not running); user to open Thorium logged-in so cron recovers. Producer falls back to Yahoo if 401.
- Telegram: `kirim_telegram.py` reads `Database/radar_snapshot.json` from R2; only 15:50 session sends.

### UI anchors for the new feature (app.py)
- Tabs defined line ~1535: `tab1..tab7`, Tab 4 = "💼 Portofolio Bot" (line ~2417 `with tab4:`).
- Portfolio loaders: `muat_portofolio_arena(rumus_id)` line ~1280 → `Database/portofolio_aktif_rumus_N.csv`; histori `Database/histori_transaksi_rumus_N.csv`; sinyal `Database/sinyal_ai_rumus_N.csv`.
- Tab 4 has: reset saldo button, manual BUY (🛒) / JUAL (💸) buttons (label "JUAL SORE" kept deliberately as functional label), per-arena tables, buku besar (`bangun_buku_besar.py`), R2 mirror of Database/ CSVs.
- Existing helper service modules pattern: `services/screener_v7.py` (added by other agent, hooked into Tab 7), `services/alpha_features.py` (not yet hooked).

## IMPLEMENTATION PLAN FOR NEXT SESSION (agreed with user)

1. **sidang_lib.py — 2-stage sidang**: stage 1 unchanged (Top 5 per rumus). Stage 2: one small extra Gemini call per rumus: "from these 5 tickers pick the 3 most worthy" (AI does the re-filtering, consistent with user's wish) → write `Database/sinyal_top3_rumus_N.csv` (same schema + Stempel; subset of the 5) + upload R2. Guard: if stage-2 AI fails → fallback = first 3 of Top 5 list order.
2. **Shadow persistence**: `Database/shadow_top3_rumus_N.csv` (active virtual positions: Tanggal_Beli, Ticker, Harga_Beli, Lot, Virtual_Modal, Target_TP, Target_CL, Stempel) + `Database/shadow_top3_history_rumus_N.csv` (same columns as real histori: Tanggal_Beli/Tanggal_Jual/Ticker/Harga_Beli/Harga_Jual/Status/Total_Return_Rp/Return_%). Use ~Rp100M virtual budget per rumus, per-stock sizing mirroring real bot logic.
3. **bot_simulator.py**: extend TP/CL + 15:00 square-off sweep to also evaluate shadow_top3 files (sell virtual position on price >= TP or <= CL, log into shadow history; idempotency via anti-duplicate like real). Do NOT touch real portfolio logic. BUY at 15:50: after real buy, append shadow positions from sinyal_top3 (virtual money, no saldo check needed).
4. **jalankan_bot.sh 15:50 block**: sidang (now writes 5+3) → kirim_telegram (include Top 3 list in the same single daily message) → bot buy (real) + shadow init.
5. **app.py Tab 4**: two sections per arena: "💼 PORTO TOP 5" (existing) and "🥇 PORTO TOP 3 (SHADOW)" — shadow table + shadow P/L summary + comparison "Top 5 vs Top 3 profit %". Respect existing patterns (R2 mirror optional for shadow files).
6. **kirim_telegram.py**: append Top 3 section to the 15:50 message.
7. **Keep**: existing schedule (15:00 sell / 15:50 buy), R2 pipeline, token guard, cron structure. **Do not modify** WEB-SCREENING.
8. Test: syntax check, `--tp-sl-only` smoke, dry-run sidang stage 2, verify shadow files created, git commit+push origin main.

## RULES / PREFERENCES
- User language: Indonesian; keep replies short/concise; findings-first.
- Only SAHAM-SCREENING in scope. DATA-CENTER changes allowed for producer needs; WEB-SCREENING untouched.
- Never delete/overwrite raw artifacts (e.g. Arsip_Reset backups, bot.log); commit only when asked or when pipeline auto-commits.
- git remote for SAHAM-SCREENING = origin. DATA-CENTER is not a repo.
