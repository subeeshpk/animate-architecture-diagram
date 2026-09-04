"""
animate_diagram.common

Shared helpers used by both the drawio and generic animation modules:
namespace handling, the dash-flow style block, and how a staggered
animation-delay gets applied to a connector element.
"""
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"


def register_namespaces():
    """Call once per script before parsing/writing SVGs, so ElementTree
    round-trips the svg/xlink namespaces cleanly instead of inventing
    ns0/ns1-style prefixes."""
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)


def build_dash_style_element(speed, dash):
    """Return a <style> element implementing the moving-dashes flow
    animation, for insertion at the top of the SVG tree."""
    dash_total = sum(int(x) for x in dash.split())
    style_el = ET.Element("style")
    style_el.text = f"""
    .flow-line {{
      stroke-dasharray: {dash};
      animation: flow {speed}s linear infinite;
    }}
    @keyframes flow {{
      to {{ stroke-dashoffset: -{dash_total}; }}
    }}
    """
    return style_el


def apply_dash_animation(path_el, index, stagger, speed=None):
    """Add the flow-line class and a staggered animation-delay to a
    connector path/line element, in place.

    speed: optional per-edge override (seconds per loop). All dash-styled
    edges share one <style> block/@keyframes (see build_dash_style_element)
    with one duration baked into it, so a per-edge override can't come
    from a second shared class -- instead this adds an inline
    "animation-duration" declaration, which CSS's own cascade rules give
    priority over the class's "animation" shorthand for that one edge,
    without needing a duplicate keyframes block (the keyframes are
    percentage-based, not duration-based, so they're shared safely).
    Left out entirely (the default) when no override is given, so the
    output is byte-identical to before this parameter existed."""
    existing_class = (path_el.get("class") or "").strip()
    path_el.set("class", (existing_class + " flow-line").strip())
    delay = round(index * stagger, 2)
    existing_style = (path_el.get("style") or "").rstrip(";")
    declarations = f"animation-delay:{delay}s;"
    if speed is not None:
        declarations += f"animation-duration:{speed}s;"
    new_style = f"{existing_style};{declarations}" if existing_style else declarations
    path_el.set("style", new_style)


# Tags that can execute code when an SVG is rendered inline in a page (as
# opposed to opened standalone as a file). NOTE: <foreignObject> is
# deliberately NOT in this list -- draw.io/diagrams.net exports use it as
# the *primary* rendering path for every text label (each one is wrapped
# in <switch><foreignObject>...flexbox-centered HTML...</foreignObject>
# <text>...approximate fallback...</text></switch>), so deleting it
# outright knocks every label back to its crude fallback <text> position
# and visibly misaligns them. It's still safe to keep: sanitize_svg_tree()
# recurses into every element regardless of nesting, so a <script> tag or
# on*="" handler placed *inside* a <foreignObject> is still stripped by
# the rules below -- only the wrapper itself, and its legitimate content,
# survive.
_DANGEROUS_SVG_TAGS = {"script", "iframe", "embed", "object"}


def _local_name(tag):
    return tag.split("}")[-1].lower()


def sanitize_svg_tree(root):
    """Strip elements/attributes that could execute script if this SVG is
    rendered inline in an HTML page: <script>/<iframe>/<embed>/<object>
    tags (wherever they appear, including nested inside a <foreignObject>),
    any on*="..." event-handler attribute, and javascript:/data:text/html
    URIs in href/xlink:href. Mutates the tree in place; returns nothing.

    SVG is an executable format, not just an image format -- untrusted
    SVG content (e.g. a file someone uploaded) must go through this
    before it's ever embedded inline in a web page. This does not touch
    the CLI's normal output path; it exists for callers (like the web UI)
    that render an SVG's markup directly into HTML."""
    for el in root.iter():
        for child in list(el):
            if _local_name(child.tag) in _DANGEROUS_SVG_TAGS:
                el.remove(child)

    for el in root.iter():
        for attr in list(el.attrib):
            local_attr = _local_name(attr)
            value = el.attrib[attr]
            if local_attr.startswith("on"):
                del el.attrib[attr]
            elif local_attr == "href" and value.strip().lower().startswith(("javascript:", "data:text/html")):
                del el.attrib[attr]


def reject_dangerous_xml(raw_text):
    """Raise ValueError if raw_text declares an internal XML entity
    (<!ENTITY ...>). xml.etree.ElementTree (stdlib) has no protection
    against XML entity-expansion ("billion laughs") attacks -- a tiny file
    with a handful of nested <!ENTITY> definitions can expand to gigabytes
    in memory during parsing.

    Note this deliberately does NOT reject a plain <!DOCTYPE> by itself --
    that's extremely common and harmless (e.g. draw.io/most SVG tools emit
    `<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" ".../svg11.dtd">`, an
    external reference with no internal entity subset; ElementTree never
    fetches that external DTD, so it carries no expansion or XXE risk).
    The actual attack vector is an internal <!ENTITY> definition, which is
    what this checks for."""
    if "<!entity" in raw_text.lower():
        raise ValueError(
            "This SVG contains an <!ENTITY> declaration, which isn't "
            "supported (it's rejected as a precaution against XML entity-"
            "expansion attacks). Re-export without an embedded DTD entity."
        )
