# Changelog

## Unreleased
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
