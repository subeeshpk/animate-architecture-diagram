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


def apply_dash_animation(path_el, index, stagger):
    """Add the flow-line class and a staggered animation-delay to a
    connector path/line element, in place."""
    existing_class = (path_el.get("class") or "").strip()
    path_el.set("class", (existing_class + " flow-line").strip())
    delay = round(index * stagger, 2)
    existing_style = (path_el.get("style") or "").rstrip(";")
    new_style = f"{existing_style};animation-delay:{delay}s;" if existing_style else f"animation-delay:{delay}s;"
    path_el.set("style", new_style)
