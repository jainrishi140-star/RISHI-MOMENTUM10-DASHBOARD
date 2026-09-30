"""Live (hedged / unhedged) vs SSR model, evaluated in option POINTS."""
import sys, json
import pandas as pd, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.dates as mdates

F = sys.argv[1]
OUT = '.'
T0 = pd.Timestamp('2025-04-01')            # first live trade -> common start
BLUE, ORANGE, AQUA, MAG = '#2a78d6', '#eb6834', '#1baf7a', '#e87ba4'

# ---------------- load & clean ----------------
L = pd.read_excel(F, sheet_name=0).iloc[:, :10]
H = pd.read_excel(F, sheet_name=1)
S = pd.read_excel(F, sheet_name=2, header=1).iloc[:, 1:10]
S.columns = ['Entry Date','Exit Date','Type','Strike','Expiry','EntryPx','ExitPx','Net','Cum']
fixes = []
def dt(v): return pd.to_datetime(v, errors='coerce')

L['Entry'] = L['Entry Date'].map(dt); L['Exit'] = L['Exit Date'].map(dt)
L['Type'] = L['Ce/Pe'].str.upper()
def fix(df, i, col, val, why):
    fixes.append(f"{why} (row {i+2}): {col} {df.at[i,col]} -> {val}"); df.at[i, col] = pd.Timestamp(val)
fix(L,111,'Entry','2025-11-10',"live: entry '10//11/25'")
fix(L,75,'Exit','2025-07-16',"live: exit date missing (matched to SSR log)")
fix(L,212,'Exit','2026-04-30',"live: exit date missing (open trade, -39.5 pts as logged; SSR exit was -185)")
fix(L,275,'Entry','2026-09-23',"live: year/month typo"); fix(L,275,'Exit','2026-09-24',"live: month typo")
fix(L,276,'Entry','2026-09-24',"live: month typo")
L['Pts'] = L['Net Points']; L['Qty'] = L['Qty'].astype(float)

H['Entry'] = H['Entry Date'].map(dt); H['Exit'] = H['Exit Date'].map(dt)
H['Type'] = H['Ce/Pe'].str.upper()
fix(H,11,'Exit','2025-05-27',"hedge: exit typo"); fix(H,112,'Entry','2026-01-01',"hedge: entry year typo")
fix(H,131,'Exit','2026-02-03',"hedge: exit month typo (the +221pt Budget-week hedge win)")
fix(H,238,'Exit','2026-09-02',"hedge: month typo"); fix(H,239,'Entry','2026-09-02',"hedge: month typo")
# normalise hedge to live-qty-equivalent points (hedge qty is sometimes 2x-2.3x live qty)
ref = L.sort_values('Entry').set_index('Entry')['Qty']; ref = ref[~ref.index.duplicated(keep='last')]
H['LiveQty'] = ref.reindex(ref.index.union(H['Exit'])).ffill().reindex(H['Exit']).values
H['Pts_eq'] = H['Pnl'] / H['LiveQty']
S['Entry'] = S['Entry Date'].map(dt); S['Exit'] = S['Exit Date'].map(dt); S['Pts'] = S['Net']
S = S[S['Exit'] >= T0].reset_index(drop=True)
for n, d in (('live', L), ('hedge', H), ('model', S)):
    bad = d[(d.Exit < d.Entry) | ((d.Exit - d.Entry).dt.days > 10)]
    assert bad.empty or n == 'model', (n, bad)

# ---------------- series ----------------
END = pd.Timestamp('2026-09-30')
days = pd.date_range(T0, END, freq='D')
def daily(df, col): return df.groupby('Exit')[col].sum().reindex(days, fill_value=0.0)
d_unh, d_hed, d_mod = daily(L,'Pts'), daily(H,'Pts_eq'), daily(S,'Pts')
d_hedraw = daily(H,'Net Points')
d_hedged = d_unh + d_hed
eq = pd.DataFrame({'Live unhedged': d_unh.cumsum(), 'Live hedged': d_hedged.cumsum(),
                   'SSR model': d_mod.cumsum(), 'Hedge P&L (live-qty pts)': d_hed.cumsum()})
def dd(c):
    c = c.copy(); base = pd.concat([pd.Series([0.0], index=[c.index[0]-pd.Timedelta(days=1)]), c])
    return (c - base.cummax().iloc[1:])
dds = pd.DataFrame({k: dd(eq[k]) for k in ['Live unhedged','Live hedged','SSR model']})

def dd_info(c):
    d = dd(c); trough = d.idxmin(); peak_c = c[:trough].cummax()
    peak_dt = c[:trough][c[:trough] == peak_c.iloc[-1]].index[-1]
    rec = c[trough:][c[trough:] >= peak_c.iloc[-1]]
    # longest underwater spell
    uw = (d < 0); grp = (uw != uw.shift()).cumsum(); best = (0, None, None)
    for _, g in uw.groupby(grp):
        if g.iloc[0] and len(g) > best[0]: best = (len(g), g.index[0], g.index[-1])
    return dict(maxdd=d.min(), peak=peak_dt, trough=trough, recovered=(rec.index[0] if len(rec) else None),
                longest_uw_days=best[0], uw_from=best[1], uw_to=best[2], cur_dd=d.iloc[-1])

def streaks(x):
    w = l = cw = cl = 0
    for v in x:
        if v > 0: cw += 1; cl = 0
        elif v < 0: cl += 1; cw = 0
        else: cw = cl = 0
        w, l = max(w, cw), max(l, cl)
    return w, l

def metrics(trades, cum, name):
    p = trades.sort_values('Exit')['Pts'].values
    win, loss = p[p > 0], p[p < 0]; net = p.sum(); info = dd_info(cum)
    months = (END - T0).days / 30.4375
    sw, sl = streaks(p)
    return {'Series': name, 'Trades': len(p), 'Wins': len(win), 'Losses': len(loss),
            'Win rate %': 100*len(win)/len(p), 'Gross profit': win.sum(), 'Gross loss': loss.sum(), 'Net pts': net,
            'Loss/Profit (BT "Risk/Reward")': -loss.sum()/win.sum(), 'Profit factor': win.sum()/-loss.sum(),
            'Avg win': win.mean(), 'Avg loss': loss.mean(), 'Expectancy/trade': net/len(p),
            'Max win': win.max(), 'Max loss': loss.min(), 'Avg monthly pts': net/months,
            'Max DD pts': info['maxdd'], 'Max DD trough': info['trough'].date(),
            'Longest underwater days': info['longest_uw_days'],
            'Underwater from': info['uw_from'].date(), 'Underwater to': info['uw_to'].date(),
            'Current DD': info['cur_dd'], 'Return/MaxDD': net/-info['maxdd'],
            'Max win streak': sw, 'Max loss streak': sl}

Lh = pd.concat([L[['Exit','Pts']], H[['Exit']].assign(Pts=H['Pts_eq'])])   # backtest convention: hedge legs = separate trades
m_unh = metrics(L, eq['Live unhedged'], 'Live - unhedged')
m_hed = metrics(Lh, eq['Live hedged'], 'Live - with hedge (hedge legs as separate trades)')
m_mod = metrics(S, eq['SSR model'], 'SSR model (no hedge), same window')
# hedge-era only (apples to apples): from first hedge exit
HE = H['Entry'].min()
Lp, Sp = L[L.Entry >= HE], S[S.Entry >= HE]
def sub(d, start): return d[start:]
eqh = pd.DataFrame({'Live unhedged': d_unh[HE:].cumsum(), 'Live hedged': d_hedged[HE:].cumsum(), 'SSR model': d_mod[HE:].cumsum()})
def hm(name, tr, c): 
    p = tr['Pts']; info = dd_info(c)
    return {'Series': name, 'Net pts': p.sum(), 'Max DD pts': info['maxdd'], 'Return/MaxDD': p.sum()/-info['maxdd'],
            'Worst day': c.diff().fillna(c.iloc[0]).min()}
hedge_era = pd.DataFrame([hm('Live unhedged', Lp, eqh['Live unhedged']),
                          hm('Live hedged', pd.concat([Lp[['Exit','Pts']], H[['Exit']].assign(Pts=H['Pts_eq'])]), eqh['Live hedged']),
                          hm('SSR model', Sp, eqh['SSR model'])])
hedge_era.insert(1, 'From', HE.date())

# hedge diagnostics
hd = H['Pts_eq']
hedge_diag = {'hedge legs': len(H), 'hedge win rate %': 100*(hd > 0).mean(), 'net hedge pts (live-qty)': hd.sum(),
              'net hedge pts (raw, unweighted)': H['Net Points'].sum(),
              'hedge pts excl. 2026-02-03 event': hd[H['Exit'] != '2026-02-03'].sum(),
              'best hedge day pts': d_hed.max(), 'best hedge day': str(d_hed.idxmax().date()),
              'avg bleed/hedge-leg excl. top-5': np.sort(hd.values)[:-5].mean()}

# ---------------- live vs model matching ----------------
Lm = L.copy(); Lm['id'] = range(len(Lm)); Sm = S.copy(); Sm['id'] = range(len(Sm))
pairs, used, lused = [], set(), set()
for dmax, pmax in ((3, 12), (3, 50)):            # strict pass, then looser price tolerance for leftovers
    for _, r in Lm[~Lm.id.isin(lused)].sort_values('Entry').iterrows():
        c = Sm[(~Sm.id.isin(used)) & (Sm.Strike == r.Strike) & (Sm.Type == r.Type) &
               ((Sm.Entry - r.Entry).abs().dt.days <= dmax) & ((Sm.EntryPx - r['Entry Price']).abs() <= pmax)].copy()
        if len(c):
            c['k'] = (c.Entry - r.Entry).abs().dt.days*100 + (c.EntryPx - r['Entry Price']).abs()
            j = c.sort_values('k').iloc[0]; used.add(j.id); lused.add(r.id)
            pairs.append(dict(live_id=r.id, model_id=j.id, entry=r.Entry, live_exit=r.Exit, model_exit=j.Exit, strike=r.Strike, type=r.Type,
                              live_entry_px=r['Entry Price'], model_entry_px=j.EntryPx, live_pts=r.Pts, model_pts=j.Pts))
P = pd.DataFrame(pairs); P['diff'] = P.live_pts - P.model_pts
P['entry_slip'] = P.live_entry_px - P.model_entry_px          # shorts: + = better fill than model
live_only = Lm[~Lm.id.isin(P.live_id)]
model_only = Sm[~Sm.id.isin(P.model_id)]
model_end = S['Exit'].max()
live_only_in, live_only_after = live_only[live_only.Exit <= model_end], live_only[live_only.Exit > model_end]
def gap_label(d):
    if d.Entry < pd.Timestamp('2025-09-03') and d.Entry > pd.Timestamp('2025-07-10'): return 'Jul17-Sep02 2025 (no live trades)'
    if pd.Timestamp('2026-03-05') <= d.Entry < pd.Timestamp('2026-03-18'): return 'Mar 5-17 2026 (no live trades)'
    if pd.Timestamp('2026-04-30') <= d.Entry < pd.Timestamp('2026-05-25'): return 'Apr30-May24 2026 (no live trades)'
    return 'other (isolated skips)'
model_only = model_only.assign(gap=model_only.apply(gap_label, axis=1))
gap_tab = model_only.groupby('gap')['Pts'].agg(['count', 'sum']).rename(columns={'count': 'model trades not in live', 'sum': 'model pts not captured'})
dev = {'model trades': len(S), 'live trades': len(L), 'matched': len(P),
       'model-only (live missed)': len(model_only), 'model-only pts': model_only.Pts.sum(),
       'live-only trades': len(live_only), 'live-only pts': live_only.Pts.sum(),
       'matched: live pts': P.live_pts.sum(), 'matched: model pts': P.model_pts.sum(), 'matched: execution diff pts': P['diff'].sum(),
       'matched: avg diff/trade': P['diff'].mean(), 'matched: median diff': P['diff'].median(), 'matched: std of diff': P['diff'].std(),
       'matched: avg entry-price slippage (+=better)': P.entry_slip.mean(),
       'matched: % within +-5pts': 100*(P['diff'].abs() <= 5).mean(), 'matched: corr(live,model)': P.live_pts.corr(P.model_pts),
       'live net (all)': L.Pts.sum(), 'model net (all)': S.Pts.sum(), 'total gap live-model': L.Pts.sum() - S.Pts.sum(),
       '  from execution on matched': P['diff'].sum(), '  from live-only trades': live_only.Pts.sum(), '  from model trades not taken': -model_only.Pts.sum()}

# monthly table
mon = pd.DataFrame({'Live unhedged': d_unh, 'Hedge': d_hed, 'Live hedged': d_hedged, 'SSR model': d_mod}).resample('MS').sum()
mon.index = mon.index.strftime('%b-%y'); mon['Live-Model (unh)'] = mon['Live unhedged'] - mon['SSR model']

# ---------------- outputs ----------------
summary = pd.DataFrame([m_unh, m_hed, m_mod]).set_index('Series').T
with pd.ExcelWriter(f'{OUT}/ssr_live_vs_model_analysis.xlsx') as xw:
    summary.to_excel(xw, sheet_name='Summary'); hedge_era.to_excel(xw, sheet_name='Hedge-era compare', index=False)
    pd.Series(dev).to_frame('value').to_excel(xw, sheet_name='Deviation vs model'); gap_tab.to_excel(xw, sheet_name='Missed by period')
    pd.Series(hedge_diag).to_frame('value').to_excel(xw, sheet_name='Hedge diagnostics')
    mon.round(1).to_excel(xw, sheet_name='Monthly'); P.to_excel(xw, sheet_name='Matched trades', index=False)
    model_only[['Entry','Exit','Type','Strike','Pts','gap']].to_excel(xw, sheet_name='Model-only (missed)', index=False)
    live_only[['Entry','Exit','Type','Strike','Pts']].to_excel(xw, sheet_name='Live-only', index=False)
    pd.concat([eq, dds.add_suffix(' DD')], axis=1).to_excel(xw, sheet_name='Daily equity & DD')
    pd.Series(fixes).to_frame('data fixes applied').to_excel(xw, sheet_name='Data fixes')

# charts
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True,
                     'grid.color': '#e6e5e0', 'grid.linewidth': .6, 'axes.edgecolor': '#b5b4ad'})
def style(ax): ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%y')); ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ev = pd.Timestamp('2026-02-03')
fig, ax = plt.subplots(2, 1, figsize=(13, 9), sharex=True, gridspec_kw={'height_ratios': [1.25, 1]})
for k, c, ls in (('Live unhedged', BLUE, '-'), ('Live hedged', ORANGE, '-'), ('SSR model', '#8a8983', '--')):
    ax[0].plot(eq.index, eq[k], color=c, lw=2, ls=ls, label=f"{k}  ({eq[k].iloc[-1]:,.0f} pts)")
    ax[1].plot(dds.index, dds[k], color=c, lw=2, ls=ls, label=f"{k}  (max DD {dds[k].min():,.0f})")
ax[1].fill_between(dds.index, dds['Live unhedged'], 0, color=BLUE, alpha=.08)
ax[0].axvline(HE, color='#b5b4ad', lw=1, ls=':'); ax[0].text(HE, ax[0].get_ylim()[1]*.02, ' hedge starts', color='#52514e', fontsize=9)
ax[0].annotate('3-Feb-26 gap: live -798, hedge +221', (ev, eq.loc[ev,'Live unhedged']), (ev - pd.Timedelta(days=130), 900),
               arrowprops=dict(arrowstyle='-', color='#52514e'), fontsize=9, color='#52514e')
ax[0].set_title('Cumulative points (realised on exit date), from 1-Apr-25', loc='left', fontweight='bold'); ax[0].set_ylabel('Points')
ax[1].set_title('Drawdown from running peak (points)', loc='left', fontweight='bold'); ax[1].set_ylabel('Points')
for a in ax: a.legend(loc='upper left' if a is ax[0] else 'lower left', frameon=False); style(a)
plt.tight_layout(); plt.savefig(f'{OUT}/equity_and_drawdown.png', dpi=140); plt.close()

fig, ax = plt.subplots(2, 1, figsize=(13, 7.5), sharex=True)
gap = eq['Live unhedged'] - eq['SSR model']; gap[model_end + pd.Timedelta(days=1):] = np.nan  # model log ends 25-Sep
ax[0].plot(gap.index, gap, color=BLUE, lw=2); ax[0].axhline(0, color='#52514e', lw=.8)
ax[0].set_title('Live (unhedged) minus SSR model, cumulative points  (drops = model trades live did not take / worse fills)', loc='left', fontweight='bold')
for lo, hi, t in (('2025-07-17','2025-09-02','no live trades'), ('2026-03-05','2026-03-17','no live trades'), ('2026-04-30','2026-05-24','no live trades')):
    for a in ax: a.axvspan(pd.Timestamp(lo), pd.Timestamp(hi), color='#eb6834', alpha=.10, lw=0)
    ax[0].text(pd.Timestamp(lo)+pd.Timedelta(days=2), gap.min()*.98, t, fontsize=8, color='#52514e', rotation=90, va='bottom')
ex = pd.Series(0.0, index=days)
for _, r in P.iterrows(): ex[r.live_exit] += r['diff']
ax[1].bar(ex.index, ex.cumsum().diff().fillna(0), color=AQUA, width=1.5)
ax[1].set_title('Execution difference on matched trades (live pts - model pts), by exit date', loc='left', fontweight='bold')
ax[1].plot(ex.index, ex.cumsum(), color='#0b0b0b', lw=1.5, label=f'cumulative ({P["diff"].sum():+.0f} pts)'); ax[1].legend(frameon=False, loc='upper left')
for a in ax: style(a)
plt.tight_layout(); plt.savefig(f'{OUT}/deviation_vs_model.png', dpi=140); plt.close()

fig, ax = plt.subplots(figsize=(13, 4.2))
ax.plot(eq.index, eq['Hedge P&L (live-qty pts)'], color=MAG, lw=2, label=f"Hedge P&L cumulative ({eq['Hedge P&L (live-qty pts)'].iloc[-1]:,.0f} pts)")
ax.axhline(0, color='#52514e', lw=.8); ax.set_title('Hedge book alone (live-qty-equivalent points)', loc='left', fontweight='bold'); ax.legend(frameon=False, loc='upper left'); style(ax)
plt.tight_layout(); plt.savefig(f'{OUT}/hedge_pnl.png', dpi=140); plt.close()

pd.set_option('display.width', 250); pd.set_option('display.float_format', lambda v: f'{v:,.2f}')
print(summary.to_string()); print(hedge_era.to_string()); print(json.dumps({k:(round(v,2) if isinstance(v,float) else v) for k,v in dev.items()}, indent=1, default=str))
print(gap_tab); print(json.dumps({k:(round(v,2) if isinstance(v,float) else v) for k,v in hedge_diag.items()}, indent=1)); print(mon.round(0).to_string())
print('\n'.join(fixes)); print(live_only.assign(x=live_only.Exit)[['Entry','Exit','Type','Strike','Pts']].to_string())
print(P.sort_values('diff').head(5)[['entry','strike','live_pts','model_pts','diff']]); print(P.sort_values('diff').tail(5)[['entry','strike','live_pts','model_pts','diff']])
