"""
23_dept_site.py -- build the departments page (departments.html), the
field-level companion to the main dashboard, in the charlescrabtree.org house
style: Cormorant Garamond display, Barlow body, JetBrains Mono labels, navy
accent, light paper, square corners.

Reads ~/uniranks/work_dept/dept_latent_scores.csv and dept_item_parameters.csv,
embeds a compact JSON (top 400 institutions per field by latest theta,
2-decimal quantisation, rank credible intervals included) and writes
~/uniranks/out/departments.html.
"""
import json
import os

import numpy as np
import pandas as pd

W = os.path.expanduser("~/uniranks/work_dept")
OUT = os.path.expanduser("~/uniranks/out")
os.makedirs(OUT, exist_ok=True)
PINNED = "Monash University"
TOP_PER_FIELD = 400

sc = pd.read_csv(f"{W}/dept_latent_scores.csv")
it = pd.read_csv(f"{W}/dept_item_parameters.csv")
HAS_RANK_CI = "rank_q025" in sc.columns

CATEGORY = {"AS01": "Natural Sciences", "AS02": "Engineering",
            "AS03": "Life Sciences", "AS04": "Medical Sciences",
            "AS05": "Social Sciences", "THEA": "Humanities"}

fields = []
for (fc, fn), g in sc.groupby(["field_code", "field_name"]):
    years = sorted(g.year.unique().tolist())
    latest = g[g.year == years[-1]]
    keep = set(latest.sort_values("theta_mean", ascending=False)
               .head(TOP_PER_FIELD).inst_id)
    pin = g[g.inst_name == PINNED]
    if len(pin):
        keep |= set(pin.inst_id)
    g = g[g.inst_id.isin(keep)]
    insts = []
    for iid, gi in g.groupby("inst_id"):
        gi = gi.set_index("year").reindex(years)
        m = [None if pd.isna(v) else round(float(v), 2) for v in gi.theta_mean]
        s = [None if pd.isna(v) else round(float(v), 2) for v in gi.theta_sd]
        rk = [None if pd.isna(v) else int(v) for v in gi.rank_in_year]
        nl = [0 if pd.isna(v) else int(v) for v in gi.n_listings]
        rec = dict(n=None, c=None, m=m, s=s, r=rk, l=nl)
        if HAS_RANK_CI:
            rec["rl"] = [None if pd.isna(v) else int(v) for v in gi.rank_q025]
            rec["rh"] = [None if pd.isna(v) else int(v) for v in gi.rank_q975]
        row = gi.dropna(subset=["inst_name"]).iloc[-1]
        rec["n"] = row.inst_name
        rec["c"] = None if pd.isna(row.country) else row.country
        insts.append(rec)
    insts.sort(key=lambda r: -(r["m"][-1] if r["m"][-1] is not None else -99))
    sy = it[it.field_code == fc]
    fields.append(dict(
        code=fc, name=fn, cat=CATEGORY.get(fc[:4], "Other"), years=years,
        systems=[dict(s=r.system, rel=round(float(r.reliability), 2))
                 for r in sy.itertuples()],
        insts=insts))

fields.sort(key=lambda f: (f["cat"], f["name"]))
DATA = json.dumps(dict(fields=fields, pinned=PINNED), separators=(",", ":"))

HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Departmental standing: latent measures by field</title>
<meta name="description" content="Subject-level university rankings pooled with the same dynamic Bayesian latent-trait model.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=JetBrains+Mono:wght@400;600&family=Barlow:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap">
<style>
:root{
  --paper:#ffffff; --paper-2:#f4f5fa; --ink:#0c0c12; --ink-2:#24243a; --ink-3:#4c4c63;
  --rule:#bcbdd0; --rule-2:#e3e4ee; --accent:#143a63; --accent-2:#2f6ba6;
  --s1:#143a63; --s2:#c2571f; --s3:#177a55; --s4:#a97b00;
  --s5:#a04b74; --s6:#4a7a1e; --s7:#5747a7; --s8:#a53434;
  --serif:'Cormorant Garamond',Georgia,serif;
  --sans:'Barlow',system-ui,sans-serif;
  --mono:'JetBrains Mono','SF Mono',monospace;
  color-scheme:light;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
 font:16px/1.62 var(--sans);font-weight:400}
.page{max-width:1040px;margin:0 auto;padding:56px 26px 96px}
.col{max-width:680px}
h1{font-family:var(--serif);font-size:44px;line-height:1.12;font-weight:600;
 letter-spacing:-.01em;margin:0 0 16px}
.byline{color:var(--ink-2);font-size:14.5px;margin:0 0 8px}
.byline a{color:inherit}
.tabs{font-family:var(--mono);font-size:12px;letter-spacing:.08em;
 text-transform:uppercase;margin:0 0 30px}
.tabs a{color:var(--ink-3);text-decoration:none;border-bottom:0;padding:3px 0;margin-right:18px}
.tabs a:hover{color:var(--accent)}
.tabs b{color:var(--accent);font-weight:600;margin-right:18px;
 border-bottom:2px solid var(--accent);padding-bottom:3px}
.lede{font-size:17.5px;line-height:1.62;margin:0 0 12px}
p{margin:0 0 14px}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid rgba(20,58,99,.35);padding-bottom:.5px}
a:hover{color:var(--accent-2)}
section{padding-top:38px;margin-top:38px;border-top:1px solid var(--rule)}
h2{font-family:var(--mono);font-size:12.5px;font-weight:600;letter-spacing:.1em;
 text-transform:uppercase;color:var(--accent);margin:0 0 10px}
h2 .num{color:var(--ink-3);font-weight:400;margin-right:10px}
.note{color:var(--ink-2);font-size:14.5px;margin:0 0 22px;max-width:70ch}
.small{font-size:13.5px;color:var(--ink-3)}
svg{display:block;width:100%;overflow:visible}
button,select,input{font:inherit;color:inherit}
input[type=text],input:not([type]),select{background:transparent;border:0;
 border-bottom:1px solid var(--rule);padding:5px 2px;font-size:14.5px;color:var(--ink);border-radius:0}
input:focus,select:focus{outline:0;border-bottom-color:var(--accent)}
.ctl{display:flex;gap:22px;flex-wrap:wrap;align-items:baseline;margin-bottom:20px;
 font-size:14px;color:var(--ink-2)}
.ctl label{display:inline-flex;gap:7px;align-items:baseline}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:6px 12px 6px 0;border-bottom:1px solid var(--rule-2);vertical-align:baseline}
thead th{font-family:var(--mono);color:var(--ink-3);font-weight:400;font-size:10.5px;
 letter-spacing:.08em;text-transform:uppercase;border-bottom:1px solid var(--rule)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;padding-right:18px}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover td{background:var(--paper-2)}
.scroll{max-height:480px;overflow:auto}
.ci{display:inline-block;height:2px;background:var(--accent);vertical-align:middle}
.tags{display:flex;gap:5px 16px;flex-wrap:wrap;margin:0 0 18px;font-size:13.5px}
.tag{display:inline-flex;align-items:center;gap:6px;color:var(--ink-2);white-space:nowrap}
.tag i{width:16px;height:2px;display:inline-block;flex:none}
.tag button{background:none;border:0;cursor:pointer;color:var(--ink-3);font-size:15px;padding:0}
.spark{width:110px;height:22px;display:inline-block;vertical-align:middle}
footer{margin-top:46px;padding-top:26px;border-top:1px solid var(--rule);
 color:var(--ink-3);font-size:13.5px;max-width:74ch}
@media (max-width:620px){.page{padding:34px 18px 70px}h1{font-size:32px}}
</style></head><body>
<div class="page">
<header class="col">
 <h1>Departmental standing</h1>
 <p class="byline">Charles Crabtree · Monash University · <span id="dateline"></span></p>
 <p class="tabs"><a href="index.html">Universities</a> <b>Departments</b>
   <a href="methods.html">Methods</a></p>
 <p class="lede">The same measurement model as the university page, fit separately
 within each academic field: every subject ranking is a noisy, censored instrument
 reading a department's underlying standing. Departments borrow strength from their
 university's overall position, with a per-field loading estimated from the data.</p>
 <p class="small" id="scope"></p>
 <p class="small">Units are one first-year standard deviation <i>within the field</i>.
 Compare institutions and years inside a field; do not compare levels across fields.
 Fields covered by a single instrument are smoothed estimates of that instrument, and
 the intervals say so honestly.</p>
</header>

<section>
 <h2><span class="num">1</span>Standings</h2>
 <div class="ctl">
  <label>Field <select id="fsel"></select></label>
  <label>Year <select id="ysel"></select></label>
  <label>Find <input id="q" placeholder="institution"></label>
 </div>
 <p class="note" id="fnote"></p>
 <div class="scroll"><table id="tbl"></table></div>
</section>

<section>
 <h2><span class="num">2</span>Trajectories</h2>
 <p class="note" id="trajnote"></p>
 <div class="ctl">
  <label>Show
   <select id="ymode">
     <option value="theta">latent θ</option>
     <option value="rank">rank within field</option>
   </select></label>
 </div>
 <div class="tags" id="tags"></div>
 <figure><svg id="traj" viewBox="0 0 660 330"></svg></figure>
</section>

<section>
 <h2><span class="num">3</span>Institution profile</h2>
 <p class="note">One university across every field it reaches. Ranks are within-field,
 with the 95% credible interval in brackets; the sparkline is the rank trajectory
 (up is better). Click a field name to open it above.</p>
 <div class="ctl">
  <label>Institution <input id="prof" list="profdl" placeholder="type a name" style="min-width:260px"></label>
  <datalist id="profdl"></datalist>
 </div>
 <div class="scroll"><table id="proftbl"></table></div>
</section>

<footer>
 <p>Sources: ShanghaiRanking Global Ranking of Academic Subjects (2017–2025, 57
 subjects, via the public JSON API), Times Higher Education subject tables
 (2020–2026 editions, via the public ranking-table JSON), the CWTS Leiden Ranking
 main fields (official edition files, 2015–2023, PP top 10% with a 100-publication
 floor), and QS World University Rankings by Subject where recovered. Broad fields
 are attached to their constituent narrow fields; the concordances and their
 construct caveats are in the repo (DEPARTMENTS.md, code/20_dept_ingest.py).</p>
 <p>Estimates: dept_latent_scores.csv.gz · parameters: dept_item_parameters.csv ·
 <a href="index.html">university page</a> · <a href="methods.html">methods note</a>.</p>
</footer>
</div>
<script>
const D=__DATA__;
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const COLS=['--s1','--s2','--s3','--s4','--s5','--s6','--s7','--s8'];
const cvar=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
$('dateline').textContent=new Date().toISOString().slice(0,10);
let F=D.fields[0],extra=[];
const fsel=$('fsel');
let lastCat='';
for(const [k,f] of D.fields.entries()){
  if(f.cat!==lastCat){const og=document.createElement('optgroup');og.label=f.cat;fsel.appendChild(og);lastCat=f.cat;}
  const o=document.createElement('option');o.value=k;o.textContent=f.name;
  fsel.lastChild.appendChild(o);
}
const wanted=location.hash.replace('#','');
const byCode=D.fields.findIndex(f=>f.code===wanted);
const polisci=D.fields.findIndex(f=>/Political/.test(f.name));
fsel.value=byCode>=0?byCode:(polisci>=0?polisci:0);F=D.fields[+fsel.value];
$('scope').textContent=D.fields.length+' fields · '+
  D.fields.reduce((a,f)=>a+f.insts.length,0).toLocaleString()+' department series';
function setYears(){
  const y=$('ysel');y.innerHTML='';
  for(const yr of F.years){const o=document.createElement('option');o.value=yr;o.textContent=yr;y.appendChild(o);}
  y.value=F.years[F.years.length-1];
}
function yIdx(){return F.years.indexOf(+$('ysel').value);}
function note(){
  const sys=F.systems.map(s=>s.s+' (reliability '+s.rel.toFixed(2)+')').join(', ');
  $('fnote').textContent=F.name+' · instruments: '+sys+
   (F.systems.length<2?' — single instrument: read these as smoothed '+F.systems[0].s+' standings.':'');
}
function table(){
  const t=yIdx(),q=($('q').value||'').toLowerCase();
  let rows=F.insts.filter(r=>r.m[t]!=null&&(!q||r.n.toLowerCase().includes(q)));
  rows.sort((a,b)=>b.m[t]-a.m[t]);
  const mmax=Math.max(...rows.map(r=>r.m[t])),mmin=Math.min(...rows.map(r=>r.m[t]));
  const hasCI=rows.length&&rows[0].rl;
  let h='<thead><tr><th class="n">#</th>'+(hasCI?'<th class="n">95% rank</th>':'')+
    '<th>Institution</th><th>Country</th>'+
    '<th class="n">θ</th><th class="n">±95%</th><th></th><th class="n">listings</th></tr></thead><tbody>';
  rows.forEach((r,k)=>{
    const w=Math.max(2,60*(r.m[t]-mmin)/(mmax-mmin||1));
    h+='<tr data-n="'+esc(r.n)+'"><td class="n">'+(k+1)+'</td>'+
      (hasCI?'<td class="n small">'+(r.rl[t]!=null?r.rl[t]+'–'+r.rh[t]:'')+'</td>':'')+
      '<td>'+esc(r.n)+'</td><td>'+esc(r.c||'')+'</td><td class="n">'+r.m[t].toFixed(2)+
      '</td><td class="n">'+(1.96*r.s[t]).toFixed(2)+'</td>'+
      '<td><span class="ci" style="width:'+w+'px"></span></td>'+
      '<td class="n">'+r.l[t]+'</td></tr>';
  });
  $('tbl').innerHTML=h+'</tbody>';
  $('tbl').querySelectorAll('tbody tr').forEach(tr=>{
    tr.style.cursor='pointer';
    tr.onclick=()=>{const n=tr.dataset.n;if(!extra.includes(n)){extra.push(n);draw();}};
  });
}
function series(){
  const t=F.years.length-1;
  const base=F.insts.filter(r=>r.m[t]!=null).slice(0,5).map(r=>r.n);
  for(const n of extra)if(!base.includes(n))base.push(n);
  if(!base.includes(D.pinned)&&F.insts.some(r=>r.n===D.pinned))base.push(D.pinned);
  return base.slice(0,8).map(n=>F.insts.find(r=>r.n===n)).filter(Boolean);
}
function draw(){
  const S=series(),svg=$('traj'),W=660,H=330,P={l:44,r:8,t:12,b:26};
  const xs=F.years,X=v=>P.l+(v-xs[0])/(xs[xs.length-1]-xs[0]||1)*(W-P.l-P.r);
  const rankMode=$('ymode').value==='rank';
  const hasCI=S.length&&S[0].rl;
  $('trajnote').textContent=rankMode
    ?'Top five in the latest year, plus any institution added from the table (click a '+
     'row). Rank within the field implied by the model each year, on a logarithmic '+
     'axis so movement near the top is visible.'+(hasCI?' The band is the 95% '+
     'credible interval of the first series’ rank.':'')
    :'Top five in the latest year, plus any institution added from the table (click a '+
     'row). The band is the 95% credible interval for the first series.';
  let g='',Y;
  if(rankMode){
    let rv=[];S.forEach(r=>{r.r.forEach(v=>{if(v!=null)rv.push(v);});
      if(hasCI&&r===S[0])r.rh.forEach(v=>{if(v!=null)rv.push(v);});});
    const rlo=Math.max(1,Math.min(...rv)),rhi=Math.max(...rv);
    const L=v=>Math.log(v),span=L(rhi)-L(rlo)||1;
    Y=v=>P.t+(L(Math.max(1,v))-L(rlo))/span*(H-P.t-P.b);
    [1,2,5,10,20,50,100,200,500,1000,2000].filter(v=>v>=rlo&&v<=rhi).forEach(v=>{
      g+='<line x1="'+P.l+'" x2="'+(W-P.r)+'" y1="'+Y(v)+'" y2="'+Y(v)+'" stroke="var(--rule-2)"/>'+
         '<text x="'+(P.l-6)+'" y="'+(Y(v)+4)+'" text-anchor="end" font-size="11" font-family="var(--mono)" fill="var(--ink-3)">'+v+'</text>';
    });
  }else{
    let vals=[];S.forEach(r=>r.m.forEach((v,i)=>{if(v!=null){vals.push(v+1.96*(r.s[i]||0));vals.push(v-1.96*(r.s[i]||0));}}));
    const lo=Math.min(...vals),hi=Math.max(...vals);
    Y=v=>P.t+(hi-v)/(hi-lo||1)*(H-P.t-P.b);
    for(let v=Math.ceil(lo*2)/2;v<=hi;v+=0.5){
      g+='<line x1="'+P.l+'" x2="'+(W-P.r)+'" y1="'+Y(v)+'" y2="'+Y(v)+'" stroke="var(--rule-2)"/>'+
         '<text x="'+(P.l-6)+'" y="'+(Y(v)+4)+'" text-anchor="end" font-size="11" font-family="var(--mono)" fill="var(--ink-3)">'+v.toFixed(1)+'</text>';
    }
  }
  xs.forEach(x=>{g+='<text x="'+X(x)+'" y="'+(H-6)+'" text-anchor="middle" font-size="11" font-family="var(--mono)" fill="var(--ink-3)">'+x+'</text>';});
  S.forEach((r,k)=>{
    const col=cvar(COLS[k%COLS.length]);
    const vals=rankMode?r.r:r.m;
    if(k===0){
      let band='',back='';
      if(rankMode&&hasCI){
        xs.forEach((x,i)=>{if(r.rl[i]!=null)band+=(band?'L':'M')+X(x)+' '+Y(r.rl[i])+' ';});
        for(let i=xs.length-1;i>=0;i--)if(r.rh[i]!=null)back+='L'+X(xs[i])+' '+Y(r.rh[i])+' ';
      }else if(!rankMode){
        xs.forEach((x,i)=>{if(r.m[i]!=null)band+=(band?'L':'M')+X(x)+' '+Y(r.m[i]+1.96*r.s[i])+' ';});
        for(let i=xs.length-1;i>=0;i--)if(r.m[i]!=null)back+='L'+X(xs[i])+' '+Y(r.m[i]-1.96*r.s[i])+' ';
      }
      if(band)g+='<path d="'+band+back+'Z" fill="'+col+'" opacity="0.10"/>';
    }
    let p='';
    xs.forEach((x,i)=>{if(vals[i]!=null)p+=(p?'L':'M')+X(x)+' '+Y(vals[i])+' ';});
    g+='<path d="'+p+'" fill="none" stroke="'+col+'" stroke-width="1.8"/>';
    xs.forEach((x,i)=>{if(r.l[i]>0&&vals[i]!=null)g+='<circle cx="'+X(x)+'" cy="'+Y(vals[i])+'" r="2.4" fill="'+col+'"/>';});
  });
  svg.innerHTML=g;
  $('tags').innerHTML=S.map((r,k)=>'<span class="tag"><i style="background:'+cvar(COLS[k%COLS.length])+'"></i>'+
    esc(r.n)+(extra.includes(r.n)?' <button data-n="'+esc(r.n)+'">×</button>':'')+'</span>').join('');
  $('tags').querySelectorAll('button').forEach(b=>b.onclick=()=>{extra=extra.filter(n=>n!==b.dataset.n);draw();});
}

// ---------- institution profile
const INST={};
D.fields.forEach((f,fi)=>f.insts.forEach(r=>{(INST[r.n]=INST[r.n]||[]).push([fi,r]);}));
const dl=$('profdl');
Object.keys(INST).sort().forEach(n=>{const o=document.createElement('option');o.value=n;dl.appendChild(o);});
function spark(f,r){
  const xs=f.years,w=110,h=22,pad=2;
  const vals=xs.map((_,i)=>r.r[i]);
  const fin=vals.filter(v=>v!=null);
  if(fin.length<2)return '';
  const lo=Math.min(...fin),hi=Math.max(...fin);
  const X=i=>pad+i/(xs.length-1||1)*(w-2*pad);
  const Y=v=>pad+(Math.log(v)-Math.log(Math.max(1,lo)))/((Math.log(hi)-Math.log(Math.max(1,lo)))||1)*(h-2*pad);
  let p='';
  vals.forEach((v,i)=>{if(v!=null)p+=(p?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1)+' ';});
  return '<svg class="spark" viewBox="0 0 '+w+' '+h+'"><path d="'+p+
    '" fill="none" stroke="var(--accent)" stroke-width="1.4"/></svg>';
}
function profile(){
  const name=$('prof').value;
  const hits=INST[name];
  if(!hits){$('proftbl').innerHTML='';return;}
  const rows=hits.map(([fi,r])=>{
    const f=D.fields[fi],t=f.years.length-1;
    return {f,fi,r,rank:r.r[t],rl:r.rl?r.rl[t]:null,rh:r.rh?r.rh[t]:null,
            th:r.m[t],yr:f.years[t]};
  }).filter(x=>x.rank!=null).sort((a,b)=>a.rank-b.rank);
  let h='<thead><tr><th>Field</th><th class="n">Year</th><th class="n">Rank</th>'+
    '<th class="n">95% rank</th><th class="n">θ</th><th>Trend</th></tr></thead><tbody>';
  rows.forEach(x=>{
    h+='<tr><td><a href="#'+x.f.code+'" data-fi="'+x.fi+'" class="pf">'+esc(x.f.name)+'</a></td>'+
      '<td class="n">'+x.yr+'</td><td class="n">'+x.rank+'</td>'+
      '<td class="n small">'+(x.rl!=null?x.rl+'–'+x.rh:'')+'</td>'+
      '<td class="n">'+x.th.toFixed(2)+'</td><td>'+spark(x.f,x.r)+'</td></tr>';
  });
  $('proftbl').innerHTML=h+'</tbody>';
  $('proftbl').querySelectorAll('a.pf').forEach(a=>a.onclick=e=>{
    e.preventDefault();
    fsel.value=a.dataset.fi;F=D.fields[+a.dataset.fi];
    history.replaceState(null,'','#'+F.code);refresh();
    document.querySelector('section').scrollIntoView({behavior:'smooth'});
  });
}
$('prof').onchange=profile;
if(INST[D.pinned]){$('prof').value=D.pinned;profile();}

function refresh(){note();setYears();table();extra=[];draw();}
fsel.onchange=()=>{F=D.fields[+fsel.value];history.replaceState(null,'','#'+F.code);refresh();};
$('ysel').onchange=()=>{table();};
$('q').oninput=()=>table();
$('ymode').onchange=()=>draw();
note();setYears();table();draw();
</script></body></html>"""

html = HTML.replace("__DATA__", DATA)
open(f"{OUT}/departments.html", "w").write(html)
print(f"wrote departments.html ({os.path.getsize(f'{OUT}/departments.html')/1e6:.2f} MB), "
      f"{len(fields)} fields, rank CIs: {HAS_RANK_CI}")
