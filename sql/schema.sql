-- My research db: DXY/FX paper (Risks, submitted) and the commodity cross-sectional paper (Commodities)
-- Star schema. dim_ tables = what I tested, fact_ tables = results. SQLite.

PRAGMA foreign_keys = ON;

CREATE TABLE dim_study (
    study_id      INTEGER PRIMARY KEY,
    short_name    TEXT NOT NULL UNIQUE,          -- 'DXY' or 'COMMODITIES'
    title         TEXT NOT NULL,
    journal       TEXT,
    status        TEXT,
    sample_start  DATE,
    sample_end    DATE,
    repository    TEXT
);

CREATE TABLE dim_instrument (
    instrument_id INTEGER PRIMARY KEY,
    ticker        TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    asset_class   TEXT NOT NULL,                 -- Commodity, Commodity index, Equity, FX
    sector        TEXT,
    source        TEXT NOT NULL,                 -- Bloomberg, Barchart (exchange), Free provider, FRED
    in_universe   TEXT                           -- Top6 / added in Top7 ... (commodity study only)
);

CREATE TABLE dim_strategy (
    strategy_id   INTEGER PRIMARY KEY,
    study_id      INTEGER NOT NULL REFERENCES dim_study(study_id),
    universe      TEXT NOT NULL,                 -- Top6..Top9
    split         TEXT NOT NULL,                 -- e.g. 2-2-2
    lookback      TEXT NOT NULL,                 -- e.g. Monthly (21d)
    lookback_days INTEGER NOT NULL,
    frequency     TEXT NOT NULL,                 -- Daily .. Annual
    grp           TEXT NOT NULL,                 -- Top, Median, Worst, Top-minus-Worst
    label         TEXT NOT NULL,                 -- readable name for the dashboard
    is_duplicate  INTEGER NOT NULL DEFAULT 0,    -- 1 if same portfolio as a lower strategy_id; views skip these
    UNIQUE (universe, split, lookback, frequency, grp)
);

-- one row per strategy per cost level (0/1/2/5 bp)
CREATE TABLE fact_strategy_result (
    strategy_id     INTEGER NOT NULL REFERENCES dim_strategy(strategy_id),
    cost_bp         REAL NOT NULL,
    final_value_100 REAL NOT NULL,               -- what $100 grows to by the end of the sample
    sharpe          REAL NOT NULL,               -- annualised, rf = 0
    excess_sharpe   REAL,                        -- over T-bills; for long-short I don't subtract rf
    PRIMARY KEY (strategy_id, cost_bp)
);

CREATE TABLE fact_strategy_profile (
    strategy_id       INTEGER PRIMARY KEY REFERENCES dim_strategy(strategy_id),
    volatility        REAL, max_drawdown REAL, turnover_per_year REAL,
    breakeven_bp_vs_bh REAL,                     -- cost (bp) where final value drops to BCOMTR buy & hold
    ew_sharpe_same_freq REAL                     -- 1/N on the same commodities, same frequency
);

CREATE TABLE fact_strategy_monthly (
    strategy_id INTEGER NOT NULL REFERENCES dim_strategy(strategy_id),
    month       DATE NOT NULL,
    ret_gross   REAL NOT NULL,
    PRIMARY KEY (strategy_id, month)
);

CREATE TABLE fact_benchmark_monthly (
    benchmark TEXT NOT NULL,                     -- BCOMTR, 1/N Top6 Monthly, ...
    month     DATE NOT NULL,
    ret       REAL NOT NULL,
    PRIMARY KEY (benchmark, month)
);

CREATE TABLE fact_noise_ceiling (
    universe TEXT, split TEXT, grp TEXT,
    best_real_sharpe REAL, best_config TEXT, null_median REAL, ceiling_95 REAL,
    share_null_ge_real REAL, n_configs_above INTEGER, replications INTEGER,
    PRIMARY KEY (universe, split, grp)
);

CREATE TABLE fact_rebalance_offset (
    universe TEXT, split TEXT, lookback TEXT, frequency TEXT, grp TEXT,
    sharpe_calendar REAL, sharpe_min REAL, sharpe_max REAL, sharpe_mean REAL, sharpe_range REAL,
    calendar_rank INTEGER, n_offsets INTEGER,
    PRIMARY KEY (universe, split, lookback, frequency, grp)
);

CREATE TABLE fact_open_screen (
    series TEXT PRIMARY KEY, source TEXT, sector TEXT, sessions INTEGER,
    open_at_low INTEGER, open_at_high INTEGER, binomial_p REAL,
    mean_open_position REAL, open_outside_range_pct REAL, open_eq_prev_close_pct REAL, flag TEXT
);

-- headline numbers from each paper, plus the file each one came from
CREATE TABLE fact_finding (
    finding_id  INTEGER PRIMARY KEY,
    study_id    INTEGER NOT NULL REFERENCES dim_study(study_id),
    theme       TEXT NOT NULL,                   -- e.g. 'Data defect', 'Undeclared search'
    metric      TEXT NOT NULL,
    value_a     REAL, label_a TEXT,              -- e.g. free provider
    value_b     REAL, label_b TEXT,              -- e.g. exchange futures
    plain_english TEXT NOT NULL,
    source_file TEXT NOT NULL
);

-- DXY overnight / daytime / buy-and-hold legs, monthly, on both data sources
CREATE TABLE fact_dxy_leg_monthly (
    source TEXT NOT NULL,                        -- 'Free provider' or 'Exchange futures'
    leg    TEXT NOT NULL,                        -- 'Overnight', 'Daytime', 'Buy and hold'
    month  DATE NOT NULL,
    ret    REAL NOT NULL,
    PRIMARY KEY (source, leg, month)
);
