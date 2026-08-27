"""
animate_diagram.drawio

Animates connector edges in an SVG exported from draw.io / diagrams.net.
Unlike a naive fill:none heuristic, this reads draw.io's own embedded
diagram metadata (the hidden 'content' attribute on the root <svg>) to
find the exact cell IDs that are edges -- so it never mistakes a shape's
outline (e.g. a UML actor's fill:none body stroke) for a connector.

Requires: draw.io export with "Include a copy of my diagram" checked
(this is the default) so the content attribute is present.

Three animation styles:
    dash  (default) -- the connector line turns into moving dashes,
                       like a continuous stream (stroke-dashoffset).
    dot   -- the connector line stays solid; a single small circle
             travels its length on a loop, like one packet/request
             moving through the system (SVG native animateMotion).
    pig   -- same mechanism as dot, but the traveling shape is an
             emoji (a pig, by default) instead of a plain circle.
             Use --emoji to swap in any other emoji/character.
"""
import re
import html
import sys
import argparse
import xml.etree.ElementTree as ET

from .common import SVG_NS, register_namespaces, build_dash_style_element, apply_dash_animation, reject_dangerous_xml

register_namespaces()


def get_edge_ids(raw_svg_text):
    m = re.search(r'content="([^"]*)"', raw_svg_text)
    if not m:
        return []
    content = html.unescape(m.group(1))
    return re.findall(r'<mxCell id="([^"]+)"[^>]*edge="1"', content)


def find_connector_path(group_el):
    """Within a data-cell-id group, the connector line is the first
    path with fill:none (the arrowhead, if present, is filled solid)."""
    for path in group_el.iter("{%s}path" % SVG_NS):
        fill = (path.get("fill") or "").replace(" ", "")
        style = (path.get("style") or "").replace(" ", "")
        if fill == "none" or "fill:none" in style:
            return path
    return None


def animate(input_path, output_path, speed=1.0, stagger=0.35, dash="8 6",
            style="dash", dot_radius=5.0, dot_color="#E08A1E",
            emoji="🐷", emoji_size=20.0):
    """Animate a draw.io-exported SVG. Returns (animated_count, total_edges),
    or raises ValueError if no draw.io edge metadata is found."""
    with open(input_path, encoding="utf-8") as f:
        raw = f.read()
    reject_dangerous_xml(raw)
    edge_ids = get_edge_ids(raw)
    if not edge_ids:
        raise ValueError(
            "No embedded draw.io edge metadata found in this file. "
            "Re-export with 'Include a copy of my diagram' checked, "
            "or use animate_diagram.generic for non-draw.io SVGs."
        )

    try:
        tree = ET.parse(input_path)
    except ET.ParseError as e:
        raise ValueError(f"Could not parse {input_path} as XML/SVG: {e}")
    root = tree.getroot()
    animated = 0

    # Index every data-cell-id group once (O(tree size)) instead of running
    # a fresh root.find() XPath scan per edge (which was O(edges x tree size)).
    # Keep the *first* match for a given id, matching root.find()'s semantics.
    cell_by_id = {}
    for el in root.iter():
        cell_id = el.get("data-cell-id")
        if cell_id is not None and cell_id not in cell_by_id:
            cell_by_id[cell_id] = el

    if style == "dash":
        style_el = build_dash_style_element(speed, dash)
        root.insert(0, style_el)

        for i, edge_id in enumerate(edge_ids):
            group = cell_by_id.get(edge_id)
            if group is None:
                continue
            path = find_connector_path(group)
            if path is None:
                continue
            apply_dash_animation(path, i, stagger)
            animated += 1

    else:  # dot or pig mode: line stays as-is, a shape rides along it via animateMotion
        for i, edge_id in enumerate(edge_ids):
            group = cell_by_id.get(edge_id)
            if group is None:
                continue
            path = find_connector_path(group)
            if path is None:
                continue
            path_id = f"packet-path-{i}"
            path.set("id", path_id)
            if not path.get("d"):
                continue
            delay = round(i * stagger, 2)

            if style == "pig":
                traveler = ET.SubElement(group, "{%s}text" % SVG_NS)
                traveler.set("font-size", str(emoji_size))
                traveler.set("text-anchor", "middle")
                traveler.set("dominant-baseline", "central")
                traveler.text = emoji
            else:  # dot
                traveler = ET.SubElement(group, "{%s}circle" % SVG_NS)
                traveler.set("r", str(dot_radius))
                traveler.set("fill", dot_color)

            anim = ET.SubElement(traveler, "{%s}animateMotion" % SVG_NS)
            anim.set("dur", f"{speed}s")
            anim.set("repeatCount", "indefinite")
            anim.set("begin", f"{delay}s")
            mpath = ET.SubElement(anim, "{%s}mpath" % SVG_NS)
            mpath.set("{http://www.w3.org/1999/xlink}href", f"#{path_id}")
            animated += 1

    tree.write(output_path, encoding="unicode", xml_declaration=True)
    return animated, len(edge_ids)


def main():
    parser = argparse.ArgumentParser(
        description="Animate connector edges in a draw.io-exported SVG.",
        epilog="Example: animate-drawio-svg input/source.svg output/animated.svg --style dot"
    )
    parser.add_argument("input", help="path to the SVG exported from draw.io")
    parser.add_argument("output", help="path to write the animated SVG")
    parser.add_argument("--speed", type=float, default=1.0, help="seconds per animation loop (default: 1.0)")
    parser.add_argument("--stagger", type=float, default=0.35, help="delay in seconds between successive edges animating; use 0 to animate all edges together (default: 0.35)")
    parser.add_argument("--dash", default="8 6", help="stroke-dasharray pattern, e.g. '8 6' (default) or '4 4' for finer dashes")
    parser.add_argument("--style", choices=["dash", "dot", "pig"], default="dash", help="'dash' for a moving-dashes stream, 'dot' for a traveling circle, 'pig' for a traveling emoji (default: dash)")
    parser.add_argument("--dot-radius", type=float, default=5.0, help="radius in px of the traveling dot, only used with --style dot (default: 5.0)")
    parser.add_argument("--dot-color", default="#E08A1E", help="fill color of the traveling dot, only used with --style dot (default: #E08A1E)")
    parser.add_argument("--emoji", default="🐷", help="emoji/character to animate along the path, only used with --style pig (default: 🐷)")
    parser.add_argument("--emoji-size", type=float, default=20.0, help="font size in px of the traveling emoji, only used with --style pig (default: 20.0)")
    args = parser.parse_args()

    try:
        animated, total = animate(
            args.input, args.output, speed=args.speed, stagger=args.stagger,
            dash=args.dash, style=args.style, dot_radius=args.dot_radius,
            dot_color=args.dot_color, emoji=args.emoji, emoji_size=args.emoji_size,
        )
    except ValueError as e:
        print(e)
        sys.exit(1)

    print(f"Animated {animated} of {total} edge(s) found in the diagram.")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
