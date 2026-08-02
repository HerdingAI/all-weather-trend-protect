"""rate_regime_test.py -- how do the books behave when yields RISE?

The recommendation leans on gold and long duration. Long duration is the one
sleeve with an obvious enemy: rising rates. 2022 is the only stocks-and-bonds-
together episode in the panel, so this widens the question to EVERY sustained
rising-rate episode since 1985, identified from the 10y yield rather than
assumed.

Episodes are defined mechanically: months where the 10y yield is more than
50bp above its level 12 months earlier, grouped into runs of >=6 months.

This is a CONDITIONAL stress test, NOT a forecast. It answers 'what happened
last time yields rose', not 'what will yields do'.

KEY LIMITATION: the window is 1985-2026, which is a DISINFLATIONARY era. Every
episode here is a cyclical blip inside a secular downtrend. The 1970s -- the
only true secular inflation regime -- can be tested for GOLD alone, because
Long Treasuries start 1986-06. That is open-questions Q3.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import candidates as C  # noqa: E402

H = os.path.dirname(os.path.abspath(__file__)) + '/'
p=pd.read_csv(H+'output/study_panel.csv',index_col=0,parse_dates=True)
tnx=pd.read_csv(H+'output/monthly_prices.csv',index_col=0,parse_dates=True)['^TNX'].dropna()

# 12-month change in the 10y yield, in percentage POINTS
chg=(tnx-tnx.shift(12)).dropna()
rising = chg[chg>0.5]      # yields up more than 50bp over 12m
print(f'10y yield {tnx.index.min():%Y-%m}..{tnx.index.max():%Y-%m}: '
      f'{tnx.iloc[0]:.2f}% -> {tnx.iloc[-1]:.2f}%')
print(f'months with 12m yield rise > +0.5pp: {len(rising)} of {len(chg)} ({100*len(rising)/len(chg):.0f}%)')

# contiguous rising-rate episodes
flag=(chg>0.5)
grp=(flag!=flag.shift()).cumsum()
eps=[(g.index.min(),g.index.max()) for k,g in flag.groupby(grp) if g.iloc[0] and len(g)>=6]
print(f'\nsustained episodes (>=6 months):')
for a,b in eps: print(f'   {a:%Y-%m} .. {b:%Y-%m}  ({(b.to_period("M")-a.to_period("M")).n+1} mo, '
                      f'yield {tnx[a]:.2f} -> {tnx[b]:.2f})')

def cum(w,idx):
    a=list(w); sub=p.loc[idx]
    if any(x not in sub.columns for x in a) or sub[a].isna().any().any(): return None
    r=sum(sub[x]*v for x,v in w.items()); return ((1+r).prod()-1)*100

print('\n'+'='*92)
print('BOOK RETURNS IN EACH SUSTAINED RISING-RATE EPISODE')
print('='*92)
names=['Current allocation','80/20 VTI-GLD','70/15/15 eq-gold-dur','60/20/20 eq-gold-dur',
       '50/25/25 eq-gold-dur','60/20/20 eq-gold-agg','Classic 60/40','100% US Total']
hdr=f"{'episode':22s}"+''.join(f'{n.split()[0][:9]:>10s}' for n in names)
print(hdr)
allrows={n:[] for n in names}
for a,b in eps:
    idx=p.loc[a:b].index
    row=f'{a:%Y-%m}..{b:%Y-%m}   '
    for n in names:
        v=cum(C.CANDIDATES[n],idx)
        row+=f'{v:9.1f}%' if v is not None else '       n/a'
        if v is not None: allrows[n].append(v)
    print(row)
print()
print(f"{'AVG of episodes':22s}"+''.join(f'{np.mean(allrows[n]):9.1f}%' if allrows[n] else '       n/a' for n in names))
print(f"{'WORST episode':22s}"+''.join(f'{min(allrows[n]):9.1f}%' if allrows[n] else '       n/a' for n in names))

# sleeve behaviour in rising rates
print('\n'+'='*92); print('SLEEVE BEHAVIOUR, all months with 12m yield rise > +0.5pp'); print('='*92)
idx=p.index.intersection(rising.index)
for c in ['US Total Market','Long Treasuries','US Aggregate Bonds','Gold','Intl Developed','US Small Value','PM Equity']:
    s=p[c].reindex(idx).dropna()
    if len(s)<24: continue
    ann=((1+s).prod()**(12/len(s))-1)*100
    print(f'  {c:20s} n={len(s):3d}  annualised {ann:+6.2f}%  hit rate {100*(s>0).mean():4.0f}%')
