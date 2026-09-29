"""Browser part of check_panel (system Python with Playwright; Blender's Python has no browser).

Run:  python world/panel/browser_check.py <base url>
Prints one JSON line: the ids the page rendered, the gate state after a click, the toast of a rejected command.
"""
import json
import sys
import time

from playwright.sync_api import sync_playwright


def main():
    base = sys.argv[1]
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/")
        pg.wait_for_selector("#mnemo .node", timeout=15000)
        pg.wait_for_function("document.getElementById('clock').textContent.includes('доба')", timeout=15000)
        out["nodes"] = pg.eval_on_selector_all("#mnemo .node", "els => els.map(e => e.dataset.id)")
        out["gates"] = pg.eval_on_selector_all("#mnemo .gate", "els => els.map(e => e.dataset.id)")
        pg.click("#g-6\\.9 .hit", force=True)
        t0 = time.time()
        state = ""
        while time.time() - t0 < 20:
            state = pg.get_attribute("#g-6\\.9", "class") or ""
            if " open" in f" {state}" and "opening" not in state:
                break
            time.sleep(0.2)
        out["gate_after_click"] = state
        pg.click("#n-H5 .head", force=True)
        pg.wait_for_selector("#obj button", timeout=5000)
        pg.click("#obj button:has-text('Пуск')")
        pg.wait_for_selector("#toast.show", timeout=5000)
        out["toast"] = pg.text_content("#toast")
        out["page_errors"] = errors
        b.close()
    print(json.dumps(out, ensure_ascii=True))          # ASCII escapes: the parent may read any console code page


if __name__ == "__main__":
    main()
