"""
07_dashboard.py -- build the self-contained interactive page.

Design brief: this is a working paper that happens to be interactive, not a
product dashboard. Single column, hairline rules instead of cards, numbered
sections, tabular figures, no stat tiles, no drop shadows, no rounded boxes.
Series colours come from a CVD-validated palette; everything around them is ink
and paper.

Monash University is PINNED in the comparison: always present, always the first
series, and not removable.
"""
import os, json
import numpy as np
import pandas as pd

W = os.path.expanduser("~/uniranks/work")
OUT = os.path.expanduser("~/uniranks/out")
os.makedirs(OUT, exist_ok=True)

PINNED = "Monash University"

sc = pd.read_csv(f"{W}/latent_scores.csv")
item = pd.read_csv(f"{W}/item_parameters.csv")
ed = pd.read_csv(f"{W}/edition_summary.csv")
panel = pd.read_csv(f"{W}/panel_long.csv")
years = sorted(sc.year.unique())
NY = len(years)

sc = sc.sort_values(["inst_id", "year"])
insts = []
for iid, gg in sc.groupby("inst_id"):
    gg = gg.set_index("year").reindex(years)
    insts.append({
        "id": iid,
        "n": gg["inst_name"].dropna().iloc[0],
        "c": (gg["country"].dropna().iloc[0] if gg["country"].notna().any() else "—"),
        "m": [int(round(v * 100)) for v in gg["theta_mean"]],
        "s": [int(round(v * 100)) for v in gg["theta_sd"]],
        "o": [int(v) for v in gg["n_listings"].fillna(0)],
    })
insts.sort(key=lambda d: -max(d["m"]))

t = sc[sc.in_sample].copy()
t["r"] = t.groupby("year")["theta_mean"].rank(ascending=False)
cc = t[t.r <= 200].groupby(["year", "country"]).size().rename("n").reset_index()
big = cc.groupby("country")["n"].sum().sort_values(ascending=False).head(8).index.tolist()
country_series = {c: [int(cc[(cc.country == c) & (cc.year == y)]["n"].sum()) for y in years]
                  for c in big}

systems = sorted(ed.system.unique())
cover = {s: [int(ed[(ed.system == s) & (ed.ref_year == y)]["N"].sum()) for y in years]
         for s in systems}
item_rows = json.loads(item.round(3).to_json(orient="records"))

FWD = {"THE", "USNews"}
panel["ref_year"] = panel["year"] - (panel["system"].isin(FWD) |
                                     ((panel["system"] == "QS") & (panel["year"] >= 2013))
                                     ).astype(int)
top_ids = set(sc[sc.rank_in_year <= 400].inst_id.unique())
pub = {}
for (iid, y), gg in panel[panel.inst_id.isin(top_ids)].groupby(["inst_id", "ref_year"]):
    pub.setdefault(iid, {})[int(y)] = {s: int(r) for s, r in
                                       zip(gg["system"], gg["rank"]) if r == r}
# Display names are NOT unique across institution ids, so the published-rank
# lookup is keyed on inst_id, never on the label.
pub_by_pos = {k: pub[d["id"]] for k, d in enumerate(insts) if d["id"] in pub}
name_to_idx = {}
for k, d in enumerate(insts):
    name_to_idx.setdefault(d["n"], k)

stats = dict(systems=len(systems), editions=int(len(ed)),
             y0=int(min(years)), y1=int(max(years)),
             institutions=len(insts), listings=int(ed["N"].sum()),
             pinned=next((k for k, d in enumerate(insts)
                          if d["n"] == PINNED), -1))


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    return o


for d in insts:
    d.pop("id", None)

DATA = json.dumps(_clean(dict(years=years, insts=insts, country=country_series,
                              countryOrder=big, cover=cover, systems=systems,
                              item=item_rows, pub=pub_by_pos, stats=stats)),
                  separators=(",", ":"))

HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>A latent measure of international university standing, 2003–2026</title>
<meta name="description" content="__NSYS__ international university rankings pooled with a dynamic Bayesian latent-trait model.">
<style>
:root{
  --paper:#fffefb; --ink:#16150f; --ink-2:#4a4841; --ink-3:#807d73;
  --rule:#dcd9cf; --rule-2:#efece3;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100;
  --s5:#e87ba4; --s6:#008300; --s7:#4a3aa7; --s8:#e34948;
  --q1:#cde2fb; --q2:#9ec5f4; --q3:#6da7ec; --q4:#3987e5;
  --q5:#2a78d6; --q6:#256abf; --q7:#184f95; --q8:#0d366b;
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
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);
 font:16px/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
 font-feature-settings:"kern" 1;}
.page{max-width:1040px;margin:0 auto;padding:56px 26px 96px}
.col{max-width:660px}
h1{font-size:29px;line-height:1.24;font-weight:600;letter-spacing:-.015em;margin:0 0 14px}
.byline{color:var(--ink-2);font-size:14.5px;margin:0 0 26px}
.byline a{color:inherit}
.lede{font-size:17px;line-height:1.66;color:var(--ink);margin:0 0 10px}
p{margin:0 0 14px}
a{color:var(--s1);text-decoration:none;border-bottom:1px solid currentColor;
  padding-bottom:.5px}
a:hover{color:var(--ink)}
section{padding-top:38px;margin-top:38px;border-top:1px solid var(--rule)}
h2{font-size:15px;font-weight:600;letter-spacing:.01em;margin:0 0 6px}
h2 .num{color:var(--ink-3);font-variant-numeric:tabular-nums;margin-right:10px;
  font-weight:400}
.note{color:var(--ink-2);font-size:14.5px;margin:0 0 22px;max-width:66ch}
.small{font-size:13.5px;color:var(--ink-3)}
figure{margin:0}
svg{display:block;width:100%;overflow:visible}
button,select,input{font:inherit;color:inherit}
input[type=text],input:not([type]),select{background:transparent;border:0;
  border-bottom:1px solid var(--rule);padding:5px 2px;font-size:14.5px;
  color:var(--ink);border-radius:0}
input:focus,select:focus{outline:0;border-bottom-color:var(--s1)}
select{border-bottom:1px solid var(--rule);padding-right:14px}
.ctl{display:flex;gap:22px;flex-wrap:wrap;align-items:baseline;margin-bottom:20px;
  font-size:14px;color:var(--ink-2)}
.ctl label{display:inline-flex;gap:7px;align-items:baseline}
.tags{display:flex;gap:5px 16px;flex-wrap:wrap;margin:0 0 18px;font-size:13.5px}
.tag{display:inline-flex;align-items:center;gap:6px;color:var(--ink-2);
  white-space:nowrap}
.tag i{width:16px;height:2px;display:inline-block;flex:none}
.tag button{background:none;border:0;cursor:pointer;color:var(--ink-3);
  font-size:15px;line-height:1;padding:0 0 0 1px}
.tag button:hover{color:var(--ink)}
.tag .pin{color:var(--ink-3);font-size:11.5px;letter-spacing:.04em;
  text-transform:uppercase}
table{border-collapse:collapse;width:100%;font-size:14px}
caption{caption-side:top;text-align:left;color:var(--ink-3);font-size:13px;
  padding-bottom:8px}
th,td{text-align:left;padding:6px 12px 6px 0;border-bottom:1px solid var(--rule-2);
  vertical-align:baseline}
thead th{color:var(--ink-3);font-weight:500;font-size:12.5px;letter-spacing:.03em;
  border-bottom:1px solid var(--rule)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;
  padding-right:18px}
td.n:last-child,th.n:last-child{padding-right:0}
tbody tr:last-child td{border-bottom:0}
.scroll{max-height:420px;overflow:auto}
.tip{position:fixed;pointer-events:none;background:var(--paper);
  border:1px solid var(--rule);padding:9px 12px;font-size:13px;opacity:0;
  transition:opacity .08s;z-index:9;max-width:290px;line-height:1.5}
.tip b{font-weight:600;display:block;margin-bottom:3px}
.tip .r{color:var(--ink-2)}
details{margin-top:14px}
summary{cursor:pointer;font-size:13.5px;color:var(--ink-3);list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"+ ";color:var(--ink-3)}
details[open] summary::before{content:"– "}
footer{margin-top:46px;padding-top:26px;border-top:1px solid var(--rule);
  color:var(--ink-3);font-size:13.5px;max-width:72ch}
.mode{background:none;border:0;cursor:pointer;color:var(--ink-3);font-size:13.5px;
  padding:0;border-bottom:1px solid var(--rule)}
.mode:hover{color:var(--ink)}
@media (max-width:620px){.page{padding:34px 18px 70px}h1{font-size:24px}}
</style></head><body>
<div class="page">

<header class="col">
 <h1>A latent measure of international university standing, 2003–2026</h1>
 <p class="byline">Charles Crabtree · Monash University · <span id="dateline"></span></p>
 <p class="byline" style="margin-top:-16px"><b>Universities</b> ·
   <a href="departments.html">Departments</a> ·
   <a href="methods.html">Methods</a></p>
 <p class="lede">__NSYS__ international ranking systems, pooled with a dynamic Bayesian
 latent-trait model. Each ranking is treated as one noisy, censored instrument reading a
 single underlying quantity, rather than as an answer in itself.</p>
 <p class="small" id="scope"></p>
</header>

<section>
 <h2><span class="num">1</span>Trajectories</h2>
 <p class="note">Monash is pinned to every comparison. Add others to compare against it.
 The shaded band is the 90% credible interval; it widens in years when fewer rankings
 listed the institution, which is the honest way to show that we know less about those
 years. Dots mark years with at least one listing.</p>
 <div class="ctl">
   <label>Compare with
     <input id="search" list="dl" placeholder="type an institution" style="min-width:230px"></label>
   <datalist id="dl"></datalist>
   <label><input type="checkbox" id="bands" checked> credible bands</label>
 </div>
 <div class="tags" id="tags"></div>
 <figure><svg id="traj" viewBox="0 0 940 430" role="img"
   aria-label="Latent standing over time for the selected institutions"></svg></figure>
 <details><summary>table</summary><div class="scroll" id="trajTable"></div></details>
</section>

<section>
 <h2><span class="num">2</span>Where Monash sits</h2>
 <p class="note">Position on the pooled scale each year, and the published ranks the
 estimate was built from.</p>
 <div class="scroll"><table id="pinTab"></table></div>
</section>

<section>
 <h2><span class="num">3</span>The global top 200, by country</h2>
 <p class="note">How many of each country's institutions sit in the top 200 of the pooled
 scale — not of any one published table.</p>
 <figure><svg id="ctry" viewBox="0 0 940 400" role="img"
   aria-label="Count of top-200 institutions by country over time"></svg></figure>
 <div class="tags" id="ctryLeg"></div>
</section>

<section>
 <h2><span class="num">4</span>The rankings as measuring instruments</h2>
 <p class="note">Reliability is α²/(α²+σ²): the share of a ranking's variation that the
 shared factor explains. A low value means that ranking is either noisy or is measuring
 something the others are not — which makes it the more informative one to have.</p>
 <figure><svg id="rel" viewBox="0 0 940 330" role="img"
   aria-label="Reliability by ranking system"></svg></figure>
 <table id="itemTab" style="margin-top:26px"></table>
</section>

<section>
 <h2><span class="num">5</span>What data actually exists</h2>
 <p class="note">List length by ranking and reference year. Blank means no edition could
 be retrieved — the model treats those as missing, not as zero. THE, U.S. News and
 post-2013 QS editions are shifted back one year so a column refers to one real-world
 moment.</p>
 <figure><svg id="cov" viewBox="0 0 940 300" role="img"
   aria-label="Data coverage by ranking system and year"></svg></figure>
</section>

<section>
 <h2><span class="num">6</span>The scale, by year</h2>
 <div class="ctl">
   <label>Year <select id="yearSel"></select></label>
   <label>Filter <input id="tsearch" placeholder="name or country" style="min-width:190px"></label>
   <label><input type="checkbox" id="minlist" checked> at least 3 rankings</label>
 </div>
 <div class="scroll"><table id="rankTab"></table></div>
</section>

<footer>
 <p id="foot"></p>
 <p><button class="mode" id="theme">switch to dark</button></p>
</footer>
</div>
<div class="tip" id="tip"></div>
<script id="payload" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('payload').textContent);
const YEARS=D.years,NY=YEARS.length,S=D.stats,PIN=S.pinned;
const SLOTS=['--s1','--s2','--s3','--s4','--s5','--s6','--s7','--s8'];
const cvar=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let CS=SLOTS.map(cvar);
const NS='http://www.w3.org/2000/svg';
const el=(t,a={})=>{const n=document.createElementNS(NS,t);for(const k in a)n.setAttribute(k,a[k]);return n};
const tip=document.getElementById('tip');
function showTip(e,h){tip.innerHTML=h;tip.style.opacity=1;
  const r=tip.getBoundingClientRect();
  tip.style.left=Math.min(e.clientX+14,innerWidth-r.width-10)+'px';
  tip.style.top=Math.max(8,e.clientY-r.height-14)+'px';}
const hideTip=()=>tip.style.opacity=0;
function declash(ys,gap,lo,hi){
  const ord=ys.map((v,i)=>[v,i]).sort((a,b)=>a[0]-b[0]);let prev=-1e9;
  for(const p of ord){const v=Math.max(p[0],prev+gap);prev=v;ys[p[1]]=v}
  const over=prev-hi; if(over>0) for(let i=0;i<ys.length;i++) ys[i]-=over;
  const under=lo-Math.min(...ys); if(under>0) for(let i=0;i<ys.length;i++) ys[i]+=under;
  return ys;}
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

document.getElementById('dateline').textContent =
  new Date(Date.parse('2026-08-12')).toLocaleDateString('en-GB',
    {day:'numeric',month:'long',year:'numeric'});
document.getElementById('scope').textContent =
  `${S.systems} ranking systems · ${S.editions} system-editions · `+
  `${S.listings.toLocaleString()} published listings · `+
  `${S.institutions.toLocaleString()} institutions · ${S.y0}–${S.y1}`;

/* ---------------------------------------------------------- 1 trajectories */
const sel=[];                       // PIN is implicit and always first
const byName=new Map(D.insts.map((d,i)=>[d.n,i]));
document.getElementById('dl').innerHTML=D.insts.slice(0,4000)
  .map(d=>`<option value="${esc(d.n)}">`).join('');
['University of Melbourne','The University of Queensland','University of Sydney']
  .forEach(n=>{if(byName.has(n)&&byName.get(n)!==PIN)sel.push(byName.get(n))});
const series=()=>PIN>=0?[PIN,...sel]:sel;

function drawTraj(){
  const svg=document.getElementById('traj');svg.innerHTML='';
  const W=940,H=430,L=42,R=232,T=28,B=34;
  const bands=document.getElementById('bands').checked;
  const ss=series();
  let lo=1e9,hi=-1e9;
  ss.forEach(i=>{const d=D.insts[i];for(let k=0;k<NY;k++){
    const m=d.m[k]/100,s=d.s[k]/100;
    lo=Math.min(lo,bands?m-1.65*s:m);hi=Math.max(hi,bands?m+1.65*s:m);}});
  if(!ss.length){lo=0;hi=4}
  const pad=(hi-lo)*.09;lo-=pad;hi+=pad;
  const x=k=>L+k*(W-L-R)/(NY-1), y=v=>T+(hi-v)*(H-T-B)/(hi-lo);
  for(let t=0;t<=4;t++){const v=lo+(hi-lo)*t/4;
    svg.appendChild(el('line',{x1:L,x2:W-R,y1:y(v),y2:y(v),
      stroke:cvar('--rule-2'),'stroke-width':1}));
    const tx=el('text',{x:L-8,y:y(v)+4,'text-anchor':'end',fill:cvar('--ink-3'),
      'font-size':11.5});tx.textContent=v.toFixed(1);svg.appendChild(tx);}
  YEARS.forEach((yr,k)=>{if(yr%3)return;
    const t=el('text',{x:x(k),y:H-B+19,'text-anchor':'middle',fill:cvar('--ink-3'),
      'font-size':11.5});t.textContent=yr;svg.appendChild(t)});
  const yl=el('text',{x:L-8,y:T-13,'text-anchor':'end',fill:cvar('--ink-3'),'font-size':11.5});
  yl.textContent='θ';svg.appendChild(yl);

  ss.forEach((i,si)=>{
    const d=D.insts[i],c=CS[si%8],pin=(i===PIN);
    if(bands){let p='';
      for(let k=0;k<NY;k++)p+=`${k?'L':'M'}${x(k)},${y(d.m[k]/100+1.65*d.s[k]/100)}`;
      for(let k=NY-1;k>=0;k--)p+=`L${x(k)},${y(d.m[k]/100-1.65*d.s[k]/100)}`;
      svg.appendChild(el('path',{d:p+'Z',fill:c,opacity:pin?.16:.1}));}
    let p='';for(let k=0;k<NY;k++)p+=`${k?'L':'M'}${x(k)},${y(d.m[k]/100)}`;
    svg.appendChild(el('path',{d:p,fill:'none',stroke:c,
      'stroke-width':pin?2.4:1.6,'stroke-linejoin':'round','stroke-linecap':'round'}));
    for(let k=0;k<NY;k++) if(d.o[k]>0)
      svg.appendChild(el('circle',{cx:x(k),cy:y(d.m[k]/100),r:pin?2.7:2.1,fill:c,
        stroke:cvar('--paper'),'stroke-width':1.2}));
  });
  const lys=declash(ss.map(i=>y(D.insts[i].m[NY-1]/100)),15,T+6,H-B);
  ss.forEach((i,si)=>{const d=D.insts[i],c=CS[si%8],ye=y(d.m[NY-1]/100);
    if(Math.abs(lys[si]-ye)>3)
      svg.appendChild(el('path',{d:`M${W-R+1},${ye}L${W-R+8},${lys[si]}`,stroke:c,
        'stroke-width':1,fill:'none',opacity:.5}));
    const t=el('text',{x:W-R+12,y:lys[si]+4,fill:c,'font-size':12,
      'font-weight':i===PIN?600:500});
    t.textContent=d.n.length>32?d.n.slice(0,31)+'…':d.n;svg.appendChild(t);});

  const cross=el('line',{y1:T,y2:H-B,stroke:cvar('--ink-3'),'stroke-width':1,opacity:0});
  svg.appendChild(cross);
  const hit=el('rect',{x:L,y:T,width:W-L-R,height:H-T-B,fill:'transparent'});
  svg.appendChild(hit);
  hit.addEventListener('mousemove',e=>{
    const bb=svg.getBoundingClientRect();
    let k=Math.round(((e.clientX-bb.left)/bb.width*W-L)/((W-L-R)/(NY-1)));
    k=Math.max(0,Math.min(NY-1,k));
    cross.setAttribute('x1',x(k));cross.setAttribute('x2',x(k));cross.setAttribute('opacity',.35);
    let h=`<b>${YEARS[k]}</b>`;
    ss.forEach((i,si)=>{const d=D.insts[i];
      h+=`<div><span style="color:${CS[si%8]}">■</span> ${esc(d.n)} `+
         `<span class="r">${(d.m[k]/100).toFixed(2)} ±${(1.96*d.s[k]/100).toFixed(2)}`+
         `${d.o[k]?' · '+d.o[k]+' listing'+(d.o[k]>1?'s':''):' · not listed'}</span></div>`;});
    showTip(e,h);});
  hit.addEventListener('mouseleave',()=>{cross.setAttribute('opacity',0);hideTip()});
  drawTags();drawTrajTable();
}
function drawTags(){
  document.getElementById('tags').innerHTML=series().map((i,si)=>{
    const pin=(i===PIN);
    return `<span class="tag"><i style="background:${CS[si%8]}"></i>${esc(D.insts[i].n)}`+
      (pin?' <span class="pin">pinned</span>'
          :` <button data-i="${si-(PIN>=0?1:0)}" aria-label="remove">×</button>`)+'</span>';
  }).join('');
  document.querySelectorAll('.tag button').forEach(b=>b.onclick=()=>{
    sel.splice(+b.dataset.i,1);drawTraj()});
}
function drawTrajTable(){
  const cols=YEARS.map((y,k)=>[y,k]).filter(([y])=>!(y%3));
  let h='<table><thead><tr><th>Institution</th>'+
    cols.map(([y])=>`<th class="n">${y}</th>`).join('')+'</tr></thead><tbody>';
  series().forEach(i=>{const d=D.insts[i];
    h+=`<tr><td>${esc(d.n)}</td>`+cols.map(([,k])=>
      `<td class="n">${(d.m[k]/100).toFixed(2)}</td>`).join('')+'</tr>';});
  document.getElementById('trajTable').innerHTML=h+'</tbody></table>';
}
document.getElementById('search').addEventListener('change',e=>{
  const i=byName.get(e.target.value);
  if(i!==undefined&&i!==PIN&&!sel.includes(i)){if(sel.length>=7)sel.shift();sel.push(i)}
  e.target.value='';drawTraj();});
document.getElementById('bands').addEventListener('change',drawTraj);

/* ---------------------------------------------------------- 2 pinned detail */
function drawPin(){
  if(PIN<0){document.getElementById('pinTab').innerHTML=
    '<tbody><tr><td>Monash University is not in the modelled universe.</td></tr></tbody>';return}
  const d=D.insts[PIN],p=D.pub[PIN]||{};
  const rows=YEARS.map((y,k)=>({y,k})).filter(r=>d.o[r.k]>0).reverse();
  let h='<caption>Monash University · pooled estimate and the published ranks behind it'+
        '</caption><thead><tr><th class="n">Year</th><th class="n">θ</th>'+
        '<th class="n">95% CI</th><th class="n">Rank</th><th class="n">Listings</th>'+
        '<th>Published ranks</th></tr></thead><tbody>';
  rows.forEach(({y,k})=>{
    const v=d.m[k]/100,s=d.s[k]/100,pr=p[y]||{};
    const ps=Object.entries(pr).map(([sy,r])=>`${sy}&nbsp;${r}`).join(', ')||'—';
    h+=`<tr><td class="n">${y}</td><td class="n">${v.toFixed(2)}</td>`+
       `<td class="n">[${(v-1.96*s).toFixed(2)}, ${(v+1.96*s).toFixed(2)}]</td>`+
       `<td class="n">${rankOf(PIN,k)}</td><td class="n">${d.o[k]}</td>`+
       `<td class="r" style="color:var(--ink-2)">${ps}</td></tr>`;});
  document.getElementById('pinTab').innerHTML=h+'</tbody>';
}
const rankCache={};
function rankOf(i,k){
  if(!rankCache[k]){
    rankCache[k]=D.insts.map((d,j)=>({j,v:d.m[k],o:d.o[k]})).filter(r=>r.o>0)
      .sort((a,b)=>b.v-a.v).reduce((m,r,n)=>(m[r.j]=n+1,m),{});}
  return rankCache[k][i]||'—';
}

/* ---------------------------------------------------------- 3 countries */
function drawCountry(){
  const svg=document.getElementById('ctry');svg.innerHTML='';
  const W=940,H=400,L=38,R=160,T=12,B=32;
  const ord=D.countryOrder.slice(0,6);
  let hi=0;ord.forEach(c=>D.country[c].forEach(v=>hi=Math.max(hi,v)));
  hi=Math.ceil(hi/10)*10;
  const i0=YEARS.indexOf(2004),i1=YEARS.indexOf(2025);
  const x=k=>L+(k-i0)*(W-L-R)/(i1-i0), y=v=>T+(hi-v)*(H-T-B)/hi;
  for(let t=0;t<=4;t++){const v=hi*t/4;
    svg.appendChild(el('line',{x1:L,x2:W-R,y1:y(v),y2:y(v),stroke:cvar('--rule-2'),'stroke-width':1}));
    const tx=el('text',{x:L-8,y:y(v)+4,'text-anchor':'end',fill:cvar('--ink-3'),'font-size':11.5});
    tx.textContent=v;svg.appendChild(tx);}
  YEARS.forEach((yr,k)=>{if(k<i0||k>i1||yr%3)return;
    const t=el('text',{x:x(k),y:H-B+19,'text-anchor':'middle',fill:cvar('--ink-3'),'font-size':11.5});
    t.textContent=yr;svg.appendChild(t)});
  ord.forEach((c,si)=>{const v=D.country[c],col=CS[si%8];
    let p='';for(let k=i0;k<=i1;k++)p+=`${k===i0?'M':'L'}${x(k)},${y(v[k])}`;
    svg.appendChild(el('path',{d:p,fill:'none',stroke:col,'stroke-width':1.6,'stroke-linejoin':'round'}));
    for(let k=i0;k<=i1;k++)svg.appendChild(el('circle',{cx:x(k),cy:y(v[k]),r:2,fill:col}));});
  const lys=declash(ord.map(c=>y(D.country[c][i1])),15,T+6,H-B);
  ord.forEach((c,si)=>{const col=CS[si%8],ye=y(D.country[c][i1]);
    if(Math.abs(lys[si]-ye)>3)
      svg.appendChild(el('path',{d:`M${W-R+1},${ye}L${W-R+8},${lys[si]}`,stroke:col,
        'stroke-width':1,fill:'none',opacity:.5}));
    const t=el('text',{x:W-R+12,y:lys[si]+4,fill:col,'font-size':12,'font-weight':500});
    t.textContent=c;svg.appendChild(t);});
  const hit=el('rect',{x:L,y:T,width:W-L-R,height:H-T-B,fill:'transparent'});svg.appendChild(hit);
  hit.addEventListener('mousemove',e=>{const bb=svg.getBoundingClientRect();
    let k=Math.round(i0+((e.clientX-bb.left)/bb.width*W-L)/((W-L-R)/(i1-i0)));
    k=Math.max(i0,Math.min(i1,k));
    let h=`<b>${YEARS[k]}</b>`;
    ord.forEach((c,si)=>{h+=`<div><span style="color:${CS[si%8]}">■</span> ${c} `+
      `<span class="r">${D.country[c][k]}</span></div>`});
    showTip(e,h)});
  hit.addEventListener('mouseleave',hideTip);
  document.getElementById('ctryLeg').innerHTML=ord.map((c,si)=>
    `<span class="tag"><i style="background:${CS[si%8]}"></i>${c}</span>`).join('');
}

/* ---------------------------------------------------------- 4 reliability */
function drawRel(){
  const svg=document.getElementById('rel');svg.innerHTML='';
  const rows=[...D.item].sort((a,b)=>a.reliability-b.reliability);
  const W=940,H=330,L=112,R=74,T=8,B=28;
  const bh=(H-T-B)/rows.length, x=v=>L+v*(W-L-R);
  for(let t=0;t<=5;t++){const v=t/5;
    svg.appendChild(el('line',{x1:x(v),x2:x(v),y1:T,y2:H-B,stroke:cvar('--rule-2'),'stroke-width':1}));
    const tx=el('text',{x:x(v),y:H-B+18,'text-anchor':'middle',fill:cvar('--ink-3'),'font-size':11.5});
    tx.textContent=v.toFixed(1);svg.appendChild(tx);}
  rows.forEach((r,k)=>{
    const yy=T+k*bh+bh*.3,hh=bh*.4;
    const rect=el('rect',{x:L,y:yy,width:Math.max(1.5,x(r.reliability)-L),height:hh,
      fill:cvar('--q5')});
    svg.appendChild(rect);
    svg.appendChild(el('line',{x1:x(r.reliability_lo),x2:x(r.reliability_hi),
      y1:yy+hh/2,y2:yy+hh/2,stroke:cvar('--q8'),'stroke-width':1.4}));
    const lb=el('text',{x:L-10,y:yy+hh/2+4,'text-anchor':'end',fill:cvar('--ink'),'font-size':12.5});
    lb.textContent=r.system;svg.appendChild(lb);
    const vl=el('text',{x:x(r.reliability_hi)+9,y:yy+hh/2+4,fill:cvar('--ink-3'),'font-size':12});
    vl.textContent=r.reliability.toFixed(2);svg.appendChild(vl);
    rect.addEventListener('mousemove',e=>showTip(e,
      `<b>${r.system}</b><div class="r">${r.years} · ${r.editions} edition(s)</div>`+
      `<div class="r">reliability ${r.reliability.toFixed(2)} `+
      `[${r.reliability_lo.toFixed(2)}, ${r.reliability_hi.toFixed(2)}]</div>`+
      `<div class="r">α = ${r.alpha_discrimination.toFixed(2)} · σ = ${r.sigma_noise.toFixed(2)}</div>`));
    rect.addEventListener('mouseleave',hideTip);});
  document.getElementById('itemTab').innerHTML=
    '<thead><tr><th>Ranking</th><th>Years</th><th class="n">Editions</th>'+
    '<th class="n">Median list</th><th class="n">α</th><th class="n">σ</th>'+
    '<th class="n">Reliability</th></tr></thead><tbody>'+
    [...D.item].sort((a,b)=>b.reliability-a.reliability).map(r=>
     `<tr><td>${r.system}</td><td>${r.years}</td><td class="n">${r.editions}</td>`+
     `<td class="n">${r.median_list_length}</td>`+
     `<td class="n">${r.alpha_discrimination.toFixed(2)}</td>`+
     `<td class="n">${r.sigma_noise.toFixed(2)}</td>`+
     `<td class="n">${r.reliability.toFixed(2)}</td></tr>`).join('')+'</tbody>';
}

/* ---------------------------------------------------------- 5 coverage */
function drawCov(){
  const svg=document.getElementById('cov');svg.innerHTML='';
  const sys=D.systems,W=940,H=300,L=106,R=12,T=8,B=30;
  const cw=(W-L-R)/NY, ch=(H-T-B)/sys.length;
  const q=['--q1','--q2','--q3','--q4','--q5','--q6','--q7','--q8'].map(cvar);
  const lg=Math.log10, mn=lg(80), mx=lg(3200);
  sys.forEach((s,r)=>{
    const lb=el('text',{x:L-9,y:T+r*ch+ch/2+4,'text-anchor':'end',fill:cvar('--ink'),'font-size':12});
    lb.textContent=s;svg.appendChild(lb);
    YEARS.forEach((y,c)=>{const v=D.cover[s][c];if(!v)return;
      const f=Math.max(0,Math.min(.999,(lg(v)-mn)/(mx-mn)));
      const rect=el('rect',{x:L+c*cw+.8,y:T+r*ch+1.2,width:cw-1.6,height:ch-2.4,
        fill:q[Math.floor(f*8)]});
      svg.appendChild(rect);
      rect.addEventListener('mousemove',e=>showTip(e,
        `<b>${s} ${y}</b><div class="r">${v.toLocaleString()} institutions listed</div>`));
      rect.addEventListener('mouseleave',hideTip);});});
  YEARS.forEach((y,c)=>{if(y%3)return;
    const t=el('text',{x:L+c*cw+cw/2,y:H-B+18,'text-anchor':'middle',fill:cvar('--ink-3'),'font-size':11});
    t.textContent=y;svg.appendChild(t)});
}

/* ---------------------------------------------------------- 6 table */
const ysel=document.getElementById('yearSel');
ysel.innerHTML=YEARS.map(y=>`<option ${y===2024?'selected':''}>${y}</option>`).join('');
function drawRank(){
  const y=+ysel.value,k=YEARS.indexOf(y);
  const q=document.getElementById('tsearch').value.toLowerCase();
  const minl=document.getElementById('minlist').checked?3:1;
  const rows=D.insts.map((d,i)=>({d,i,v:d.m[k]/100,s:d.s[k]/100,o:d.o[k]}))
    .filter(r=>r.o>=minl).sort((a,b)=>b.v-a.v);
  rows.forEach((r,n)=>r.pos=n+1);
  const shown=rows.filter(r=>!q||r.d.n.toLowerCase().includes(q)||
    r.d.c.toLowerCase().includes(q)).slice(0,300);
  document.getElementById('rankTab').innerHTML=
   `<caption>${rows.length.toLocaleString()} institutions listed by at least `+
   `${minl} ranking${minl>1?'s':''} in ${y}; showing ${shown.length}</caption>`+
   '<thead><tr><th class="n">#</th><th>Institution</th><th>Country</th>'+
   '<th class="n">θ</th><th class="n">95% CI</th><th class="n">Listings</th>'+
   '<th>Published ranks</th></tr></thead><tbody>'+
   shown.map(r=>{
     const p=(D.pub[r.i]||{})[y];
     const ps=p?Object.entries(p).map(([s,v])=>`${s}&nbsp;${v}`).join(', '):'—';
     const hl=(r.i===PIN)?' style="font-weight:600"':'';
     return `<tr${hl}><td class="n">${r.pos}</td><td>${esc(r.d.n)}</td>`+
      `<td>${esc(r.d.c)}</td><td class="n">${r.v.toFixed(2)}</td>`+
      `<td class="n">[${(r.v-1.96*r.s).toFixed(2)}, ${(r.v+1.96*r.s).toFixed(2)}]</td>`+
      `<td class="n">${r.o}</td>`+
      `<td style="color:var(--ink-2)">${ps}</td></tr>`}).join('')+'</tbody>';
}
ysel.onchange=drawRank;
document.getElementById('tsearch').oninput=drawRank;
document.getElementById('minlist').onchange=drawRank;

document.getElementById('foot').innerHTML=
 'Latent standing (θ) is the posterior mean of a dynamic Bayesian latent-trait model '+
 'with ranking-specific discrimination, location and noise, a random-walk prior over '+
 'institutional quality, and explicit interval and left censoring for banded ranks and '+
 'non-listing. Higher is better; one unit is one 2003 standard deviation. Comparisons '+
 'of levels across distant years rest on the item parameters being constant over time. '+
 'Full method, data provenance and limitations in the '+
 '<a href="methods.html">methods note</a>. The estimates behind this page are in '+
 '<a href="data/latent_scores.csv">latent_scores.csv</a>, the harmonised source data in '+
 '<a href="data/rankings_panel_long.csv">rankings_panel_long.csv</a>, and the pipeline '+
 'that produced both is in <code>code/</code>.';

const tbtn=document.getElementById('theme');
function setTheme(dark){
  document.documentElement.setAttribute('data-theme',dark?'dark':'light');
  tbtn.textContent=dark?'switch to light':'switch to dark';
  CS=SLOTS.map(cvar);redraw();}
tbtn.onclick=()=>setTheme(document.documentElement.getAttribute('data-theme')!=='dark');
if(matchMedia('(prefers-color-scheme:dark)').matches)tbtn.textContent='switch to light';
function redraw(){drawTraj();drawPin();drawCountry();drawRel();drawCov();drawRank()}
redraw();
</script></body></html>"""

NWORD = {12: "Twelve", 13: "Thirteen", 14: "Fourteen", 15: "Fifteen",
         16: "Sixteen"}.get(item.system.nunique(), str(item.system.nunique()))
html = HTML.replace("__DATA__", DATA).replace("__NSYS__", NWORD)
open(f"{OUT}/university_rankings_dashboard.html", "w").write(html)
print(f"wrote page ({os.path.getsize(f'{OUT}/university_rankings_dashboard.html')/1e6:.2f} MB); "
      f"pinned index = {stats['pinned']}")
