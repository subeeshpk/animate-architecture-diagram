"""Tests for web/app.py's /pick route tmp-file handling.
Run with: python3 -m unittest discover -s tests -v"""
import io
import os
import sys
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
sys.path.insert(0, os.path.join(REPO_ROOT, "web"))

import app as webapp  # noqa: E402


class TestPickRouteCleansUpOnFailure(unittest.TestCase):
    """/pick saves the upload to TMP_DIR before it knows whether the file
    is usable, so each of its three early-return (failure) paths must
    unlink that file itself -- nothing else will. Without that cleanup,
    every rejected upload (bad XML, malformed SVG, no draw.io metadata)
    leaves an orphaned "<token>-input.svg" in web/tmp/ forever."""

    def setUp(self):
        webapp.app.config["TESTING"] = True
        self.client = webapp.app.test_client()

    def _svg_count(self):
        return len(list(webapp.TMP_DIR.glob("*.svg")))

    def test_entity_declaration_failure_leaves_no_orphan(self):
        before = self._svg_count()
        bad = b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY x "boom">]>' \
              b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
        resp = self.client.post(
            "/pick",
            data={"file": (io.BytesIO(bad), "bad.svg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self._svg_count(), before)

    def test_no_drawio_metadata_failure_leaves_no_orphan(self):
        before = self._svg_count()
        bad = b'<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
        resp = self.client.post(
            "/pick",
            data={"file": (io.BytesIO(bad), "bad.svg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self._svg_count(), before)

    def test_malformed_xml_failure_leaves_no_orphan(self):
        before = self._svg_count()
        # Has a content= attribute (so get_edge_ids finds an edge and the
        # "no metadata" branch is skipped) but the outer SVG body itself
        # doesn't parse as XML, so this hits the ET.ParseError branch.
        bad = (
            b'<svg xmlns="http://www.w3.org/2000/svg" content="'
            b'&lt;mxGraphModel&gt;&lt;root&gt;'
            b'&lt;mxCell id=&quot;e1&quot; edge=&quot;1&quot;/&gt;'
            b'&lt;/root&gt;&lt;/mxGraphModel&gt;"><unclosed></svg>'
        )
        resp = self.client.post(
            "/pick",
            data={"file": (io.BytesIO(bad), "bad.svg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self._svg_count(), before)


if __name__ == "__main__":
    unittest.main()
