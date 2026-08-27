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
from animate_diagram.common import sanitize_svg_tree  # noqa: E402
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
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/animate", methods=["POST"])
def animate_route():
    _sweep_stale_tmp_files()

    uploaded = request.files.get("svg")
    if not uploaded or uploaded.filename == "":
        flash("Please choose an SVG file to upload.")
        return redirect(url_for("index"))
    if not uploaded.filename.lower().endswith(".svg"):
        flash("Please upload a .svg file.")
        return redirect(url_for("index"))

    engine = request.form.get("engine", "auto")
    style = request.form.get("style", "dash")

    def _float(name, default):
        raw = request.form.get(name, "").strip()
        try:
            return float(raw) if raw else default
        except ValueError:
            return default

    speed = _float("speed", 1.0)
    stagger = _float("stagger", 0.35)
    dash = request.form.get("dash", "").strip() or "8 6"
    dot_radius = _float("dot_radius", 5.0)
    dot_color = request.form.get("dot_color", "").strip() or "#E08A1E"
    emoji = request.form.get("emoji", "").strip() or "\U0001F437"
    emoji_size = _float("emoji_size", 20.0)

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
