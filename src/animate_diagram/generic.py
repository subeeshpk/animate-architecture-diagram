"""
animate_diagram.generic

Adds a marching-dash "data flow" animation to every connector line/path
in an SVG exported from any tool (Figma, Lucidchart, etc.) that doesn't
embed draw.io-style edge metadata. Use animate_diagram.drawio instead
whenever the source SVG came from draw.io -- it's more reliable.

How it finds connectors:
    Architecture diagram tools consistently export arrows/lines as
    <path>, <line>, or <polyline> elements with fill:none and a stroke
    color (boxes/shapes have a fill, connectors don't). This script
    matches on that pattern, which can occasionally over-match a shape's
    own outline (see README "Known limitations").
"""
import sys
import argparse
import xml.etree.ElementTree as ET

from .common import register_namespaces, build_dash_style_element, apply_dash_animation, reject_dangerous_xml

register_namespaces()

CONNECTOR_TAGS = {"path", "line", "polyline"}


def is_connector(el):
    tag = el.tag.split("}")[-1]
    if tag not in CONNECTOR_TAGS:
        return False
    fill = (el.get("fill") or "").replace(" ", "")
    style = (el.get("style") or "").replace(" ", "")
    no_fill = fill == "none" or "fill:none" in style
    has_stroke = bool(el.get("stroke")) or "stroke:" in style
    return no_fill and has_stroke


def animate(input_path, output_path, speed=1.0, stagger=0.35, dash="8 6"):
    """Animate any SVG's connector-like elements. Returns the count
    animated, or raises ValueError if none were found."""
    with open(input_path, encoding="utf-8") as f:
        reject_dangerous_xml(f.read())

    try:
        tree = ET.parse(input_path)
    except ET.ParseError as e:
        raise ValueError(f"Could not parse {input_path} as XML/SVG: {e}")
    root = tree.getroot()

    connectors = [el for el in root.iter() if is_connector(el)]
    if not connectors:
        raise ValueError(
            "No connector-like elements found (looked for <path>/<line>/<polyline> "
            "with fill:none and a stroke). This can happen if your export tool "
            "groups/flattens connectors differently."
        )

    style_el = build_dash_style_element(speed, dash)
    root.insert(0, style_el)

    for i, el in enumerate(connectors):
        apply_dash_animation(el, i, stagger)

    tree.write(output_path, encoding="unicode", xml_declaration=True)
    return len(connectors)


def main():
    parser = argparse.ArgumentParser(
        description="Animate connector-like elements in any exported SVG (fallback for non-draw.io sources).",
        epilog="Example: animate-svg-flow input/source.svg output/animated.svg --stagger 0.4"
    )
    parser.add_argument("input", help="path to the exported SVG (from draw.io, Figma, etc.)")
    parser.add_argument("output", help="path to write the animated SVG")
    parser.add_argument("--speed", type=float, default=1.0, help="seconds per animation loop (default 1.0)")
    parser.add_argument("--stagger", type=float, default=0.35, help="delay in seconds between successive connectors, 0 = all move together (default 0.35)")
    parser.add_argument("--dash", default="8 6", help="stroke-dasharray pattern, e.g. '8 6' (default) or '4 4' for finer dashes")
    args = parser.parse_args()

    try:
        count = animate(args.input, args.output, speed=args.speed, stagger=args.stagger, dash=args.dash)
    except ValueError as e:
        print(e)
        sys.exit(1)

    print(f"Animated {count} connector(s) in document order.")
    print(f"Wrote {args.output} — open it in a browser to preview.")
    if args.stagger > 0:
        print("Tip: if the sequence doesn't match your intended data flow, open the SVG in a text")
        print("editor, find the relevant <path>/<line> elements, and manually adjust their")
        print("animation-delay values — much less work than writing the animation from scratch.")


if __name__ == "__main__":
    main()
