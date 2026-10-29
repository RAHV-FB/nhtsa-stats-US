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
 frequency:{src:"descriptive/frequency_vs_severity.csv",heading:"Frequency versus fatal severity",tag:"01",description:"The share of fatal crashes divided by the share of police-reported crashes. Higher ratios mean over-representation, not causation.",caption:"FARS census numerator and CRSS survey-weighted denominator. Uncertainty is reported in the source table.",ratio:true,value:r=>+r.overrep_ratio,lo:r=>num(r.overrep_low),hi:r=>num(r.overrep_high),name:r=>factorText(r.factor,r.label)+" · "+levelText(r.level),detail:r=>"Fatal crash share: "+percent(+r.share_fatal_fars)+"; all crashes: "+percent(+r.share_all_crashes)+"; 95% CI "+ratio(+r.overrep_low)+"–"+ratio(+r.overrep_high),display:v=>ratio(v)+"×",eligible:r=>r.overrep_ratio!==""},
 severity:{src:"severity/fatal_crude_vs_adjusted.csv",heading:"Crude versus adjusted severity",tag:"02",description:"Model A fatal-crash risk ratios after accounting for recorded pre-crash circumstances. Reference categories have ratio 1 and are excluded from the bar chart.",caption:"CRSS, 2016–2024. The table includes crude, model A and model B estimates, with confidence intervals. Adjusted estimates are not causal effects.",ratio:true,value:r=>+r.A_adj_rr,lo:r=>num(r.A_adj_rr_low),hi:r=>num(r.A_adj_rr_high),name:r=>factorText(r.factor)+" · "+levelText(r.level),detail:r=>"Crude RR "+ratio(+r.crude_rr)+"; adjusted RR "+ratio(+r.A_adj_rr)+"; 95% CI "+ratio(+r.A_adj_rr_low)+"–"+ratio(+r.A_adj_rr_high),display:v=>ratio(v)+"×",eligible:r=>r.A_adj_rr!==""&&+r.A_adj_rr!==1&&!(r.adj_flag||"").toLowerCase().includes("suppress")},
 attribution:{src:"contributions/ranking.csv",heading:"Ranking depends on the question",tag:"03",description:"Adjusted crash-level associations for the factors that can be ranked. Drug status and occupant-level restraint effects cannot be ranked on the same basis.",caption:"Phase 2 standardised adjusted risk ratios, not causal fractions. The underlying table includes other possible rankings and unrankable factors.",ratio:true,value:r=>+r.adjusted_rr,name:r=>({"exceeded":"Exceeded speed limit / racing","speeding_other":"Other speeding","alcohol":"Alcohol involved"}[r.factor]||pretty(r.factor)),detail:r=>r.note||"Model-based association",display:v=>ratio(v)+"×",eligible:r=>r.rankable==="True"},
 trends:{src:"descriptive/fars_annual.csv",heading:"Annual US road deaths",tag:"04",description:"The fatal-crash census counts deaths each year. They are not rates per trip or per mile.",caption:"FARS observed death counts, 2016–2024. Interpret changes separately from exposure and changes in nonfatal crash reporting.",value:r=>+r.deaths,name:r=>r.YEAR,detail:r=>"Fatal crashes: "+integer(+r.fatal_crashes)+"; deaths: "+integer(+r.deaths),display:v=>integer(v),eligible:r=>true}
};
const FACTORS={
 speed:{kind:"ADJUSTED ASSOCIATION",title:"Alcohol does not explain away speeding.",body:"Exceeding the speed limit / racing has a crude fatal crash risk ratio of 10.0. Alcohol adjustment alone reduces this to about 7.0, and full adjustment to 4.88. Alcohol accounts for around 9% of the original log association under Shapley accounting. The finding is conditional on a reported crash and remains vulnerable to post-crash recording differences and unmeasured circumstances.",headline:"4.88×",stat:"Fully adjusted fatal risk ratio (95% CI 4.12–5.79)",caution:"Police-recorded speeding is not a directly measured travel speed; a conditional association is not a speed-camera effect.",report:"speeding_confounding"},
 alcohol:{kind:"INDEPENDENT ASSOCIATION",title:"Alcohol retains a substantial association of its own.",body:"Speeding type accounts for only around 4% of alcohol’s crude log association with fatal crashes. FARS estimates 105,821 deaths in crashes involving a driver at BAC ≥ 0.08 across 2016–2024, using imputed alcohol status. Those deaths overlap with those counted under speeding, drugs and non-use of restraints. Association and involvement are not the same as individual causal attribution.",headline:"105,821",stat:"Deaths in BAC ≥ 0.08 crashes, 2016–2024 (multiple imputation)",caution:"The count is not a number of deaths exclusively caused by alcohol; exposure coding and selection remain important.",report:"factor_contributions"},
 drugs:{kind:"NOT IDENTIFIABLE",title:"Missing drug testing prevents a reliable ranking.",body:"In fatal crashes, 62% of killed drivers were tested for drugs, but only 19% of surviving drivers were tested. Police-reported drug status is frequently unknown. Changing how unknowns are allocated produces dramatically different estimates. Detecting a drug does not establish impairment. This study therefore refuses to rank population-wide drug fatality severity alongside the other factors.",headline:"Not ranked",stat:"Drug severity association not reliably identified",caution:"Selective testing and missingness make a precise population-wide estimate unjustifiable.",report:"alcohol_drugs_restraints"},
 belts:{kind:"WITHIN-VEHICLE COMPARISON",title:"Belt use is associated with lower death risk within the same vehicle.",body:"In matched within-vehicle comparisons among fatal crashes, the estimated death risk ratio for belted versus unbelted front occupants is approximately 0.34. The estimate varies by crash configuration and is highly sensitive to survivors’ potential over-reporting of belt use. It measures a different stage of harm from factors associated with crash occurrence or energy.",headline:"0.34×",stat:"Belted versus unbelted death risk (95% CI 0.33–0.35)",caution:"Conditional on a fatal crash; reporting bias changes the estimated magnitude.",report:"alcohol_drugs_restraints"}
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
async function findings(){
 const node=$("#findings-list"),filter=$("#finding-search"),kind=$("#finding-kind");
 try{
  const data=await resource("findings.json","json");if(!Array.isArray(data))throw Error("Not a findings array");
  [...new Set(data.map(x=>x.kind||"adjusted"))].sort().forEach(k=>{const opt=document.createElement("option");opt.value=k;opt.textContent=k;kind.append(opt);});
  function render(){
   const q=filter.value.toLowerCase().trim(),k=kind.value;
   const subset=data.map((f,i)=>({f,i})).filter(({f})=>(!k||f.kind===k)&&(!q||Object.values(f).some(v=>typeof v==="string"&&v.toLowerCase().includes(q))));
   node.innerHTML=subset.length?subset.map(({f,i})=>{
    const fields=[["Effect",f.effect],["Uncertainty",f.uncertainty],["Population",f.population],["Denominator",f.denominator],["Adjustment",f.adjustment],["Robustness",f.robustness],["Limitations",f.limitations],["Evidence table",f.evidence]].filter(x=>x[1]);
    return '<details class="finding"><summary><span class="finding-count">'+String(i+1).padStart(2,"0")+'</span><span class="finding-name">'+esc(f.title)+'</span><span class="finding-arrow" aria-hidden="true">+</span></summary><div class="finding-content"><span class="kind-tag">'+esc(f.kind||"adjusted")+'</span><p>'+esc(f.statement)+'</p><dl>'+fields.map(([key,val])=>"<dt>"+esc(key)+"</dt><dd>"+esc(val)+"</dd>").join("")+"</dl></div></details>";
   }).join(""):failure("No findings match the current filters.");
  }
  filter.addEventListener("input",render);kind.addEventListener("change",render);render();
 }catch(e){node.innerHTML=failure("Findings could not be loaded; see the research report in GitHub.");}
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
function factor(key){
 const f=FACTORS[key];if(!f)return;
 $$("#factor-tabs button").forEach(b=>{const on=b.dataset.factor===key;b.classList.toggle("active",on);b.setAttribute("aria-selected",String(on));b.tabIndex=on?0:-1;});
 $("#factor-panel").setAttribute("aria-labelledby","tab-"+key);
 $("#factor-panel").innerHTML='<div><div class="evidence-type">'+esc(f.kind)+'</div><h4>'+esc(f.title)+'</h4><p>'+esc(f.body)+'</p></div><div class="factor-detail"><h5>Research result</h5><div class="big">'+esc(f.headline)+'</div><p>'+esc(f.stat)+'</p><h5>Evidence limitation</h5><p>'+esc(f.caution)+'</p><a href="#library" data-report="'+esc(f.report)+'">Read the full analysis ↗</a></div>';
}
async function overlap(){
 try{
  const rows=await resource("tables/contributions/fars_overlap_summary.csv","csv");
  const labels={"speeding-related crash":"Speeding-related crash","driver BAC >= .08 (MI)":"BAC ≥ 0.08 driver","driver drug-positive (determinate crashes only)":"Drug-positive driver*","victim an unbelted vehicle occupant":"Unbelted occupant"};
  const data=rows.filter(r=>labels[r.factor]),max=Math.max(...data.map(r=>+r.deaths));
  $("#overlap-chart").innerHTML=data.map(r=>'<div class="factor-count-row"><span class="factor-count-label">'+esc(labels[r.factor])+'</span><span class="factor-count-value">'+integer(+r.deaths)+'</span><div class="factor-count-track"><div class="factor-count-fill" style="width:'+(+r.deaths/max*100).toFixed(1)+'%"></div></div></div>').join("");
 }catch(e){$("#overlap-chart").innerHTML=failure("The source counts are not currently available.");}
}
function factors(){
 const buttons=$$("#factor-tabs button");
 buttons.forEach((b,i)=>{b.addEventListener("click",()=>factor(b.dataset.factor));b.addEventListener("keydown",e=>{if(["ArrowRight","ArrowLeft"].includes(e.key)){e.preventDefault();const next=buttons[(i+(e.key==="ArrowRight"?1:buttons.length-1))%buttons.length];factor(next.dataset.factor);next.focus();}});});
 factor("speed");overlap();
}
async function policy(){
 const select=$("#policy-factor"),range=$("#policy-target");
 const groups={alcohol:"alcohol",speeding:"speeding",exceeded:"speeding_exceeded_limit",unbelted:"unrestrained_lpv",drugs:"drugs"};
 try{
  const values=await resource("tables/simulation/threshold_required_share.csv","csv");
  function render(){
   const target=+range.value;$("#policy-target-label").textContent=target+"%";
   const row=values.find(r=>r.segment===groups[select.value]);
   if(!row){$("#policy-percent").textContent="—";return;}
   const total=+row.all_deaths_per_year,segment=+row.segment_deaths_per_year,deaths=total*target/100,share=100*deaths/segment;
   $("#policy-percent").textContent=share.toFixed(1)+"%";
   $("#policy-explainer").textContent="2022–2024 annual baseline: "+integer(total)+" road deaths; "+integer(segment)+" in the selected segment. Preventing "+integer(deaths)+" road deaths nationally requires preventing "+share.toFixed(1)+"% of this segment’s deaths."+(share>100?" Not feasible through this segment alone.":"")+(select.value==="drugs"?" *Lower bound due to drug-testing missingness.":"");
  }
  select.addEventListener("change",render);range.addEventListener("input",render);render();
 }catch(e){$("#policy-percent").textContent="—";$("#policy-explainer").textContent="The baseline data cannot be loaded.";}
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
 escaped=escaped.replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>").replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g,"<em>$1</em>").replace(/(?<!\w)_([^_\n]+)_(?!\w)/g,"<em>$1</em>");
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
function init(){menu();findings();explorer();factors();policy();library();}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
