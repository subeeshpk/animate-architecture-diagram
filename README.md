# animate-architecture-diagram

Turn a static architecture diagram (exported as SVG) into an animated one showing data flow — dashed lines, a traveling packet dot, or a traveling emoji — without hand-editing any coordinates.

Point it at an SVG in `input/`, get back an animated SVG in `output/`. Open the result in a browser to preview it live, then screen-record it (e.g. with [ScreenToGif](https://www.screentogif.com/)) to produce a GIF for slides, docs, or LinkedIn.

## Project structure

```
animate-architecture-diagram/
├── src/
│   └── animate_diagram/
│       ├── __init__.py
│       ├── common.py     # shared helpers used by both modules below
│       ├── drawio.py     # main animator, for draw.io/diagrams.net exports
│       └── generic.py    # fallback animator, for other SVG sources
├── scripts/                # zero-install entry points (no pip install needed)
│   ├── animate_drawio_svg.py
│   └── animate_svg_flow.py
├── input/                   # drop your source SVGs here
│   └── source.svg           # sample draw.io export used by the test suite
├── output/                  # animated SVGs land here
│   ├── animated-dash.svg    # sample outputs for each style, checked into
│   ├── animated-dot.svg     # the repo as a reference/demo
│   └── animated-pig.svg
├── tests/                   # unittest suite, stdlib only
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
└── .gitignore
```

## Which one do I use?

| Your SVG came from | Use |
|---|---|
| draw.io / diagrams.net | `animate_diagram.drawio` |
| Figma, Lucidchart, or anything else | `animate_diagram.generic` |

`animate_diagram.drawio` is the reliable one for draw.io exports: it reads draw.io's own embedded diagram data (the hidden `content` attribute on the root `<svg>`) to know exactly which elements are edges. This matters because some shapes — a UML actor icon's body outline, for example — also happen to use `fill:none` strokes, and a naive "line with no fill" guess would wrongly animate those too.

`animate_diagram.generic` is the fallback for SVGs with no draw.io metadata. It uses that naive heuristic (any `<path>`/`<line>`/`<polyline>` with `fill:none` and a stroke is treated as a connector), which works fine for simpler diagrams but can over-match on complex icon sets (see Known limitations).

## Requirements

Python 3.8+, standard library only at runtime — no dependencies to install to *use* the tool.

**For the draw.io animator:** export from draw.io with **"Include a copy of my diagram"** checked (this is the default export setting, so most exports already have it).

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

- **`dash`** *(default)* — the connector line turns into moving dashes, like a continuous stream. Built with `stroke-dasharray` + an animated `stroke-dashoffset`.
- **`dot`** — the connector line stays solid; a small circle travels its length on a loop, representing one request/packet moving through the system. Built with native SVG `animateMotion` + `mpath`, so it automatically follows bends in the line.
- **`pig`** — same mechanism as `dot`, but the traveling shape is an emoji (🐷 by default) instead of a plain circle. Use `--emoji` to swap in anything else (`🚀`, `📦`, ...).

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

## Running the tests

No extra dependencies — the test suite uses only Python's built-in `unittest`:

```bash
python3 -m unittest discover -s tests -v
```

The tests call the `animate_diagram` modules directly, plus one subprocess check confirming the CLI entry point itself works, all against the real `input/source.svg`. A regression test also documents `animate_diagram.generic`'s known over-counting behavior (see below) so it's caught if it silently gets worse.

## Known limitations

- `animate_diagram.generic`'s heuristic (any `fill:none` stroked path is a connector) can over-count: on `input/source.svg` it animates 14 elements where only 13 are real edges, because a UML actor icon's body outline matches the same pattern. This is why `animate_diagram.drawio` exists as the more reliable option whenever draw.io metadata is available — use the generic one only when it isn't.
- `animateMotion` (used by `dot` and `pig`) works when you open the SVG file directly in a browser, but many CMS/blog editors strip it out when you paste an SVG inline — this workflow is built around screen-recording the animation into a GIF, not embedding the live SVG elsewhere.
- If the draw.io animator reports "No embedded draw.io edge metadata found," re-export with "Include a copy of my diagram" checked, or fall back to `animate_diagram.generic`.
- If it finds edges but animates fewer than expected, draw.io may have nested the connector path deeper than the group-scan expects — open the SVG and check how that specific edge is structured.

## Author

[subeeshpk](https://github.com/subeeshpk)

## License

MIT © [subeeshpk](https://github.com/subeeshpk) — see [LICENSE](LICENSE).
