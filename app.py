"""Local dashboard. Every chart and table here is a SQL query on research.db.

Run from this folder:
    python build_db.py          # first time, or after the paper outputs change
    streamlit run app.py
"""
import sqlite3
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB = Path(__file__).resolve().parent / 'research.db'
st.set_page_config(page_title='Backtest Reality Check', layout='wide')


@st.cache_data   # cached per query, so clear the cache or restart after rebuilding the db
def q(sql, params=()):
    with sqlite3.connect(DB) as con:
        return pd.read_sql(sql, con, params=params)


st.title('Backtest Reality Check')
st.caption('Two research studies on why trading strategies that look profitable in a backtest often are not. '
           'Aryan Meena with Prof. Eugene Pinsky, Boston University.')

tab1, tab2, tab3, tab4, tab5 = st.tabs(['Summary', 'Would it have made money?', 'Is it better than luck?',
                                        'Dollar Index: two data sources', 'Data quality'])

with tab1:
    f = q('SELECT s.short_name AS study, f.theme, f.metric, f.value_a, f.label_a, f.value_b, f.label_b, f.plain_english, f.source_file '
          'FROM fact_finding f JOIN dim_study s USING (study_id) ORDER BY f.finding_id')
    for _, r in f.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.markdown(f"**{r.study} | {r.theme}.** {r.plain_english}")
        c2.metric(r.label_a, f'{r.value_a:,.3g}')
        c3.metric(r.label_b, f'{r.value_b:,.3g}')
    st.caption('Source of each number: ' + '; '.join(f.source_file.unique()))

with tab2:
    st.subheader('Commodity strategies: value of $100 invested in Jan 2001, by trading cost')
    cost = st.select_slider('Trading cost per unit traded (basis points)', options=[0, 1, 2, 5], value=0)
    best = q('SELECT * FROM v_best_by_frequency')
    bh = q('SELECT final_value_100 FROM fact_strategy_result WHERE strategy_id = -1').iloc[0, 0]
    col = {0: 'value_0bp', 1: 'value_1bp', 2: 'value_2bp', 5: 'value_5bp'}[cost]
    fig = px.bar(best, x='frequency', y=col, hover_data=['label', 'breakeven_bp_vs_bh', 'turnover_per_year'],
                 labels={col: 'Final value of $100', 'frequency': 'Rebalance frequency'},
                 category_orders={'frequency': ['Daily', 'Weekly', 'Biweekly', 'Monthly', 'Quarterly', 'Semiannual', 'Annual']})
    fig.add_hline(y=bh, line_dash='dash', line_color='#D62728', annotation_text=f'Buy & hold ${bh:,.0f}')
    st.plotly_chart(fig, width='stretch')
    st.dataframe(best, width='stretch', hide_index=True)
    st.subheader('How many strategies beat buy-and-hold as costs rise?')
    st.dataframe(q('SELECT * FROM v_share_beating_bh'), hide_index=True)

with tab3:
    st.subheader('Noise ceiling: the best result a search of this size finds with random rankings')
    nv = q('SELECT * FROM v_noise_verdict')
    nv['grid'] = nv.universe + ' ' + nv.split
    fig = go.Figure()
    for g in nv.grp.unique():
        z = nv[nv.grp == g]
        fig.add_bar(name=g, x=z.grid, y=z.best_sharpe)
    fig.update_layout(barmode='group', yaxis_title='Best Sharpe ratio (gross)')
    st.plotly_chart(fig, width='stretch')
    st.dataframe(nv, hide_index=True, width='stretch')
    st.subheader('Rebalance-date luck')
    st.dataframe(q('SELECT * FROM v_rebalance_date_risk'), hide_index=True)

with tab4:
    st.subheader('Same index, same rule, two data vendors')
    legs = q('SELECT source, leg, month, ret FROM fact_dxy_leg_monthly ORDER BY source, leg, month')
    legs['value'] = legs.groupby(['source', 'leg']).ret.transform(lambda r: 100 * (1 + r).cumprod())
    fig = px.line(legs, x='month', y='value', color='leg', facet_col='source', labels={'value': 'Growth of $100'})
    st.plotly_chart(fig, width='stretch')
    st.caption('On the free feed the overnight leg loses 39% and the daytime leg almost doubles; on exchange futures both are near zero. '
               "The difference traces to a persistent downward bias in the free feed's recorded opening prices.")

with tab5:
    st.subheader('Open-price screen: does the recorded open sit at the low far more often than at the high?')
    st.dataframe(q('SELECT * FROM v_data_quality'), hide_index=True, width='stretch')
    st.dataframe(q('SELECT * FROM fact_open_screen ORDER BY flag DESC, binomial_p'), hide_index=True, width='stretch')
