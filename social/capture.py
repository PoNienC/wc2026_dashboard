"""Render a poster HTML page to a PNG at a fixed mobile-portrait size.

Input CRS: n/a (screen raster). Layer: social_export.
Usage: python capture.py <input.html> <output.png> [width] [height]
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

def render(html: Path, out: Path, width: int, height: int) -> None:
    """Screenshot ``html`` at ``width`` x ``height`` CSS px, 2x device scale."""
    url = html.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(viewport={"width": width, "height": height},
                                device_scale_factor=2)
        page.goto(url, wait_until="networkidle", timeout=30000)
        try:
            page.wait_for_function("window.__ready === true", timeout=15000)
        except Exception:
            pass  # fall back to whatever has painted
        page.wait_for_timeout(700)
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": width, "height": height})
        browser.close()

if __name__ == "__main__":
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 1080
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 1350
    render(src, dst, w, h)
    print(f"wrote {dst} ({w}x{h} @2x)")
