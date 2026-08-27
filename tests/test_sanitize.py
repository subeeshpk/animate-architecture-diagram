import unittest
import xml.etree.ElementTree as ET

from animate_diagram.common import sanitize_svg_tree, register_namespaces

register_namespaces()


class TestSanitizeSvgTree(unittest.TestCase):
    def test_removes_script_tag(self):
        root = ET.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<script>alert(1)</script>'
            '<path d="M0 0" fill="none" stroke="#000"/>'
            '</svg>'
        )
        sanitize_svg_tree(root)
        out = ET.tostring(root, encoding="unicode")
        self.assertNotIn("<script", out)
        self.assertIn("<path", out)

    def test_removes_event_handler_attribute(self):
        root = ET.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)">'
            '<rect onclick="alert(2)" fill="#fff"/>'
            '</svg>'
        )
        sanitize_svg_tree(root)
        self.assertIsNone(root.get("onload"))
        rect = root.find("{http://www.w3.org/2000/svg}rect")
        self.assertIsNone(rect.get("onclick"))

    def test_preserves_foreignobject_but_strips_nested_script(self):
        # <foreignObject> itself must survive -- draw.io/diagrams.net uses
        # it as the primary (flexbox-centered) rendering path for every
        # text label; deleting the wrapper knocks labels back to their
        # crude <text x= y=> fallback position and visibly misaligns them.
        # A <script> nested inside it must still be stripped, though.
        root = ET.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<foreignObject><body xmlns="http://www.w3.org/1999/xhtml">'
            '<div>Write</div><script>alert(1)</script></body></foreignObject>'
            '</svg>'
        )
        sanitize_svg_tree(root)
        out = ET.tostring(root, encoding="unicode")
        self.assertIn("foreignObject", out)
        self.assertIn("Write", out)
        self.assertNotIn("<script", out)

    def test_strips_iframe_embed_object_anywhere_including_nested(self):
        root = ET.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<iframe src="https://evil.example"/>'
            '<foreignObject><body xmlns="http://www.w3.org/1999/xhtml">'
            '<embed src="https://evil.example"/><object data="https://evil.example"/>'
            '</body></foreignObject>'
            '</svg>'
        )
        sanitize_svg_tree(root)
        out = ET.tostring(root, encoding="unicode")
        self.assertNotIn("<iframe", out)
        self.assertNotIn("<embed", out)
        self.assertNotIn("<object", out)
        self.assertNotIn("evil.example", out)

    def test_removes_javascript_uri_href(self):
        root = ET.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<a xlink:href="javascript:alert(1)"><rect fill="#fff"/></a>'
            '</svg>'
        )
        sanitize_svg_tree(root)
        a_el = root.find("{http://www.w3.org/2000/svg}a")
        self.assertIsNone(a_el.get("{http://www.w3.org/1999/xlink}href"))

    def test_leaves_ordinary_animation_markup_untouched(self):
        root = ET.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path id="p1" d="M0 0 L10 10" fill="none" stroke="#000">'
            '<animateMotion dur="1s" repeatCount="indefinite"/>'
            '</path>'
            '</svg>'
        )
        sanitize_svg_tree(root)
        out = ET.tostring(root, encoding="unicode")
        self.assertIn("animateMotion", out)
        self.assertIn('stroke="#000"', out)


if __name__ == "__main__":
    unittest.main()
