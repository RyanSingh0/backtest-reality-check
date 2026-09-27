-- One view per question someone outside quant would actually ask. The dashboard reads these.

-- Q1. Best strategy at each rebalance frequency, and what it's worth after costs.
-- Ranked on gross (0 bp) value, duplicates dropped, then pivot the cost levels into columns.
DROP VIEW IF EXISTS v_best_by_frequency;
CREATE VIEW v_best_by_frequency AS
WITH gross AS (
  SELECT s.frequency, s.strategy_id, s.label, r.final_value_100,
         ROW_NUMBER() OVER (PARTITION BY s.frequency ORDER BY r.final_value_100 DESC) AS rk
  FROM dim_strategy s JOIN fact_strategy_result r USING (strategy_id)
  WHERE r.cost_bp = 0 AND s.is_duplicate = 0)
SELECT g.frequency, g.label, g.strategy_id,
       MAX(CASE WHEN r.cost_bp = 0 THEN r.final_value_100 END) AS value_0bp,
       MAX(CASE WHEN r.cost_bp = 1 THEN r.final_value_100 END) AS value_1bp,
       MAX(CASE WHEN r.cost_bp = 2 THEN r.final_value_100 END) AS value_2bp,
       MAX(CASE WHEN r.cost_bp = 5 THEN r.final_value_100 END) AS value_5bp,
       p.breakeven_bp_vs_bh, p.turnover_per_year, p.max_drawdown
FROM gross g JOIN fact_strategy_result r USING (strategy_id) JOIN fact_strategy_profile p USING (strategy_id)
WHERE g.rk = 1
GROUP BY g.frequency, g.label, g.strategy_id;

-- Q2. How many strategies beat buy-and-hold as costs rise?
-- Compared against gross buy & hold (strategy -1, cost 0) at every cost level.
DROP VIEW IF EXISTS v_share_beating_bh;
CREATE VIEW v_share_beating_bh AS
SELECT r.cost_bp,
       COUNT(*) AS n_strategies,
       SUM(r.final_value_100 > (SELECT final_value_100 FROM fact_strategy_result WHERE strategy_id = -1 AND cost_bp = 0)) AS n_beat_bh,
       ROUND(1.0 * SUM(r.final_value_100 > (SELECT final_value_100 FROM fact_strategy_result WHERE strategy_id = -1 AND cost_bp = 0)) / COUNT(*), 4) AS share_beat_bh
FROM fact_strategy_result r JOIN dim_strategy s USING (strategy_id)
WHERE s.is_duplicate = 0 AND r.strategy_id > 0
GROUP BY r.cost_bp;

-- Q3. Is the best result better than luck? Noise-ceiling verdict per grid.
-- Within 0.01 Sharpe of the ceiling I call it too close.
DROP VIEW IF EXISTS v_noise_verdict;
CREATE VIEW v_noise_verdict AS
SELECT universe, split, grp, best_config, ROUND(best_real_sharpe, 3) AS best_sharpe, ROUND(ceiling_95, 3) AS luck_ceiling,
       CASE WHEN ABS(best_real_sharpe - ceiling_95) < 0.01 THEN 'too close to call'
            WHEN best_real_sharpe > ceiling_95 THEN 'better than luck'
            ELSE 'within luck' END AS verdict
FROM fact_noise_ceiling;

-- Q4. Which group beats just holding everything equally, and how volatile is it?
-- Long-short (Top-minus-Worst) left out, it isn't comparable to 1/N.
DROP VIEW IF EXISTS v_group_vs_equal_weight;
CREATE VIEW v_group_vs_equal_weight AS
SELECT s.grp, COUNT(*) AS n,
       ROUND(AVG(r.sharpe), 3) AS avg_sharpe,
       ROUND(AVG(p.ew_sharpe_same_freq), 3) AS avg_equal_weight_sharpe,
       ROUND(AVG(r.sharpe > p.ew_sharpe_same_freq), 3) AS share_beating_equal_weight,
       ROUND(AVG(p.volatility), 3) AS avg_volatility
FROM dim_strategy s JOIN fact_strategy_result r USING (strategy_id) JOIN fact_strategy_profile p USING (strategy_id)
WHERE r.cost_bp = 0 AND s.grp <> 'Top-minus-Worst'
GROUP BY s.grp;

-- Q5. How much does the rebalance date matter?
DROP VIEW IF EXISTS v_rebalance_date_risk;
CREATE VIEW v_rebalance_date_risk AS
SELECT frequency, COUNT(*) AS n_strategies, ROUND(AVG(sharpe_range), 3) AS avg_sharpe_range_across_dates,
       ROUND(AVG(calendar_rank = 1), 3) AS share_where_calendar_date_is_best
FROM fact_rebalance_offset GROUP BY frequency;

-- Q6. Which data feeds fail the open-price screen?
DROP VIEW IF EXISTS v_data_quality;
CREATE VIEW v_data_quality AS
SELECT source, COUNT(*) AS n_series, SUM(flag = 'FAIL') AS n_fail,
       GROUP_CONCAT(CASE WHEN flag = 'FAIL' THEN series END, '; ') AS failing_series
FROM fact_open_screen GROUP BY source;

-- Q7. Calendar-year return for any strategy. Compounds monthly returns via EXP(SUM(LN(1 + r))).
DROP VIEW IF EXISTS v_strategy_calendar_year;
CREATE VIEW v_strategy_calendar_year AS
SELECT strategy_id, SUBSTR(month, 1, 4) AS year,
       EXP(SUM(LN(1 + ret_gross))) - 1 AS year_return
FROM fact_strategy_monthly GROUP BY strategy_id, SUBSTR(month, 1, 4);
