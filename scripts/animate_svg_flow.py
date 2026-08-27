#!/usr/bin/env python3
"""
Zero-install entry point: run this directly without `pip install`.
Equivalent to the `animate-svg-flow` command once the package is installed.

Usage:
    python3 scripts/animate_svg_flow.py input/source.svg output/animated.svg
    python3 scripts/animate_svg_flow.py input/source.svg output/animated.svg --stagger 0.4
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from animate_diagram.generic import main

if __name__ == "__main__":
    main()
