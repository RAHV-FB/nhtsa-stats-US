import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const root = path.resolve(import.meta.dirname, "..");
const read = name => fs.readFileSync(path.join(root, name), "utf8");
const html = read("index.html");
const css = read("assets/site.css");
const script = read("assets/site.js");
assert.ok(html.includes('<html lang="en">'));
assert.ok(html.includes('name="description"'));
assert.ok(css.includes("@media(max-width:550px)"));
for (const id of ["main", "deaths-by-year", "who-died", "pedestrians", "night", "age", "rural", "limits", "data", "reports", "explorer-chart", "report-list", "report-article"]) {
  assert.ok(html.includes('id="' + id + '"'), "Missing accessible page element " + id);
}
for (const chart of ["deaths", "changes", "indexed", "striking", "speed", "lighttruck", "tod", "age", "rural"]) assert.ok(html.includes('data-chart="' + chart + '"'), "Missing chart " + chart);
assert.ok(!/FACTORS|policy\(|findings\(|overlap\(/.test(script), "Removed feature code is still present");
const sandbox = {document: {readyState: "loading", addEventListener() {}}, console};
const {csv, markdown, safeLink, ratio, QUERY, REPORTS, fmt, STORIES} = vm.runInNewContext(
  script + "\n;({csv,markdown,safeLink,ratio,QUERY,REPORTS,fmt,STORIES})", sandbox
);
assert.equal(csv('a,b\n"one,two",3\n"line\nbreak",4\n').length, 2);
assert.equal(csv('a,b\n"one,two",3\n')[0].a, "one,two");
assert.equal(csv('a,b\n"line\nbreak",4\n')[0].a, "line\nbreak");
assert.ok(markdown("# Heading\n\nA **bold** claim.\n\n| x | y |\n|---|---|\n| 1 | 2 |\n").includes("<table>"));
assert.ok(markdown("# Heading").includes("<h1>Heading</h1>"));
assert.ok(markdown("<script>alert(1)</script>").includes("&lt;script&gt;"));
const count = (text, part) => text.split(part).length - 1;
const wrapped = markdown("1. **Bold.** Pedestrian\n   crashes are 1.2%\n   of police\n2. Second\n\n   Indented paragraph\n\n3. Third\n");
assert.equal(count(wrapped, "<ol>"), 1);
assert.equal(count(wrapped, "<li>"), 3);
assert.ok(wrapped.includes("<strong>Bold.</strong> Pedestrian crashes are 1.2% of police</li>"));
assert.ok(wrapped.includes("<p>Indented paragraph</p>"));
assert.ok(!wrapped.includes("</ol>\n<p>") && !wrapped.includes("</ol>\n<ol"));
assert.equal(count(markdown("- a\n  b\n- c\n\n- d"), "<ul>"), 1);
assert.ok(markdown("- a\n  - nested\n- b").includes("<li>a\n<ul><li>nested</li></ul></li>"));
assert.ok(markdown("73. x\n74. y").includes('<ol start="73">'));
assert.ok(markdown("1. x\n2. y").includes("<ol>"));
assert.ok(!markdown("between 1.7 and\n73. Even the two").includes("<ol"));
assert.ok(markdown("Use `a < b & 96;` here").includes("<code>a &lt; b &amp; 96;</code>"));
assert.ok(!markdown("Use `x` and `*y*`").includes("`") && markdown("`*y*`").includes("<code>*y*</code>"));
assert.ok(!markdown("| a |\n|---|\n| exceeded_limit_or_racing |").includes("<em>"));
assert.ok(markdown("a _b_ c").includes("<em>b</em>"));
assert.ok(markdown("<!-- hidden -->\n\n> quote\n\n```\n<b>\n```").includes("&lt;b&gt;"));
assert.equal(ratio(4.951), "4.95");
assert.equal(ratio(12.84), "12.8");
assert.equal(ratio(9.996), "10.0");
assert.equal(ratio(15.599), "15.6");
assert.equal(safeLink("javascript:alert(1)"), null);
assert.equal(safeLink("../../../etc/passwd"), null);
assert.equal(Object.keys(QUERY).length, 3);
for (const def of Object.values(QUERY)) {
  const file = path.join(root, "data", "tables", def.src);
  assert.ok(fs.existsSync(file), "Missing bundled chart data " + def.src);
  const data = csv(fs.readFileSync(file, "utf8"));
  assert.ok(data.length > 0, "Empty chart data " + def.src);
  assert.ok(data.some(row => def.eligible(row)), "No eligible chart data " + def.src);
}
const severity = csv(read("data/tables/severity/fatal_crude_vs_adjusted.csv"));
const labelled = [...severity.filter(QUERY.severity.eligible).map(QUERY.severity.name), ...csv(read("data/tables/descriptive/frequency_vs_severity.csv")).filter(QUERY.frequency.eligible).map(QUERY.frequency.name)];
assert.ok(labelled.every(name => !/[a-z]_[a-z]/.test(name)), "Chart label shows a raw code");
assert.equal(QUERY.severity.name({factor: "light", level: "dark_not_lighted"}), "Light condition · Dark, unlit");
assert.equal(QUERY.frequency.name({factor: "crash_type", label: "Crash type", level: "sv_rollover_first"}), "Crash type · Single vehicle, rollover first");
assert.equal(QUERY.severity.name({factor: "YEAR", level: "2021"}), "Year · 2021");
assert.ok(severity.filter(QUERY.severity.eligible).every(row => QUERY.severity.hi(row) >= QUERY.severity.lo(row)));
assert.equal(Number.isNaN(QUERY.frequency.lo({overrep_low: ""})), true);
assert.equal(QUERY.trends.display(37806), "37,806");
for (const [key, label] of REPORTS) {
  const file = path.join(root, "data", "reports", key + ".md");
  assert.ok(fs.existsSync(file), "Missing report " + label);
  assert.ok(fs.statSync(file).size > 500, "Suspiciously empty report " + label);
}
// Claims registry: every statistic written in prose in index.html or site.js is bound to its bundled CSV value.
const table = name => csv(read("data/tables/" + name));
const num = Number;
const annual = table("descriptive/fars_annual.csv");
const year = y => annual.find(r => r.YEAR === String(y));
const deaths = y => num(year(y).deaths);
const changes = table("trends/fars_changes.csv");
const change = name => changes.find(r => r.indicator === name);
const striking = table("vulnerable/fars_pedestrian_deaths_by_striking_vehicle.csv");
const strikingYear = y => striking.find(r => r.YEAR === String(y));
const contrasts = table("vulnerable/pedestrian_killed_contrasts.csv");
const contrast = (factor, level) => contrasts.find(r => r.factor === factor && r.level === level);
const lightTruck = table("vulnerable/pedestrian_light_truck_by_speed.csv");
const lt = quantity => lightTruck.find(r => r.quantity === quantity);
const freq = table("descriptive/frequency_vs_severity.csv");
const tod = level => freq.find(r => r.factor === "tod" && r.level === level);
const ageRow = level => table("person/lpv_killed_crude_vs_adjusted.csv").find(r => r.factor === "age_band" && r.level === level);
const timing = group => table("stages/death_timing.csv").find(r => r.group === group);
const ems = (y, road) => table("stages/ems_availability.csv").find(r => r.YEAR === String(y) && r.road === road);
const sum = (rows, col) => rows.reduce((total, r) => total + num(r[col]), 0);
const pct0 = x => fmt.pct(x, 0), pct1 = x => fmt.pct(x, 1), pct2 = x => fmt.pct(x, 2);
const signed = x => (x < 0 ? "−" : "+") + Math.abs(x * 100).toFixed(0) + "%";
const sumCols = ["deaths_car", "deaths_large", "deaths_motorcycle", "deaths_other_unknown", "deaths_pickup", "deaths_suv", "deaths_van"];
const pairShare = col => num(change("motorcyclist_deaths")[col]) + num(change("pedestrian_deaths")[col]);
const growth = col => annual[annual.length - 1][col] / annual[0][col] - 1;
const use = (csvName, row, colName, value, file = "index.html") => ({csv: csvName, row, col: colName, value, file});
const F = "descriptive/fars_annual.csv", C = "trends/fars_changes.csv", S = "vulnerable/fars_pedestrian_deaths_by_striking_vehicle.csv";
const K = "vulnerable/pedestrian_killed_contrasts.csv", L = "vulnerable/pedestrian_light_truck_by_speed.csv", Q = "descriptive/frequency_vs_severity.csv";
const P = "person/lpv_killed_crude_vs_adjusted.csv", D = "stages/death_timing.csv", E = "stages/ems_availability.csv";
const changePct = (name, col) => fmt.pct(num(change(name)[col]) / 100, 0);
const hr = level => level.split("-").map(Number);
const [nightStart, nightEnd] = hr("00-05"), [morningStart, morningEnd] = hr("06-09");
const Y0 = annual[0].YEAR, Yn = annual[annual.length - 1].YEAR, Y = y => year(y).YEAR;
const maxYear = annual.reduce((a, b) => (num(b.deaths) > num(a.deaths) ? b : a));
const mdash = (a, b) => a + "–" + b;
const band = level => level.replace("-", "–");
const ltSpeed = (quantity, re) => quantity.match(re)[1];
const ltLow = ltSpeed(lt("risk car <=35").quantity, /<=(\d+)/), ltHigh = ltSpeed(lt("risk car 40+").quantity, /(\d+)\+/);
const lowSpeed = ltLow;
const rr = lt("RR SUV/pickup vs car, <=35 mph"), old75 = ageRow("75+"), ageRef = ageRow("25-34");
const fromTo = (a, b) => fmt.int(num(a)) + " to " + fmt.int(num(b));
const chg = (name, col) => num(change(name)[col]);
const sentence = (...parts) => parts.join("");
// Claims registry: each phrase is bound, with its surrounding words, to the CSV values it states. "line" claims are whole text lines.
const claims = [];
const add = (text, csvName, cells, value, opts = {}) => claims.push({text, csv: csvName, row: "", col: cells, value, line: !!opts.line});
add("US road deaths, " + mdash(2016, 2024), F, "first and last YEAR", () => "US road deaths, " + mdash(Y0, Yn));
add("39,254 people died on US roads in 2024.", F, "YEAR=2024 deaths", () => fmt.int(deaths(2024)) + " people died on US roads in " + Yn + ".");
add("crash records for 2016–2024 to show", F, "first and last YEAR", () => "crash records for " + mdash(Y0, Yn) + " to show");
add("353,706", F, "sum(deaths)", () => fmt.int(sum(annual, "deaths")), {line: true});
add("deaths, 2016–2024", F, "first and last YEAR", () => "deaths, " + mdash(Y0, Yn), {line: true});
add("43,230", F, "max(deaths)", () => fmt.int(num(maxYear.deaths)), {line: true});
add("deaths in 2021, the highest year", F, "YEAR of max(deaths)", () => "deaths in " + maxYear.YEAR + ", the highest year", {line: true});
add("+8%", C, "deaths pct_change_2019_2024", () => signed(chg("deaths", "pct_change_2019_2024") / 100), {line: true});
add("deaths in 2024 vs 2019", C, "deaths columns 2024, 2019", () => "deaths in " + Yn + " vs " + Y(2019), {line: true});
add("18%", C, "pedestrian_deaths share_of_total_2024", () => pct0(chg("pedestrian_deaths", "share_of_total_2024")), {line: true});
add("of 2024 deaths were pedestrians", C, "pedestrian_deaths column 2024", () => "of " + Yn + " deaths were pedestrians", {line: true});
add("Deaths rose sharply in 2020–21 and are still above 2019", F, "deaths 2019, 2020, 2021, 2024", () => (deaths(2020) > deaths(2019) && deaths(2021) > deaths(2020) && deaths(2024) > deaths(2019) ? "Deaths rose sharply in " + Y(2020) + "–" + Y(2021).slice(2) + " and are still above " + Y(2019) : "?"), {line: true});
add("Road deaths were 36,355 in 2019.", F, "YEAR=2019 deaths", () => "Road deaths were " + fmt.int(deaths(2019)) + " in " + Y(2019) + ".");
add("They rose to 39,007 in 2020 and 43,230 in 2021, then fell for three years to 39,254 in 2024 — still 8% more than in 2019.", F + " + " + C, "YEAR=2020, 2021, 2024 deaths; deaths pct_change_2019_2024", () => "They rose to " + fmt.int(deaths(2020)) + " in " + Y(2020) + " and " + fmt.int(deaths(2021)) + " in " + Y(2021) + ", then fell for " + ({3: "three"}[num(Y(2024)) - num(Y(2021))] || "?") + " years to " + fmt.int(deaths(2024)) + " in " + Y(2024) + " — still " + changePct("deaths", "pct_change_2019_2024") + " more than in " + Y(2019) + ".");
add("Most of the increase since 2019 was among motorcyclists and pedestrians", C, "share_of_total_change_2019_2024", () => (pairShare("share_of_total_change_2019_2024") > 0.5 ? "Most of the increase since " + Y(2019) + " was among motorcyclists and pedestrians" : "?"), {line: true});
add("Between 2019 and 2024, motorcyclist deaths rose 23% (5,044 to 6,227)", C, "motorcyclist_deaths 2019, 2024, pct_change", () => "Between " + Y(2019) + " and " + Yn + ", motorcyclist deaths rose " + changePct("motorcyclist_deaths", "pct_change_2019_2024") + " (" + fromTo(chg("motorcyclist_deaths", "2019"), chg("motorcyclist_deaths", "2024")) + ")");
add("pedestrian deaths 13% (6,272 to 7,080)", C, "pedestrian_deaths 2019, 2024, pct_change", () => "pedestrian deaths " + changePct("pedestrian_deaths", "pct_change_2019_2024") + " (" + fromTo(chg("pedestrian_deaths", "2019"), chg("pedestrian_deaths", "2024")) + ")");
add("Deaths of people inside cars, SUVs, pickups and vans rose 2% (22,370 to 22,739).", C, "lpv_occupant_deaths 2019, 2024, pct_change", () => "Deaths of people inside cars, SUVs, pickups and vans rose " + changePct("lpv_occupant_deaths", "pct_change_2019_2024") + " (" + fromTo(chg("lpv_occupant_deaths", "2019"), chg("lpv_occupant_deaths", "2024")) + ").");
add("Motorcyclists and pedestrians were 31% of deaths in 2019 but account for 69% of the increase.", C, "motorcyclist_deaths + pedestrian_deaths: share_of_total_2019, share_of_total_change_2019_2024", () => "Motorcyclists and pedestrians were " + pct0(pairShare("share_of_total_2019")) + " of deaths in " + Y(2019) + " but account for " + pct0(pairShare("share_of_total_change_2019_2024")) + " of the increase.");
add("Change in deaths, 2019 to 2024", C, "column names 2019, 2024", () => "Change in deaths, " + Y(2019) + " to " + Yn, {line: true});
add("Deaths by road user, indexed to 2016 = 100", F, "YEAR=2016 index", () => "Deaths by road user, indexed to " + Y0 + " = " + Math.round(num(annual[0].deaths_pedestrian) / num(annual[0].deaths_pedestrian) * 100), {line: true});
add("2016–2024: pedestrian deaths +16%, cyclist deaths +29%, passenger deaths −12%.", F, "deaths_pedestrian, deaths_cyclist, deaths_passenger first to last year", () => mdash(Y0, Yn) + ": pedestrian deaths " + signed(growth("deaths_pedestrian")) + ", cyclist deaths " + signed(growth("deaths_cyclist")) + ", passenger deaths " + signed(growth("deaths_passenger")) + ".", {line: true});
add("SUVs struck 1,149 of the pedestrians killed in 2016 and 1,746 in 2024, a rise from 19% to 25% of pedestrian deaths.", S, "deaths_suv, share_suv for 2016 and 2024", () => "SUVs struck " + fmt.int(num(strikingYear(2016).deaths_suv)) + " of the pedestrians killed in " + strikingYear(2016).YEAR + " and " + fmt.int(num(strikingYear(2024).deaths_suv)) + " in " + strikingYear(2024).YEAR + ", a rise from " + pct0(num(strikingYear(2016).share_suv)) + " to " + pct0(num(strikingYear(2024).share_suv)) + " of pedestrian deaths.");
add("The share killed by passenger cars fell from 42% to 36%.", S, "share_car for 2016 and 2024", () => "The share killed by passenger cars fell from " + pct0(num(strikingYear(2016).share_car)) + " to " + pct0(num(strikingYear(2024).share_car)) + ".");
add("2.2% where the limit is 25 mph or less", K, "str_speed_limit/<=25 crude_rate", () => pct1(num(contrast("str_speed_limit", "<=25").crude_rate)) + " where the limit is " + "<=25".slice(2) + " mph or less");
add("14.8% at 40–45 mph", K, "str_speed_limit/40-45 crude_rate", () => pct1(num(contrast("str_speed_limit", "40-45").crude_rate)) + " at " + band("40-45") + " mph");
add("33.1% at 50–55 mph", K, "str_speed_limit/50-55 crude_rate", () => pct1(num(contrast("str_speed_limit", "50-55").crude_rate)) + " at " + band("50-55") + " mph");
add("At night on unlit roads 25.9% died, against 2.6% in daylight.", K, "light/dark_not_lighted and light/daylight crude_rate", () => "At night on unlit roads " + pct1(num(contrast("light", "dark_not_lighted").crude_rate)) + " died, against " + pct1(num(contrast("light", "daylight").crude_rate)) + " in daylight.");
add("On roads limited to 35 mph or less, 7.0% of pedestrians struck by an SUV or pickup died, against 4.3% of those struck by a car — 1.6 times as often (95% CI 1.25–2.10)", L, "risk SUV/pickup <=35, risk car <=35, RR <=35", () => "On roads limited to " + lowSpeed + " mph or less, " + pct1(num(lt("risk SUV/pickup <=35").estimate)) + " of pedestrians struck by an SUV or pickup died, against " + pct1(num(lt("risk car <=35").estimate)) + " of those struck by a car — " + fmt.times(num(rr.estimate)) + " times as often (95% CI " + num(rr.low).toFixed(2) + "–" + num(rr.high).toFixed(2) + ")");
add("On roads limited to 40 mph or more the difference is smaller: 16.3% against 13.8%.", L, "risk SUV/pickup 40+, risk car 40+", () => (num(lt("risk SUV/pickup 40+").estimate) - num(lt("risk car 40+").estimate) < num(lt("risk SUV/pickup <=35").estimate) - num(lt("risk car <=35").estimate) || num(lt("RR SUV/pickup vs car, 40+ mph").estimate) < num(rr.estimate) ? "On roads limited to " + ltHigh + " mph or more the difference is smaller: " + pct1(num(lt("risk SUV/pickup 40+").estimate)) + " against " + pct1(num(lt("risk car 40+").estimate)) + "." : "?"));
add("Vehicle type is other or unknown for about 11% of pedestrian deaths.", S, "sum(deaths_other_unknown)/sum(all deaths)", () => "Vehicle type is other or unknown for about " + pct0(sum(striking, "deaths_other_unknown") / sumCols.reduce((t, c) => t + sum(striking, c), 0)) + " of pedestrian deaths.");
add("Crashes between midnight and 6 a.m. are four times as likely to be fatal as crashes from 6 to 10 a.m.", Q, "tod/00-05 and 06-09 fatal_rate", () => "Crashes between midnight and " + (nightEnd + 1) + " a.m. are " + (Math.round(num(tod("00-05").fatal_rate) / num(tod("06-09").fatal_rate)) === 4 ? "four" : "?") + " times as likely to be fatal as crashes from " + morningStart + " to " + (morningEnd + 1) + " a.m.", {line: true});
add("Of police-reported crashes between midnight and 5:59 a.m., 1.5% were fatal, against 0.38% between 6:00 and 9:59 a.m.", Q, "tod/00-05 and 06-09 fatal_rate", () => "Of police-reported crashes between midnight and " + nightEnd + ":59 a.m., " + pct1(num(tod("00-05").fatal_rate)) + " were fatal, against " + pct2(num(tod("06-09").fatal_rate)) + " between " + morningStart + ":00 and " + morningEnd + ":59 a.m.");
add("These hours have 8% of police-reported crashes but 20% of fatal ones.", Q, "tod/00-05 share_all_crashes, share_fatal_fars", () => "These hours have " + pct0(num(tod("00-05").share_all_crashes)) + " of police-reported crashes but " + pct0(num(tod("00-05").share_fatal_fars)) + " of fatal ones.");
add("Occupants aged 75 and over are the most likely to die in a crash", P, "age_band/75+ rate is the maximum", () => (num(old75.rate) === Math.max(...table(P).filter(r => r.factor === "age_band").map(r => num(r.rate))) ? "Occupants aged " + old75.level.replace("+", "") + " and over are the most likely to die in a crash" : "?"), {line: true});
add("0.49% of car, SUV, pickup and van occupants aged 75 or older were killed, against 0.18% of those aged 25–34.", P, "age_band/75+ and 25-34 rate", () => pct2(num(old75.rate)) + " of car, SUV, pickup and van occupants aged " + old75.level.replace("+", "") + " or older were killed, against " + pct2(num(ageRef.rate)) + " of those aged " + band(ageRef.level) + ".");
add("the gap widens to 5.5 times (95% CI 4.7–6.5)", P, "age_band/75+ A_adj_rr, A_adj_rr_low, A_adj_rr_high", () => "the gap widens to " + fmt.times(num(old75.A_adj_rr)) + " times (95% CI " + fmt.times(num(old75.A_adj_rr_low)) + "–" + fmt.times(num(old75.A_adj_rr_high)) + ")");
add("Of the 151,940 people killed on rural roads in 2016–2024, 67% died at the scene, against 49% of the 200,359 killed on urban roads.", D, "rural road and urban road deaths, share_died_at_scene", () => "Of the " + fmt.int(num(timing("rural road").deaths)) + " people killed on rural roads in " + mdash(Y0, Yn) + ", " + pct0(num(timing("rural road").share_died_at_scene)) + " died at the scene, against " + pct0(num(timing("urban road").share_died_at_scene)) + " of the " + fmt.int(num(timing("urban road").deaths)) + " killed on urban roads.");
add("In 2024 the median time from the crash to the arrival of emergency medical services, where recorded, was 14 minutes on rural roads and 8 minutes on urban ones.", E, "YEAR=2024 rural and urban median_minutes_crash_to_arrival", () => "In " + ems(2024, "rural").YEAR + " the median time from the crash to the arrival of emergency medical services, where recorded, was " + ems(2024, "rural").median_minutes_crash_to_arrival + " minutes on rural roads and " + ems(2024, "urban").median_minutes_crash_to_arrival + " minutes on urban ones.");
add("In 2024 arrival time is recorded for 45% of fatal crashes on rural roads and 38% on urban roads", E, "YEAR=2024 rural and urban share_arrival_time_known", () => "In " + ems(2024, "rural").YEAR + " arrival time is recorded for " + pct0(num(ems(2024, "rural").share_arrival_time_known)) + " of fatal crashes on rural roads and " + pct0(num(ems(2024, "urban").share_arrival_time_known)) + " on urban roads");
// Numbers that are structure, not statistics: story numbers, the explorer's table indices and the fixed 95% confidence level.
const structural = ["1 · DEATHS BY YEAR", "2 · WHO DIED", "3 · PEDESTRIANS", "4 · TIME OF DAY", "5 · AGE", "6 · RURAL ROADS", "01Frequency vs fatal severity", "02Crude vs adjusted risk", "03Fatal crash trends", "TABLE 01", "with 95% confidence interval", "design-based 95% CIs"];
const esc = x => x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const phrase = (text, line) => new RegExp((line ? "^" : "(?<![\\d.,+−])") + esc(text) + (line ? "$" : "(?![\\d,]?\\d)"), line ? "gm" : "g");
const flat = html.slice(html.indexOf("<body>")).replace(/<script[\s\S]*?<\/script>/g, "").replace(/<\/?(span|code|a|strong|em|b)\b[^>]*>/g, "").replace(/<[^>]+>/g, "\n").split("\n").map(line => line.trim()).filter(Boolean).join("\n");
let claimCount = 0, rest = flat;
const seen = new Set();
for (const claim of claims) {
  assert.ok(!seen.has(claim.text), "Duplicate claim " + claim.text);
  seen.add(claim.text);
  assert.equal(claim.value(), claim.text, "Claim differs from " + claim.csv + " [" + claim.row + "] " + claim.col + ": " + claim.text);
  assert.equal((flat.match(phrase(claim.text, claim.line)) || []).length, 1, "Claim expected once in index.html: " + claim.text);
  rest = rest.replace(phrase(claim.text, claim.line), "§");
  claimCount++;
}
for (const text of structural) {
  assert.ok(flat.includes(text), "Structural phrase missing: " + text);
  rest = rest.replaceAll(text, "§");
}
assert.deepEqual(rest.match(/\d[\d,.]*/g) || [], [], "Unregistered number in page text: " + (rest.match(/.{0,30}\d[\d,.]*.{0,15}/g) || []).join(" | "));
// Wording claims for numbers written as words.
const ratioTod = num(tod("00-05").fatal_rate) / num(tod("06-09").fatal_rate);
assert.ok(html.includes("four times as likely") && Math.round(ratioTod) === 4 && Math.abs(ratioTod - 4) < 0.1, "'four times' differs from the fatal-rate ratio");
assert.ok(html.includes("Two in three") && Math.abs(num(timing("rural road").share_died_at_scene) - 2 / 3) < 0.01, "'Two in three' differs from share_died_at_scene");
assert.ok(html.includes("for three years") && deaths(2021) > deaths(2022) && deaths(2022) > deaths(2023) && deaths(2023) > deaths(2024) && 2024 - 2021 === 3, "'three years of decline' differs from fars_annual.csv");
assert.ok(html.includes("Most of the increase") && pairShare("share_of_total_change_2019_2024") > 0.5, "'Most of the increase' differs from fars_changes.csv");
assert.ok(html.includes("most likely to die") && num(ageRow("75+").rate) === Math.max(...table(P).filter(r => r.factor === "age_band").map(r => num(r.rate))), "Highest age band differs from the table");
assert.equal(annual.length, 9, "'Nine years' differs from fars_annual.csv");
assert.ok(num(strikingYear(2024).share_suv) > num(strikingYear(2016).share_suv) && num(strikingYear(2024).share_car) < num(strikingYear(2016).share_car), "SUV/car share direction differs from the table");
// site.js prose carries no data statistics; chart numbers are formatted from the CSVs at runtime.
assert.ok(!/\d+(\.\d+)?%/.test(script.replace(/95%/g, "")), "site.js contains a hard-coded statistic");
// Every story chart builds from its bundled CSV and exposes a data table.
const siteCsv = name => csv(fs.readFileSync(path.join(root, "data/tables", name), "utf8"));
const fetched = {};
sandbox.fetch = async url => ({ok: true, status: 200, text: async () => fs.readFileSync(path.join(root, url), "utf8")});
for (const key of Object.keys(STORIES)) {
  const spec = await STORIES[key]();
  assert.ok(spec.table.head.length > 1 && spec.table.rows.length > 0, "Chart " + key + " has no data table");
  assert.ok(spec.table.rows.every(row => row.length === spec.table.head.length), "Chart " + key + " table is ragged");
}
console.log("Claims registry: " + claimCount + " claims bound to CSV values.");

assert.ok(markdown("**Teenage *less* severe** x").includes("<strong>Teenage <em>less</em> severe</strong>"));
assert.ok(markdown("text\n\n    a = 1 < 2\n\n    b\n\npara").includes("<pre><code>a = 1 &lt; 2\n\nb</code></pre>"));
assert.ok(!markdown("- item\n\n  more text").includes("<pre>"));
assert.ok(!QUERY.frequency.eligible({level: "unknown", overrep_ratio: "2"}) && QUERY.frequency.eligible({level: "yes", overrep_ratio: "2"}));
assert.ok(QUERY.severity.eligible({level: "yes", factor: "light", A_adj_rr: "2", flag: "", adj_flag: ""}));
for (const bad of [{level: "unknown"}, {level: "other"}, {factor: "YEAR"}, {flag: "unstable"}, {adj_flag: "level RSE>30%"}]) {
  assert.ok(!QUERY.severity.eligible({level: "yes", factor: "light", A_adj_rr: "2", flag: "", adj_flag: "", ...bad}));
}
console.log("Road Evidence: static structure, story charts, claims registry, reports and CSV/Markdown parser passed.");
