"""Makes research_public.db, the copy of research.db that is safe to put on GitHub.

The only raw vendor series in the database is the BCOMTR benchmark's monthly return, so I drop it.
Everything else is results I computed (strategy returns, test statistics, screen counts).
"""
import shutil
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
src, dst = HERE / 'research.db', HERE / 'research_public.db'
shutil.copy(src, dst)
con = sqlite3.connect(dst)
con.execute("DELETE FROM fact_benchmark_monthly WHERE benchmark = 'BCOMTR buy and hold'")
con.commit()
con.execute('VACUUM')
con.close()
print(dst.name, round(dst.stat().st_size / 1e6, 1), 'MB')
