#!/usr/bin/env python3
"""Figure 3. Screenshots of the local α-synuclein page from the frozen site build.

    python scripts/fig3_screens.py            # serve site/dist, capture, compose
    python scripts/fig3_screens.py --compose  # compose from figures/_screens/*.png

The page is the local build, not conformome.org. Viewport 1400 px, device scale 2.
"""
from __future__ import annotations

import functools
import http.server
import socket
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from figstyle import COL2, save  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.image as mpimg  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SITE = REPO / "site" / "dist"
SCREENS = Path(__file__).resolve().parents[1] / "figures" / "_screens"
PANELS = ("states", "coverage", "viewer")

# Prefer an already-installed browser. Do not download a new Chromium.
BROWSER_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def _browser() -> str:
    for path in BROWSER_CANDIDATES:
        if Path(path).exists():
            return path
    raise SystemExit("fig3: no Chrome or Edge executable found; set one of the paths in BROWSER_CANDIDATES")


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def capture() -> None:
    if not (SITE / "protein" / "P37840" / "index.html").exists():
        raise SystemExit("fig3: site/dist/protein/P37840/index.html is missing; run make site")
    from playwright.sync_api import sync_playwright

    port = _port()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    SCREENS.mkdir(parents=True, exist_ok=True)
    url = f"http://127.0.0.1:{port}/protein/P37840/index.html"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=_browser(), headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, device_scale_factor=2)
            page.goto(url, wait_until="networkidle", timeout=120_000)
            page.wait_for_selector("h1")

            def section_clip(title: str) -> dict:
                box = page.evaluate(
                    """(title) => {
                        const h = [...document.querySelectorAll('h2')].find(e => e.textContent.includes(title));
                        if (!h) return null;
                        let bottom = h.getBoundingClientRect().bottom;
                        let n = h.nextElementSibling;
                        while (n && n.tagName !== 'H2') { bottom = n.getBoundingClientRect().bottom; n = n.nextElementSibling; }
                        const top = h.getBoundingClientRect().top;
                        return {x: 0, y: top + window.scrollY, width: 1400, height: Math.min(bottom - top + 8, 1400)};
                    }""",
                    title,
                )
                if not box:
                    raise SystemExit(f"fig3: no section titled {title!r}")
                return box

            # The sections sit below the first viewport, so the clip needs the full-page image.
            page.screenshot(path=str(SCREENS / "states.png"), full_page=True,
                            clip=section_clip("States and transitions"))
            page.screenshot(path=str(SCREENS / "coverage.png"), full_page=True,
                            clip=section_clip("Coverage grid"))

            # The fibril is not always the first model. Select it, then wait for the Mol* canvas.
            options = page.locator("#model-select option")
            labels = options.all_text_contents()
            fibril = next((i for i, lab in enumerate(labels) if "fibril" in lab.lower()), None)
            if fibril is None:
                raise SystemExit(f"fig3: no fibril model in the viewer select ({labels})")
            page.select_option("#model-select", index=fibril)
            page.wait_for_selector("#viewer canvas", timeout=120_000)
            page.wait_for_timeout(4000)
            viewer = page.locator("#viewer")
            viewer.screenshot(path=str(SCREENS / "viewer.png"))
            browser.close()
    finally:
        httpd.shutdown()


def compose() -> None:
    missing = [name for name in PANELS if not (SCREENS / f"{name}.png").exists()]
    if missing:
        raise SystemExit(f"fig3: missing screenshots {missing}; run without --compose")
    images = [mpimg.imread(SCREENS / f"{name}.png") for name in PANELS]
    # Scale each panel to the full text width. Heights follow the screenshot aspect.
    width_in = COL2
    heights = [width_in * im.shape[0] / im.shape[1] for im in images]
    fig_h = sum(heights) + 0.35 * len(images)
    fig = plt.figure(figsize=(width_in, fig_h))
    fig.subplots_adjust(left=0.04, right=0.99, top=0.98, bottom=0.01, hspace=0.08)
    letters = "ABC"
    for i, (im, h) in enumerate(zip(images, heights)):
        ax = fig.add_axes([0.05, 1 - (sum(heights[:i + 1]) + 0.28 * (i + 1)) / fig_h, 0.93, h / fig_h])
        ax.imshow(im)
        ax.set_anchor("N")
        ax.axis("off")
        ax.text(-0.03, 1.02, letters[i], transform=ax.transAxes, fontsize=9, fontweight="bold", va="bottom", ha="right")
    save(fig, "fig3_screens")


def main() -> None:
    if "--compose" not in sys.argv:
        capture()
    compose()


if __name__ == "__main__":
    main()
