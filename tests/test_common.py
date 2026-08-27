"""Unit tests for animate_diagram.common. Run with: python3 -m unittest discover -s tests -v"""
import os
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from animate_diagram.common import build_dash_style_element, apply_dash_animation


class TestBuildDashStyleElement(unittest.TestCase):
    def test_dash_total_matches_pattern(self):
        style_el = build_dash_style_element(speed=1.0, dash="8 6")
        self.assertIn("stroke-dashoffset: -14", style_el.text)

    def test_speed_is_used_in_animation_duration(self):
        style_el = build_dash_style_element(speed=2.5, dash="4 4")
        self.assertIn("animation: flow 2.5s linear infinite", style_el.text)

    def test_uneven_dash_pattern(self):
        style_el = build_dash_style_element(speed=1.0, dash="10 3")
        self.assertIn("stroke-dashoffset: -13", style_el.text)


class TestApplyDashAnimation(unittest.TestCase):
    def test_adds_flow_line_class(self):
        path = ET.Element("path")
        apply_dash_animation(path, index=0, stagger=0.35)
        self.assertIn("flow-line", path.get("class"))

    def test_preserves_existing_class(self):
        path = ET.Element("path", {"class": "existing-class"})
        apply_dash_animation(path, index=0, stagger=0.35)
        self.assertIn("existing-class", path.get("class"))
        self.assertIn("flow-line", path.get("class"))

    def test_staggers_delay_by_index(self):
        path0 = ET.Element("path")
        path1 = ET.Element("path")
        apply_dash_animation(path0, index=0, stagger=0.35)
        apply_dash_animation(path1, index=2, stagger=0.35)
        self.assertIn("animation-delay:0.0s", path0.get("style"))
        self.assertIn("animation-delay:0.7s", path1.get("style"))

    def test_preserves_existing_inline_style(self):
        path = ET.Element("path", {"style": "stroke:#000000"})
        apply_dash_animation(path, index=0, stagger=0.35)
        self.assertIn("stroke:#000000", path.get("style"))
        self.assertIn("animation-delay", path.get("style"))


if __name__ == "__main__":
    unittest.main()
