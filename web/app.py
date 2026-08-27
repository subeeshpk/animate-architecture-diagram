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
import io
import os
import sys
import uuid
from pathlib import Path

from flask import Flask, render_template, request, send_from_directory, flash, redirect, url_for

# make the src/ package importable without requiring an install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from animate_diagram import drawio, generic  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
TMP_DIR = BASE_DIR / "tmp"
TMP_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB, plenty for an architecture diagram SVG

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-local-secret")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/animate", methods=["POST"])
def animate_route():
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
    app.run(debug=True, port=5050)
