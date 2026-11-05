/* Road Deaths in America. Progressive enhancement only: the page is complete without this file.
   Inlined into index.html by `nhtsa analyze site`. No dependencies. */
(function () {
  "use strict";

  /* ---------- pure helpers (tested in website/tests/site.test.mjs) ---------- */

  // The sort key held in a table cell's data-sort attribute: a number, a string, or null (unknown).
  function parseCell(raw) {
    if (raw === null || raw === undefined) return null;
    var s = String(raw).trim();
    if (s === "") return null;
    var n = Number(s);
    return isFinite(n) ? n : s;
  }

  // Comparator for two parsed cells. Unknown (null) always sorts last, in either direction.
  function compareRows(a, b, dir) {
    var sign = dir === "desc" || dir === -1 ? -1 : 1;
    if (a === null && b === null) return 0;
    if (a === null) return 1;
    if (b === null) return -1;
    if (typeof a === "number" && typeof b === "number") return sign * (a - b);
    var x = String(a), y = String(b);
    return sign * (x < y ? -1 : x > y ? 1 : 0);
  }

  function tipText(text) {
    return String(text === null || text === undefined ? "" : text).replace(/\s+/g, " ").trim();
  }

  // Index of the x position nearest to svgX, for n points spread evenly between x0 and x1.
  function nearestIndex(svgX, x0, x1, n) {
    if (n <= 1 || x1 <= x0) return 0;
    var i = Math.round(((svgX - x0) / (x1 - x0)) * (n - 1));
    return Math.max(0, Math.min(n - 1, i));
  }

  // Content of the line-chart tooltip at point idx: the x label and one row per series with its
  // value first and its name second, highest value first.
  function lineTip(data, idx) {
    var rows = data.series.map(function (s, k) {
      return { name: s.name, text: s.text[idx], color: s.color, value: s.values[idx], order: k };
    });
    rows.sort(function (a, b) { return b.value - a.value || a.order - b.order; });
    return { title: data.xs[idx], rows: rows };
  }

  function matchesQuery(haystack, query) {
    var q = tipText(query).toLowerCase();
    return q === "" || String(haystack).toLowerCase().indexOf(q) !== -1;
  }

  /* ---------- browser behaviour ---------- */

  function initTooltip() {
    var tip = document.createElement("div");
    tip.className = "tip";
    tip.setAttribute("role", "tooltip");
    tip.hidden = true;
    document.body.appendChild(tip);
    Array.prototype.forEach.call(document.querySelectorAll("[data-tip][title]"), function (el) {
      el.removeAttribute("title"); // the custom tooltip replaces the native one
    });

    function place(x, y) {
      var w = tip.offsetWidth, h = tip.offsetHeight;
      var vx = window.pageXOffset, vw = document.documentElement.clientWidth;
      var left = x + 14, top = y + 16;
      if (left + w > vx + vw - 8) left = Math.max(vx + 8, x - w - 14);
      if (y + 16 + h > window.pageYOffset + window.innerHeight - 8) top = Math.max(8, y - h - 12);
      tip.style.left = left + "px";
      tip.style.top = top + "px";
    }
    function showText(text, x, y) {
      tip.textContent = tipText(text);
      tip.hidden = false;
      place(x, y);
    }
    function showRows(content, x, y) {
      tip.textContent = "";
      var t = document.createElement("div");
      t.className = "tip-title";
      t.textContent = content.title;
      tip.appendChild(t);
      content.rows.forEach(function (r) {
        var row = document.createElement("div");
        row.className = "tip-row";
        var key = document.createElement("span");
        key.className = "tip-key";
        key.style.background = "var(--" + r.color + ")";
        var val = document.createElement("span");
        val.className = "tip-val";
        val.textContent = r.text;
        var name = document.createElement("span");
        name.textContent = r.name;
        row.appendChild(key);
        row.appendChild(val);
        row.appendChild(name);
        tip.appendChild(row);
      });
      tip.hidden = false;
      place(x, y);
    }
    function hide() { tip.hidden = true; }

    document.addEventListener("pointermove", function (e) {
      var t = e.target && e.target.closest ? e.target.closest("[data-tip]") : null;
      if (t) showText(t.getAttribute("data-tip"), e.pageX, e.pageY);
      else if (!(e.target.classList && e.target.classList.contains("ln-hit"))) hide();
    });
    document.addEventListener("pointerdown", function (e) {
      var t = e.target && e.target.closest ? e.target.closest("[data-tip]") : null;
      if (t && e.pointerType === "touch") showText(t.getAttribute("data-tip"), e.pageX, e.pageY);
      else if (!(e.target.classList && e.target.classList.contains("ln-hit"))) hide();
    });
    document.addEventListener("focusin", function (e) {
      var t = e.target && e.target.closest ? e.target.closest("[data-tip]") : null;
      if (!t) return;
      var r = t.getBoundingClientRect();
      showText(t.getAttribute("data-tip"), r.left + window.pageXOffset, r.bottom + window.pageYOffset - 16);
    });
    document.addEventListener("focusout", hide);
    window.addEventListener("scroll", hide, { passive: true });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") hide(); });

    // line charts: a crosshair snapping to the nearest x and one tooltip listing every series
    Array.prototype.forEach.call(document.querySelectorAll(".lines[data-series]"), function (box) {
      var data;
      try { data = JSON.parse(box.getAttribute("data-series")); } catch (err) { return; }
      Array.prototype.forEach.call(box.querySelectorAll("svg.ln"), function (svg) {
        var hit = svg.querySelector(".ln-hit"), hair = svg.querySelector(".ln-xhair");
        if (!hit || !hair) return;
        var x0 = Number(svg.getAttribute("data-x0")), x1 = Number(svg.getAttribute("data-x1"));
        var vb = svg.viewBox.baseVal;
        function move(e) {
          var rect = svg.getBoundingClientRect();
          var sx = ((e.clientX - rect.left) / rect.width) * vb.width;
          var idx = nearestIndex(sx, x0, x1, data.xs.length);
          var gx = x0 + (idx * (x1 - x0)) / (data.xs.length - 1);
          hair.setAttribute("x1", gx);
          hair.setAttribute("x2", gx);
          hair.removeAttribute("hidden");
          showRows(lineTip(data, idx), e.pageX, e.pageY);
        }
        function leave() { hair.setAttribute("hidden", ""); hide(); }
        hit.addEventListener("pointermove", move);
        hit.addEventListener("pointerdown", move);
        hit.addEventListener("pointerleave", leave);
      });
    });
  }

  function initStates() {
    var table = document.getElementById("states-table");
    if (!table || !table.tBodies.length) return;
    var tbody = table.tBodies[0];
    var heads = Array.prototype.slice.call(table.tHead.rows[0].cells);
    var empty = tbody.querySelector(".st-empty");
    var state = { col: 1, dir: "desc" };

    function dataRows() {
      return Array.prototype.filter.call(tbody.rows, function (r) { return r !== empty; });
    }
    function sortKey(row, col) { return parseCell(row.cells[col].getAttribute("data-sort")); }
    function apply() {
      var rows = dataRows();
      var pinned = rows.filter(function (r) { return r.getAttribute("data-pinned") === "true"; });
      var rest = rows.filter(function (r) { return pinned.indexOf(r) === -1; });
      rest.sort(function (a, b) { return compareRows(sortKey(a, state.col), sortKey(b, state.col), state.dir); });
      pinned.concat(rest).forEach(function (r) { tbody.appendChild(r); });
      if (empty) tbody.appendChild(empty);
      heads.forEach(function (th, i) {
        th.setAttribute("aria-sort", i === state.col ? (state.dir === "desc" ? "descending" : "ascending") : "none");
      });
    }
    heads.forEach(function (th, i) {
      var btn = th.querySelector("button");
      if (!btn) return;
      btn.addEventListener("click", function () {
        if (state.col === i) state.dir = state.dir === "desc" ? "asc" : "desc";
        else { state.col = i; state.dir = th.getAttribute("data-type") === "text" ? "asc" : "desc"; }
        apply();
      });
    });

    var input = document.getElementById("state-filter");
    if (input) {
      input.addEventListener("input", function () {
        var shown = 0;
        dataRows().forEach(function (r) {
          var pinned = r.getAttribute("data-pinned") === "true";
          var ok = pinned || matchesQuery(r.getAttribute("data-name") || "", input.value);
          r.hidden = !ok;
          if (ok && !pinned) shown += 1;
        });
        if (empty) empty.hidden = shown !== 0;
      });
    }
  }

  function initNav() {
    if (!("IntersectionObserver" in window)) return;
    var nav = document.querySelector(".bar nav");
    if (!nav) return;
    var links = {};
    Array.prototype.forEach.call(nav.querySelectorAll('a[href^="#"]'), function (a) {
      links[a.getAttribute("href").slice(1)] = a;
    });
    function current(id) {
      Object.keys(links).forEach(function (k) {
        if (k === id) links[k].setAttribute("aria-current", "true");
        else links[k].removeAttribute("aria-current");
      });
      var a = links[id];
      if (a && nav.scrollWidth > nav.clientWidth) {
        var left = a.offsetLeft - nav.offsetLeft;
        if (left < nav.scrollLeft || left + a.offsetWidth > nav.scrollLeft + nav.clientWidth) {
          nav.scrollLeft = Math.max(0, left - 16);
        }
      }
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) current(en.target.id); });
    }, { rootMargin: "-25% 0px -65% 0px" });
    Array.prototype.forEach.call(document.querySelectorAll("main > section[id]"), function (s) { io.observe(s); });
  }

  function init() {
    initTooltip();
    initStates();
    initNav();
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
  }

  // Expression value of this script, read by website/tests/site.test.mjs.
  return { compareRows: compareRows, parseCell: parseCell, tipText: tipText,
           nearestIndex: nearestIndex, lineTip: lineTip, matchesQuery: matchesQuery };
})();
