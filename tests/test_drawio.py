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


class TestEdgeOverrides(unittest.TestCase):
    """Per-edge style overrides (used by the web UI's style picker)."""

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

    def test_no_overrides_matches_plain_call(self):
        """edge_overrides={} (or omitted) must behave identically to not
        passing it at all -- this is the backward-compatibility guarantee
        the whole refactor rests on."""
        (animated_a, total_a), output_a = self._animate(style="dot")
        (animated_b, total_b), output_b = self._animate(style="dot", edge_overrides={})
        self.assertEqual((animated_a, total_a), (animated_b, total_b))
        self.assertEqual(output_a, output_b)

    def test_per_edge_style_mix(self):
        with open(INPUT_SVG, encoding="utf-8") as f:
            edge_ids = drawio.get_edge_ids(f.read())
        overrides = {
            edge_ids[0]: {"style": "pig", "emoji": "🚀"},
            edge_ids[1]: {"style": "dot", "dot_color": "#00FF00"},
            edge_ids[2]: {"style": "skip"},
        }
        (animated, total), output = self._animate(style="dash", edge_overrides=overrides)
        # 13 edges total, one skipped -> 12 animated
        self.assertEqual((animated, total), (12, 13))
        self.assertIn("🚀", output)
        self.assertIn("#00FF00", output)
        # the dash <style> block must still be emitted since most edges
        # fall back to the global "dash" default
        self.assertIn("stroke-dashoffset", output)

    def test_skip_all_animates_nothing(self):
        with open(INPUT_SVG, encoding="utf-8") as f:
            edge_ids = drawio.get_edge_ids(f.read())
        overrides = {eid: {"style": "skip"} for eid in edge_ids}
        (animated, total), output = self._animate(style="dash", edge_overrides=overrides)
        self.assertEqual((animated, total), (0, 13))
        # no edge used dash, so the shared style block shouldn't be added either
        self.assertNotIn("stroke-dashoffset", output)


class TestGetEdgeDetails(unittest.TestCase):
    def test_returns_one_entry_per_edge_in_order(self):
        with open(INPUT_SVG, encoding="utf-8") as f:
            raw = f.read()
        ids = drawio.get_edge_ids(raw)
        details = drawio.get_edge_details(raw)
        self.assertEqual([d["id"] for d in details], ids)

    def test_finds_edge_label(self):
        with open(INPUT_SVG, encoding="utf-8") as f:
            raw = f.read()
        details = drawio.get_edge_details(raw)
        labels = [d["label"] for d in details]
        self.assertIn("Write", labels)

    def test_empty_without_metadata(self):
        self.assertEqual(drawio.get_edge_details("<svg></svg>"), [])

    def test_entity_bomb_hidden_in_content_falls_back_safely(self):
        """The outer reject_dangerous_xml(raw) check (run by callers before
        this function) only scans the raw, still HTML-escaped file text --
        an <!ENTITY> hidden inside the escaped content="..." attribute
        reads as "&lt;!ENTITY" there, not "<!entity", so it slips past that
        check. get_edge_details() parses `content` as its own second XML
        document (after html.unescape), so it needs -- and, since the fix,
        has -- its own reject_dangerous_xml(content) guard. This should
        return the safe empty-label fallback almost instantly rather than
        attempting to expand the entity bomb."""
        import html as html_module
        import time

        entity_bomb = (
            '<?xml version="1.0"?>'
            '<!DOCTYPE mxGraphModel [.'
            '<!ENTITY a "aaaaaaaaaaaaaaaaaaaa">'
            '<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
            '<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">'
            ']>'
            '<mxGraphModel><root>'
            '<mxCell id="edge1" edge="1" source="a" target="b"><mxGeometry/></mxCell>'
            '</root></mxGraphModel>'
        )
        escaped = html_module.escape(entity_bomb)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" content="{escaped}">'
            '<g data-cell-id="edge1"><path stroke="#000" fill="none" d="M0 0 L10 10"/></g>'
            '</svg>'
        )

        # The outer check must NOT catch this -- that's what makes it a
        # real regression test for the inner guard rather than a no-op.
        from animate_diagram.common import reject_dangerous_xml
        try:
            reject_dangerous_xml(svg)
            outer_caught = False
        except ValueError:
            outer_caught = True
        self.assertFalse(outer_caught, "outer raw-text check unexpectedly caught the escaped payload")

        start = time.time()
        details = drawio.get_edge_details(svg)
        elapsed = time.time() - start

        self.assertEqual(details, [{"id": "edge1", "label": "", "source_label": "", "target_label": ""}])
        self.assertLess(elapsed, 1.0, "get_edge_details took too long -- may be expanding the entity bomb")


class TestIndexCellsById(unittest.TestCase):
    def test_matches_root_find_semantics(self):
        tree = ET.parse(INPUT_SVG)
        root = tree.getroot()
        index = drawio.index_cells_by_id(root)
        for cell_id in list(index.keys())[:5]:
            expected = root.find(f'.//*[@data-cell-id="{cell_id}"]')
            self.assertIs(index[cell_id], expected)


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
