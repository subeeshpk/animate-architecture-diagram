"""Tests for animate_diagram.drawio. Run with: python3 -m unittest discover -s tests -v"""
import os
import sys
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from animate_diagram import drawio

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
INPUT_SVG = os.path.join(REPO_ROOT, "input", "source.svg")


class TestGetEdgeIds(unittest.TestCase):
    def test_finds_no_edges_without_content_attribute(self):
        self.assertEqual(drawio.get_edge_ids("<svg></svg>"), [])

    def test_finds_edge_ids_in_embedded_content(self):
        raw = (
            '<svg content="&lt;mxCell id=&quot;e1&quot; edge=&quot;1&quot;/&gt;'
            '&lt;mxCell id=&quot;shape1&quot;/&gt;"></svg>'
        )
        self.assertEqual(drawio.get_edge_ids(raw), ["e1"])

    def test_real_example_has_thirteen_edges(self):
        # Regression check against input/source.svg. If this number changes,
        # the file was likely re-exported -- update deliberately, and keep
        # the README's example counts in sync.
        with open(INPUT_SVG, encoding="utf-8") as f:
            raw = f.read()
        self.assertEqual(len(drawio.get_edge_ids(raw)), 13)


class TestFindConnectorPath(unittest.TestCase):
    def test_returns_fill_none_path(self):
        group = ET.fromstring(
            '<g xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0" fill="none" stroke="#000"/>'
            '<path d="M0 0" fill="#000"/>'
            "</g>"
        )
        result = drawio.find_connector_path(group)
        self.assertEqual(result.get("fill"), "none")

    def test_returns_none_when_no_connector_present(self):
        group = ET.fromstring(
            '<g xmlns="http://www.w3.org/2000/svg"><path d="M0 0" fill="#000"/></g>'
        )
        self.assertIsNone(drawio.find_connector_path(group))


class TestAnimateFunction(unittest.TestCase):
    """Calls animate_diagram.drawio.animate() directly (no subprocess)."""

    def _animate(self, **kwargs):
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
            out_path = tmp.name
        try:
            result = drawio.animate(INPUT_SVG, out_path, **kwargs)
            with open(out_path, encoding="utf-8") as f:
                output = f.read()
            return result, output
        finally:
            os.remove(out_path)

    def test_dash_style_animates_all_edges(self):
        (animated, total), output = self._animate(style="dash")
        self.assertEqual((animated, total), (13, 13))
        self.assertIn("stroke-dashoffset", output)

    def test_dot_style_uses_animate_motion_with_circle(self):
        (animated, total), output = self._animate(style="dot")
        self.assertEqual((animated, total), (13, 13))
        self.assertIn("animateMotion", output)
        self.assertIn("<circle", output)

    def test_pig_style_uses_custom_emoji(self):
        (animated, total), output = self._animate(style="pig", emoji="🚀")
        self.assertEqual((animated, total), (13, 13))
        self.assertIn("🚀", output)

    def test_raises_on_missing_metadata(self):
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as tmp:
            tmp.write("<svg xmlns='http://www.w3.org/2000/svg'></svg>")
            no_metadata_path = tmp.name
        try:
            with self.assertRaises(ValueError):
                drawio.animate(no_metadata_path, "/tmp/should-not-be-created.svg")
        finally:
            os.remove(no_metadata_path)

    def test_raises_valueerror_on_malformed_xml(self):
        """A file with a matching draw.io content= attribute but that isn't
        well-formed XML must raise a clean ValueError, not an uncaught
        xml.etree.ElementTree.ParseError."""
        malformed = (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'content="&lt;mxGraphModel&gt;&lt;root&gt;'
            '&lt;mxCell id=&quot;e1&quot; edge=&quot;1&quot;/&gt;'
            '&lt;/root&gt;&lt;/mxGraphModel&gt;">'
            '<g data-cell-id="e1"><path d="M0 0 L10 & 10" fill="none" stroke="#000"/></g>'
            '</svg>'
        )
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as tmp:
            tmp.write(malformed)
            bad_path = tmp.name
        try:
            with self.assertRaises(ValueError):
                drawio.animate(bad_path, "/tmp/should-not-be-created.svg")
        finally:
            os.remove(bad_path)

    def test_rejects_doctype_entity_declaration(self):
        """Guards against XML entity-expansion ("billion laughs") DoS: a
        DOCTYPE/ENTITY declaration must be rejected before parsing, even if
        it also happens to carry valid-looking draw.io edge metadata."""
        bomb = (
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE svg [<!ENTITY a "x"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">]>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" content="&lt;mxCell id=&quot;e1&quot; edge=&quot;1&quot;/&gt;">'
            '<g data-cell-id="e1"><path d="M0 0" fill="none" stroke="#000" title="&b;"/></g>'
            '</svg>'
        )
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as tmp:
            tmp.write(bomb)
            bomb_path = tmp.name
        try:
            with self.assertRaises(ValueError):
                drawio.animate(bomb_path, "/tmp/should-not-be-created.svg")
        finally:
            os.remove(bomb_path)


class TestCliEndToEnd(unittest.TestCase):
    """Confirms the installed console command / CLI entry point itself works,
    the same way a user would invoke it from the command line."""

    def test_cli_via_python_module(self):
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
            out_path = tmp.name
        try:
            env = dict(os.environ, PYTHONPATH=os.path.join(REPO_ROOT, "src"))
            result = subprocess.run(
                [sys.executable, "-m", "animate_diagram.drawio", INPUT_SVG, out_path, "--style", "dot"],
                capture_output=True, text=True, check=True, env=env,
            )
            self.assertIn("Animated 13 of 13", result.stdout)
        finally:
            os.remove(out_path)


if __name__ == "__main__":
    unittest.main()
