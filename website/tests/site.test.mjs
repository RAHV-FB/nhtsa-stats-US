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
for (const id of ["main", "findings-list", "explorer-chart", "factor-panel", "policy-percent", "report-list", "report-article"]) {
  assert.ok(html.includes('id="' + id + '"'), "Missing accessible page element " + id);
}
assert.ok(html.includes('href="#methodology"'));
const sandbox = {document: {readyState: "loading", addEventListener() {}}, console};
const {csv, markdown, safeLink, ratio, QUERY, REPORTS} = vm.runInNewContext(
  script + "\n;({csv,markdown,safeLink,ratio,QUERY,REPORTS})", sandbox
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
const originalCounts = csv(read("data/tables/contributions/fars_overlap_summary.csv"));
assert.ok(originalCounts.some(row => row.factor === "sum of the four factor counts"));
const policy = csv(read("data/tables/simulation/threshold_required_share.csv"));
const alcohol5 = policy.find(row => row.segment === "alcohol" && row.reduction_of_all_deaths_pct === "5");
assert.ok(alcohol5 && Math.abs(Number(alcohol5.required_share_of_segment_deaths)-0.163)<0.005);

// Provenance registry: every hard-coded statistic must appear in the page and equal its bundled source table value.
const table = name => csv(read("data/tables/" + name));
const models = table("speeding/key_models.csv").filter(r => r.exposure === "exceeded" && r.outcome === "fatal");
const model = name => models.find(r => r.model === name);
const shapley = (exposure, block) => table("speeding/shapley.csv").find(r => r.exposure === exposure && r.outcome === "fatal" && r.variant === "all_blocks" && r.block === block);
const pedestrian = table("descriptive/frequency_vs_severity.csv").find(r => r.factor === "crash_type" && r.level === "pedestrian");
const overlap = name => table("contributions/fars_overlap_summary.csv").find(r => r.factor === name);
const tested = survival => table("drugs/testing_rates.csv").find(r => r.dimension === "all years" && r.survival === survival);
const belt = table("matched/belt_effect.csv").find(r => r.estimand === "fatality_rr_belted_vs_unbelted_given_fatal_crash");
const sum = (name, col) => table(name).reduce((total, r) => total + Number(r[col]), 0);
const pct = (x, d = 0) => (x * 100).toFixed(d) + "%";
const group = n => Math.round(n).toLocaleString("en-US");
const claims = [
  {text: "10.0", file: "index.html", csv: "speeding/key_models.csv", row: "model=crude", col: "rr", value: () => Number(model("crude").rr).toFixed(1)},
  {text: "4.88", file: "index.html", csv: "speeding/key_models.csv", row: "model=all_blocks", col: "rr", value: () => Number(model("all_blocks").rr).toFixed(2)},
  {text: "4.12–5.79", file: "index.html", csv: "speeding/key_models.csv", row: "model=all_blocks", col: "rr_low–rr_high", value: () => Number(model("all_blocks").rr_low).toFixed(2) + "–" + Number(model("all_blocks").rr_high).toFixed(2)},
  {text: "5.2 (4.3–6.3)", file: "index.html", csv: "speeding/key_models.csv", row: "model=environment_and_other_behaviour", col: "rr (rr_low–rr_high)", value: () => {const m = model("environment_and_other_behaviour"); return Number(m.rr).toFixed(1) + " (" + Number(m.rr_low).toFixed(1) + "–" + Number(m.rr_high).toFixed(1) + ")";}},
  {text: "5.2 (4.3–6.3)", file: "assets/site.js", csv: "speeding/key_models.csv", row: "model=environment_and_other_behaviour", col: "rr (rr_low–rr_high)", value: () => {const m = model("environment_and_other_behaviour"); return Number(m.rr).toFixed(1) + " (" + Number(m.rr_low).toFixed(1) + "–" + Number(m.rr_high).toFixed(1) + ")";}},
  {text: "69%", file: "index.html", csv: "speeding/key_models.csv", row: "model=all_blocks", col: "share_logrr_retained", value: () => pct(Number(model("all_blocks").share_logrr_retained))},
  {text: "68.8%", file: "index.html", csv: "speeding/key_models.csv", row: "all_blocks vs crude", col: "ln(rr)/ln(crude rr)", value: () => pct(Math.log(Number(model("all_blocks").rr)) / Math.log(Number(model("crude").rr)), 1)},
  {text: "7.0", file: "assets/site.js", csv: "speeding/key_models.csv", row: "model=other_behaviour_only", col: "rr", value: () => Number(model("other_behaviour_only").rr).toFixed(1)},
  {text: "about 9%", file: "index.html", csv: "speeding/shapley.csv", row: "exceeded/fatal/all_blocks/alcohol", col: "shapley_share_of_crude", value: () => "about " + pct(Number(shapley("exceeded", "alcohol").shapley_share_of_crude))},
  {text: "around 9%", file: "assets/site.js", csv: "speeding/shapley.csv", row: "exceeded/fatal/all_blocks/alcohol", col: "shapley_share_of_crude", value: () => "around " + pct(Number(shapley("exceeded", "alcohol").shapley_share_of_crude))},
  {text: "4–16%", file: "index.html", csv: "speeding/shapley.csv", row: "exceeded/fatal/all_blocks/alcohol", col: "min_share_any_order–max_share_any_order", value: () => {const r = shapley("exceeded", "alcohol"); return (Number(r.min_share_any_order) * 100).toFixed(0) + "–" + pct(Number(r.max_share_any_order));}},
  {text: "4–16%", file: "assets/site.js", csv: "speeding/shapley.csv", row: "exceeded/fatal/all_blocks/alcohol", col: "min_share_any_order–max_share_any_order", value: () => {const r = shapley("exceeded", "alcohol"); return (Number(r.min_share_any_order) * 100).toFixed(0) + "–" + pct(Number(r.max_share_any_order));}},
  {text: "around 4%", file: "assets/site.js", csv: "speeding/shapley.csv", row: "alcohol/fatal/all_blocks/speeding_type", col: "shapley_share_of_crude", value: () => "around " + pct(Number(shapley("alcohol", "speeding_type").shapley_share_of_crude))},
  {text: "353,706", file: "index.html", csv: "descriptive/fars_annual.csv", row: "all years", col: "sum(deaths)", value: () => group(sum("descriptive/fars_annual.csv", "deaths"))},
  {text: "325,922", file: "index.html", csv: "descriptive/fars_annual.csv", row: "all years", col: "sum(fatal_crashes)", value: () => group(sum("descriptive/fars_annual.csv", "fatal_crashes"))},
  {text: "468,993", file: "index.html", csv: "descriptive/crss_annual.csv", row: "all years", col: "sum(n_sample)", value: () => group(sum("descriptive/crss_annual.csv", "n_sample"))},
  {text: "1.2%", file: "index.html", csv: "descriptive/frequency_vs_severity.csv", row: "crash_type/pedestrian", col: "share_all_crashes", value: () => pct(Number(pedestrian.share_all_crashes), 1)},
  {text: "18.6%", file: "index.html", csv: "descriptive/frequency_vs_severity.csv", row: "crash_type/pedestrian", col: "share_fatal_fars", value: () => pct(Number(pedestrian.share_fatal_fars), 1)},
  {text: "15.6×", file: "index.html", csv: "descriptive/frequency_vs_severity.csv", row: "crash_type/pedestrian", col: "overrep_ratio", value: () => Number(pedestrian.overrep_ratio).toFixed(1) + "×"},
  {text: "13.2–18.5", file: "index.html", csv: "descriptive/frequency_vs_severity.csv", row: "crash_type/pedestrian", col: "overrep_low–overrep_high", value: () => Number(pedestrian.overrep_low).toFixed(1) + "–" + Number(pedestrian.overrep_high).toFixed(1)},
  {text: "62%", file: "index.html", csv: "drugs/testing_rates.csv", row: "all years/killed", col: "share_tested", value: () => pct(Number(tested("killed").share_tested))},
  {text: "19%", file: "index.html", csv: "drugs/testing_rates.csv", row: "all years/survived", col: "share_tested", value: () => pct(Number(tested("survived").share_tested))},
  {text: "109%", file: "index.html", csv: "contributions/fars_overlap_summary.csv", row: "sum of the four factor counts", col: "deaths/all deaths", value: () => pct(Number(overlap("sum of the four factor counts").deaths) / Number(overlap("all deaths").deaths))},
  {text: "65%", file: "index.html", csv: "contributions/fars_overlap_summary.csv", row: "union", col: "deaths/all deaths", value: () => pct(Number(overlap("deaths involving at least one factor (union)").deaths) / Number(overlap("all deaths").deaths))},
  {text: "44 percentage points", file: "index.html", csv: "contributions/fars_overlap_summary.csv", row: "sum minus union", col: "deaths/all deaths", value: () => ((Number(overlap("sum of the four factor counts").deaths) - Number(overlap("deaths involving at least one factor (union)").deaths)) / Number(overlap("all deaths").deaths) * 100).toFixed(0) + " percentage points"},
  {text: "222,767", file: "index.html", csv: "contributions/fars_overlap_summary.csv", row: "all deaths", col: "deaths_undetermined_drug_status", value: () => group(Number(overlap("all deaths").deaths_undetermined_drug_status))},
  {text: "105,821", file: "assets/site.js", csv: "contributions/fars_overlap_summary.csv", row: "driver BAC >= .08 (MI)", col: "deaths", value: () => group(Number(overlap("driver BAC >= .08 (MI)").deaths))},
  {text: "0.34", file: "assets/site.js", csv: "matched/belt_effect.csv", row: "fatality_rr_belted_vs_unbelted_given_fatal_crash", col: "estimate", value: () => Number(belt.estimate).toFixed(2)},
  {text: "0.33–0.35", file: "assets/site.js", csv: "matched/belt_effect.csv", row: "fatality_rr_belted_vs_unbelted_given_fatal_crash", col: "low–high", value: () => Number(belt.low).toFixed(2) + "–" + Number(belt.high).toFixed(2)},
  {text: "16.3%", file: "index.html", csv: "simulation/threshold_required_share.csv", row: "alcohol/5", col: "required_share_of_segment_deaths", value: () => pct(Number(alcohol5.required_share_of_segment_deaths), 1)}
];
for (const claim of claims) {
  assert.ok(read(claim.file).includes(claim.text), "Claim not found in " + claim.file + ": " + claim.text);
  assert.equal(claim.value(), claim.text, "Claim " + claim.text + " differs from " + claim.csv + " [" + claim.row + "] " + claim.col);
}
assert.ok(QUERY.severity.eligible({level: "yes", factor: "light", A_adj_rr: "2", flag: "", adj_flag: ""}));
for (const bad of [{level: "unknown"}, {level: "other"}, {factor: "YEAR"}, {flag: "unstable"}, {adj_flag: "level RSE>30%"}]) {
  assert.ok(!QUERY.severity.eligible({level: "yes", factor: "light", A_adj_rr: "2", flag: "", adj_flag: "", ...bad}));
}
console.log("Road Evidence: static structure, chart tables, reports, CSV/Markdown parser and policy baseline passed.");
