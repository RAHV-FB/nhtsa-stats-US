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
console.log("Road Evidence: static structure, chart tables, reports, CSV/Markdown parser and policy baseline passed.");
