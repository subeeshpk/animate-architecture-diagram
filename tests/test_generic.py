"""Tests for animate_diagram.generic. Run with: python3 -m unittest discover -s tests -v"""
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from animate_diagram import generic

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
INPUT_SVG = os.path.join(REPO_ROOT, "input", "source.svg")


class TestIsConnector(unittest.TestCase):
    def test_accepts_fill_none_path_with_stroke(self):
        el = ET.fromstring('<path xmlns="http://www.w3.org/2000/svg" fill="none" stroke="#000"/>')
        self.assertTrue(generic.is_connector(el))

    def test_rejects_filled_shape(self):
        el = ET.fromstring('<path xmlns="http://www.w3.org/2000/svg" fill="#fff" stroke="#000"/>')
        self.assertFalse(generic.is_connector(el))

    def test_rejects_non_connector_tag(self):
        el = ET.fromstring('<rect xmlns="http://www.w3.org/2000/svg" fill="none" stroke="#000"/>')
        self.assertFalse(generic.is_connector(el))

    def test_known_limitation_matches_uml_actor_body_outline(self):
        # A UML actor icon's body is drawn as a fill:none, stroked path --
        # structurally identical to a real connector line. This is *expected*
        # to return True; it's why animate_diagram.drawio is the more
        # reliable option for draw.io exports specifically.
        actor_body = ET.fromstring(
            '<path xmlns="http://www.w3.org/2000/svg" '
            'd="M 34 20 L 34 45" fill="none" stroke="#82b366"/>'
        )
        self.assertTrue(generic.is_connector(actor_body))


class TestAnimateFunction(unittest.TestCase):
    def test_real_example_overcounts_by_one_actor_outline(self):
        # Regression check documenting the known heuristic gap: the example
        # diagram has 13 real edges (per animate_diagram.drawio's metadata-
        # based count) but this generic module also catches one UML actor's
        # body outline, animating 14. If this changes, update deliberately
        # and update the README's "Known limitations" section to match.
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
            out_path = tmp.name
        try:
            count = generic.animate(INPUT_SVG, out_path)
            self.assertEqual(count, 14)
        finally:
            os.remove(out_path)

    def test_raises_on_no_connectors_found(self):
        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as tmp:
            tmp.write("<svg xmlns='http://www.w3.org/2000/svg'><rect fill='#fff'/></svg>")
            empty_path = tmp.name
        try:
            with self.assertRaises(ValueError):
                generic.animate(empty_path, "/tmp/should-not-be-created.svg")
        finally:
            os.remove(empty_path)


if __name__ == "__main__":
    unittest.main()
