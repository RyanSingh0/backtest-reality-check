-- Risks manuscript, Revision 1 (Oct 2026): brings an existing research.db in line with
-- dxy-fx-strategies commit ac63b42. build_db.py already writes these values on a fresh build;
-- this file updates a database built before the revision.   sqlite3 research.db < sql/revision1.sql
BEGIN;
UPDATE dim_study SET status = 'Under review, revision submitted' WHERE short_name = 'DXY';

UPDATE fact_finding SET value_a = -1.36, label_a = 'Free provider (same sessions)',
  plain_english = 'The same trading rule on the same sessions shows a strong overnight effect on free data (p < 0.0001) and none on exchange futures (p = 0.33).',
  source_file = 'Risks manuscript, Revision 1; results/revision/text_numbers.txt'
  WHERE study_id = 1 AND metric = 'Overnight-leg Sharpe ratio';

UPDATE fact_finding SET
  plain_english = 'The standard overfitting check rates the false result robust and the correct data as likely overfit.'
  WHERE study_id = 1 AND metric = 'Probability of backtest overfitting';

UPDATE fact_finding SET
  plain_english = 'A one-line check on the data itself (p = 3.7e-13) flags the free feed and none of the six exchange futures series, with 3.3% false alarms across 30 clean three-year windows.',
  source_file = 'results/part1_exchange_battery.txt; results/revision/screen_study.txt'
  WHERE study_id = 1 AND metric = 'Opens at the daily low vs high';

UPDATE fact_finding SET
  plain_english = 'A strategy first reported at 0.79 drops to 0.72 after a code fix and fails every correction once all 216 variants that were tried are counted.',
  source_file = 'Risks manuscript, Revision 1; results/part2_declared_search.txt; results/revision/text_numbers.txt'
  WHERE study_id = 1 AND theme = 'Undeclared search';

UPDATE fact_finding SET metric = 'Best Sharpe of 1,312 configurations vs mean luck ceiling (2,000 bootstrap runs)',
  value_b = 0.737, label_b = 'Luck ceiling (mean of 2,000 runs)',
  plain_english = 'Re-running the whole 1,312-strategy search on 2,000 resampled versions of the data, the real best sits at the 23rd percentile of what luck alone produces (p = 0.77).',
  source_file = 'Risks manuscript, Revision 1; results/revision/ceiling_summary.txt'
  WHERE study_id = 1 AND theme = 'Honest search';

-- new DXY row: keep the ledger order (all DXY rows first) by rebuilding ids
CREATE TEMP TABLE ff AS SELECT * FROM fact_finding ORDER BY finding_id;
INSERT INTO ff (finding_id, study_id, theme, metric, value_a, label_a, value_b, label_b, plain_english, source_file)
  SELECT (SELECT finding_id FROM fact_finding WHERE study_id = 1 AND theme = 'Honest search') + 0.5, 1, 'Carry',
  'Carry Sharpe: futures (roll signal) vs 24-year spot total return', 0.377, 'Futures 2011-2025', 0.019, 'Spot total return 2002-2026',
  'An apparent carry reversal was mostly a missing interest term; neither version beats its own luck ceiling (p 0.21 and 0.40).',
  'Risks manuscript, Revision 1; results/revision/carry_instability.txt';
DELETE FROM fact_finding;
INSERT INTO fact_finding (study_id, theme, metric, value_a, label_a, value_b, label_b, plain_english, source_file)
  SELECT study_id, theme, metric, value_a, label_a, value_b, label_b, plain_english, source_file FROM ff ORDER BY finding_id;
DROP TABLE ff;
COMMIT;
