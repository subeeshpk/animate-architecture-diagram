# animate-architecture-diagram

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Dependencies: stdlib only (CLI)](https://img.shields.io/badge/CLI%20deps-stdlib%20only-informational)](#requirements)

Turn a static architecture diagram (exported as SVG) into an animated one showing data flow — dashed lines, a traveling packet dot, or a traveling emoji — without hand-editing any coordinates.

Point it at an SVG in `input/`, get back an animated SVG in `output/`. Open the result in a browser to preview it live, then screen-record it (e.g. with [ScreenToGif](https://www.screentogif.com/)) to produce a GIF for slides, docs, or LinkedIn. There's also a local **[web UI](#web-ui)** if you'd rather not touch a terminal at all.

## Contents

- [Which one do I use?](#which-one-do-i-use)
- [Requirements](#requirements)
- [Setup](#setup)
- [Usage](#usage)
- [Animation styles](#animation-styles)
- [Examples](#examples)
- [Web UI](#web-ui)
  - [Per-edge style picker](#per-edge-style-picker)
- [Running the tests](#running-the-tests)
- [Project structure](#project-structure)
- [Known limitations](#known-limitations)
- [Author](#author)
- [License](#license)

## Which one do I use?

| Your SVG came from | Use |
|---|---|
| draw.io / diagrams.net | `animate_diagram.drawio` |
| Figma, Lucidchart, or anything else | `animate_diagram.generic` |

`animate_diagram.drawio` is the reliable one for draw.io exports: it reads draw.io's own embedded diagram data (the hidden `content` attribute on the root `<svg>`) to know exactly which elements are edges. This matters because some shapes — a UML actor icon's body outline, for example — also happen to use `fill:none` strokes, and a naive "line with no fill" guess would wrongly animate those too.

`animate_diagram.generic` is the fallback for SVGs with no draw.io metadata. It uses that naive heuristic (any `<path>`/`<line>`/`<polyline>` with `fill:none` and a stroke is treated as a connector), which works fine for simpler diagrams but can over-match on complex icon sets (see [Known limitations](#known-limitations)).

## Requirements

Python 3.8+, standard library only at runtime — no dependencies to install to *use* the CLI. The optional [web UI](#web-ui) adds one dependency, Flask.

**For the draw.io animator:** export from draw.io with **"Include a copy of my diagram"** checked (this is the default export setting, so most exports already have it).

## Setup

The scripts themselves need nothing beyond the standard library, but if you're on macOS you can easily have more than one `python3` on your machine (Apple's Command Line Tools stub, Homebrew, pyenv, Anaconda, ...) — and if `pip install` and `python3 script.py` resolve to *different* ones, you'll install a package into a Python that never runs it (this bites hardest once you also want the [web UI](#web-ui), since that pulls in Flask as a real dependency instead of being pure stdlib).

Avoid the whole class of problem with a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows
```

Once activated, `python3` and `pip` inside that shell always point at the same interpreter, so every command below just works. Re-run the `source` line whenever you open a new terminal for this project (`deactivate` to leave the venv).

If you'd rather not bother with a venv, at minimum confirm they match before installing anything:

```bash
which -a python3
python3 -c "import sys; print(sys.executable)"
python3 -m pip --version   # note which interpreter this reports
```

and always invoke pip as `python3 -m pip ...` rather than a bare `pip`, so it can't silently pick a different interpreter than the `python3` you're about to run.

## Usage

You can run this two ways — pick whichever fits how you work.

### Option A: zero-install scripts

```bash
python3 scripts/animate_drawio_svg.py input/source.svg output/my-diagram.svg
python3 scripts/animate_drawio_svg.py input/source.svg output/my-diagram.svg --style dot
python3 scripts/animate_drawio_svg.py input/source.svg output/my-diagram.svg --style pig --emoji "🚀"

# non-draw.io SVG (Figma, Lucidchart, etc.)
python3 scripts/animate_svg_flow.py input/source.svg output/my-diagram.svg
```

### Option B: install as a package, get real commands

```bash
pip install -e .

animate-drawio-svg input/source.svg output/my-diagram.svg --style dot
animate-svg-flow input/source.svg output/my-diagram.svg
```

Both options run the exact same code — `scripts/` just adds `src/` to the path manually instead of relying on an install.

Full flag reference is always available via:
```bash
python3 scripts/animate_drawio_svg.py --help
```

## Animation styles

| Style | Effect | How |
|---|---|---|
| `dash` *(default)* | The connector line turns into moving dashes, like a continuous stream. | `stroke-dasharray` + an animated `stroke-dashoffset` |
| `dot` | The connector line stays solid; a small circle travels its length on a loop, representing one request/packet moving through the system. | Native SVG `animateMotion` + `mpath`, so it automatically follows bends in the line |
| `pig` | Same mechanism as `dot`, but the traveling shape is an emoji (🐷 by default) instead of a plain circle. Use `--emoji` to swap in anything else (`🚀`, `📦`, ...). | `animateMotion` + `mpath` |

Key flags per style:

| Flag | Applies to | Default | What it does |
|---|---|---|---|
| `--style` | `drawio` | `dash` | Which animation style to use: `dash`, `dot`, or `pig` |
| `--speed` | all | `1.0` | Seconds per animation loop |
| `--stagger` | all | `0.35` | Delay (seconds) between each successive edge starting to animate; `0` = all edges move together |
| `--dash` | `dash` | `"8 6"` | The dash/gap pattern |
| `--dot-radius` | `dot` | `5.0` | Radius (px) of the traveling circle |
| `--dot-color` | `dot` | `#E08A1E` | Fill color of the traveling circle |
| `--emoji` | `pig` | `🐷` | The character that travels along the path |
| `--emoji-size` | `pig` | `20.0` | Font size (px) of the traveling emoji |

## Examples

`input/source.svg` is a sample draw.io diagram; `output/animated-{dash,dot,pig}.svg` are its animated results in each style. Open any of them directly in a browser to see the animation.

## Web UI

A small local Flask app wraps the same `animate_diagram` functions with a browser upload/preview/download flow — no CLI needed.

```bash
pip install -e ".[web]"
python3 web/app.py
```

Then open http://127.0.0.1:5050, upload an SVG, pick a style and options, and either preview the animation inline or download the result. It reuses `animate_diagram.drawio` and `.generic` directly, so behavior matches the CLI exactly.

**Security, by default:** uploaded SVGs are treated as untrusted. Before anything is previewed inline or offered for download, `animate_diagram.common.sanitize_svg_tree()` strips `<script>` tags, `on*=""` event-handler attributes, and `javascript:`/`data:text/html` URIs — everywhere in the tree, including inside a `<foreignObject>` (which is left in place otherwise, since draw.io relies on it to render text labels correctly). The app also sends Content-Security-Policy/X-Frame-Options headers as a second layer of defense, and guards against malformed or malicious XML: `animate_diagram.common.reject_dangerous_xml()` rejects an embedded `<!ENTITY>` declaration before *any* parsing of the upload — including draw.io's own embedded diagram metadata — as a dependency-free defense against XML entity-expansion ("billion laughs") DoS, and a corrupted file that isn't valid XML gets a clean error instead of crashing the request. Generated and uploaded files in `web/tmp/` are swept once they're over an hour old, on both success and failure. By default the server runs with Flask's debug mode off; set `FLASK_DEBUG=1` if you want the interactive debugger for local development.

This is a local, single-user tool by design — it hasn't been hardened for multi-user or public deployment.

### Per-edge style picker

For draw.io exports, the web UI also offers "Pick styles per edge…" as an alternative to the single-style "Animate" button: it shows the diagram unanimated with each connector clickable, lets you assign dash/dot/pig/skip (plus emoji/color/speed) individually per edge, and animates with that mix.

- Click a connector in the preview to jump to its row, or hover a row to highlight its connector in the preview.
- Each edge is labeled with its own text where draw.io provides one, otherwise its source → target shape names, otherwise a generic "Edge N".
- Set an edge's style to `skip` to leave that one connector unanimated entirely.
- Each edge also has its own optional speed field (seconds per loop) — leave it blank to use the global speed above, or set it to make one connector visibly faster or slower than the rest (e.g. a "hot path" that loops quickly, or a rarely-hit fallback path that crawls). `stagger` (when each edge starts) stays global regardless.

This only works with the draw.io engine, since identifying "which edge is which" relies on the exported diagram metadata — the generic (non-draw.io) engine has no per-edge identity to select against.

## Running the tests

No extra dependencies for the core suite — most of it uses only Python's built-in `unittest`; the `web/app.py` route tests additionally need Flask (`pip install -e ".[web]"`), same as the web UI itself.

```bash
python3 -m unittest discover -s tests -v
```

46 tests, all passing, covering: both animation engines end-to-end against the real `input/source.svg` (including that a per-edge speed override produces its own inline `animation-duration`/`dur` value while leaving every other edge on the global speed), the CLI entry point via a subprocess check, the web UI's `/pick` route (including that a rejected upload doesn't leak a temp file), SVG sanitization, and the XML entity-expansion guard — including a regression test for a payload smuggled inside draw.io's own escaped diagram metadata, not just the outer file. A regression test also documents `animate_diagram.generic`'s known over-counting behavior (see [Known limitations](#known-limitations)) so it's caught if it silently gets worse.

## Project structure

```
animate-architecture-diagram/
├── src/
│   └── animate_diagram/
│       ├── __init__.py
│       ├── common.py       # shared helpers: namespaces, dash-style block, SVG
│       │                   # sanitization, XML entity-bomb guard
│       ├── drawio.py       # main animator, for draw.io/diagrams.net exports
│       └── generic.py      # fallback animator, for other SVG sources
├── scripts/                 # zero-install entry points (no pip install needed)
│   ├── animate_drawio_svg.py
│   └── animate_svg_flow.py
├── web/                      # optional local Flask UI (pip install -e ".[web]")
│   ├── app.py                # routes: /animate, /pick, /animate_custom, /download
│   ├── static/
│   │   └── picker.js         # per-edge picker's click-to-select UI, no dependencies
│   ├── templates/            # index.html, pick.html, result.html
│   └── tmp/                   # uploads/generated files, swept hourly (git-ignored)
├── input/                    # drop your source SVGs here
│   └── source.svg             # sample draw.io export used by the test suite
├── output/                    # animated SVGs land here
│   ├── animated-dash.svg      # sample outputs for each style, checked into
│   ├── animated-dot.svg       # the repo as a reference/demo
│   └── animated-pig.svg
├── tests/                    # unittest suite (stdlib + Flask test client)
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
└── .gitignore
```

## Known limitations

- `animate_diagram.generic`'s heuristic (any `fill:none` stroked path is a connector) can over-count: on `input/source.svg` it animates 14 elements where only 13 are real edges, because a UML actor icon's body outline matches the same pattern. This is why `animate_diagram.drawio` exists as the more reliable option whenever draw.io metadata is available — use the generic one only when it isn't.
- `animateMotion` (used by `dot` and `pig`) works when you open the SVG file directly in a browser, but many CMS/blog editors strip it out when you paste an SVG inline — this workflow is built around screen-recording the animation into a GIF, not embedding the live SVG elsewhere.
- If the draw.io animator reports "No embedded draw.io edge metadata found," re-export with "Include a copy of my diagram" checked, or fall back to `animate_diagram.generic`.
- If it finds edges but animates fewer than expected, draw.io may have nested the connector path deeper than the group-scan expects — open the SVG and check how that specific edge is structured.
- The per-edge picker's `token` isn't validated against the shape it's actually generated in (a random 12-character hex string) before being used to build a file path — low-risk given this is a local single-user tool, but worth hardening before running it anywhere less trusted than localhost.

## Author

[subeeshpk](https://github.com/subeeshpk)

## License

MIT © [subeeshpk](https://github.com/subeeshpk) — see [LICENSE](LICENSE).