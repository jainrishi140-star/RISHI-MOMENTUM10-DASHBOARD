import sys, runpy, json
F='/root/.claude/uploads/6e1e2ec9-2d1c-5e62-af43-648d665ca3ee/1ca5f93a-SSR_log-_Live_vs_log.xlsx'
sys.argv=['x',F]
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()): g=runpy.run_path('ssr_analysis.py')
import pandas as pd, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, matplotlib.dates as mdates
eq,dds,mon,P,S,L,H,d_unh,d_hed,d_hedged,d_mod=[g[k] for k in 'eq dds mon P S L H d_unh d_hed d_hedged d_mod'.split()]
BLUE,ORANGE,GREY,AQUA='#2a78d6','#eb6834','#8a8983','#1baf7a'
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.color':'#e6e5e0','grid.linewidth':.6,'axes.edgecolor':'#b5b4ad'})
# DD episode (peak -> recovery) for max DD
def episode(c):
    i=g['dd_info'](c); end=i['recovered'] or c.index[-1]
    return i['peak'].date(), i['trough'].date(), (i['recovered'].date() if i['recovered'] else 'not recovered'), (end-i['peak']).days
ep={k:episode(eq[k]) for k in ['Live unhedged','Live hedged','SSR model']}
months=(g['END']-g['T0']).days/30.4375
out={'ep':{k:[str(x) for x in v] for k,v in ep.items()},'months':months,
 'pos_months':{k:int((mon[k]>0).sum()) for k in ['Live unhedged','Live hedged','SSR model']},'n_months':len(mon),
 'best_month':{k:float(mon[k].max()) for k in ['Live unhedged','Live hedged','SSR model']},
 'worst_month':{k:float(mon[k].min()) for k in ['Live unhedged','Live hedged','SSR model']}}
# excluding 2 largest single-day event: Feb-26
for k in ['Live unhedged','Live hedged','SSR model']: pass
out['unh_ex_feb3']=float(L.Pts.sum()+797.8)
json.dump(out,open('/tmp/claude-0/-home-user-RISHI-MOMENTUM10-DASHBOARD/6e1e2ec9-2d1c-5e62-af43-648d665ca3ee/scratchpad/extra.json','w'),indent=1,default=str)
print(json.dumps(out,indent=1,default=str))

def fmt(ax): ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%y')); ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
# 1 metric comparison: backtest (hedged, 2019-25) vs live
m_u,m_h,m_m=g['m_unh'],g['m_hed'],g['m_mod']
bt={'Avg monthly points':156,'Return / max DD':13.47,'Max drawdown (pts)':777,'Win rate %':45}
liv={'Avg monthly points':(m_u['Avg monthly pts'],m_h['Avg monthly pts'],m_m['Avg monthly pts']),
     'Return / max DD':(m_u['Return/MaxDD'],m_h['Return/MaxDD'],m_m['Return/MaxDD']),
     'Max drawdown (pts)':(-m_u['Max DD pts'],-m_h['Max DD pts'],-m_m['Max DD pts']),
     'Win rate %':(m_u['Win rate %'],m_h['Win rate %'],m_m['Win rate %'])}
fig,axs=plt.subplots(1,4,figsize=(14,4))
labs=['Backtest\n(hedged)','Live\nunhedged','Live\nhedged','SSR\nmodel']; cols=['#0b0b0b',BLUE,ORANGE,GREY]
for ax,(k,v) in zip(axs,bt.items()):
    vals=[v,*liv[k]]; b=ax.bar(range(4),vals,color=cols,width=.62)
    for r,x in zip(b,vals): ax.text(r.get_x()+r.get_width()/2,r.get_height(),f'{x:,.1f}' if x<100 else f'{x:,.0f}',ha='center',va='bottom',fontsize=9)
    ax.set_xticks(range(4)); ax.set_xticklabels(labs,fontsize=8); ax.set_title(k,loc='left',fontweight='bold',fontsize=10); ax.grid(axis='x',visible=False); ax.set_ylim(0,max(vals)*1.15)
plt.tight_layout(); plt.savefig('backtest_vs_live.png',dpi=140); plt.close()
# 2 monthly bars
fig,ax=plt.subplots(figsize=(13,4.6)); x=np.arange(len(mon)); w=.28
for i,(k,c) in enumerate((('Live unhedged',BLUE),('Live hedged',ORANGE),('SSR model',GREY))): ax.bar(x+(i-1)*w,mon[k],w,color=c,label=k)
ax.axhline(0,color='#52514e',lw=.8); ax.set_xticks(x); ax.set_xticklabels(mon.index,rotation=45,fontsize=8); ax.legend(frameon=False,ncol=3,loc='lower left'); ax.grid(axis='x',visible=False)
ax.set_title('Monthly points (by exit date)',loc='left',fontweight='bold'); plt.tight_layout(); plt.savefig('monthly_points.png',dpi=140); plt.close()
# 3 flagged periods
fl=[('2025-07-17','2025-09-02','Sabbatical leave\n(CFA) - Zubin','#eb6834'),('2026-03-05','2026-03-17','Discretionary\nshorts skipped','#8a3ffc'),('2026-04-30','2026-05-24','Sabbatical leave\n(CFA) - Zubin','#eb6834')]
fig,ax=plt.subplots(figsize=(13,4.8))
ax.plot(eq.index,eq['SSR model'],color=GREY,lw=2,ls='--',label='SSR model'); ax.plot(eq.index,eq['Live unhedged'],color=BLUE,lw=2,label='Live unhedged')
top=eq['SSR model'].max()
for lo,hi,t,c in fl:
    ax.axvspan(pd.Timestamp(lo),pd.Timestamp(hi),color=c,alpha=.15,lw=0); ax.text(pd.Timestamp(lo)+(pd.Timestamp(hi)-pd.Timestamp(lo))/2,top*1.02,t,ha='center',va='bottom',fontsize=8)
ax.set_ylim(top=top*1.2); ax.legend(frameon=False,loc='lower right'); fmt(ax); ax.set_title('Periods with no live trades (flagged) vs SSR model',loc='left',fontweight='bold',y=1.0)
plt.tight_layout(); plt.savefig('flagged_periods.png',dpi=140); plt.close()
# 4 scatter
fig,ax=plt.subplots(figsize=(5.6,5.4)); ax.scatter(P.model_pts,P.live_pts,s=14,color=BLUE,alpha=.7); lim=[-820,320]; ax.plot(lim,lim,color='#52514e',lw=.8)
ax.set_xlabel('SSR model points per trade'); ax.set_ylabel('Live points per trade'); ax.set_title(f'Matched trades (n={len(P)}), corr={P.live_pts.corr(P.model_pts):.2f}',loc='left',fontweight='bold'); plt.tight_layout(); plt.savefig('matched_scatter.png',dpi=140); plt.close()
# flagged period table data
for lo,hi,t,c in fl:
    lo,hi=pd.Timestamp(lo),pd.Timestamp(hi); mo=g['model_only']; sel=mo[(mo.Entry>=lo)&(mo.Entry<=hi)]
    print(t.replace('\n',' '),lo.date(),hi.date(),len(sel),round(sel.Pts.sum(),1), 'model wins',int((sel.Pts>0).sum()))
