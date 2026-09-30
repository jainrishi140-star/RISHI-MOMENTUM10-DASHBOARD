const fs=require('fs');
const {Document,Packer,Paragraph,TextRun,Table,TableRow,TableCell,ImageRun,HeadingLevel,AlignmentType,WidthType,ShadingType,BorderStyle,LevelFormat,PageBreak,Footer,PageNumber,TableOfContents}=require('docx');
const W=9906;
const png=f=>{const b=fs.readFileSync(f);return [b.readUInt32BE(16),b.readUInt32BE(20)]};
const img=(f,wpx=640,cap)=>{const [w,h]=png(f);const out=[new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:120,after:60},children:[new ImageRun({type:'png',data:fs.readFileSync(f),transformation:{width:wpx,height:Math.round(wpx*h/w)},altText:{title:f,description:cap||f,name:f}})]})];
 if(cap) out.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:200},children:[new TextRun({text:cap,italics:true,size:18,color:'52514E'})]}));return out};
const P=(t,o={})=>new Paragraph({spacing:{after:120},...o,children:(Array.isArray(t)?t:[t]).map(x=>typeof x==='string'?new TextRun({text:x,size:21}):x)});
const B=t=>new TextRun({text:t,bold:true,size:21});
const H1=t=>new Paragraph({heading:HeadingLevel.HEADING_1,children:[new TextRun(t)]});
const H2=t=>new Paragraph({heading:HeadingLevel.HEADING_2,children:[new TextRun(t)]});
const bl=(t)=>new Paragraph({numbering:{reference:'b',level:0},spacing:{after:80},children:(Array.isArray(t)?t:[t]).map(x=>typeof x==='string'?new TextRun({text:x,size:21}):x)});
const bd={style:BorderStyle.SINGLE,size:4,color:'C9C8C0'};const borders={top:bd,bottom:bd,left:bd,right:bd};
function table(head,rows,cw,opt={}){
 const cell=(t,i,hd,shade)=>new TableCell({borders,width:{size:cw[i],type:WidthType.DXA},margins:{top:50,bottom:50,left:90,right:90},
  shading:hd?{type:ShadingType.CLEAR,fill:'1F2A44',color:'auto'}:(shade?{type:ShadingType.CLEAR,fill:shade,color:'auto'}:undefined),
  children:[new Paragraph({alignment:i===0||opt.left?AlignmentType.LEFT:AlignmentType.CENTER,children:[new TextRun({text:String(t),size:opt.size||18,bold:hd||i===0&&opt.boldFirst,color:hd?'FFFFFF':'0B0B0B'})]})]});
 return new Table({width:{size:cw.reduce((a,b)=>a+b),type:WidthType.DXA},columnWidths:cw,rows:[new TableRow({tableHeader:true,children:head.map((h,i)=>cell(h,i,true))}),
  ...rows.map((r,ri)=>new TableRow({cantSplit:true,children:r.map((c,i)=>cell(c,i,false,ri%2?'F4F3EF':null))}))]});}
const sp=()=>new Paragraph({spacing:{after:120},children:[]});
const pb=()=>new Paragraph({children:[new PageBreak()]});

const c=[];
c.push(new Paragraph({spacing:{before:1400,after:120},children:[new TextRun({text:'SSR Nifty Trend-Following Options',size:26,color:'52514E'})]}));
c.push(new Paragraph({spacing:{after:200},children:[new TextRun({text:'Live Performance Evaluation',bold:true,size:56})]}));
c.push(new Paragraph({spacing:{after:120},children:[new TextRun({text:'Live (with hedge / without hedge) vs SSR model signal log vs Backtest (2019-2025)',size:26})]}));
c.push(new Paragraph({spacing:{after:80},children:[new TextRun({text:'Live window: 1 Apr 2025 - 30 Sep 2026   |   Basis: option points (capital-independent)',size:20,color:'52514E'})]}));
c.push(new Paragraph({spacing:{after:400},children:[new TextRun({text:'Prepared for internal strategy review',size:20,color:'52514E'})]}));
c.push(H1('1. Executive summary'));
c.push(P([B('Bottom line: '),'over the 18 live months the strategy did not improve on the backtest. Live earns a fraction of the backtest point-rate, with deeper drawdowns and far weaker return-to-drawdown. The SSR model log itself shows the same shortfall, so the gap comes mainly from the signal, not from live execution.']));
[
 [B('Points earned. '),'Live unhedged +1,044 pts (58/month), live with hedge +577 pts (32/month), SSR model +1,088 pts (61/month), versus a backtest average of 156 pts/month.'],
 [B('Live as a share of backtest. '),'Avg monthly points: 37% (unhedged) and 21% (hedged). Return / max drawdown: 0.73 and 0.50 versus 13.47, i.e. about 5% and 4%.'],
 [B('Drawdown. '),'Max drawdown -1,422 pts (unhedged) and -1,155 pts (hedged) versus -777 pts in the backtest. The drawdown began at the 27 Jan 2026 peak; unhedged took 231 days to recover, hedged had not fully recovered by 30 Sep 2026.'],
 [B('The one tail event. '),'3 Feb 2026 produced a single-trade loss of -798 pts (backtest worst: -318). The hedge returned +221 pts that day, cutting the worst day to -576 pts. Excluding that one trade, unhedged live would show +1,842 pts (about 102/month, 65% of backtest rate).'],
 [B('Hedge economics. '),'The hedge book made -467 pts in total (16% win rate on 256 legs); excluding 3 Feb it lost -689 pts. It reduced max drawdown by about 19% but lowered return / drawdown (0.73 to 0.50).'],
 [B('Fidelity to the SSR model. '),'259 of 278 live trades match a model trade; per-trade points correlate 0.99 and average execution slippage is only -0.6 pts per trade (-164 pts cumulative). Live is 44 pts behind the model in total.'],
 [B('Periods with no live trades. '),'Zubin\'s sabbatical leave for CFA (17 Jul - 2 Sep 2025 and 30 Apr - 24 May 2026) and discretionary shorts skipped (5 - 17 Mar 2026). The model made +155, +370 and -553 pts in those windows respectively, net -28 pts, so these gaps were close to neutral overall but concentrated risk in the timing (see section 6).'],
].forEach(t=>c.push(bl(t)));
c.push(pb());
c.push(H1('2. Data and methodology'));
[
 [B('Sources. '),'Workbook with three sheets: live trade log without hedge (278 trades), hedge trade log (256 legs, all "Audi" strategy), and the SSR TFO model log (383 trades from 20 Jan 2025). Backtest statistics come from the with-hedge results table supplied (2019-2025).'],
 [B('Points basis. '),'All comparisons use option points, so differences in capital and lot sizing do not distort results. Live and model trade P&L is net points per trade.'],
 [B('Hedge normalisation. '),'Hedge quantity was sometimes 2x-2.3x the live quantity (e.g. 13,910 and 15,730 vs 6,955). Hedge P&L is therefore converted to live-quantity-equivalent points (rupee hedge P&L divided by the live quantity on that date) so hedged equity = live points + hedge points on a like-for-like lot.'],
 [B('Common window. '),'The model log starts 20 Jan 2025 but live starts 1 Apr 2025, so the model is rebased to 1 Apr 2025. The model log ends 25 Sep 2026; live has one extra trade (29 Sep, +33 pts). The hedge started 6 May 2025; before that hedged = unhedged.'],
 [B('Equity and drawdown. '),'Cumulative points are realised on the trade exit date. Drawdown is measured from the running peak of that curve, closed-trade basis.'],
 [B('Trade matching. '),'Live trades were matched to model trades by strike, option type, entry date (within 3 days) and entry price (within 12 pts, then 50 pts for leftovers).'],
 [B('Backtest convention. '),'The backtest counts each hedge as a separate trade (so trades, wins and losses are about double, and win rate is diluted). Live "with hedge" statistics are shown in the same convention. The backtest\'s reported max loss (-318) excludes the hedge; net of the hedge day gain it is -178.'],
 [B('Data quality. '),'11 date typos were corrected and 2 live trades have no exit date (Appendix A). The log\'s own cumulative columns were recomputed from Net Points because they do not tie out in places.'],
].forEach(t=>c.push(bl(t)));
c.push(pb());
c.push(H1('3. Backtest (2019-2025) vs live: full scorecard'));
c.push(P('All columns in points. Backtest is the with-hedge run (hedge legs counted as separate trades). Live with-hedge uses the same convention; SSR model is unhedged over the same 1 Apr 2025 - 25 Sep 2026 window.'));
const hd=['Metric','Backtest (hedged) 2019-25','Live unhedged','Live with hedge','SSR model (unhedged)'];
const cw=[2400,1900,1800,1900,1906];
const rows=[
['Win trades','1,038','140','181','161'],['Loss trades','1,290','138','352','167'],['Total trades','2,328','278','534','329'],
['Win rate','45%','50.4%','33.9%','48.9%'],['Total profit (pts)','43,426','10,825','11,560','12,397'],['Total loss (pts)','-32,960','-9,781','-10,984','-11,309'],
['Total P&L (pts)','10,466','1,044','577','1,088'],['Risk/Reward (gross loss / gross profit)','0.76','0.90','0.95','0.91'],['Profit factor','1.32','1.11','1.05','1.10'],
['Avg profit (pts)','42','77','64','77'],['Avg loss (pts)','-26','-71','-31','-68'],['Expectancy per trade (net / trades)','4.5 (sheet states 33)','3.75','1.08','3.31'],
['Max profit (pts)','231','305','305','304'],['Max loss, single trade (pts)','-318 (-178 net of hedge)','-798','-798 (-576 net of hedge, same day)','-768'],
['Avg monthly profit (pts)','156','58','32','61'],['Max drawdown (pts)','-777','-1,422','-1,155','-1,183'],
['Max drawdown duration (days)','191 (22 Feb - 1 Sep 2021)','231 (27 Jan - 15 Sep 2026)','246+ (not recovered)','84 (27 Jan - 21 Apr 2026)'],
['Return / max drawdown','13.47','0.73','0.50','0.92'],['Max winning streak','6','9','7','7'],['Max losing streak','11','6','8','9'],
['Positive months','n/a','13 of 18','13 of 18','13 of 18'],
];
c.push(table(hd,rows,cw,{boldFirst:true}));
c.push(sp());
c.push(P([B('Note on expectancy. '),'The backtest sheet lists expectancy of 33, but its own totals give 10,466 / 2,328 = 4.5 pts per trade (or 9.0 per base trade). The figure of 33 does not reconcile and should be checked before it is quoted.']));
c.push(H2('3.1 How much has live improved on the backtest?'));
c.push(P('Measured against the backtest, live has not improved on the core return and risk measures. The table shows live as a percentage of the backtest value; a higher figure is better for return metrics and a lower figure is better for risk metrics.'));
c.push(table(['Measure','Backtest','Live unhedged','Live hedged','Live / backtest (unh | hedged)','Verdict'],[
['Avg monthly points','156','58','32','37% | 21%','Weaker'],
['Return / max DD','13.47','0.73','0.50','5% | 4%','Much weaker'],
['Max drawdown','777','1,422','1,155','183% | 149%','Worse'],
['Max DD duration (days)','191','231','246+','121% | 129%+','Worse'],
['Avg loss','-26','-71','-31','273% | 120%','Worse'],
['Avg profit','42','77','64','183% | 152%','Better'],
['Max losing streak','11','6','8','55% | 73%','Better'],
['Worst single trade','-318','-798','-576 (net)','251% | 181%','Worse'],
],[2000,1100,1300,1300,2206,2000]));
c.push(sp());
c.push(P('Areas that are better: average winning trade is larger (77 vs 42 pts) and the longest losing streak is shorter (6-8 vs 11). But average loss size is almost 3x the backtest (71 vs 26 pts unhedged), which cancels the larger winners. Profit factor fell from 1.32 to about 1.1.'));
c.push(P([B('Context for a fair reading. '),'Live covers 18 months (about 15 trades a month, similar to the backtest\'s roughly 17 base trades a month) against about 67 months in the backtest, so one event such as 3 Feb 2026 weighs heavily. Still, the SSR model log, which is not affected by live execution, shows the same shortfall (61 pts a month, return / drawdown 0.92). Live months with a positive result: 13 of 18, in line with the model.']));
c.push(...img('backtest_vs_live.png',640,'Figure 1. Backtest vs live: monthly points, return/drawdown, max drawdown, win rate'));
c.push(pb());
c.push(H1('4. Live with hedge vs without hedge'));
c.push(...img('equity_and_drawdown.png',640,'Figure 2. Equity curve and drawdown: live unhedged, live hedged and SSR model (points)'));
c.push(table(['Measure','Live unhedged','Live with hedge','Change'],[
['Net points','1,044','577','-467'],['Max drawdown (pts)','-1,422','-1,155','+267 (19% smaller)'],['Return / max DD','0.73','0.50','-0.23'],
['Worst single day (pts)','-798','-576','+222'],['Avg monthly points','58','32','-26'],['Profit factor','1.11','1.05','-0.06'],
['Best month','+476','+415',''],['Worst month','-1,073 (Feb-26)','-902 (Feb-26)','+171'],
],[3000,2300,2300,2306]));
c.push(sp());
c.push(P([B('Hedge-era comparison (from 6 May 2025, when hedging began): '),'unhedged +1,084 pts, max DD -1,422, return/DD 0.76; hedged +617 pts, max DD -1,155, return/DD 0.53; SSR model +1,063 pts, max DD -1,183, return/DD 0.90.']));
c.push(...img('hedge_pnl.png',640,'Figure 3. Hedge book alone, cumulative live-quantity points'));
[
 [B('Cost. '),'256 hedge legs, 16% win rate, net -467 pts (-430 pts on raw unweighted points). Excluding the +221 pt event on 3 Feb 2026, the hedge lost -689 pts, about -4 pts per leg.'],
 [B('Benefit. '),'One event paid back +221 pts. It reduced the worst day from -798 to -576 and cut max drawdown by 267 pts.'],
 [B('Break-even. '),'At the present bleed rate the hedge needs about 2.1 events of the size of 3 Feb 2026 to pay for itself over this window; on a return-per-drawdown basis it has not yet added value. It functions as insurance: it lowers tail loss but costs about 26 pts a month.'],
 [B('Backtest comparison. '),'In the backtest the hedge offset the worst trade by 140 pts (-318 to -178). Live, the worst trade was 2.5x larger and the hedge offset was 221 pts, leaving a net -576 pts, about 3.2x the backtest hedged max loss.'],
].forEach(t=>c.push(bl(t)));
c.push(pb());
c.push(H1('5. Live vs SSR model signal log'));
c.push(P('Of the 278 live trades, 259 matched a model trade. The model has 329 trades in the comparison window (exit on or after 1 Apr 2025).'));
c.push(table(['Component','Trades','Points'],[
['Model net points (1 Apr 2025 - 25 Sep 2026)','329','+1,088'],['Live unhedged net points','278','+1,044'],['Total gap (live - model)','','-44'],
['  Execution on matched trades (live - model)','259','-164'],['  Live-only trades (mostly different strike / early exit)','19','-383'],['  Model trades not taken by live','70','+503 (live avoided -503)'],
],[5400,1700,2806],{left:false}));
c.push(sp());
[
 'Execution: the average matched trade differs by -0.6 pts (median -0.5), 69% of matched trades are within 5 pts, and correlation of trade points is 0.99. Live is tracking the signal closely on the trades it takes.',
 'Largest per-trade deviations: 2 Mar 2026 (live 185 vs model 266, exited 4 Mar rather than 10 Mar, -81), 30 Mar 2026 (-44), 29 Apr 2026 (live -39.5 vs model -185, +145, open trade with no exit logged), 24 Sep 2026 (+83).',
 'Skipped or unmatched trades mostly reflect the flagged no-trade periods and a small number of strike substitutions (live-only trades), which largely offset each other.',
].forEach(t=>c.push(bl(t)));
c.push(...img('deviation_vs_model.png',640,'Figure 4. Live (unhedged) minus SSR model, cumulative points, with execution difference on matched trades'));
c.push(...img('matched_scatter.png',360,'Figure 5. Matched trades: live vs model points'));
c.push(...img('monthly_points.png',640,'Figure 6. Monthly points: live unhedged, live hedged, SSR model'));
c.push(H2('5.1 Monthly points'));
const mon=JSON.parse(fs.readFileSync('monthly.json'));
c.push(table(['Month','Live unhedged','Hedge','Live hedged','SSR model','Live - model'],mon.map(m=>[m.m,...[m.u,m.h,m.lh,m.s,m.d].map(v=>(v>0?'+':'')+Math.round(v).toLocaleString('en-US'))]),[1500,1700,1500,1700,1700,1806]));
c.push(pb());
c.push(H1('6. Flagged periods with no live trades'));
c.push(P('Three periods in the live log have no trades although the model kept signalling. They are flagged below with the reason supplied. Points are the SSR model result for trades that were not taken in the window.'));
c.push(table(['Period','Reason flagged','Model trades','Model wins','Model points not captured','Effect on live'],[
['17 Jul - 2 Sep 2025','Zubin\'s sabbatical leave (CFA)','27','14','+155','Missed profit'],
['5 - 17 Mar 2026','Discretionary shorts skipped','4','4','+370','Missed profit'],
['30 Apr - 24 May 2026','Zubin\'s sabbatical leave (CFA)','17','4','-553','Avoided loss'],
['Total','','48','22','-28','Approximately neutral'],
],[1900,2200,1100,1000,1806,1900]));
c.push(sp());
c.push(...img('flagged_periods.png',640,'Figure 7. Flagged periods over the SSR model and live unhedged equity curves'));
[
 'Net effect is only -28 model points, so the gaps did not change the overall result materially. Their effect on the path was large: the missed March 2026 rally in the model (+370 pts in four trades, all winners) coincided with the deepest live drawdown, and the pause from 30 Apr avoided a -553 pt stretch in which only 4 of 17 model trades won.',
 'Live was 800+ pts below the model at the end of April 2026, recovering most of it by mid-May 2026 purely by sitting out the weak stretch. This is luck of timing, not a systematic edge, and should not be extrapolated.',
 'Sabbatical periods leave the strategy unattended and exposed to whichever regime follows; the July - September 2025 gap missed +155 pts and the April - May 2026 gap avoided -553 pts, opposite results from the same cause.',
 'The 30 Apr 2026 open trade (24,300 PE) was logged at -39.5 pts without an exit; the model closed the same trade at -185. If it was actually closed at the model level, live would be about 145 pts lower. Please confirm.',
].forEach(t=>c.push(bl(t)));
c.push(pb());
c.push(H1('7. Conclusions and recommendations'));
[
 [B('Live has not beaten the backtest. '),'At 37% (unhedged) and 21% (hedged) of the backtest\'s monthly point-rate, with return / drawdown of 0.7 and 0.5 versus 13.5, the live period is materially weaker. The model\'s own results over the same window are equally weak (61 pts a month, 0.92), so this is a signal-performance question rather than an execution one.'],
 [B('Execution is not the problem. '),'Live tracks the model with 0.99 correlation and about -0.6 pts a trade of slippage. The largest gaps come from unattended periods and a few discretionary strike or exit choices.'],
 [B('Tail risk is the issue. '),'Loss size is the difference: average loss is 71 pts live versus 26 pts in the backtest, and one -798 pt trade equals roughly 2.5x the backtest worst case. Review stop / exit rules for expiry-day gaps.'],
 [B('The hedge is expensive insurance. '),'It cuts drawdown by 19% but costs about 26 pts a month and lowers return per unit of drawdown. Consider sizing or tenor changes, or hedging only around known event risk, and re-test on the backtest.'],
 [B('Operational cover. '),'Formal coverage for planned absences (as with the CFA leave) would remove discretionary timing from the live results; also close the logging gaps (two trades without exit dates, date typos).'],
 [B('Sample size. '),'18 months and about 278 trades is short compared with the backtest; a drawdown of 1,400 pts came from a single event. Re-evaluate after at least 12 more months, and report the results with and without the 3 Feb 2026 trade.'],
].forEach(t=>c.push(bl(t)));
c.push(H1('Appendix A. Data corrections applied'));
JSON.parse(fs.readFileSync('fixes.json')).forEach(t=>c.push(bl(t)));
c.push(P('Reproducible with analysis/ssr_analysis.py and analysis/report_data.py; full tables are in ssr_live_vs_model_analysis.xlsx.'));

const doc=new Document({creator:'Analysis',title:'SSR Live Performance Evaluation',
 styles:{default:{document:{run:{font:'Calibri',size:21}}},paragraphStyles:[
  {id:'Heading1',name:'Heading 1',basedOn:'Normal',next:'Normal',quickFormat:true,run:{size:32,bold:true,color:'1F2A44',font:'Calibri'},paragraph:{spacing:{before:240,after:160},outlineLevel:0}},
  {id:'Heading2',name:'Heading 2',basedOn:'Normal',next:'Normal',quickFormat:true,run:{size:25,bold:true,color:'2A78D6',font:'Calibri'},paragraph:{spacing:{before:200,after:120},outlineLevel:1}}]},
 numbering:{config:[{reference:'b',levels:[{level:0,format:LevelFormat.BULLET,text:'•',alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:540,hanging:270}}}}]}]},
 sections:[{properties:{page:{size:{width:11906,height:16838},margin:{top:1000,bottom:1000,left:1000,right:1000}}},
  footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new TextRun({text:'SSR live performance evaluation  |  page ',size:16,color:'8A8983'}),new TextRun({children:[PageNumber.CURRENT],size:16,color:'8A8983'})]})]})},
  children:c.filter(Boolean)}]});
Packer.toBuffer(doc).then(b=>{fs.writeFileSync('SSR_Live_Performance_Evaluation.docx',b);console.log('ok')});
