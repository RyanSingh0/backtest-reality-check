(function () {
  const D = window.__DATA__;
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const $ = id => document.getElementById(id);
  const money = v => '$' + Math.round(v).toLocaleString('en-US');
  const FREQ = ['Daily', 'Weekly', 'Biweekly', 'Monthly', 'Quarterly', 'Semiannual', 'Annual'];
  const best = FREQ.map(f => D.best.find(b => b.frequency === f));
  const BH = D.bh;
  let cost = 0, screenFilter = 'all';
  const charts = {};

  // studies
  $('studies').innerHTML = D.studies.map(s =>
    `<div class="study"><b>${s.title}</b><span>${s.journal} &middot; ${s.status} &middot; ${s.sample_start.slice(0, 4)} to ${s.sample_end.slice(0, 4)}</span></div>`).join('');

  // ledger
  const fmt = (v, metric) => {
    if (/\$|value of \$100/i.test(metric)) return money(v);
    if (/share/i.test(metric)) return Math.round(v * 100) + '%';
    if (/%\)/.test(metric)) return v.toFixed(1) + '%';
    if (/Opens at/.test(metric)) return v.toFixed(0);
    return (v < 0 ? '−' : '') + Math.abs(v).toFixed(v >= 10 ? 1 : 3).replace(/0$/, '');
  };
  $('ledgerRows').innerHTML = D.findings.map(f => `
    <div class="row">
      <div class="tagcell"><span class="tag ${f.study === 'DXY' ? 'dxy' : 'com'}">${f.study === 'DXY' ? 'Dollar index' : 'Commodities'}</span></div>
      <div class="claim">${f.plain_english}<small>${f.theme}: ${f.metric}</small></div>
      <div class="fig"><span class="v">${fmt(f.value_a, f.metric)}</span><span class="l">${f.label_a}</span></div>
      <div class="fig"><span class="v">${fmt(f.value_b, f.metric)}</span><span class="l">${f.label_b}</span></div>
    </div>`).join('');

  // share KPIs
  $('shareKpis').innerHTML = D.share.map(s =>
    `<div class="kpi"><div class="v">${(s.share_beat_bh * 100).toFixed(1)}%</div><div class="l">of ${s.n_strategies.toLocaleString()} strategies beat buy &amp; hold at ${s.cost_bp} bp (${s.n_beat_bh})</div></div>`).join('');

  // money table
  function moneyTable() {
    const cls = v => v > BH ? 'up' : 'dn';
    let h = `<thead><tr><th>Frequency</th><th>Best strategy</th><th class="n">0 bp</th><th class="n">1 bp</th><th class="n">2 bp</th><th class="n">5 bp</th><th class="n">Break-even</th><th class="n">Turnover / yr</th><th class="n">Worst drawdown</th></tr></thead><tbody>`;
    h += `<tr><td>Buy &amp; hold</td><td>Bloomberg Commodity Index</td>${[0, 1, 2, 3].map(() => `<td class="n bh">${money(BH)}</td>`).join('')}<td class="n">&ndash;</td><td class="n">&ndash;</td><td class="n">&ndash;</td></tr>`;
    best.forEach(b => {
      h += `<tr><td>${b.frequency}</td><td>${b.label.replace(/, \w+ rebalance$/, '')}</td>${['v0', 'v1', 'v2', 'v5'].map(k => `<td class="n ${cls(b[k])}">${money(b[k])}</td>`).join('')}` +
        `<td class="n">${b.be >= 100 ? Math.round(b.be) : b.be.toFixed(1)} bp</td><td class="n">${b.turn.toFixed(1)}&times;</td><td class="n">${(b.mdd * 100).toFixed(0)}%</td></tr>`;
    });
    $('moneyTable').innerHTML = h + '</tbody>';
  }

  // calendar table
  const nOff = { Biweekly: 2, Quarterly: 3, Semiannual: 6, Annual: 12 };
  const cal = ['Biweekly', 'Quarterly', 'Semiannual', 'Annual'].map(f => D.calendar.find(c => c.frequency === f));
  $('calTable').innerHTML = `<thead><tr><th>Frequency</th><th class="n">Possible dates</th><th class="n">Standard date is best</th><th class="n">By chance</th></tr></thead><tbody>` +
    cal.map(c => `<tr><td>${c.frequency}</td><td class="n">${nOff[c.frequency]}</td><td class="n">${(c.share_where_calendar_date_is_best * 100).toFixed(0)}%</td><td class="n">${(100 / nOff[c.frequency]).toFixed(0)}%</td></tr>`).join('') + '</tbody>';

  // luck KPIs
  const cnt = v => D.noise.filter(n => n.verdict === v).length;
  $('luckKpis').innerHTML = [['better than luck', 'Beat the ceiling'], ['too close to call', 'Within 0.01 of it'], ['within luck', 'Below it']]
    .map(([v, l]) => `<div class="kpi"><div class="v">${cnt(v)} / ${D.noise.length}</div><div class="l">${l}</div></div>`).join('');

  // quality KPIs and screen table
  $('qualityKpis').innerHTML = D.quality.map(q =>
    `<div class="kpi"><div class="v">${q.n_fail} / ${q.n_series}</div><div class="l">${q.source}: series that fail</div></div>`).join('');
  function screenTable() {
    const rows = D.screen.filter(r => screenFilter === 'all' || r.flag === 'FAIL')
      .sort((a, b) => (a.flag === b.flag ? a.binomial_p - b.binomial_p : a.flag === 'FAIL' ? -1 : 1));
    const pf = p => p < 1e-3 ? p.toExponential(1) : p.toFixed(3);
    $('screenTable').innerHTML = `<thead><tr><th>Series</th><th>Source</th><th class="n">Open at low</th><th class="n">Open at high</th><th class="n">p-value</th><th class="n">Open outside range</th><th>Result</th></tr></thead><tbody>` +
      rows.map(r => `<tr><td>${r.series}</td><td>${r.source}</td><td class="n">${r.open_at_low}</td><td class="n">${r.open_at_high}</td><td class="n">${pf(r.binomial_p)}</td><td class="n">${r.open_outside_range_pct.toFixed(1)}%</td><td><span class="chip ${r.flag === 'FAIL' ? 'fail' : 'pass'}">${r.flag === 'FAIL' ? 'Fail' : 'Pass'}</span></td></tr>`).join('') + '</tbody>';
  }

  // charts
  function base() {
    const ink = css('--muted'), rule = css('--rule');
    Chart.defaults.font.family = css('--body'); Chart.defaults.font.size = 12; Chart.defaults.color = ink;
    return {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { display: false } },
      scales: { x: { grid: { color: rule }, ticks: { color: ink } }, y: { grid: { color: rule }, ticks: { color: ink } } }
    };
  }
  const bhLine = (y, color) => ({
    id: 'bhLine', afterDatasetsDraw(c) {
      const { ctx, chartArea: a, scales: { y: s } } = c; const py = s.getPixelForValue(y);
      ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.setLineDash([6, 4]);
      ctx.beginPath(); ctx.moveTo(a.left, py); ctx.lineTo(a.right, py); ctx.stroke();
      ctx.setLineDash([]); ctx.fillStyle = color; ctx.font = '600 12px ' + css('--mono'); ctx.textAlign = 'left';
      ctx.fillText('Buy & hold ' + money(y), a.left + 6, py - 6); ctx.restore();
    }
  });

  function drawMoney() {
    const key = 'v' + cost, vals = best.map(b => b[key]);
    const o = base();
    o.scales.y.title = { display: true, text: 'Final value of $100' };
    o.scales.y.ticks.callback = v => money(v);
    o.scales.y.beginAtZero = true;
    o.scales.x.grid.display = false;
    o.plugins.tooltip = { callbacks: { title: i => best[i[0].dataIndex].label, label: i => money(i.raw) + ' at ' + cost + ' bp' } };
    charts.money && charts.money.destroy();
    charts.money = new Chart($('moneyChart'), {
      type: 'bar', data: { labels: FREQ, datasets: [{ data: vals, backgroundColor: vals.map(v => v > BH ? css('--good') : css('--bad')), borderRadius: 2, maxBarThickness: 64 }] },
      options: o, plugins: [bhLine(BH, css('--bh'))]
    });
  }

  function drawLuck() {
    const groups = { Top: css('--bh'), Median: css('--good'), Worst: css('--bad'), 'Top-minus-Worst': css('--flag') };
    $('luckLegend').innerHTML = Object.entries(groups).map(([g, c]) => `<span><i style="background:${c}"></i>${g}</span>`).join('');
    const o = base();
    o.scales.x.title = { display: true, text: 'Luck ceiling (Sharpe a random search reaches)' };
    o.scales.y.title = { display: true, text: 'Best real Sharpe ratio' };
    o.scales.x.min = o.scales.y.min = 0.4; o.scales.x.max = o.scales.y.max = 0.72;
    o.plugins.tooltip = { callbacks: { label: i => { const r = i.raw.r; return `${r.universe} ${r.split} ${r.grp}: ${r.best_sharpe.toFixed(3)} vs ${r.luck_ceiling.toFixed(3)} (${r.verdict})`; } } };
    const diag = { id: 'diag', beforeDatasetsDraw(c) {
      const { ctx, scales: { x, y } } = c; ctx.save(); ctx.strokeStyle = css('--muted'); ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(x.getPixelForValue(0.4), y.getPixelForValue(0.4)); ctx.lineTo(x.getPixelForValue(0.72), y.getPixelForValue(0.72)); ctx.stroke();
      ctx.setLineDash([]); ctx.fillStyle = css('--muted'); ctx.font = '12px ' + css('--body');
      ctx.fillText('better than luck', x.getPixelForValue(0.42), y.getPixelForValue(0.70)); ctx.fillText('within luck', x.getPixelForValue(0.63), y.getPixelForValue(0.43)); ctx.restore(); } };
    charts.luck && charts.luck.destroy();
    charts.luck = new Chart($('luckChart'), {
      type: 'scatter',
      data: { datasets: Object.keys(groups).map(g => ({ label: g, data: D.noise.filter(n => n.grp === g).map(n => ({ x: n.luck_ceiling, y: n.best_sharpe, r: n })), backgroundColor: groups[g], pointRadius: 5, pointHoverRadius: 7 })) },
      options: o, plugins: [diag]
    });
  }

  function drawCal() {
    const o = base(); o.scales.x.grid.display = false; o.scales.y.beginAtZero = true;
    o.scales.y.title = { display: true, text: 'Average Sharpe range (best date minus worst)' };
    charts.cal && charts.cal.destroy();
    charts.cal = new Chart($('calChart'), { type: 'bar', data: { labels: cal.map(c => c.frequency), datasets: [{ data: cal.map(c => c.avg_sharpe_range_across_dates), backgroundColor: css('--accent'), borderRadius: 2, maxBarThickness: 64 }] }, options: o });
  }

  function drawLegs(src, id) {
    const col = { Overnight: css('--bad'), Daytime: css('--good'), 'Buy and hold': css('--bh') };
    const o = base(); o.scales.x.grid.display = false; o.scales.y.min = 40; o.scales.y.max = 220;
    o.scales.y.ticks.callback = v => money(v);
    o.plugins.tooltip = { callbacks: { label: i => i.dataset.label + ': ' + money(i.raw) } };
    const legs = Object.keys(col).map(l => ({ l, pts: D.legs[src + '|' + l] }));
    const labels = ['start'].concat(legs[0].pts.map(p => p[0])).map(x => x === 'start' ? '' : x);
    charts[id] && charts[id].destroy();
    charts[id] = new Chart($(id), {
      type: 'line',
      data: { labels, datasets: legs.map(({ l, pts }) => ({ label: l, data: [100].concat(pts.map(p => p[1])), borderColor: col[l], backgroundColor: col[l], borderWidth: 2.5, pointRadius: 0, tension: 0.15 })) },
      options: o
    });
  }

  function drawAll() { drawMoney(); drawLuck(); drawCal(); drawLegs('Free provider', 'freeChart'); drawLegs('Exchange futures', 'exChart'); }

  function seg(id, attr, cb) {
    $(id).addEventListener('click', e => {
      const b = e.target.closest('button'); if (!b) return;
      $(id).querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
      cb(b.dataset[attr]);
    });
  }
  seg('costSeg', 'c', v => { cost = +v; drawMoney(); });
  seg('screenSeg', 'f', v => { screenFilter = v; screenTable(); });

  moneyTable(); screenTable();
  if (window.Chart) drawAll();
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  mq.addEventListener && mq.addEventListener('change', () => window.Chart && drawAll());
  new MutationObserver(() => window.Chart && drawAll()).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
})();
