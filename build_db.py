"""Rebuilds research.db (SQLite) from both papers' outputs. Run from this folder: python build_db.py

Reads (the two research repos cloned next to this one):
  ../commodity-tercile-strategies/paper_analysis/  all_configs.csv, numbers.json, rebalance_offsets.csv, open_price_screen.csv
  ../commodity-tercile-strategies                  package + Bloomberg workbook in data/, to rebuild monthly strategy returns
  ../dxy-fx-strategies/data/               futures/DX.csv and vendor/fx_ohlc_2010_2025.csv for the DXY legs
Then runs sql/views.sql on top.
"""
import sys, json, sqlite3, itertools, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
COMM = ROOT / 'commodity-tercile-strategies'
if not COMM.exists():                        # my local working folder has the older name
    COMM = ROOT / 'Commodities Research'
PA = COMM / 'paper_analysis'
DXY = ROOT / 'dxy-fx-strategies'
sys.path.insert(0, str(COMM))
from commodity_research.loader import Data
from commodity_research import engine as E, grid as G
from commodity_research.config import START_POS as S0
from commodity_research.universe import UNIVERSES, TR, NAME, SECTOR, ORDER

DB = BASE / 'research.db'


def main():
    # always start from an empty file, never append to an old build
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript((BASE / 'sql' / 'schema.sql').read_text())
    N = json.load(open(PA / 'numbers.json'))

    # ---------------------------------
    # 1) STUDIES
    # ---------------------------------
    con.executemany('INSERT INTO dim_study VALUES (?,?,?,?,?,?,?,?)', [
        (1, 'DXY', 'Two Blind Spots in Backtest Validation: From a Manufactured Dollar Index Anomaly to a Corrected Null Result',
         'Risks (MDPI)', 'Under review, revision submitted', '2010-12-01', '2025-12-30', 'https://github.com/RyanSingh0/dxy-fx-strategies'),
        (2, 'COMMODITIES', 'Volatility Sorting, an Untradeable Reversal and Rebalance-Date Luck: What Survives a Declared Search Over Cross-Sectional Commodity Strategies',
         'Commodities (MDPI)', 'Manuscript ready', N['eval_start'], N['eval_end'], 'https://github.com/RyanSingh0/commodity-tercile-strategies')])

    # ---------------------------------
    # 2) INSTRUMENTS
    # ---------------------------------
    rows = []
    tag = {k: ('Top6' if i < 6 else f'added in Top{i + 1}') for i, k in enumerate(ORDER)}
    for k, t in TR.items():
        if t:
            rows.append((t, NAME[k], 'Commodity', SECTOR[k], 'Bloomberg', tag.get(k)))
    rows += [('BCOMTR', 'Bloomberg Commodity Index Total Return', 'Commodity index', None, 'Bloomberg', None),
             ('SPX', 'S&P 500 (price)', 'Equity', None, 'Bloomberg', None),
             ('DX', 'U.S. Dollar Index futures', 'FX', None, 'Barchart (exchange)', None),
             ('DXY_FREE', 'U.S. Dollar Index, free provider', 'FX', None, 'Free provider', None),
             ('DTB3', '3-month Treasury bill', 'Rates', None, 'FRED', None)]
    con.executemany('INSERT INTO dim_instrument (ticker,name,asset_class,sector,source,in_universe) VALUES (?,?,?,?,?,?)', rows)

    # ---------------------------------
    # 3) STRATEGIES AND RESULTS
    # ---------------------------------
    cfg = pd.read_csv(PA / 'all_configs.csv')
    d = Data()
    seen = {}
    monthly = []
    sid = 0
    for u, (keys, splits) in UNIVERSES.items():
        P, _, _ = d.prices(keys)
        for sz in splits:
            sp = '-'.join(map(str, sz))
            for lb, f in itertools.product(E.LOOKBACKS, E.FREQS):
                res, reb, order, sig = E.run_config(P, d.dates, E.LOOKBACKS[lb], f, sz, S0, 0.0)
                for g in G.GROUPS:
                    sid += 1
                    r = res[g][0][S0 + 1:]
                    # some configs give the exact same portfolio; hash the returns and flag repeats
                    fp = hashlib.md5(np.round(r, 12).tobytes()).hexdigest()
                    dup = int(fp in seen); seen.setdefault(fp, sid)
                    lab = G.label({'Universe': u, 'Split': sp, 'Group': g, 'Lookback': lb}) + f', {f.lower()} rebalance'
                    con.execute('INSERT INTO dim_strategy VALUES (?,?,?,?,?,?,?,?,?,?)',
                                (sid, 2, u, sp, lb, E.LOOKBACKS[lb], f, g, lab, dup))
                    c = cfg[(cfg.Universe == u) & (cfg.Split == sp) & (cfg.Lookback == lb) & (cfg.Frequency == f) & (cfg.Group == g)].iloc[0]
                    for bp in (0, 1, 2, 5):
                        con.execute('INSERT INTO fact_strategy_result VALUES (?,?,?,?,?)',
                                    (sid, bp, float(c[f'fv{bp}']), float(c[f'sr{bp}']), float(c[f'exsr{bp}'])))
                    be = float(c.be_bh) if np.isfinite(c.be_bh) else None
                    con.execute('INSERT INTO fact_strategy_profile VALUES (?,?,?,?,?,?)',
                                (sid, float(c.vol), float(c.mdd0), float(c.turn), be, float(c.ew_sr0)))
                    m = (1 + pd.Series(r, index=d.dates[S0 + 1:])).resample('ME').prod() - 1
                    monthly += [(sid, str(k.date()), float(v)) for k, v in m.items()]
    con.executemany('INSERT INTO fact_strategy_monthly VALUES (?,?,?)', monthly)
    # BCOMTR buy & hold goes in as strategy -1 so the views can compare against it
    bh = d.BCOM_R.iloc[S0 + 1:]
    con.execute('INSERT INTO dim_strategy VALUES (?,?,?,?,?,?,?,?,?,?)', (-1, 2, 'Benchmark', '-', 'n/a', 0, 'Buy & hold', 'BCOMTR', 'BCOMTR buy and hold', 0))
    con.execute('INSERT INTO fact_strategy_result VALUES (?,?,?,?,?)', (-1, 0, float(100 * (1 + bh).prod()), N['bh']['sharpe'], N['bh']['excess_sharpe']))
    bm = (1 + bh).resample('ME').prod() - 1
    rowsb = [('BCOMTR buy and hold', str(k.date()), float(v)) for k, v in bm.items()]
    for u in UNIVERSES:
        P, _, _ = d.prices(UNIVERSES[u][0])
        r, t, reb = E.equal_weight(P, d.dates, 'Monthly', S0)
        m = (1 + pd.Series(r[S0 + 1:], index=d.dates[S0 + 1:])).resample('ME').prod() - 1
        rowsb += [(f'1/N {u} monthly', str(k.date()), float(v)) for k, v in m.items()]
    con.executemany('INSERT INTO fact_benchmark_monthly VALUES (?,?,?)', rowsb)

    # ---------------------------------
    # 4) NOISE CEILING, REBALANCE OFFSETS, OPEN-PRICE SCREEN
    # ---------------------------------
    con.executemany('INSERT INTO fact_noise_ceiling VALUES (?,?,?,?,?,?,?,?,?,?)',
                    [(x['Universe'], x['Split'], x['Group'], x['best_real'], x['best_cfg'], x['null_median'], x['ceiling'],
                      x['share_null_ge'], x['n_above'], x['reps']) for x in N['noise_ceiling']])
    off = pd.read_csv(PA / 'rebalance_offsets.csv')
    con.executemany('INSERT INTO fact_rebalance_offset VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    [tuple(r) for r in off[['Universe', 'Split', 'Lookback', 'Frequency', 'Group', 'sr_calendar', 'sr_min', 'sr_max',
                                            'sr_mean', 'range', 'calendar_rank', 'n_offsets']].itertuples(index=False)])
    scr = pd.read_csv(PA / 'open_price_screen.csv')
    con.executemany('INSERT INTO fact_open_screen VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    [(r['Series'], r['Source'], r['Sector'], int(r['Sessions (H>L)']), int(r['Open = low']), int(r['Open = high']),
                      float(r['Binomial p']), float(r['Mean open position (0.5 = unbiased)']), float(r['Open outside range %']),
                      float(r['Open = previous close %']), r['Flag']) for _, r in scr.iterrows()])

    # ---------------------------------
    # 5) FINDINGS
    # ---------------------------------
    # Numbers must match the manuscripts exactly. Hardcoded ones come from the file in the last column.
    F = [
        (1, 'Data defect', 'Overnight-leg Sharpe ratio', -1.36, 'Free provider (same sessions)', 0.25, 'Exchange futures',
         'The same trading rule on the same sessions shows a strong overnight effect on free data (p < 0.0001) and none on exchange futures (p = 0.33).', 'Risks manuscript, Revision 1; results/revision/text_numbers.txt'),
        (1, 'Data defect', 'Headline strategy total return (%)', 218.8, 'Free provider', 1.0, 'Exchange futures',
         'A backtest that more than tripled money on free data earns about 1% on correct data.', 'Risks manuscript, Sec. 5; results/part1_exchange_battery.txt'),
        (1, 'Data defect', 'Probability of backtest overfitting', 0.016, 'Free provider', 0.765, 'Exchange futures',
         'The standard overfitting check rates the false result robust and the correct data as likely overfit.', 'Risks manuscript, Sec. 8; results/part1_exchange_battery.txt'),
        (1, 'Data defect', 'Opens at the daily low vs high', 204, 'Free provider (at low)', 82, 'Free provider (at high)',
         'A one-line check on the data itself (p = 3.7e-13) flags the free feed and none of the six exchange futures series, with 3.3% false alarms across 30 clean three-year windows.', 'results/part1_exchange_battery.txt; results/revision/screen_study.txt'),
        (1, 'Undeclared search', 'Regime-strategy Sharpe as reported vs deflated Sharpe after declaring 216 configurations', 0.72, 'Reported', 0.613, 'Deflated Sharpe (needs > 0.95)',
         'A strategy first reported at 0.79 drops to 0.72 after a code fix and fails every correction once all 216 variants that were tried are counted.', 'Risks manuscript, Revision 1; results/part2_declared_search.txt; results/revision/text_numbers.txt'),
        (1, 'Honest search', 'Best Sharpe of 1,312 configurations vs mean luck ceiling (2,000 bootstrap runs)', 0.653, 'Best real', 0.737, 'Luck ceiling (mean of 2,000 runs)',
         'Re-running the whole 1,312-strategy search on 2,000 resampled versions of the data, the real best sits at the 23rd percentile of what luck alone produces (p = 0.77).', 'Risks manuscript, Revision 1; results/revision/ceiling_summary.txt'),
        (1, 'Carry', 'Carry Sharpe: futures (roll signal) vs 24-year spot total return', 0.377, 'Futures 2011-2025', 0.019, 'Spot total return 2002-2026',
         'An apparent carry reversal was mostly a missing interest term; neither version beats its own luck ceiling (p 0.21 and 0.40).', 'Risks manuscript, Revision 1; results/revision/carry_instability.txt'),
        (2, 'Momentum', 'Best momentum-spread Sharpe vs median best under random ranking', max(x['best_real'] for x in N['noise_ceiling'] if x['Group'] == 'Top-minus-Worst'), 'Best real',
         float(np.median([x['null_median'] for x in N['noise_ceiling'] if x['Group'] == 'Top-minus-Worst'])), 'Random ranking (median best)',
         'Buying recent winners and selling recent losers does no better than a random ranking in a search this size.', 'Commodities manuscript, Sec. 4.2'),
        (2, 'Volatility sorting', 'Share of cells where the middle group beats equal weight', N['median_beats_ew_cells'], 'Middle group', N['top_beats_ew_cells'], 'Top group',
         'The middle group wins mostly by holding the most volatile commodity (natural gas) less often.', 'Commodities manuscript, Sec. 4.3'),
        (2, 'Execution', 'One-day reversal Sharpe: same close vs one day later (Top 9)', N['reversal']['Top9_worst3']['lag0']['sharpe'], 'Same close',
         N['reversal']['Top9_worst3']['lag1']['sharpe'], 'One day later',
         'The best-looking effect exists only at prices nobody can trade at, and costs of about 5 bp remove it.', 'Commodities manuscript, Sec. 4.4'),
        (2, 'Rebalance date', 'Best annual strategy: final value of $100, December vs median of all 12 months', N['star_by_month'][11]['final'],
         'December rebalance', float(np.median([m['final'] for m in N['star_by_month']])), 'Median over 12 months',
         'The best strategy after costs owes its rank to the calendar date it rebalances on.', 'Commodities manuscript, Sec. 4.5'),
        (2, 'Out of sample', 'Top 5 chosen on 2001-2013: best final value of $100 over 2014-2026 vs buy & hold', max(x['final_out'] for x in N['wf_split']),
         'Best of the 5', N['wf_split_bh']['final_out'], 'Buy & hold',
         'The strategies that looked best in the first half all trailed buy-and-hold in the second.', 'Commodities manuscript, Sec. 4.6'),
    ]
    con.executemany('INSERT INTO fact_finding (study_id,theme,metric,value_a,label_a,value_b,label_b,plain_english,source_file) VALUES (?,?,?,?,?,?,?,?,?)', F)

    # ---------------------------------
    # 6) DXY OVERNIGHT / DAYTIME LEGS, BOTH SOURCES
    # ---------------------------------
    ex = pd.read_csv(DXY / 'data' / 'futures' / 'DX.csv', skipfooter=1, engine='python')
    ex['Date'] = pd.to_datetime(ex['Time']); ex = ex.sort_values('Date').set_index('Date')
    # Same convention as the Risks paper (src/part1_data_defect/exchange_battery.py): nearby series as delivered, no roll fix
    on_ex = ex['Open'] / ex['Latest'].shift(1) - 1
    day_ex = ex['Latest'] / ex['Open'] - 1
    bh_ex = ex['Latest'].ffill().pct_change()
    fr = pd.read_csv(DXY / 'data' / 'vendor' / 'fx_ohlc_2010_2025.csv', parse_dates=['Date']).set_index('Date')
    on_fr = fr['DXY_Open'] / fr['DXY_Close'].shift(1) - 1
    day_fr = fr['DXY_Close'] / fr['DXY_Open'] - 1
    bh_fr = fr['DXY_Close'].ffill().pct_change()                # 138 missing closes, carry the last print
    legs = []
    for src, parts in [('Exchange futures', (on_ex, day_ex, bh_ex)), ('Free provider', (on_fr, day_fr, bh_fr))]:
        for leg, s in zip(['Overnight', 'Daytime', 'Buy and hold'], parts):
            m = (1 + s.dropna()).resample('ME').prod() - 1
            legs += [(src, leg, str(k.date()), float(v)) for k, v in m.items()]
    con.executemany('INSERT INTO fact_dxy_leg_monthly VALUES (?,?,?,?)', legs)

    con.commit()
    con.executescript((BASE / 'sql' / 'views.sql').read_text())
    con.commit()
    # row counts, quick sanity check
    for t in ['dim_strategy', 'fact_strategy_result', 'fact_strategy_monthly', 'fact_noise_ceiling', 'fact_rebalance_offset',
              'fact_open_screen', 'fact_finding', 'fact_dxy_leg_monthly', 'fact_benchmark_monthly']:
        print(t, con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0])
    con.close()


if __name__ == '__main__':
    main()
