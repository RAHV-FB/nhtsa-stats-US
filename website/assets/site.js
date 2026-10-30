"use strict";
/* Road Evidence: zero-dependency interactive research site. No cookies or tracking. */
const ROOT="data/",SOURCE="https://github.com/RAHV-FB/nhtsa-stats-US/blob/main/";
const REPORTS=[
 ["findings","Core research findings","reports/findings.md"],
 ["speeding_confounding","Speeding and confounding","reports/speeding_confounding.md"],
 ["factor_contributions","Factor contributions","reports/factor_contributions.md"],
 ["alcohol_drugs_restraints","Alcohol, drugs and seat belts","reports/alcohol_drugs_restraints.md"],
 ["multifactor_interactions","Multiple-factor interactions","reports/multifactor_interactions.md"],
 ["case_comparisons","Case comparisons","reports/case_comparisons.md"],
 ["interactions","Interaction analysis","reports/interactions.md"],
 ["policy_analysis","Policy and interventions","reports/policy_analysis.md"],
 ["methodology","Methodology","docs/methodology.md"],
 ["limitations","Limitations","docs/limitations.md"],
 ["model_validation","Model validation","docs/model_validation.md"]
];
const FACTOR_TEXT={light:"Light condition",weather:"Weather",surface:"Road surface",speed_limit:"Speed limit",tod:"Time of day",weekend:"Weekend (Sat/Sun)",junction:"Junction",urbanicity:"Area (CRSS urbanicity)",region:"Census region",interstate:"Interstate",work_zone:"Work zone",young_driver:"Driver aged 15–20 involved",older_driver:"Driver aged 65+ involved",any_motorcycle:"Motorcycle involved",any_heavy_truck:"Medium/heavy truck or bus involved",speeding:"Speeding-related (police-reported)",speeding_type:"Speeding type",alcohol:"Alcohol involved (police-reported)",alcohol_im:"Alcohol involved (NHTSA-imputed)",drugs:"Drug involvement (police-reported)",distracted:"Distracted driver (police-reported)",crash_type:"Crash type",n_vehicles:"Vehicles in transport",YEAR:"Year"};
const LEVEL_TEXT={yes:"Yes",no:"No",unknown:"Unknown",other:"Other",clear:"Clear",cloudy:"Cloudy",rain:"Rain",snow_sleet:"Snow or sleet",fog:"Fog",daylight:"Daylight",dawn_dusk:"Dawn or dusk",dark_lighted:"Dark, lit",dark_not_lighted:"Dark, unlit",dark_unknown_lighting:"Dark, lighting unknown",dry:"Dry",wet:"Wet",snow_ice:"Snow or ice",non_junction:"Non-junction",intersection:"Intersection",driveway:"Driveway",interchange:"Interchange",urban:"Urban",rural:"Rural",northeast:"Northeast",midwest:"Midwest",south:"South",west:"West",mv_rear_end:"Rear-end collision",mv_angle:"Angle collision",mv_sideswipe:"Sideswipe collision",mv_head_on:"Head-on collision",mv_other:"Other multi-vehicle crash",sv_on_roadway:"Single vehicle, on roadway",sv_off_roadway:"Single vehicle, off roadway",sv_rollover_first:"Single vehicle, rollover first",pedestrian:"Pedestrian",cyclist:"Cyclist",exceeded_limit_or_racing:"Exceeded limit or racing",too_fast_for_conditions:"Too fast for conditions",speeding_unspecified:"Speeding, unspecified","00-05":"00:00–05:59","06-09":"06:00–09:59","10-15":"10:00–15:59","16-19":"16:00–19:59","20-23":"20:00–23:59","<=25":"≤25 mph","30-35":"30–35 mph","40-45":"40–45 mph","50-55":"50–55 mph","60-65":"60–65 mph","70+":"70+ mph",none_nontrafficway:"None / non-trafficway"};
const pretty=s=>{s=String(s??"").replaceAll("_"," ");return s.charAt(0).toUpperCase()+s.slice(1);};
const factorText=(f,label)=>FACTOR_TEXT[f]||label||pretty(f), levelText=l=>LEVEL_TEXT[l]||pretty(l);
const num=s=>s===""||s==null?NaN:+s;
const QUERY={
 frequency:{src:"descriptive/frequency_vs_severity.csv",heading:"Frequency versus fatal severity",tag:"01",description:"The share of fatal crashes divided by the share of police-reported crashes. Higher ratios mean over-representation, not causation.",caption:"FARS census numerator and CRSS survey-weighted denominator. Uncertainty is reported in the source table. Unknown or other levels are excluded.",ratio:true,value:r=>+r.overrep_ratio,lo:r=>num(r.overrep_low),hi:r=>num(r.overrep_high),name:r=>factorText(r.factor,r.label)+" · "+levelText(r.level),detail:r=>"Fatal crash share: "+percent(+r.share_fatal_fars)+"; all crashes: "+percent(+r.share_all_crashes)+"; 95% CI "+ratio(+r.overrep_low)+"–"+ratio(+r.overrep_high),display:v=>ratio(v)+"×",eligible:r=>r.overrep_ratio!==""&&!["unknown","other"].includes(r.level)},
 severity:{src:"severity/fatal_crude_vs_adjusted.csv",heading:"Crude versus adjusted severity",tag:"02",description:"Model A fatal-crash risk ratios after accounting for recorded pre-crash circumstances. Reference categories have ratio 1 and are excluded from the bar chart.",caption:"CRSS, 2016–2024. The table includes crude, model A and model B estimates, with confidence intervals. Adjusted estimates are not causal effects. Unknown or other levels, years and unstable estimates are excluded.",ratio:true,value:r=>+r.A_adj_rr,lo:r=>num(r.A_adj_rr_low),hi:r=>num(r.A_adj_rr_high),name:r=>factorText(r.factor)+" · "+levelText(r.level),detail:r=>"Crude RR "+ratio(+r.crude_rr)+"; adjusted RR "+ratio(+r.A_adj_rr)+"; 95% CI "+ratio(+r.A_adj_rr_low)+"–"+ratio(+r.A_adj_rr_high),display:v=>ratio(v)+"×",eligible:r=>r.A_adj_rr!==""&&+r.A_adj_rr!==1&&!["unknown","other"].includes(r.level)&&r.factor!=="YEAR"&&!r.flag&&!r.adj_flag},
 attribution:{src:"contributions/ranking.csv",heading:"Ranking depends on the question",tag:"03",description:"Adjusted crash-level associations for the factors that can be ranked. Drug status and occupant-level restraint effects cannot be ranked on the same basis.",caption:"Standardised adjusted risk ratios, not causal fractions. The underlying table includes other possible rankings and unrankable factors.",ratio:true,value:r=>+r.adjusted_rr,name:r=>({"exceeded":"Exceeded speed limit / racing","speeding_other":"Other speeding","alcohol":"Alcohol involved"}[r.factor]||pretty(r.factor)),detail:r=>r.note||"Model-based association",display:v=>ratio(v)+"×",eligible:r=>r.rankable==="True"},
 trends:{src:"descriptive/fars_annual.csv",heading:"Annual US road deaths",tag:"04",description:"The fatal-crash census counts deaths each year. They are not rates per trip or per mile.",caption:"FARS observed death counts, 2016–2024. Interpret changes separately from exposure and changes in nonfatal crash reporting.",value:r=>+r.deaths,name:r=>r.YEAR,detail:r=>"Fatal crashes: "+integer(+r.fatal_crashes)+"; deaths: "+integer(+r.deaths),display:v=>integer(v),eligible:r=>true}
};
const $=(s,root=document)=>root.querySelector(s), $$=(s,root=document)=>[...root.querySelectorAll(s)];
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const ratio=n=>{if(!Number.isFinite(n))return "—";const d=+n.toFixed(2)<10?2:1;return n.toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d});};
const integer=n=>Number.isFinite(n)?Math.round(n).toLocaleString("en-US"):"—";
const percent=n=>Number.isFinite(n)?(n*100).toFixed(1)+"%":"—";
const failure=s=>'<p role="status" class="empty-line">'+esc(s)+'</p>';
const memo=new Map();
async function resource(path,format="text"){
 const key=format+":"+path;
 if(memo.has(key))return memo.get(key);
 const promise=fetch(ROOT+path).then(async r=>{if(!r.ok)throw Error(path+" returned "+r.status);const text=await r.text();return format==="csv"?csv(text):format==="json"?JSON.parse(text):text;}).catch(e=>{memo.delete(key);throw e;});
 memo.set(key,promise);return promise;
}
function csv(input){
 let records=[],record=[],field="",quoted=false;
 for(let i=0;i<input.length;i++){
  const c=input[i];
  if(quoted){if(c==='"'&&input[i+1]==='"'){field+='"';i++;}else if(c==='"')quoted=false;else field+=c;}
  else if(c==='"')quoted=true;
  else if(c===','){record.push(field);field="";}
  else if(c==='\r'||c==='\n'){if(c==='\r'&&input[i+1]==='\n')i++;record.push(field);if(record.some(x=>x!==""))records.push(record);record=[];field="";}
  else field+=c;
 }
 if(field||record.length){record.push(field);records.push(record);}
 const header=(records.shift()||[]).map(x=>x.replace(/^\uFEFF/,""));
 return records.map(r=>Object.fromEntries(header.map((h,i)=>[h,r[i]??""])));
}
function menu(){
 const b=$("#menu-button"),n=$("#main-nav");
 b.addEventListener("click",()=>{const active=n.classList.toggle("open");b.setAttribute("aria-expanded",String(active));});
 $$("a",n).forEach(a=>a.addEventListener("click",()=>{n.classList.remove("open");b.setAttribute("aria-expanded","false");}));
}
let current="frequency",items=[];
function dataRows(rows){
 const keys=Object.keys(rows[0]||{});
 return "<thead><tr>"+keys.map(x=>"<th scope='col'>"+esc(x.replaceAll("_"," "))+"</th>").join("")+"</tr></thead><tbody>"+rows.map(r=>"<tr>"+keys.map(k=>"<td>"+esc(r[k])+"</td>").join("")+"</tr>").join("")+"</tbody>";
}
function bar(r,def,max){
 const at=v=>(v/max*100).toFixed(2)+"%";
 return '<div class="bar-row" title="'+esc(r.detail)+'"><span class="bar-label" title="'+esc(r.name)+'">'+esc(r.name)+'</span><div class="bar-track"><div class="bar-fill" style="width:'+at(r.value)+'"></div>'+(r.ci?'<i class="bar-ci" style="left:'+at(r.lo)+';width:'+at(r.hi-r.lo)+'"></i>':"")+(def.ratio?'<i class="bar-ref" style="left:'+at(1)+'"></i>':"")+'</div><span class="bar-value">'+esc(def.display(r.value))+"</span></div>";
}
function draw(){
 const def=QUERY[current],q=$("#explorer-search").value.toLowerCase().trim(),sort=$("#explorer-sort").value;
 const rows=items.filter(def.eligible).map(r=>{const lo=def.lo?.(r),hi=def.hi?.(r);return {raw:r,name:def.name(r),value:def.value(r),lo,hi,ci:Number.isFinite(lo)&&Number.isFinite(hi)&&lo<=hi,detail:def.detail(r)};}).filter(r=>Number.isFinite(r.value)&&r.value>=0&&(!q||(r.name+" "+r.detail+" "+(r.raw.factor??"")+" "+(r.raw.level??"")).toLowerCase().includes(q)));
 rows.sort((a,b)=>sort==="asc"?a.value-b.value:b.value-a.value);
 const selected=rows.slice(0,14),max=Math.max(1,...selected.map(r=>Math.max(r.value,r.ci?r.hi:0)));
 $("#explorer-chart").innerHTML=selected.length?selected.map(r=>bar(r,def,max)).join(""):failure("No data rows match these filters.");
 $("#chart-caption").textContent=def.caption+(selected.some(r=>r.ci)?" Bars show the estimate; lines show the 95% confidence interval.":"")+(def.ratio?" The dashed line marks 1×.":"")+" Displaying "+selected.length+" of "+rows.length+" eligible rows. Hover for more detail; inspect the source table below.";
 $("#explorer-table").innerHTML=dataRows(rows.slice(0,200).map(r=>r.raw));
}
async function dataset(name){
 if(!QUERY[name])return;
 current=name;const d=QUERY[name];
 $$("#dataset-options button").forEach(b=>{const active=b.dataset.dataset===name;b.classList.toggle("active",active);b.setAttribute("aria-pressed",String(active));});
 $("#dataset-tag").textContent=d.tag;$("#dataset-title").textContent=d.heading;$("#dataset-subtitle").textContent=d.description;$("#dataset-source").href=SOURCE+"outputs/tables/"+d.src;
 $("#explorer-chart").innerHTML="<p class='loading-line'>Loading analysis…</p>";
 try{const r=await resource("tables/"+d.src,"csv");if(name!==current)return;items=r;draw();}
 catch(e){if(name===current){items=[];$("#explorer-chart").innerHTML=failure("The analysis table is currently unavailable.");$("#explorer-table").innerHTML="";}}
}
function explorer(){
 $$("#dataset-options button").forEach(b=>b.addEventListener("click",()=>dataset(b.dataset.dataset)));
 $("#explorer-search").addEventListener("input",draw);$("#explorer-sort").addEventListener("change",draw);dataset("frequency");
}
function safeLink(url){
 if(url.startsWith("#"))return url;
 if(/^https?:\/\//i.test(url))return url;
 if(/^(reports|docs|outputs|src|data|scripts|tests)\//.test(url)&&!url.includes(".."))return SOURCE+url;
 return null;
}
function inline(s){
 const tokens=[];
 let escaped=esc(s.replace(/`([^`\n]+)`/g,(_,value)=>"ZZCOD"+(tokens.push("<code>"+esc(value)+"</code>")-1)+"ZZ"));
 escaped=escaped.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g,(_,name,url)=>{const u=safeLink(url.replace(/&amp;/g,"&"));return u?'<a href="'+esc(u)+'"'+(u.startsWith("http")?' target="_blank" rel="noopener noreferrer"':"")+'>'+name+"</a>":name;});
 escaped=escaped.replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>").replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g,"<em>$1</em>").replace(/(?<!\w)_([^_\n]+)_(?!\w)/g,"<em>$1</em>");
 return escaped.replace(/ZZCOD(\d+)ZZ/g,(_,id)=>tokens[+id]);
}
function markdown(input){
 const lines=input.replace(/\r\n?/g,"\n").split("\n"),result=[];let i=0;
 const split=row=>row.trim().replace(/^\|/,"").replace(/\|$/,"").split(/(?<!\\)\|/).map(v=>v.trim().replace(/\\\|/g,"|"));
 const indent=l=>l.length-l.trimStart().length;
 while(i<lines.length){
  const t=lines[i].trim();
  if(!t){i++;continue;}
  if(t.startsWith("<!--")){while(i<lines.length&&!lines[i].includes("-->"))i++;i++;continue;}
  if(t.startsWith("\x60\x60\x60")){
   const code=[];i++;while(i<lines.length&&!lines[i].trim().startsWith("\x60\x60\x60"))code.push(lines[i++]);i++;
   result.push("<pre><code>"+esc(code.join("\n"))+"</code></pre>");continue;
  }
  if(/^ {4}/.test(lines[i])&&(!i||!lines[i-1].trim())){
   const code=[];while(i<lines.length&&(/^ {4}/.test(lines[i])||(!lines[i].trim()&&i+1<lines.length&&/^ {4}/.test(lines[i+1]))))code.push(lines[i++].slice(4));
   result.push("<pre><code>"+esc(code.join("\n"))+"</code></pre>");continue;
  }
  const heading=/^(#{1,6})\s+(.+)$/.exec(t);
  if(heading){const n=heading[1].length;result.push("<h"+n+">"+inline(heading[2])+"</h"+n+">");i++;continue;}
  if(/^[-*_]{3,}$/.test(t)){result.push("<hr>");i++;continue;}
  if(t.startsWith("|")&&i+1<lines.length&&/^\|?[\s:|-]+\|/.test(lines[i+1].trim())){
   const head=split(lines[i]);i+=2;const rows=[];
   while(i<lines.length&&lines[i].trim().startsWith("|"))rows.push(split(lines[i++]));
   result.push('<div class="md-table"><table><thead><tr>'+head.map(x=>"<th>"+inline(x)+"</th>").join("")+"</tr></thead><tbody>"+rows.map(row=>"<tr>"+head.map((_,j)=>"<td>"+inline(row[j]||"")+"</td>").join("")+"</tr>").join("")+"</tbody></table></div>");continue;
  }
  if(t.startsWith(">")){const q=[];while(i<lines.length&&lines[i].trim().startsWith(">"))q.push(lines[i++].trim().replace(/^>\s?/,""));result.push("<blockquote>"+q.map(inline).join(" ")+"</blockquote>");continue;}
  if(/^(?:[-*+]|\d+[.)])\s+/.test(t)){
   const ordered=/^\d/.test(t),mark=ordered?/^\d+[.)]\s+/:/^[-*+]\s+/,base=indent(lines[i]),start=parseInt(t,10),items=[];
   const sibling=l=>indent(l)-base<2&&mark.test(l.trim());
   while(i<lines.length&&sibling(lines[i])){
    const body=[lines[i++].trim().replace(mark,"")];
    for(;i<lines.length;i++){
     const l=lines[i];
     if(!l.trim()){let j=i+1;while(j<lines.length&&!lines[j].trim())j++;if(j<lines.length&&indent(lines[j])-base>=2){body.push("");continue;}if(j<lines.length&&sibling(lines[j]))i=j;break;}
     if(indent(l)-base<2)break;
     body.push(l.slice(Math.min(indent(l),base+2)));
    }
    const html=markdown(body.join("\n"));
    items.push("<li>"+(body.includes("")?html:html.replace(/^<p>([^\n]*)<\/p>/,"$1"))+"</li>");
   }
   const tag=ordered?"ol":"ul";result.push("<"+tag+(ordered&&start!==1?' start="'+start+'"':"")+">"+items.join("")+"</"+tag+">");continue;
  }
  const paragraph=[];
  while(i<lines.length&&lines[i].trim()&&!/^(#{1,6}\s|[-*+]\s|1[.)]\s|>\s?)/.test(lines[i].trim())&&!lines[i].trim().startsWith("\x60\x60\x60")&&!(lines[i].trim().startsWith("|")&&i+1<lines.length&&/^\|?[\s:|-]+\|/.test(lines[i+1].trim())))paragraph.push(lines[i++].trim());
  if(paragraph.length)result.push("<p>"+inline(paragraph.join(" "))+"</p>");else i++;
 }
 return result.join("\n");
}
let reportRequest=0;
async function report(key){
 const selection=REPORTS.find(r=>r[0]===key);if(!selection)return;
 const request=++reportRequest,article=$("#report-article");
 $$("#report-list button").forEach(b=>{const on=b.dataset.report===key;b.classList.toggle("active",on);if(on)b.setAttribute("aria-current","true");else b.removeAttribute("aria-current");});
 article.innerHTML="<p class='loading-line'>Loading full report…</p>";
 try{
  const text=await resource("reports/"+key+".md");
  if(request!==reportRequest)return;
  article.innerHTML='<div class="report-top"><span>FULL RESEARCH REPORT · GENERATED</span><a target="_blank" rel="noopener noreferrer" href="'+esc(SOURCE+selection[2])+'">Inspect original source ↗</a></div><div class="report-body">'+markdown(text)+"</div>";
  article.scrollTop=0;
 }catch(e){if(request===reportRequest)article.innerHTML=failure("This report is unavailable. The original is in the GitHub repository.");}
}
function library(){
 $("#report-list").innerHTML=REPORTS.map((r,i)=>'<button type="button" data-report="'+esc(r[0])+'" class="report-choice">'+String(i+1).padStart(2,"0")+" · "+esc(r[1])+"</button>").join("");
 document.addEventListener("click",e=>{
  const button=e.target.closest("button[data-report]");if(button&&$("#report-list").contains(button)){report(button.dataset.report);return;}
  const link=e.target.closest("a[data-report]");if(link)report(link.dataset.report);
 });
 report("findings");
}
/* ---------- Story charts: drawn at runtime from the bundled CSV snapshots ---------- */
const SVG_COLORS={ink:"#102734",green:"#117963",amber:"#b9791b",blue:"#4b5fa8",red:"#a8423a",grey:"#6b7f8a"};
const fmt={int:integer,pct:(v,d=0)=>(v*100).toFixed(d)+"%",delta:v=>(v<0?"−":"+")+Math.abs(v*100).toFixed(0)+"%",times:v=>v.toFixed(1)};
const table=async name=>resource("tables/"+name,"csv");
const byKey=(rows,key,order)=>order.map(k=>rows.find(r=>r[key]===k)).filter(Boolean);
function legend(items,line){return '<div class="legend">'+items.map(i=>"<span><i class='"+(line?"line":"")+"' style='background:"+i.color+"'></i>"+esc(i.name)+"</span>").join("")+"</div>";}
function lineChart(host,readout,cfg){
 const W=Math.max(260,Math.floor(host.clientWidth)||600),H=W<480?250:300,narrow=W<480;
 const m={l:narrow?44:54,r:cfg.endLabel?(narrow?36:46):14,t:24,b:28};
 const xs=[...new Set(cfg.series.flatMap(s=>s.pts.map(p=>p[0])))].sort((a,b)=>a-b);
 const lo=cfg.ticks[0],hi=cfg.ticks[cfg.ticks.length-1];
 const X=x=>m.l+(x-xs[0])/(xs[xs.length-1]-xs[0])*(W-m.l-m.r),Y=y=>H-m.b-(y-lo)/(hi-lo)*(H-m.t-m.b);
 let out='<svg role="img" aria-label="'+esc(cfg.label)+'" viewBox="0 0 '+W+" "+H+'" width="'+W+'" height="'+H+'" style="touch-action:pan-y">';
 cfg.ticks.forEach(t=>{out+='<line class="ax-grid" x1="'+m.l+'" x2="'+(W-m.r)+'" y1="'+Y(t)+'" y2="'+Y(t)+'"/><text class="ax-text" x="'+(m.l-8)+'" y="'+(Y(t)+3.5)+'" text-anchor="end">'+esc(cfg.yFmt(t))+"</text>";});
 if(cfg.ref!=null)out+='<line class="ax-ref" x1="'+m.l+'" x2="'+(W-m.r)+'" y1="'+Y(cfg.ref)+'" y2="'+Y(cfg.ref)+'"/>';
 xs.forEach((x,i)=>{if(narrow&&i%2)return;out+='<text class="ax-text" x="'+X(x)+'" y="'+(H-8)+'" text-anchor="middle">'+x+"</text>";});
 cfg.series.forEach(se=>{
  out+='<path class="series-line" stroke="'+se.color+'" d="'+se.pts.map((p,i)=>(i?"L":"M")+X(p[0]).toFixed(1)+" "+Y(p[1]).toFixed(1)).join("")+'"/>';
  se.pts.forEach(p=>{out+='<circle class="series-dot" fill="'+se.color+'" r="'+(cfg.series.length>2?2.5:3.5)+'" cx="'+X(p[0]).toFixed(1)+'" cy="'+Y(p[1]).toFixed(1)+'"/>';});
 });
 (cfg.labelPts||[]).forEach(l=>{
  const p=cfg.series[0].pts.find(q=>q[0]===l.x);if(!p)return;
  const last=l.x===xs[xs.length-1],first=l.x===xs[0];
  out+='<text class="pt-label" x="'+(X(l.x)+(last?4:0))+'" y="'+(Y(p[1])+(l.pos==="below"?20:-10))+'" text-anchor="'+(last?"end":first?"start":"middle")+'">'+esc(cfg.valueFmt(p[1]))+"</text>";
 });
 if(cfg.endLabel){
  const ends=cfg.series.map(se=>({se,y:Y(se.pts[se.pts.length-1][1]),v:se.pts[se.pts.length-1][1]})).sort((a,b)=>a.y-b.y);
  for(let i=1;i<ends.length;i++)if(ends[i].y-ends[i-1].y<13)ends[i].y=ends[i-1].y+13;
  ends.forEach(e=>{out+='<text class="end-label" fill="'+e.se.color+'" x="'+(W-m.r+6)+'" y="'+(e.y+4)+'">'+esc(cfg.endLabel(e.v))+"</text>";});
 }
 out+='<line class="guide" y1="'+m.t+'" y2="'+(H-m.b)+'" visibility="hidden"/>';
 cfg.series.forEach((se,i)=>{out+='<circle class="series-dot hover-dot" data-s="'+i+'" r="5" fill="'+se.color+'" visibility="hidden"/>';});
 out+='<rect class="hit" x="'+m.l+'" y="0" width="'+(W-m.l-m.r)+'" height="'+(H-m.b)+'" fill="transparent"/></svg>';
 host.innerHTML=(cfg.series.length>1?legend(cfg.series,true):"")+out+(cfg.axisNote?'<div class="hb-axis">'+esc(cfg.axisNote)+"</div>":"");
 const svg=$("svg",host),guide=$(".guide",svg),dots=$$(".hover-dot",svg),hint=cfg.hint||"Hover or tap the chart to read a year.";
 if(readout)readout.textContent=hint;
 const show=ev=>{
  const box=svg.getBoundingClientRect(),px=(ev.clientX-box.left)*(W/box.width);
  const x=xs.reduce((best,v)=>Math.abs(X(v)-px)<Math.abs(X(best)-px)?v:best,xs[0]);
  guide.setAttribute("x1",X(x));guide.setAttribute("x2",X(x));guide.setAttribute("visibility","visible");
  const parts=[];
  cfg.series.forEach((se,i)=>{const p=se.pts.find(q=>q[0]===x);if(!p){dots[i].setAttribute("visibility","hidden");return;}dots[i].setAttribute("cx",X(x));dots[i].setAttribute("cy",Y(p[1]));dots[i].setAttribute("visibility","visible");parts.push((cfg.series.length>1?se.name+" ":"")+cfg.valueFmt(p[1]));});
  if(readout)readout.textContent=x+": "+parts.join(" · ");
 };
 svg.addEventListener("pointermove",show);svg.addEventListener("pointerdown",show);
 svg.addEventListener("pointerleave",()=>{guide.setAttribute("visibility","hidden");dots.forEach(d=>d.setAttribute("visibility","hidden"));if(readout)readout.textContent=hint;});
}
function hBars(host,cfg){
 const at=v=>(Math.max(0,Math.min(v,cfg.max))/cfg.max*100).toFixed(2)+"%";
 host.innerHTML='<div class="hb" role="img" aria-label="'+esc(cfg.label)+'">'+cfg.rows.map(r=>'<div class="hb-row"><div class="hb-label">'+esc(r.label)+(r.sub?"<small>"+esc(r.sub)+"</small>":"")+'</div><div class="hb-track"><i class="hb-fill" style="width:'+at(r.v)+(r.color?";background:"+r.color:"")+'"></i>'+(Number.isFinite(r.lo)&&Number.isFinite(r.hi)?'<i class="hb-ci" style="left:'+at(r.lo)+";width:"+(Math.min(r.hi,cfg.max)/cfg.max*100-Math.min(r.lo,cfg.max)/cfg.max*100).toFixed(2)+'%"></i>':"")+'</div><div class="hb-value">'+esc(r.text)+"</div></div>").join("")+"</div>"+(cfg.axisNote?'<div class="hb-axis">'+esc(cfg.axisNote)+"</div>":"");
}
function groupedBars(host,cfg){
 const W=Math.max(260,Math.floor(host.clientWidth)||600),H=W<480?270:310,m={l:W<480?40:50,r:10,t:30,b:40};
 const lo=cfg.ticks[0],hi=cfg.ticks[cfg.ticks.length-1],Y=y=>H-m.b-(y-lo)/(hi-lo)*(H-m.t-m.b);
 const nb=cfg.series.length,band=(W-m.l-m.r)/cfg.groups.length,bw=Math.min(70,band*.78/nb),gap=6;
 let out='<svg role="img" aria-label="'+esc(cfg.label)+'" viewBox="0 0 '+W+" "+H+'" width="'+W+'" height="'+H+'">';
 cfg.ticks.forEach(t=>{out+='<line class="ax-grid" x1="'+m.l+'" x2="'+(W-m.r)+'" y1="'+Y(t)+'" y2="'+Y(t)+'"/><text class="ax-text" x="'+(m.l-8)+'" y="'+(Y(t)+3.5)+'" text-anchor="end">'+esc(cfg.yFmt(t))+"</text>";});
 cfg.groups.forEach((g,gi)=>{
  const gw=nb*bw+(nb-1)*gap,x0=m.l+band*gi+(band-gw)/2;
  g.bars.forEach((b,bi)=>{
   const x=x0+bi*(bw+gap),c=x+bw/2,top=Y(b.v);
   out+='<rect x="'+x.toFixed(1)+'" y="'+top.toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+(Y(lo)-top).toFixed(1)+'" fill="'+cfg.series[bi].color+'"/>';
   let labelY=top;
   if(Number.isFinite(b.lo)&&Number.isFinite(b.hi)){out+='<line class="col-ci" x1="'+c+'" x2="'+c+'" y1="'+Y(b.lo)+'" y2="'+Y(b.hi)+'"/><line class="col-ci" x1="'+(c-6)+'" x2="'+(c+6)+'" y1="'+Y(b.lo)+'" y2="'+Y(b.lo)+'"/><line class="col-ci" x1="'+(c-6)+'" x2="'+(c+6)+'" y1="'+Y(b.hi)+'" y2="'+Y(b.hi)+'"/>';labelY=Y(b.hi);}
   out+='<text class="pt-label" x="'+c+'" y="'+(labelY-8)+'" text-anchor="middle">'+esc(cfg.valueFmt(b.v))+"</text>";
  });
  out+='<text class="ax-text" x="'+(m.l+band*(gi+.5))+'" y="'+(H-14)+'" text-anchor="middle" style="font-size:12px;font-weight:600">'+esc(g.label)+"</text>";
 });
 out+='<line class="ax-line" x1="'+m.l+'" x2="'+(W-m.r)+'" y1="'+Y(lo)+'" y2="'+Y(lo)+'"/></svg>';
 host.innerHTML=legend(cfg.series,false)+out;
}
const levelRows=(rows,factor,order)=>order.map(l=>rows.find(r=>r.factor===factor&&r.level===l)).filter(Boolean);
const STORIES={
 async deaths(){
  const rows=await table("descriptive/fars_annual.csv"),pts=rows.map(r=>[+r.YEAR,+r.deaths]);
  const label="Line chart of US road deaths per year, "+pts.map(p=>p[0]+": "+integer(p[1])).join("; ")+".";
  return {table:{head:["Year","Fatal crashes","Deaths"],rows:rows.map(r=>[r.YEAR,integer(+r.fatal_crashes),integer(+r.deaths)])},
   draw:(h,ro)=>lineChart(h,ro,{label,series:[{name:"Deaths",color:SVG_COLORS.green,pts}],ticks:[30000,35000,40000,45000],yFmt:integer,valueFmt:integer,labelPts:[{x:2019,pos:"below"},{x:2021,pos:"above"},{x:2024,pos:"below"}],axisNote:"The vertical axis starts at "+integer(30000)+" deaths."})};
 },
 async changes(){
  const rows=await table("trends/fars_changes.csv"),names={motorcyclist_deaths:"Motorcyclists",pedestrian_deaths:"Pedestrians",lpv_occupant_deaths:"Car, SUV, pickup and van occupants"};
  const sel=byKey(rows,"indicator",Object.keys(names)),data=sel.map(r=>({label:names[r.indicator],sub:integer(+r["2019"])+" → "+integer(+r["2024"])+" deaths",v:+r.pct_change_2019_2024,text:fmt.delta(+r.pct_change_2019_2024/100)}));
  return {table:{head:["Road users","Deaths 2019","Deaths 2024","Change","Percent change","Share of total change","Share of all deaths in 2019"],rows:sel.map(r=>[names[r.indicator],integer(+r["2019"]),integer(+r["2024"]),integer(+r.change_2019_2024),(+r.pct_change_2019_2024).toFixed(1)+"%",fmt.pct(+r.share_of_total_change_2019_2024,1),fmt.pct(+r.share_of_total_2019,1)])},
   draw:h=>hBars(h,{max:25,rows:data,label:"Bar chart of the percent change in deaths from 2019 to 2024: "+data.map(d=>d.label+" "+d.text+" ("+d.sub+")").join("; ")+"."})};
 },
 async indexed(){
  const rows=(await table("descriptive/fars_annual.csv")).sort((a,b)=>a.YEAR-b.YEAR),base=rows[0];
  const defs=[["deaths_pedestrian","Pedestrians",SVG_COLORS.green],["deaths_cyclist","Cyclists",SVG_COLORS.amber],["deaths_driver","Drivers",SVG_COLORS.blue],["deaths_passenger","Passengers",SVG_COLORS.red]];
  const series=defs.map(([k,name,color])=>({name,color,pts:rows.map(r=>[+r.YEAR,+r[k]/+base[k]*100])}));
  const label="Line chart of deaths by road user relative to "+base.YEAR+" (index 100). In "+rows[rows.length-1].YEAR+": "+series.map(s=>s.name+" "+Math.round(s.pts[s.pts.length-1][1])).join(", ")+".";
  return {table:{head:["Year",...defs.map(d=>d[1]+" (deaths)"),...defs.map(d=>d[1]+" (index)")],rows:rows.map(r=>[r.YEAR,...defs.map(d=>integer(+r[d[0]])),...defs.map(d=>(+r[d[0]]/+base[d[0]]*100).toFixed(1))])},
   draw:(h,ro)=>lineChart(h,ro,{label,series,ticks:[80,100,120,140],ref:100,yFmt:String,valueFmt:v=>v.toFixed(0),endLabel:v=>v.toFixed(0),axisNote:"Index: deaths in "+base.YEAR+" = "+integer(100)+"."})};
 },
 async striking(){
  const rows=await table("vulnerable/fars_pedestrian_deaths_by_striking_vehicle.csv").then(r=>r.sort((a,b)=>a.YEAR-b.YEAR));
  const defs=[["share_car","Car",SVG_COLORS.grey],["share_suv","SUV",SVG_COLORS.green],["share_pickup","Pickup",SVG_COLORS.amber],["share_large","Large truck or bus",SVG_COLORS.blue],["share_van","Van",SVG_COLORS.red]];
  const series=defs.map(([k,name,color])=>({name,color,pts:rows.map(r=>[+r.YEAR,+r[k]*100])})),last=rows[rows.length-1];
  const label="Line chart of the share of pedestrian deaths by striking vehicle type. In "+last.YEAR+": "+defs.map(d=>d[1]+" "+fmt.pct(+last[d[0]])).join(", ")+".";
  return {table:{head:["Year","Pedestrian deaths",...defs.map(d=>d[1]+" (share)")],rows:rows.map(r=>[r.YEAR,integer(["deaths_car","deaths_large","deaths_motorcycle","deaths_other_unknown","deaths_pickup","deaths_suv","deaths_van"].reduce((t,k)=>t+ +r[k],0)),...defs.map(d=>fmt.pct(+r[d[0]],1))])},
   draw:(h,ro)=>lineChart(h,ro,{label,series,ticks:[0,10,20,30,40],yFmt:v=>v+"%",valueFmt:v=>v.toFixed(1)+"%",endLabel:v=>v.toFixed(0)+"%",axisNote:"The remaining deaths are motorcycles and other or unknown vehicle types."})};
 },
 async speed(){
  const rows=levelRows(await table("vulnerable/pedestrian_killed_contrasts.csv"),"str_speed_limit",["<=25","30-35","40-45","50-55","60-65","70+"]);
  const data=rows.map(r=>({label:levelText(r.level),sub:"of "+integer(+r.n)+" struck",v:+r.crude_rate,text:fmt.pct(+r.crude_rate,1)}));
  return {table:{head:["Speed limit","Struck pedestrians (sample)","Killed","Share killed"],rows:rows.map(r=>[levelText(r.level),integer(+r.n),integer(+r.n_events),fmt.pct(+r.crude_rate,1)])},
   draw:h=>hBars(h,{max:.5,rows:data,label:"Bar chart of the share of struck pedestrians who died, by speed limit: "+data.map(d=>d.label+" "+d.text).join("; ")+"."})};
 },
 async lighttruck(){
  const all=await table("vulnerable/pedestrian_light_truck_by_speed.csv"),get=q=>all.find(r=>r.quantity===q);
  const pair=sp=>[get("risk car "+sp),get("risk SUV/pickup "+sp)].map(r=>({v:+r.estimate,lo:+r.low,hi:+r.high}));
  const groups=[{label:"≤35 mph",bars:pair("<=35")},{label:"40+ mph",bars:pair("40+")}],series=[{name:"Struck by a car",color:SVG_COLORS.grey},{name:"Struck by an SUV or pickup",color:SVG_COLORS.green}];
  const label="Grouped bar chart with 95% confidence intervals of the adjusted share of struck pedestrians who died. "+groups.map(g=>g.label+": "+g.bars.map((b,i)=>series[i].name+" "+fmt.pct(b.v,1)+" ("+fmt.pct(b.lo,1)+" to "+fmt.pct(b.hi,1)+")").join(", ")).join("; ")+".";
  const keep=all.filter(r=>r.quantity.startsWith("risk")||r.quantity.startsWith("RR"));
  return {table:{head:["Quantity","Estimate","95% CI low","95% CI high"],rows:keep.map(r=>[r.quantity,r.quantity.startsWith("risk")?fmt.pct(+r.estimate,1):(+r.estimate).toFixed(2),r.quantity.startsWith("risk")?fmt.pct(+r.low,1):(+r.low).toFixed(2),r.quantity.startsWith("risk")?fmt.pct(+r.high,1):(+r.high).toFixed(2)])},
   draw:h=>groupedBars(h,{label,groups,series,ticks:[0,.05,.1,.15,.2],yFmt:v=>fmt.pct(v),valueFmt:v=>fmt.pct(v,1)})};
 },
 async tod(){
  const rows=levelRows(await table("descriptive/frequency_vs_severity.csv"),"tod",["00-05","06-09","10-15","16-19","20-23"]);
  const data=rows.map(r=>({label:levelText(r.level),sub:fmt.pct(+r.share_all_crashes)+" of crashes · "+fmt.pct(+r.share_fatal_fars)+" of fatal crashes",v:+r.fatal_rate,lo:+r.fatal_rate_low,hi:+r.fatal_rate_high,text:fmt.pct(+r.fatal_rate,2)}));
  return {table:{head:["Time of day","Share of crashes","Share of fatal crashes (FARS)","Share fatal","95% CI low","95% CI high"],rows:rows.map(r=>[levelText(r.level),fmt.pct(+r.share_all_crashes,1),fmt.pct(+r.share_fatal_fars,1),fmt.pct(+r.fatal_rate,2),fmt.pct(+r.fatal_rate_low,2),fmt.pct(+r.fatal_rate_high,2)])},
   draw:h=>hBars(h,{max:.02,rows:data,label:"Bar chart with 95% confidence intervals of the share of police-reported crashes that were fatal, by time of day: "+data.map(d=>d.label+" "+d.text).join("; ")+"."})};
 },
 async age(){
  const rows=levelRows(await table("person/lpv_killed_crude_vs_adjusted.csv"),"age_band",["8-14","15-20","21-24","25-34","35-44","45-54","55-64","65-74","75+"]);
  const data=rows.map(r=>({label:"Age "+r.level.replace("-","–"),sub:+r.A_adj_rr===1?"reference for the adjusted ratio":"adjusted ratio "+fmt.times(+r.A_adj_rr)+"×",v:+r.rate,lo:+r.ci_low,hi:+r.ci_high,text:fmt.pct(+r.rate,2)}));
  return {table:{head:["Age","Persons (sample)","Share killed","95% CI low","95% CI high","Adjusted ratio","95% CI low","95% CI high"],rows:rows.map(r=>[r.level,integer(+r.n),fmt.pct(+r.rate,2),fmt.pct(+r.ci_low,2),fmt.pct(+r.ci_high,2),(+r.A_adj_rr).toFixed(2),(+r.A_adj_rr_low).toFixed(2),(+r.A_adj_rr_high).toFixed(2)])},
   draw:h=>hBars(h,{max:.007,rows:data,label:"Bar chart with 95% confidence intervals of the share of car, SUV, pickup and van occupants killed, by age: "+data.map(d=>d.label+" "+d.text).join("; ")+"."})};
 },
 async rural(){
  const all=await table("stages/death_timing.csv"),pick=g=>all.find(r=>r.group===g),rural=pick("rural road"),urban=pick("urban road");
  const series=[{name:"Died at the scene",color:SVG_COLORS.green},{name:"Died within one hour of the crash",color:SVG_COLORS.amber}];
  const groups=[["Rural roads",rural],["Urban roads",urban]].map(([label,r])=>({label,bars:[{v:+r.share_died_at_scene},{v:+r.share_within_1_hour}]}));
  const label="Grouped bar chart of the share of people killed who died at the scene or within one hour. "+groups.map(g=>g.label+": "+g.bars.map((b,i)=>series[i].name+" "+fmt.pct(b.v)).join(", ")).join("; ")+".";
  return {table:{head:["Road","Deaths","Died at the scene","Died within one hour"],rows:[rural,urban].map(r=>[r.group,integer(+r.deaths),fmt.pct(+r.share_died_at_scene,1),fmt.pct(+r.share_within_1_hour,1)])},
   draw:h=>groupedBars(h,{label,groups,series,ticks:[0,.2,.4,.6,.8],yFmt:v=>fmt.pct(v),valueFmt:v=>fmt.pct(v)})};
 }
};
async function stories(){
 await Promise.all($$("figure.chart[data-chart]").map(async fig=>{
  const host=$(".chart-body",fig),make=STORIES[fig.dataset.chart];
  try{
   const spec=await make(),readout=$(".chart-readout",fig),render=()=>spec.draw(host,readout);
   render();
   $("table",fig).innerHTML="<thead><tr>"+spec.table.head.map(x=>"<th scope='col'>"+esc(x)+"</th>").join("")+"</tr></thead><tbody>"+spec.table.rows.map(r=>"<tr>"+r.map(x=>"<td>"+esc(x)+"</td>").join("")+"</tr>").join("")+"</tbody>";
   if(typeof ResizeObserver==="function"){let width=host.clientWidth;new ResizeObserver(()=>{if(Math.abs(host.clientWidth-width)>1){width=host.clientWidth;render();}}).observe(host);}
  }catch(e){host.innerHTML=failure("This chart could not be loaded; the table is in the repository.");}
 }));
}
function init(){menu();stories();explorer();library();}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
