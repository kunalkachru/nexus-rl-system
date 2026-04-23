#!/usr/bin/env python3
"""Minimal Playwright UI checks for main dashboard and metrics (Colab exports tab)."""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True, help="e.g. http://127.0.0.1:7860")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install: pip install playwright && playwright install chromium", file=sys.stderr)
        return 2

    checks: list[tuple[str, bool, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(30_000)

        # Main dashboard
        page.goto(f"{base}/", wait_until="networkidle")
        checks.append(("main title", "NEXUS" in page.title() or "NEXUS" in (page.locator("h1").first.inner_text() or ""), page.title()))

        page.wait_for_selector("#episodes-count", state="visible")
        ec = page.locator("#episodes-count").inner_text()
        checks.append(("main metrics episodes", ec.strip() != "", f"episodes-count={ec!r}"))

        page.wait_for_selector("#rewardChart", state="attached")
        checks.append(("reward chart canvas", True, "canvas present"))

        # Metrics dashboard + Colab tab
        page.goto(f"{base}/metrics-dashboard", wait_until="networkidle")
        page.wait_for_selector(".tab-btn", state="visible")
        checks.append(("metrics page", "Training" in page.content() or "Metrics" in page.title(), page.title()))

        page.locator("button.tab-btn", has_text="Colab exports").first.click()
        page.wait_for_selector("#colab-run-select", state="visible")
        opts = page.locator("#colab-run-select option").count()
        checks.append(("colab run options", opts >= 1, f"option count={opts}"))

        page.wait_for_selector("#chartColabReward", state="attached")
        checks.append(("colab chart canvas", True, "colab canvas"))

        # Static export should load (200) — visible as chart has dimensions
        page.wait_for_timeout(1500)
        box = page.locator("#chartColabReward").bounding_box()
        checks.append(("colab chart size", box and box.get("width", 0) > 50, str(box)))

        browser.close()

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}: {name} ({detail})")
    if failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
