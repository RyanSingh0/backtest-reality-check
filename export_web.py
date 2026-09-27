"""Dumps the dashboard data from research.db to web/data.json for the static HTML page. Views only."""
import json, sqlite3
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent
con = sqlite3.connect(ROOT / 'research.db')
Q = lambda s: pd.read_sql(s, con)
d = {}
d['best'] = Q("SELECT frequency,label,value_0bp v0,value_1bp v1,value_2bp v2,value_5bp v5,breakeven_bp_vs_bh be,turnover_per_year turn,max_drawdown mdd FROM v_best_by_frequency").round(3).to_dict('records')
d['bh'] = float(Q("SELECT final_value_100 FROM fact_strategy_result WHERE strategy_id=-1").iloc[0, 0])
d['share'] = Q("SELECT * FROM v_share_beating_bh").to_dict('records')
d['noise'] = Q("SELECT * FROM v_noise_verdict").to_dict('records')
d['groups'] = Q("SELECT * FROM v_group_vs_equal_weight").to_dict('records')
d['calendar'] = Q("SELECT * FROM v_rebalance_date_risk").to_dict('records')
d['quality'] = Q("SELECT source,n_series,n_fail FROM v_data_quality").to_dict('records')
d['screen'] = Q("SELECT series,source,sector,open_at_low,open_at_high,binomial_p,open_outside_range_pct,flag FROM fact_open_screen").to_dict('records')
d['findings'] = Q("SELECT s.short_name study,f.theme,f.metric,f.value_a,f.label_a,f.value_b,f.label_b,f.plain_english FROM fact_finding f JOIN dim_study s USING(study_id) ORDER BY finding_id").to_dict('records')
legs = Q("SELECT source,leg,month,ret FROM fact_dxy_leg_monthly ORDER BY source,leg,month")
legs['v'] = legs.groupby(['source', 'leg']).ret.transform(lambda r: 100 * (1 + r).cumprod())
legs = legs[legs.month.str[5:7] == '12']            # keep year-end points only, keeps the json small
d['legs'] = {f'{s}|{l}': g[['month', 'v']].assign(month=lambda x: x.month.str[:4]).round(2).values.tolist() for (s, l), g in legs.groupby(['source', 'leg'])}
d['studies'] = Q("SELECT short_name,title,journal,status,sample_start,sample_end FROM dim_study").to_dict('records')
(ROOT / 'web' / 'data.json').write_text(json.dumps(d, default=float))
print({k: (len(v) if hasattr(v, '__len__') else v) for k, v in d.items()}, (ROOT / 'web' / 'data.json').stat().st_size)
