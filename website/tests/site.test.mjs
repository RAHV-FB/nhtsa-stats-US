import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";

const root = path.resolve(import.meta.dirname, "..");
const read = name => fs.readFileSync(path.join(root, name), "utf8");
const html = read("index.html");
const script = read("assets/site.js");

test("page structure", () => {
  assert.ok(html.startsWith("<!doctype html>"));
  assert.ok(html.includes('<html lang="en">'));
  assert.match(html, /<meta name="description" content="[^"]{40,}"/);
  assert.equal((html.match(/<h1[ >]/g) || []).length, 1);
  for (const id of ["top", "findings", "behaviours", "alcohol", "belts", "speed", "pedestrians",
    "motorcycles", "vehicles", "trend", "states", "limits", "method"]) {
    assert.ok(html.includes(`id="${id}"`), `missing section ${id}`);
  }
  const body = html.replace(/<(script|style)[\s\S]*?<\/\1>/g, "");
  assert.ok(!/Loading/i.test(body), "no loading placeholders");
  assert.ok(!html.includes("{{"), "unresolved placeholder");
  assert.ok(!/\b(NaN|undefined)\b/.test(body), "leaked value");
});

test("every figure has a caption and a data view", () => {
  const figures = html.split("<figure").slice(1).map(f => f.split("</figure>")[0]);
  assert.ok(figures.length >= 15);
  for (const f of figures) {
    assert.ok(f.includes("<figcaption>"), "figure without figcaption");
    assert.ok(f.includes('class="dataview"'), "figure without a data view");
  }
});

test("theme tokens and phone layout are present", () => {
  const css = read("assets/site.css");
  assert.ok(css.includes('@media (prefers-color-scheme: dark)'));
  assert.ok(css.includes(':root:not([data-theme="light"])'));
  assert.ok(css.includes(':root[data-theme="dark"]'));
  assert.ok(css.includes("body {") && css.includes("background: var(--bg)"));
  assert.ok(css.includes("prefers-reduced-motion"));
});

test("monospace text has ligatures turned off", () => {
  // Overpass Mono squeezes "fi" and "ffi" into one cell, which reads as a missing glyph.
  // The font shorthand resets ligatures, so each rule must turn them off after it.
  const css = read("assets/site.css");
  const rules = css.match(/font:[^;]*var\(--font-mono\);[^;}]*;?/g) || [];
  assert.ok(rules.length > 0, "no monospace rules found");
  for (const rule of rules) {
    assert.match(rule, /font-variant-ligatures:\s*none/, `ligatures not turned off in: ${rule}`);
  }
});

const sandbox = { document: { readyState: "loading", addEventListener() {} }, console };
const api = vm.runInNewContext(script, sandbox);
const { compareRows, parseCell, tipText, nearestIndex, lineTip, matchesQuery } = api;

test("parseCell reads numbers, text and unknowns", () => {
  assert.equal(parseCell("0.25"), 0.25);
  assert.equal(parseCell("-3"), -3);
  assert.equal(parseCell("texas"), "texas");
  assert.equal(parseCell(""), null);
  assert.equal(parseCell(null), null);
});

test("compareRows sorts numbers, text and puts unknowns last in both directions", () => {
  const sort = (xs, dir) => xs.slice().sort((a, b) => compareRows(a, b, dir));
  assert.deepEqual(sort([3, 1, null, 2], "asc"), [1, 2, 3, null]);
  assert.deepEqual(sort([3, 1, null, 2], "desc"), [3, 2, 1, null]);
  assert.deepEqual(sort(["b", "a", null], "asc"), ["a", "b", null]);
  assert.deepEqual(sort(["b", "a", null], "desc"), ["b", "a", null]);
  assert.equal(compareRows(null, null, "asc"), 0);
});

test("tipText normalises whitespace", () => {
  assert.equal(tipText("  a \n  b "), "a b");
  assert.equal(tipText(undefined), "");
});

test("nearestIndex snaps to the closest point", () => {
  assert.equal(nearestIndex(44, 44, 524, 9), 0);
  assert.equal(nearestIndex(524, 44, 524, 9), 8);
  assert.equal(nearestIndex(300, 44, 524, 9), 4);
  assert.equal(nearestIndex(-50, 44, 524, 9), 0);
  assert.equal(nearestIndex(9999, 44, 524, 9), 8);
});

test("lineTip lists every series, value first, highest first", () => {
  const data = { xs: ["2019", "2020"], series: [
    { name: "A", color: "accent", values: [100, 110], text: ["100", "110"] },
    { name: "B", color: "series-2", values: [100, 120], text: ["100", "120"] }] };
  const tip = lineTip(data, 1);
  assert.equal(tip.title, "2020");
  assert.deepEqual(tip.rows.map(r => [r.text, r.name]), [["120", "B"], ["110", "A"]]);
  assert.equal(lineTip(data, 0).rows[0].name, "A", "ties keep series order");
});

test("matchesQuery filters by name or code, case-insensitively", () => {
  assert.ok(matchesQuery("new york ny", "york"));
  assert.ok(matchesQuery("new york ny", " NY "));
  assert.ok(matchesQuery("anything", ""));
  assert.ok(!matchesQuery("texas tx", "ohio"));
});
