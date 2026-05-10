"""Test configuration for tinybrain inner package tests.

Ensures the installed tinybrain package is used rather than the outer
tinybrain/ directory which shadows it.
"""

import sys
from pathlib import Path

# Remove the outer tinybrain/ directory from sys.path if it's there,
# so the installed tinybrain package (inner) takes priority.
_outer_dir = str(Path(__file__).resolve().parent.parent)
if _outer_dir in sys.path:
    sys.path.remove(_outer_dir)
