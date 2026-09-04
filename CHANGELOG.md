# Changelog

## Unreleased
- Added an independent per-edge speed override to the web UI's per-edge style picker: each edge row now has its own optional "Speed (s/loop)" field, left blank to use the global speed or set to make one connector visibly faster or slower than the rest. For `dash`-styled edges this adds an inline `animation-duration` declaration to that one connector, which CSS's cascade rules give priority over the shared `.flow-line` class -- no duplicate `<style>`/`@keyframes` block needed, since the keyframes are percentage-based and duration-agnostic. For `dot`/`pig`-styled edges it's even simpler: each edge's `<animateMotion>` already sets its own `dur` individually, so this is just reading a per-edge value instead of the global one. `animate_diagram.drawio.animate()`'s `edge_overrides` dict gained a new `"speed"` key alongside the existing `style`/`dot_color`/`emoji` ones, following the same fallback-to-global pattern; `stagger` (when each edge starts, as opposed to how fast it loops) stays global either way.
- Follow-up fixes from a second review pass on the per-edge style picker: (1) `/pick`'s three early-return failure paths (rejected XML, missing draw.io metadata, malformed XML) now delete the just-saved upload before redirecting -- previously each failed attempt left an orphaned `<token>-input.svg` in `web/tmp/` forever, only the success path cleaned up. (2) `get_edge_details()`'s own `ET.fromstring()` call on the embedded, HTML-escaped draw.io metadata is now guarded by its own `reject_dangerous_xml()` check -- the existing outer check (run by callers on the raw file text) scans it *before* unescaping, so an `<!ENTITY>` entity-expansion payload hidden inside the escaped `content="..."` attribute previously bypassed it entirely. (3) The result page's edge-count summary ("animated N of M edge(s)") wasn't showing for per-edge results -- it checked `used_engine == 'drawio'` exactly, but `/animate_custom` reports `"drawio (per-edge)"`.
- Added a per-edge style picker to the web UI ("Pick styles per edge…"): for draw.io exports, click a connector in an unanimated preview (or hover its row) to select it, then assign dash/dot/pig/skip and an emoji/color per edge before animating -- instead of one style applied to every connector. Backed by a new `edge_overrides` parameter on `animate_diagram.drawio.animate()` (per-edge dict, falls back to the existing global style/emoji/color args for anything not overridden -- omitting it entirely behaves exactly as before) and two new helpers, `get_edge_details()` (best-effort edge labels/source/target for display) and `index_cells_by_id()` (shared with the existing O(N+M) lookup).
- Fixed a label-alignment regression from the XSS sanitizer: it was deleting every `<foreignObject>` outright, which is what draw.io/diagrams.net uses as the primary (flexbox-centered) rendering path for every text label -- deleting it dropped labels like edge captions back to their crude fallback `<text x= y=>` position, visibly misaligning them. `sanitize_svg_tree()` now leaves `<foreignObject>` itself alone and relies on its existing rules (still applied to everything nested inside it) to strip any `<script>`/`<iframe>`/`<embed>`/`<object>` tag or `on*=""` handler placed there.
- Fixed a crash: a malformed/corrupted SVG (well-formed enough to match the draw.io metadata regex but not valid XML) raised an uncaught `ParseError` in `animate_diagram.drawio` instead of a clean error -- crashed the CLI with a traceback and returned an unhandled 500 from the web UI. Now raises a friendly `ValueError`, matching how `animate_diagram.generic` already handled it.
- Added `animate_diagram.common.reject_dangerous_xml()`: rejects SVGs containing an internal `<!ENTITY>` declaration before parsing, as a dependency-free guard against XML entity-expansion ("billion laughs") DoS attacks. A plain `<!DOCTYPE>` (e.g. the standard external SVG 1.1 DTD reference most tools emit) is left alone.
- `animate_diagram.drawio.animate()` now builds a single `data-cell-id` index instead of re-scanning the whole tree with `root.find()` once per edge -- O(edges + tree size) instead of O(edges × tree size); no behavior change.
- Web UI: `web/tmp/` output files are now swept once they're over an hour old (checked on every `/animate` request) instead of accumulating forever. Flask's `debug` mode is now off by default -- set `FLASK_DEBUG=1` to opt back in for local development.
- Fixed a stored-XSS vulnerability in the web UI: an uploaded SVG containing `<script>` tags or `on*=""` event-handler attributes was rendered unescaped into the result page. Added `animate_diagram.common.sanitize_svg_tree()` (strips `<script>`/`<foreignObject>`, event-handler attributes, and `javascript:` URIs) applied before preview/download, plus Content-Security-Policy / X-Frame-Options response headers as defense in depth.
- Added a local Flask web UI (`web/app.py`, optional `pip install -e ".[web]"`) for uploading an SVG, choosing a style, previewing the animated result inline, and downloading it — no CLI needed.
- Restructured into a standard installable Python project: real `src/animate_diagram/`
  package, `pyproject.toml` with console-script entry points (`animate-drawio-svg`,
  `animate-svg-flow`), and `input/`/`output/` working folders.
- Kept a zero-install path via `scripts/animate_drawio_svg.py` and
  `scripts/animate_svg_flow.py` — run directly with `python3`, no `pip install` needed.
- Extracted shared logic (namespace setup, dash-flow style block, staggered
  animation-delay) into `animate_diagram/common.py`.
- Added a `tests/` suite (stdlib `unittest`, no extra dependencies), including
  a regression test against the real example diagram in `input/source.svg`.
- Added `.gitignore`, `LICENSE` (MIT).

## v0.3 — Pig style
- Added `--style pig`: a traveling emoji (🐷 by default, configurable via
  `--emoji`) instead of a plain dot, using the same `animateMotion` mechanism.

## v0.2 — Dot style
- Added `--style dot`: a single circle traveling along each connector via
  native SVG `animateMotion` + `mpath`, representing one packet/request
  moving through the system, as an alternative to the dashed-line stream.

## v0.1 — Initial release
- draw.io-aware animation: animates connector edges in a draw.io/diagrams.net
  export using the diagram's own embedded edge metadata, so shape outlines
  (e.g. a UML actor's body) are never mistaken for connectors.
- Generic fallback: for SVGs without draw.io metadata (Figma, Lucidchart,
  etc.), using a fill:none-plus-stroke heuristic.
