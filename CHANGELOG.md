# Changelog

## Unreleased
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
