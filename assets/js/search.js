(function () {
  var input = document.getElementById("q");
  if (!input) return;
  var listEl = document.getElementById("lesson-list");
  var resultsEl = document.getElementById("search-results");
  var metaEl = document.getElementById("search-meta");
  var indexUrl = input.getAttribute("data-index");

  var docs = null;      // loaded lazily on first interaction
  var loading = false;

  function loadIndex() {
    if (docs || loading) return;
    loading = true;
    fetch(indexUrl)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        docs = data.map(function (d) {
          return {
            title: d.title, subtitle: d.subtitle, date: d.date, url: d.url,
            content: d.content,
            hay: (d.title + " " + d.subtitle + " " + d.content).toLowerCase()
          };
        });
        if (input.value.trim()) run(input.value);
      })
      .catch(function () { loading = false; });
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function highlight(text, terms) {
    var out = escapeHtml(text);
    terms.forEach(function (t) {
      if (!t) return;
      var re = new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig");
      out = out.replace(re, "<mark>$1</mark>");
    });
    return out;
  }

  // A ~160-char window around the first matching term in the body.
  function snippet(content, terms) {
    var lc = content.toLowerCase(), pos = -1;
    for (var i = 0; i < terms.length; i++) {
      var p = lc.indexOf(terms[i]);
      if (p !== -1 && (pos === -1 || p < pos)) pos = p;
    }
    if (pos === -1) return "";
    var start = Math.max(0, pos - 60);
    var frag = content.slice(start, start + 160).trim();
    return (start > 0 ? "… " : "") + highlight(frag, terms) + " …";
  }

  function score(doc, terms) {
    var s = 0, t = doc.title.toLowerCase(), sub = doc.subtitle.toLowerCase();
    terms.forEach(function (term) {
      if (t.indexOf(term) !== -1) s += 10;
      if (sub.indexOf(term) !== -1) s += 4;
      var m = doc.content.toLowerCase().split(term).length - 1;
      s += Math.min(m, 5);
    });
    return s;
  }

  function run(q) {
    var terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) {
      resultsEl.hidden = true;
      resultsEl.innerHTML = "";
      metaEl.hidden = true;
      if (listEl) listEl.hidden = false;
      return;
    }
    if (!docs) { loadIndex(); metaEl.hidden = false; metaEl.textContent = "Searching…"; return; }

    var hits = docs
      .filter(function (d) { return terms.every(function (t) { return d.hay.indexOf(t) !== -1; }); })
      .map(function (d) { return { d: d, s: score(d, terms) }; })
      .sort(function (a, b) { return b.s - a.s; });

    if (listEl) listEl.hidden = true;
    metaEl.hidden = false;
    metaEl.textContent = hits.length + (hits.length === 1 ? " lesson" : " lessons") + " found";

    resultsEl.innerHTML = hits.map(function (h) {
      var d = h.d, snip = snippet(d.content, terms);
      return '<li class="lesson-item">' +
        '<a href="' + d.url + '">' +
        '<time>' + escapeHtml(d.date) + "</time>" +
        '<span class="lesson-item-title">' + highlight(d.title, terms) + "</span>" +
        (d.subtitle ? '<span class="lesson-item-sub">' + highlight(d.subtitle, terms) + "</span>" : "") +
        (snip ? '<span class="lesson-item-snippet">' + snip + "</span>" : "") +
        "</a></li>";
    }).join("");
    resultsEl.hidden = false;
  }

  input.addEventListener("focus", loadIndex);
  input.addEventListener("input", function () { run(input.value); });

  // "/" focuses search; Esc clears.
  document.addEventListener("keydown", function (e) {
    if (e.key === "/" && document.activeElement !== input) { e.preventDefault(); input.focus(); }
    if (e.key === "Escape" && document.activeElement === input) { input.value = ""; run(""); input.blur(); }
  });
})();
