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
const {csv, markdown, safeLink, QUERY, REPORTS} = vm.runInNewContext(
  script + "\n;({csv,markdown,safeLink,QUERY,REPORTS})", sandbox
);
assert.equal(csv('a,b\n"one,two",3\n"line\nbreak",4\n').length, 2);
assert.equal(csv('a,b\n"one,two",3\n')[0].a, "one,two");
assert.equal(csv('a,b\n"line\nbreak",4\n')[0].a, "line\nbreak");
assert.ok(markdown("# Heading\n\nA **bold** claim.\n\n| x | y |\n|---|---|\n| 1 | 2 |\n").includes("<table>"));
assert.ok(markdown("# Heading").includes("<h1>Heading</h1>"));
assert.ok(markdown("<script>alert(1)</script>").includes("&lt;script&gt;"));
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
