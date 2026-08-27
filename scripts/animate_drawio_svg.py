#!/usr/bin/env python3
"""
Zero-install entry point: run this directly without `pip install`.
Equivalent to the `animate-drawio-svg` command once the package is installed.

Usage:
    python3 scripts/animate_drawio_svg.py input/source.svg output/animated.svg
    python3 scripts/animate_drawio_svg.py input/source.svg output/animated.svg --style dot
    python3 scripts/animate_drawio_svg.py input/source.svg output/animated.svg --style pig --emoji "🚀"
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from animate_diagram.drawio import main

if __name__ == "__main__":
    main()
