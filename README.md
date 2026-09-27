# Backtest Reality Check

**Live dashboard:** https://ryansingh0.github.io/backtest-reality-check/

A SQL database and dashboard that put the results of two of my research papers with Prof. Eugene Pinsky
(Boston University) in front of people who don't read backtests for a living. Each check on the page is one a
model-validation team would run before money goes into a strategy: is the data right, does it survive trading
costs, is it better than luck, and does it depend on an arbitrary date.

| Study | Journal | Code |
|---|---|---|
| Two Blind Spots in Backtest Validation (U.S. Dollar Index) | Risks (MDPI), submitted | [dxy-fx-strategies](https://github.com/RyanSingh0/dxy-fx-strategies) |
| Volatility Sorting, an Untradeable Reversal and Rebalance-Date Luck (commodities) | Commodities (MDPI), manuscript | [commodity-tercile-strategies](https://github.com/RyanSingh0/commodity-tercile-strategies) |

## What's here

```
research.db          SQLite database with the results of both studies (26 MB)
sql/schema.sql       star schema: 3 dimension tables, 9 fact tables
sql/views.sql        7 views, each answering one business question
app.py               Streamlit dashboard, every chart is a SQL query on research.db
docs/index.html      the static dashboard served by GitHub Pages
build_db.py          rebuilds research.db from the two research repos (needs the licensed data)
export_web.py        views -> web/data.json
build_page.py        web/ + data.json -> docs/index.html
```

## Questions the views answer

| View | Question |
|---|---|
| `v_best_by_frequency` | Best strategy at each rebalance frequency, and what $100 becomes after 0/1/2/5 bp of costs |
| `v_share_beating_bh` | How many of 1,372 strategies beat buy and hold as costs rise (39% at 0 bp, 28% at 5 bp) |
| `v_noise_verdict` | Is the best result in each search grid better than a random search of the same size |
| `v_group_vs_equal_weight` | Which group beats simply holding everything equally |
| `v_rebalance_date_risk` | How much the answer moves when only the rebalance date changes |
| `v_data_quality` | Which price feeds fail the open-price screen |
| `v_strategy_calendar_year` | Calendar-year return of any strategy |

```
sqlite3 research.db "SELECT * FROM v_best_by_frequency;"
```

## Run the dashboard locally

```
pip install -r requirements.txt
streamlit run app.py
```

## Data

The database holds results I computed: strategy returns, test statistics and screen counts. It does not contain
vendor price data. The commodity inputs came from a Bloomberg terminal and are licensed, so `build_db.py` only
runs if you have that export next to the two research repos. The public `research.db` is made with
`make_public_db.py`, which also removes the benchmark index's own monthly returns.

Backtests are hypothetical. This is research, not investment advice.
