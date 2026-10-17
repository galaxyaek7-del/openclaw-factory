"""Mission 3 tests (founder directive, 2026-10-17): the cover generator
emits a 1280x720 PNG above Gumroad's 10 KB floor. Isolated to tmp dirs so
a test run never writes into the real books/covers/ tree.

    python -m pytest tests/test_cover_generator.py -q
"""
import os
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_all_covers import generate_cover  # noqa: E402


def test_cover_generates_correct_size(tmp_path):
    path = generate_cover("test-cover", "Test Product", 29, "Test", out_dir=tmp_path)
    assert Image.open(path).size == (1280, 720)


def test_cover_is_png(tmp_path):
    path = generate_cover("test-format", "Test", 10, "Test", out_dir=tmp_path)
    assert path.endswith(".png")
    assert Image.open(path).format == "PNG"


def test_cover_above_minimum_size(tmp_path):
    path = generate_cover("test-size", "A Product", 50, "Tools", out_dir=tmp_path)
    assert os.path.getsize(path) > 10000
