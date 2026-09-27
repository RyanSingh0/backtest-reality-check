"""Puts the static dashboard together: web/ pieces + web/data.json -> docs/index.html (served by GitHub Pages).

Run after export_web.py whenever the database changes.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
W = ROOT / 'web'
head = (W / 'page_head.html').read_text(encoding='utf-8')
body = (W / 'page_body.html').read_text(encoding='utf-8')
script = (W / 'page_script.js').read_text(encoding='utf-8')
data = json.loads((W / 'data.json').read_text(encoding='utf-8'))

page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="Two backtest audits (U.S. Dollar Index and commodity futures) explained for non-technical readers.">\n'
        + head + '</head>\n<body>\n' + body
        + '<script>window.__DATA__=' + json.dumps(data, separators=(',', ':')) + ';</script>\n'
        + '<script>' + script + '</script>\n</body>\n</html>\n')
(ROOT / 'docs').mkdir(exist_ok=True)
(ROOT / 'docs' / 'index.html').write_text(page, encoding='utf-8')
print('docs/index.html', len(page), 'bytes')
