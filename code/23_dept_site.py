"""
23_dept_site.py -- build the departments page (departments.html), the
field-level companion to the main dashboard. Same design language: single
column, hairline rules, ink and paper, no cards.

Reads ~/uniranks/work_dept/dept_latent_scores.csv and dept_item_parameters.csv,
embeds a compact JSON (top 400 institutions per field by latest theta,
2-decimal quantisation) and writes ~/uniranks/out/departments.html.
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
        nl = [0 if pd.isna(v) else int(v) for v in gi.n_listings]
        row = gi.dropna(subset=["inst_name"]).iloc[-1]
        insts.append(dict(n=row.inst_name, c=None if pd.isna(row.country) else row.country,
                          m=m, s=s, l=nl))
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
<title>Departmental standing: latent measures by field, 2016–2025</title>
<meta name="description" content="Subject-level university rankings pooled with the same dynamic Bayesian latent-trait model.">
<style>
:root{
  --paper:#fffefb; --ink:#16150f; --ink-2:#4a4841; --ink-3:#807d73;
  --rule:#dcd9cf; --rule-2:#efece3;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100;
  --s5:#e87ba4; --s6:#008300; --s7:#4a3aa7; --s8:#e34948;
  color-scheme:light;
}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){
  --paper:#141310; --ink:#f4f2ea; --ink-2:#b7b4a8; --ink-3:#84817a;
  --rule:#3a382f; --rule-2:#26241e;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
  --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
  color-scheme:dark;}}
:root[data-theme="dark"]{
  --paper:#141310; --ink:#f4f2ea; --ink-2:#b7b4a8; --ink-3:#84817a;
  --rule:#3a382f; --rule-2:#26241e;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
  --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
  color-scheme:dark;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
 font:16px/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.page{max-width:1040px;margin:0 auto;padding:56px 26px 96px}
.col{max-width:660px}
h1{font-size:29px;line-height:1.24;font-weight:600;letter-spacing:-.015em;margin:0 0 14px}
.byline{color:var(--ink-2);font-size:14.5px;margin:0 0 26px}
.byline a{color:inherit}
.lede{font-size:17px;line-height:1.66;margin:0 0 10px}
p{margin:0 0 14px}
a{color:var(--s1);text-decoration:none;border-bottom:1px solid currentColor;padding-bottom:.5px}
a:hover{color:var(--ink)}
section{padding-top:38px;margin-top:38px;border-top:1px solid var(--rule)}
h2{font-size:15px;font-weight:600;margin:0 0 6px}
h2 .num{color:var(--ink-3);font-variant-numeric:tabular-nums;margin-right:10px;font-weight:400}
.note{color:var(--ink-2);font-size:14.5px;margin:0 0 22px;max-width:66ch}
.small{font-size:13.5px;color:var(--ink-3)}
svg{display:block;width:100%;overflow:visible}
button,select,input{font:inherit;color:inherit}
input[type=text],input:not([type]),select{background:transparent;border:0;
 border-bottom:1px solid var(--rule);padding:5px 2px;font-size:14.5px;color:var(--ink);border-radius:0}
input:focus,select:focus{outline:0;border-bottom-color:var(--s1)}
.ctl{display:flex;gap:22px;flex-wrap:wrap;align-items:baseline;margin-bottom:20px;
 font-size:14px;color:var(--ink-2)}
.ctl label{display:inline-flex;gap:7px;align-items:baseline}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:6px 12px 6px 0;border-bottom:1px solid var(--rule-2);vertical-align:baseline}
thead th{color:var(--ink-3);font-weight:500;font-size:12.5px;letter-spacing:.03em;border-bottom:1px solid var(--rule)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;padding-right:18px}
tbody tr:last-child td{border-bottom:0}
.scroll{max-height:480px;overflow:auto}
.ci{display:inline-block;height:2px;background:var(--s1);vertical-align:middle}
.tags{display:flex;gap:5px 16px;flex-wrap:wrap;margin:0 0 18px;font-size:13.5px}
.tag{display:inline-flex;align-items:center;gap:6px;color:var(--ink-2);white-space:nowrap}
.tag i{width:16px;height:2px;display:inline-block;flex:none}
.tag button{background:none;border:0;cursor:pointer;color:var(--ink-3);font-size:15px;padding:0}
footer{margin-top:46px;padding-top:26px;border-top:1px solid var(--rule);
 color:var(--ink-3);font-size:13.5px;max-width:72ch}
.mode{background:none;border:0;cursor:pointer;color:var(--ink-3);font-size:13.5px;
 padding:0;border-bottom:1px solid var(--rule)}
@media (max-width:620px){.page{padding:34px 18px 70px}h1{font-size:24px}}
</style></head><body>
<div class="page">
<header class="col">
 <h1>Departmental standing: a latent measure by field</h1>
 <p class="byline">Charles Crabtree · Monash University · <span id="dateline"></span> ·
   <button class="mode" id="tbtn">switch theme</button></p>
 <p class="byline" style="margin-top:-16px"><a href="index.html">Universities</a> ·
   <b>Departments</b> · <a href="methods.html">Methods</a></p>
 <p class="lede">The same measurement model as the university page, fit separately
 within each academic field: every subject ranking is a noisy, censored instrument
 reading a department's underlying standing.</p>
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
 <p class="note">Top five in the latest year, plus any institution added from the
 table (click a row). The band is the 95% credible interval for the first series.</p>
 <div class="tags" id="tags"></div>
 <figure><svg id="traj" viewBox="0 0 660 330"></svg></figure>
</section>

<footer>
 <p>Sources: ShanghaiRanking Global Ranking of Academic Subjects (2017–2025, 57
 subjects, via the public JSON API), Times Higher Education subject tables
 (2020–2026 editions, 11 broad subjects, via the public ranking-table JSON), and
 the CWTS Leiden Ranking main fields (official edition files, 2015–2023, PP top
 10% with a 100-publication floor). Broad THE and Leiden fields are attached to
 their constituent narrow fields; the concordances and their construct caveats
 are in the repo (DEPARTMENTS.md, code/20_dept_ingest.py).</p>
 <p>Estimates: dept_latent_scores.csv · parameters: dept_item_parameters.csv ·
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
const polisci=D.fields.findIndex(f=>/Political/.test(f.name));
fsel.value=polisci>=0?polisci:0;F=D.fields[+fsel.value];
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
  let h='<thead><tr><th class="n">#</th><th>Institution</th><th>Country</th>'+
    '<th class="n">θ</th><th class="n">±95%</th><th></th><th class="n">listings</th></tr></thead><tbody>';
  rows.forEach((r,k)=>{
    const w=Math.max(2,60*(r.m[t]-mmin)/(mmax-mmin||1));
    h+='<tr data-n="'+esc(r.n)+'"><td class="n">'+(k+1)+'</td><td>'+esc(r.n)+'</td><td>'+
      esc(r.c||'')+'</td><td class="n">'+r.m[t].toFixed(2)+'</td><td class="n">'+
      (1.96*r.s[t]).toFixed(2)+'</td><td><span class="ci" style="width:'+w+'px"></span></td>'+
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
  const S=series(),svg=$('traj'),W=660,H=330,P={l:40,r:8,t:12,b:26};
  const xs=F.years,X=v=>P.l+(v-xs[0])/(xs[xs.length-1]-xs[0]||1)*(W-P.l-P.r);
  let vals=[];S.forEach(r=>r.m.forEach((v,i)=>{if(v!=null){vals.push(v+1.96*(r.s[i]||0));vals.push(v-1.96*(r.s[i]||0));}}));
  const lo=Math.min(...vals),hi=Math.max(...vals);
  const Y=v=>P.t+(hi-v)/(hi-lo||1)*(H-P.t-P.b);
  let g='';
  for(let v=Math.ceil(lo*2)/2;v<=hi;v+=0.5){
    g+='<line x1="'+P.l+'" x2="'+(W-P.r)+'" y1="'+Y(v)+'" y2="'+Y(v)+'" stroke="var(--rule-2)"/>'+
       '<text x="'+(P.l-6)+'" y="'+(Y(v)+4)+'" text-anchor="end" font-size="11" fill="var(--ink-3)">'+v.toFixed(1)+'</text>';
  }
  xs.forEach(x=>{g+='<text x="'+X(x)+'" y="'+(H-6)+'" text-anchor="middle" font-size="11" fill="var(--ink-3)">'+x+'</text>';});
  S.forEach((r,k)=>{
    const col=cvar(COLS[k%COLS.length]);
    if(k===0){
      let band='',back='';
      xs.forEach((x,i)=>{if(r.m[i]!=null)band+=(band?'L':'M')+X(x)+' '+Y(r.m[i]+1.96*r.s[i])+' ';});
      for(let i=xs.length-1;i>=0;i--)if(r.m[i]!=null)back+='L'+X(xs[i])+' '+Y(r.m[i]-1.96*r.s[i])+' ';
      if(band)g+='<path d="'+band+back+'Z" fill="'+col+'" opacity="0.12"/>';
    }
    let p='';
    xs.forEach((x,i)=>{if(r.m[i]!=null)p+=(p?'L':'M')+X(x)+' '+Y(r.m[i])+' ';});
    g+='<path d="'+p+'" fill="none" stroke="'+col+'" stroke-width="1.8"/>';
    xs.forEach((x,i)=>{if(r.l[i]>0&&r.m[i]!=null)g+='<circle cx="'+X(x)+'" cy="'+Y(r.m[i])+'" r="2.4" fill="'+col+'"/>';});
  });
  svg.innerHTML=g;
  $('tags').innerHTML=S.map((r,k)=>'<span class="tag"><i style="background:'+cvar(COLS[k%COLS.length])+'"></i>'+
    esc(r.n)+(extra.includes(r.n)?' <button data-n="'+esc(r.n)+'">×</button>':'')+'</span>').join('');
  $('tags').querySelectorAll('button').forEach(b=>b.onclick=()=>{extra=extra.filter(n=>n!==b.dataset.n);draw();});
}
function refresh(){note();setYears();table();extra=[];draw();}
fsel.onchange=()=>{F=D.fields[+fsel.value];refresh();};
$('ysel').onchange=()=>{table();};
$('q').oninput=()=>table();
function setTheme(dark){document.documentElement.setAttribute('data-theme',dark?'dark':'light');
  $('tbtn').textContent=dark?'switch to light':'switch to dark';draw();}
$('tbtn').onclick=()=>setTheme(document.documentElement.getAttribute('data-theme')!=='dark');
note();setYears();table();draw();
</script></body></html>"""

html = HTML.replace("__DATA__", DATA)
open(f"{OUT}/departments.html", "w").write(html)
print(f"wrote departments.html ({os.path.getsize(f'{OUT}/departments.html')/1e6:.2f} MB), "
      f"{len(fields)} fields")
