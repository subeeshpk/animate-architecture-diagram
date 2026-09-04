"""
web.app

A tiny local Flask UI around the animate_diagram package: upload an SVG,
pick a style and options, preview the animated result in the browser,
and download it.

Run with:
    pip install -e ".[web]"
    python3 web/app.py
then open http://127.0.0.1:5050
"""
import os
import sys
import time
import uuid
from pathlib import Path

from flask import Flask, render_template, request, send_from_directory, flash, redirect, url_for

# make the src/ package importable without requiring an install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from animate_diagram import drawio, generic  # noqa: E402
from animate_diagram.common import sanitize_svg_tree, reject_dangerous_xml  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
TMP_DIR = BASE_DIR / "tmp"
TMP_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB, plenty for an architecture diagram SVG
TMP_FILE_MAX_AGE_SECONDS = 60 * 60  # generated files older than this get swept


def _sweep_stale_tmp_files(max_age_seconds=TMP_FILE_MAX_AGE_SECONDS):
    """Delete generated/uploaded files in TMP_DIR older than max_age_seconds.
    Only the input file was ever cleaned up before -- output files (the ones
    kept around for preview + download) accumulated forever. Called on every
    /animate request, which is cheap and keeps disk usage bounded without
    needing a background job."""
    now = time.time()
    for f in TMP_DIR.glob("*.svg"):
        try:
            if now - f.stat().st_mtime > max_age_seconds:
                f.unlink(missing_ok=True)
        except OSError:
            pass  # another request may have already removed it -- fine

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-local-secret")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


@app.after_request
def set_security_headers(response):
    # Defense in depth alongside sanitize_svg_tree(): even if something
    # slipped through, don't let this page execute inline/external script
    # or be framed by another site. img-src is deliberately permissive --
    # draw.io diagrams commonly reference their shape-library icons as
    # external https:// images (e.g. app.diagrams.net) rather than
    # embedding them, and those still need to load.
    # script-src 'self' (not 'none') so the per-edge picker's own click-to-
    # select JS (web/static/picker.js, authored by us) can load. This does
    # NOT relax XSS protection for uploaded content: 'self' only allows
    # same-origin *external* script files, never inline scripts (no
    # 'unsafe-inline'), and there's no route that serves user-uploaded SVG
    # content as a script resource -- sanitize_svg_tree() also still strips
    # any <script> tag from uploaded SVGs regardless.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


def _validated_upload():
    """Return the uploaded file object, or None (having already flashed a
    message) if it's missing or not a .svg. Shared by /animate and /pick."""
    uploaded = request.files.get("svg")
    if not uploaded or uploaded.filename == "":
        flash("Please choose an SVG file to upload.")
        return None
    if not uploaded.filename.lower().endswith(".svg"):
        flash("Please upload a .svg file.")
        return None
    return uploaded


def _float_form(name, default):
    raw = request.form.get(name, "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


@app.route("/animate", methods=["POST"])
def animate_route():
    _sweep_stale_tmp_files()

    uploaded = _validated_upload()
    if uploaded is None:
        return redirect(url_for("index"))

    engine = request.form.get("engine", "auto")
    style = request.form.get("style", "dash")

    speed = _float_form("speed", 1.0)
    stagger = _float_form("stagger", 0.35)
    dash = request.form.get("dash", "").strip() or "8 6"
    dot_radius = _float_form("dot_radius", 5.0)
    dot_color = request.form.get("dot_color", "").strip() or "#E08A1E"
    emoji = request.form.get("emoji", "").strip() or "\U0001F437"
    emoji_size = _float_form("emoji_size", 20.0)

    token = uuid.uuid4().hex[:12]
    in_path = TMP_DIR / f"{token}-input.svg"
    out_path = TMP_DIR / f"{token}-output.svg"
    uploaded.save(in_path)

    used_engine = None
    animated_count = None
    total_edges = None
    try:
        if engine in ("auto", "drawio"):
            try:
                animated_count, total_edges = drawio.animate(
                    str(in_path), str(out_path), speed=speed, stagger=stagger, dash=dash,
                    style=style, dot_radius=dot_radius, dot_color=dot_color,
                    emoji=emoji, emoji_size=emoji_size,
                )
                used_engine = "drawio"
            except ValueError:
                if engine == "drawio":
                    raise
                animated_count = generic.animate(str(in_path), str(out_path), speed=speed, stagger=stagger, dash=dash)
                used_engine = "generic"
        else:
            animated_count = generic.animate(str(in_path), str(out_path), speed=speed, stagger=stagger, dash=dash)
            used_engine = "generic"
    except ValueError as e:
        flash(str(e))
        return redirect(url_for("index"))
    finally:
        in_path.unlink(missing_ok=True)

    # The uploaded SVG's own content survives into our output (the
    # animators only add animation attributes, they don't strip anything
    # from the source). Since we render this markup inline in the result
    # page below, sanitize it first -- SVG can carry <script> tags and
    # on*="" event handlers that would otherwise execute as this site.
    out_tree = ET.parse(out_path)
    sanitize_svg_tree(out_tree.getroot())
    out_tree.write(out_path, encoding="unicode", xml_declaration=True)

    svg_markup = out_path.read_text(encoding="utf-8")
    download_name = Path(uploaded.filename).stem + f"-animated-{style if used_engine == 'drawio' else 'dash'}.svg"

    return render_template(
        "result.html",
        svg_markup=svg_markup,
        token=token,
        download_name=download_name,
        used_engine=used_engine,
        style=style if used_engine == "drawio" else "dash",
        animated_count=animated_count,
        total_edges=total_edges,
    )


@app.route("/pick", methods=["POST"])
def pick_route():
    """Step 1 of the per-edge style picker: save the upload, render the
    *unanimated* diagram inline with each connector tagged as clickable,
    and list every edge (with a best-effort human label) so the user can
    assign a style/emoji/color per edge before actually animating."""
    _sweep_stale_tmp_files()

    uploaded = _validated_upload()
    if uploaded is None:
        return redirect(url_for("index"))

    speed = _float_form("speed", 1.0)
    stagger = _float_form("stagger", 0.35)
    dash = request.form.get("dash", "").strip() or "8 6"

    token = uuid.uuid4().hex[:12]
    in_path = TMP_DIR / f"{token}-input.svg"
    uploaded.save(in_path)
    # Unlike /animate, we deliberately keep in_path around -- /animate_custom
    # needs to re-read and re-parse the original file once the user submits
    # their per-edge choices. The usual tmp sweep (1 hour) still applies, so
    # an abandoned picker session doesn't linger forever.

    with open(in_path, encoding="utf-8") as f:
        raw = f.read()

    try:
        reject_dangerous_xml(raw)
    except ValueError as e:
        flash(str(e))
        in_path.unlink(missing_ok=True)
        return redirect(url_for("index"))

    edges = drawio.get_edge_details(raw)
    if not edges:
        flash(
            "Per-edge styling needs a draw.io export with embedded diagram "
            "metadata (no edges were found in this file's draw.io data). "
            "Try the regular \u201cAnimate\u201d button instead."
        )
        in_path.unlink(missing_ok=True)
        return redirect(url_for("index"))

    try:
        tree = ET.parse(in_path)
    except ET.ParseError as e:
        flash(f"Could not parse {uploaded.filename} as XML/SVG: {e}")
        in_path.unlink(missing_ok=True)
        return redirect(url_for("index"))
    root = tree.getroot()

    cell_by_id = drawio.index_cells_by_id(root)
    for edge in edges:
        group = cell_by_id.get(edge["id"])
        path = drawio.find_connector_path(group) if group is not None else None
        if path is None:
            edge["clickable"] = False
            continue
        edge["clickable"] = True
        existing_class = (path.get("class") or "").strip()
        path.set("class", (existing_class + " picker-edge").strip())
        path.set("data-edge-id", edge["id"])

    sanitize_svg_tree(root)
    preview_markup = ET.tostring(root, encoding="unicode")

    return render_template(
        "pick.html",
        svg_markup=preview_markup,
        edges=edges,
        token=token,
        orig_filename=uploaded.filename,
        speed=speed,
        stagger=stagger,
        dash=dash,
    )


@app.route("/animate_custom", methods=["POST"])
def animate_custom_route():
    """Step 2: apply the per-edge style choices from /pick and produce the
    animated result, same as /animate but driven by drawio.animate()'s
    edge_overrides instead of one global style."""
    token = request.form.get("token", "").strip()
    in_path = TMP_DIR / f"{token}-input.svg"
    if not token or not in_path.exists():
        flash("That upload has expired — please start again.")
        return redirect(url_for("index"))

    with open(in_path, encoding="utf-8") as f:
        raw = f.read()
    edge_ids = drawio.get_edge_ids(raw)

    speed = _float_form("speed", 1.0)
    stagger = _float_form("stagger", 0.35)
    dash = request.form.get("dash", "").strip() or "8 6"

    valid_styles = {"dash", "dot", "pig", "skip"}
    edge_overrides = {}
    for edge_id in edge_ids:
        style = request.form.get(f"style__{edge_id}", "dash").strip()
        if style not in valid_styles:
            style = "dash"
        override = {"style": style}
        dot_color = request.form.get(f"dot_color__{edge_id}", "").strip()
        if dot_color:
            override["dot_color"] = dot_color
        emoji = request.form.get(f"emoji__{edge_id}", "").strip()
        if emoji:
            override["emoji"] = emoji
        raw_edge_speed = request.form.get(f"speed__{edge_id}", "").strip()
        if raw_edge_speed:
            try:
                edge_speed = float(raw_edge_speed)
                if edge_speed > 0:
                    override["speed"] = edge_speed
            except ValueError:
                pass  # leave unset -- falls back to the global speed
        edge_overrides[edge_id] = override

    out_path = TMP_DIR / f"{token}-output.svg"
    try:
        animated_count, total_edges = drawio.animate(
            str(in_path), str(out_path), speed=speed, stagger=stagger, dash=dash,
            edge_overrides=edge_overrides,
        )
    except ValueError as e:
        flash(str(e))
        return redirect(url_for("index"))
    finally:
        in_path.unlink(missing_ok=True)

    out_tree = ET.parse(out_path)
    sanitize_svg_tree(out_tree.getroot())
    out_tree.write(out_path, encoding="unicode", xml_declaration=True)
    svg_markup = out_path.read_text(encoding="utf-8")

    orig_filename = request.form.get("orig_filename", "diagram.svg").strip() or "diagram.svg"
    download_name = Path(orig_filename).stem + "-animated-custom.svg"

    return render_template(
        "result.html",
        svg_markup=svg_markup,
        token=token,
        download_name=download_name,
        used_engine="drawio (per-edge)",
        style="custom",
        animated_count=animated_count,
        total_edges=total_edges,
    )


@app.route("/download/<token>/<path:filename>")
def download(token, filename):
    out_path = TMP_DIR / f"{token}-output.svg"
    if not out_path.exists():
        flash("That result has expired — please generate it again.")
        return redirect(url_for("index"))
    return send_from_directory(TMP_DIR, out_path.name, as_attachment=True, download_name=filename, mimetype="image/svg+xml")


if __name__ == "__main__":
    # Debug mode (Werkzeug's interactive debugger) is opt-in only: it lets
    # anyone who can trigger an unhandled exception run arbitrary Python via
    # the debugger console. Fine for local development, not something to
    # leave on by default now that this accepts file uploads.
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, port=5050)
