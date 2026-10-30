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
assert.equal(Object.keys(QUERY).length, 4);
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
const found = JSON.parse(read("data/findings.json"));
assert.equal(found.length, 10);
assert.ok(found.every(item => item.title && item.statement && item.evidence));
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
const claims = {
  "39,254": [use(F, "YEAR=2024", "deaths", () => fmt.int(deaths(2024))), use(F, "YEAR=2024", "deaths", () => fmt.int(deaths(2024)))],
  "353,706": [use(F, "all years", "sum(deaths)", () => fmt.int(sum(annual, "deaths")))],
  "43,230": [use(F, "max deaths", "deaths", () => fmt.int(Math.max(...annual.map(r => num(r.deaths))))), use(F, "YEAR=2021", "deaths", () => fmt.int(deaths(2021)))],
  "+8%": [use(C, "deaths", "pct_change_2019_2024", () => signed(num(change("deaths").pct_change_2019_2024) / 100))],
  "18%": [use(C, "pedestrian_deaths", "share_of_total_2024", () => pct0(num(change("pedestrian_deaths").share_of_total_2024)))],
  "36,355": [use(F, "YEAR=2019", "deaths", () => fmt.int(deaths(2019)))],
  "39,007": [use(F, "YEAR=2020", "deaths", () => fmt.int(deaths(2020)))],
  "8%": [use(C, "deaths", "pct_change_2019_2024", () => changePct("deaths", "pct_change_2019_2024")), use(Q, "tod/00-05", "share_all_crashes", () => pct0(num(tod("00-05").share_all_crashes)))],
  "23%": [use(C, "motorcyclist_deaths", "pct_change_2019_2024", () => changePct("motorcyclist_deaths", "pct_change_2019_2024"))],
  "5,044": [use(C, "motorcyclist_deaths", "2019", () => fmt.int(num(change("motorcyclist_deaths")["2019"])))],
  "6,227": [use(C, "motorcyclist_deaths", "2024", () => fmt.int(num(change("motorcyclist_deaths")["2024"])))],
  "13%": [use(C, "pedestrian_deaths", "pct_change_2019_2024", () => changePct("pedestrian_deaths", "pct_change_2019_2024"))],
  "6,272": [use(C, "pedestrian_deaths", "2019", () => fmt.int(num(change("pedestrian_deaths")["2019"])))],
  "7,080": [use(C, "pedestrian_deaths", "2024", () => fmt.int(num(change("pedestrian_deaths")["2024"])))],
  "2%": [use(C, "lpv_occupant_deaths", "pct_change_2019_2024", () => changePct("lpv_occupant_deaths", "pct_change_2019_2024"))],
  "22,370": [use(C, "lpv_occupant_deaths", "2019", () => fmt.int(num(change("lpv_occupant_deaths")["2019"])))],
  "22,739": [use(C, "lpv_occupant_deaths", "2024", () => fmt.int(num(change("lpv_occupant_deaths")["2024"])))],
  "31%": [use(C, "motorcyclist_deaths + pedestrian_deaths", "share_of_total_2019", () => pct0(pairShare("share_of_total_2019")))],
  "69%": [use(C, "motorcyclist_deaths + pedestrian_deaths", "share_of_total_change_2019_2024", () => pct0(pairShare("share_of_total_change_2019_2024")))],
  "+16%": [use(F, "2016 to 2024", "deaths_pedestrian", () => signed(growth("deaths_pedestrian")))],
  "+29%": [use(F, "2016 to 2024", "deaths_cyclist", () => signed(growth("deaths_cyclist")))],
  "−12%": [use(F, "2016 to 2024", "deaths_passenger", () => signed(growth("deaths_passenger")))],
  "1,149": [use(S, "YEAR=2016", "deaths_suv", () => fmt.int(num(strikingYear(2016).deaths_suv)))],
  "1,746": [use(S, "YEAR=2024", "deaths_suv", () => fmt.int(num(strikingYear(2024).deaths_suv)))],
  "19%": [use(S, "YEAR=2016", "share_suv", () => pct0(num(strikingYear(2016).share_suv)))],
  "25%": [use(S, "YEAR=2024", "share_suv", () => pct0(num(strikingYear(2024).share_suv)))],
  "42%": [use(S, "YEAR=2016", "share_car", () => pct0(num(strikingYear(2016).share_car)))],
  "36%": [use(S, "YEAR=2024", "share_car", () => pct0(num(strikingYear(2024).share_car)))],
  "2.2%": [use(K, "str_speed_limit/<=25", "crude_rate", () => pct1(num(contrast("str_speed_limit", "<=25").crude_rate)))],
  "14.8%": [use(K, "str_speed_limit/40-45", "crude_rate", () => pct1(num(contrast("str_speed_limit", "40-45").crude_rate)))],
  "33.1%": [use(K, "str_speed_limit/50-55", "crude_rate", () => pct1(num(contrast("str_speed_limit", "50-55").crude_rate)))],
  "25.9%": [use(K, "light/dark_not_lighted", "crude_rate", () => pct1(num(contrast("light", "dark_not_lighted").crude_rate)))],
  "2.6%": [use(K, "light/daylight", "crude_rate", () => pct1(num(contrast("light", "daylight").crude_rate)))],
  "7.0%": [use(L, "risk SUV/pickup <=35", "estimate", () => pct1(num(lt("risk SUV/pickup <=35").estimate)))],
  "4.3%": [use(L, "risk car <=35", "estimate", () => pct1(num(lt("risk car <=35").estimate)))],
  "1.6": [use(L, "RR SUV/pickup vs car, <=35 mph", "estimate", () => fmt.times(num(lt("RR SUV/pickup vs car, <=35 mph").estimate)))],
  "11%": [use(S, "all years", "sum(deaths_other_unknown)/sum(all deaths)", () => pct0(sum(striking, "deaths_other_unknown") / sumCols.reduce((t, c) => t + sum(striking, c), 0)))],
  "1.5%": [use(Q, "tod/00-05", "fatal_rate", () => pct1(num(tod("00-05").fatal_rate)))],
  "0.38%": [use(Q, "tod/06-09", "fatal_rate", () => pct2(num(tod("06-09").fatal_rate)))],
  "20%": [use(Q, "tod/00-05", "share_fatal_fars", () => pct0(num(tod("00-05").share_fatal_fars)))],
  "0.49%": [use(P, "age_band/75+", "rate", () => pct2(num(ageRow("75+").rate)))],
  "0.18%": [use(P, "age_band/25-34", "rate", () => pct2(num(ageRow("25-34").rate)))],
  "5.5": [use(P, "age_band/75+", "A_adj_rr", () => fmt.times(num(ageRow("75+").A_adj_rr)))],
  "4.7–6.5": [use(P, "age_band/75+", "A_adj_rr_low–A_adj_rr_high", () => fmt.times(num(ageRow("75+").A_adj_rr_low)) + "–" + fmt.times(num(ageRow("75+").A_adj_rr_high)))],
  "151,940": [use(D, "rural road", "deaths", () => fmt.int(num(timing("rural road").deaths)))],
  "67%": [use(D, "rural road", "share_died_at_scene", () => pct0(num(timing("rural road").share_died_at_scene)))],
  "49%": [use(D, "urban road", "share_died_at_scene", () => pct0(num(timing("urban road").share_died_at_scene)))],
  "200,359": [use(D, "urban road", "deaths", () => fmt.int(num(timing("urban road").deaths)))],
  "14 minutes": [use(E, "YEAR=2024/rural", "median_minutes_crash_to_arrival", () => ems(2024, "rural").median_minutes_crash_to_arrival + " minutes")],
  "8 minutes": [use(E, "YEAR=2024/urban", "median_minutes_crash_to_arrival", () => ems(2024, "urban").median_minutes_crash_to_arrival + " minutes")],
  "45%": [use(E, "YEAR=2024/rural", "share_arrival_time_known", () => pct0(num(ems(2024, "rural").share_arrival_time_known)))],
  "38%": [use(E, "YEAR=2024/urban", "share_arrival_time_known", () => pct0(num(ems(2024, "urban").share_arrival_time_known)))]
};
// Exact occurrence counting with digit boundaries (and no sign or decimal point directly before an unsigned number).
const occurrences = (text, claim) => (text.match(new RegExp("(?<![\\d.,+−])" + claim.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "(?![\\d,]?\\d)", "g")) || []).length;
const bodyText = html.slice(html.indexOf("<body>")).replace(/<script[\s\S]*?<\/script>/g, "").replace(/<\/?(span|code|a|strong|em|b)\b[^>]*>/g, "").replace(/<[^>]+>/g, "\n");
let claimCount = 0;
for (const [text, uses] of Object.entries(claims)) {
  for (const file of ["index.html", "assets/site.js"]) {
    const expected = uses.filter(u => u.file === file).length;
    assert.equal(occurrences(read(file), text), expected, "Claim " + text + " expected " + expected + "x in " + file);
  }
  for (const u of uses) {
    assert.equal(u.value(), text, "Claim " + text + " differs from " + u.csv + " [" + u.row + "] " + u.col);
    claimCount++;
  }
}
// Every other number in the page body must be a year, clock time, speed-limit band, age, kicker index or confidence level.
let rest = bodyText;
for (const text of Object.keys(claims)) rest = rest.replace(new RegExp("(?<![\\d.,+−])" + text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "(?![\\d,]?\\d)", "g"), "§");
for (const allowed of [/2020–21/g, /\b20(1[6-9]|2[0-4])\b/g, /\b0[1-4](?=[A-Z])/g, /^\s*\d ·/gm, /\b\d{1,2}:\d{2}/g, /\b\d{1,2}( to \d{1,2})? a\.m\./g, /\b\d{2}(–\d{2})? mph/g, /\b25–34\b/g, /\baged 75\b/g, /\b75 or older/g, /\b95% (CIs?|confidence interval)/g, /= 100\b/g, /^\s*0\d\s*$/gm, /TABLE 0\d/g]) rest = rest.replace(allowed, "§");
assert.deepEqual(rest.match(/\d[\d,.]*/g) || [], [], "Unregistered number in page text");
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
console.log("Claims registry: " + Object.keys(claims).length + " distinct claims, " + claimCount + " bound occurrences.");

assert.ok(markdown("**Teenage *less* severe** x").includes("<strong>Teenage <em>less</em> severe</strong>"));
assert.ok(markdown("text\n\n    a = 1 < 2\n\n    b\n\npara").includes("<pre><code>a = 1 &lt; 2\n\nb</code></pre>"));
assert.ok(!markdown("- item\n\n  more text").includes("<pre>"));
assert.ok(!QUERY.frequency.eligible({level: "unknown", overrep_ratio: "2"}) && QUERY.frequency.eligible({level: "yes", overrep_ratio: "2"}));
assert.ok(QUERY.severity.eligible({level: "yes", factor: "light", A_adj_rr: "2", flag: "", adj_flag: ""}));
for (const bad of [{level: "unknown"}, {level: "other"}, {factor: "YEAR"}, {flag: "unstable"}, {adj_flag: "level RSE>30%"}]) {
  assert.ok(!QUERY.severity.eligible({level: "yes", factor: "light", A_adj_rr: "2", flag: "", adj_flag: "", ...bad}));
}
console.log("Road Evidence: static structure, story charts, claims registry, reports and CSV/Markdown parser passed.");
