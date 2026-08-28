// Per-edge style picker: click-to-select between the rendered diagram
// preview and its list of edge rows. Vanilla JS, no dependencies -- this
// file is served same-origin under CSP's script-src 'self', so it's the
// only script that can run on this page at all.
document.addEventListener("DOMContentLoaded", function () {
  var edges = document.querySelectorAll(".picker-edge");
  var rows = document.querySelectorAll(".edge-row");

  function clearHighlights() {
    edges.forEach(function (el) { el.classList.remove("picker-edge-active"); });
    rows.forEach(function (el) { el.classList.remove("edge-row-active"); });
  }

  function activate(edgeId) {
    clearHighlights();
    edges.forEach(function (el) {
      if (el.dataset.edgeId === edgeId) el.classList.add("picker-edge-active");
    });
    var row = document.getElementById("row-" + edgeId);
    if (row) row.classList.add("edge-row-active");
  }

  edges.forEach(function (el) {
    el.addEventListener("click", function () {
      activate(el.dataset.edgeId);
      var row = document.getElementById("row-" + el.dataset.edgeId);
      if (row) row.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  });

  rows.forEach(function (row) {
    row.addEventListener("mouseenter", function () {
      activate(row.dataset.edgeId);
    });
  });

  // Style selects: dim the emoji/color fields that don't apply to the
  // currently chosen style for that row, so it's clear which inputs matter.
  document.querySelectorAll(".edge-row select[name^='style__']").forEach(function (select) {
    function sync() {
      var row = select.closest(".edge-row");
      if (!row) return;
      var style = select.value;
      var emojiField = row.querySelector("input[name^='emoji__']");
      var colorField = row.querySelector("input[name^='dot_color__']");
      if (emojiField) emojiField.closest(".field").style.opacity = (style === "pig") ? "1" : "0.35";
      if (colorField) colorField.closest(".field").style.opacity = (style === "dot") ? "1" : "0.35";
    }
    select.addEventListener("change", sync);
    sync();
  });
});
