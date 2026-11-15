"""Browser end-to-end test (Playwright + Microsoft Edge or Chromium).

Run against a server that uses a THROWAWAY database (it creates users and classifies images):
    $env:DATABASE_URL="sqlite:///C:/temp/e2e.db"; python seed.py
    $env:DATABASE_URL="sqlite:///C:/temp/e2e.db"; $env:PORT="8010"; python serve.py
    python tests/e2e/run_e2e.py --url http://localhost:8010

Writes screenshots to docs/screenshots and a results file docs/e2e-results.json. Exit code 1 on failure.
"""
import argparse
import glob
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
results, problems = [], []


def check(name, ok, detail=""):
    results.append({"test": name, "passed": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))


def hook(page, tag):
    page.on("pageerror", lambda e: problems.append(f"[{tag}] page error: {e}"))
    page.on("console", lambda m: problems.append(f"[{tag}] console error: {m.text}") if m.type == "error" and "status of 4" not in m.text else None)  # 4xx are expected in negative tests
    page.on("requestfailed", lambda r: problems.append(f"[{tag}] request failed: {r.url}"))
    page.on("response", lambda r: problems.append(f"[{tag}] HTTP {r.status} {r.url}") if r.status >= 500 else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--admin-email", default="admin@smartwaste.local")
    ap.add_argument("--admin-password", default="Admin@12345")
    ap.add_argument("--images", default=str(ROOT / "data" / "dataset" / "test"))
    ap.add_argument("--items", type=int, default=12, help="images pushed through while the dashboard is open")
    ap.add_argument("--shots", default=str(ROOT / "docs" / "screenshots"))
    a = ap.parse_args()
    B, shots = a.url.rstrip("/"), Path(a.shots)
    shots.mkdir(parents=True, exist_ok=True)
    files = sorted(glob.glob(a.images + "/*/*.jpg"))
    if not files:
        sys.exit("No test images found. Run ml/prepare_dataset.py first.")
    stamp = str(int(time.time()))
    email = f"e2e.{stamp}@example.com"

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="msedge", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)

        ctx = browser.new_context(viewport={"width": 1366, "height": 850})
        page = ctx.new_page(); hook(page, "user")

        # 1. Landing + health
        page.goto(B + "/"); page.wait_for_timeout(1500)
        check("Landing page renders hero and features", "smarter waste" in page.inner_text("h1").lower() and page.locator(".feat .f").count() == 8)
        page.screenshot(path=str(shots / "landing.png"), full_page=True)
        h = page.request.get(B + "/health").json()
        check("Health endpoint reports database up", h.get("status") == "ok", str(h))

        # 2. Access control
        page.goto(B + "/classify")
        check("Anonymous user is redirected to login", "/login" in page.url)
        page.goto(B + "/admin/")
        check("Anonymous user cannot open admin area", "/login" in page.url or "/admin/login" in page.url)

        # 3. Register / validation / login
        page.goto(B + "/register")
        page.fill("#name", "E2E User"); page.fill("#email", email)
        page.fill("#password", "password123"); page.fill("#confirm", "different123")
        page.click("button[type=submit]")
        check("Registration rejects mismatched passwords", page.locator(".flash.danger").count() == 1)
        page.fill("#password", "password123"); page.fill("#confirm", "password123")
        page.click("button[type=submit]"); page.wait_for_url("**/login")
        check("Registration succeeds", True)
        page.fill("#email", email); page.fill("#password", "wrong-password")
        page.click("button[type=submit]")
        check("Login rejects a wrong password", page.locator(".flash.danger").count() == 1)
        page.fill("#email", email); page.fill("#password", "password123")
        page.click("button[type=submit]"); page.wait_for_url("**/dashboard")
        check("Login succeeds and opens user overview", "Hello" in page.inner_text("h1"))
        page.screenshot(path=str(shots / "user_overview.png"))
        page.goto(B + "/admin/")
        check("Normal user is forbidden from the admin area", page.locator("text=Access denied").count() == 1)

        # 4. Classification via AJAX (real model)
        page.goto(B + "/classify")
        page.screenshot(path=str(shots / "classify.png"))
        page.click("#submit-btn")
        check("Classify form validates a missing location", page.locator("#error").is_visible())
        page.select_option("#location_id", label="Library")
        page.set_input_files("#image", files[0]); page.click("#submit-btn")
        page.wait_for_selector("#result", state="visible", timeout=90000); page.wait_for_timeout(1200)
        cat, conf = page.inner_text("#r-cat").lower(), page.inner_text("#ring-val")
        check("Image classified by the model with confidence and bin assignment",
              cat in {"plastic", "paper", "metal", "glass", "organic"} and conf.endswith("%") and "Library Bin" in page.inner_text("#r-bin"),
              f"{cat} {conf}")
        page.screenshot(path=str(shots / "classify_result.png"), full_page=True)
        page.set_input_files("#image", {"name": "bad.txt", "mimeType": "text/plain", "buffer": b"not an image"})
        page.click("#again"); page.select_option("#location_id", label="Library")
        page.set_input_files("#image", {"name": "bad.txt", "mimeType": "text/plain", "buffer": b"not an image"}); page.click("#submit-btn")
        page.wait_for_selector("#error", state="visible", timeout=15000)
        check("Invalid file type is rejected with a clear message", "Unsupported file type" in page.inner_text("#error"))

        page.goto(B + "/history")
        check("History lists the classified image", page.locator(".thumbs .card").count() >= 1)
        page.screenshot(path=str(shots / "history.png"))

        # 5. Admin console + real-time updates
        actx = browser.new_context(viewport={"width": 1366, "height": 850})
        admin = actx.new_page(); hook(admin, "admin")
        admin.goto(B + "/admin/login")
        admin.fill("#email", a.admin_email); admin.fill("#password", "wrong")
        admin.click("button[type=submit]")
        check("Admin login rejects a wrong password", admin.locator(".flash.danger").count() == 1)
        admin.fill("#email", a.admin_email); admin.fill("#password", a.admin_password)
        admin.click("button[type=submit]"); admin.wait_for_url("**/admin/")
        admin.wait_for_selector("#bins .bin-card", timeout=15000)
        before = int(admin.inner_text('[data-k="total"] .num').replace(",", ""))
        check("Live dashboard connected", "Live" in admin.inner_text("#live-txt"), admin.inner_text("#live-txt"))

        for f in files[1: a.items + 1]:
            page.goto(B + "/classify"); page.select_option("#location_id", label="Library")
            page.set_input_files("#image", f); page.click("#submit-btn")
            page.wait_for_selector("#result", state="visible", timeout=90000)
        admin.wait_for_timeout(7000)  # one poll cycle (5 s)
        after = int(admin.inner_text('[data-k="total"] .num').replace(",", ""))
        check("Dashboard updated in real time without reload", after >= before + a.items, f"{before} -> {after}")
        check("Activity feed shows new items", admin.locator("#feed li .pill").count() >= 1)
        admin.screenshot(path=str(shots / "admin_dashboard.png"), full_page=True)

        # 6. Alert and collection flow: a dedicated tiny bin so the 90% rule is exercised end to end
        admin.goto(B + "/admin/locations")
        admin.fill('input[name="name"]', "E2E Zone"); admin.click("text=Add location")
        admin.goto(B + "/admin/bins")
        admin.fill('input[name="name"]', "E2E Bin"); admin.select_option('select[name="location_id"]', label="E2E Zone")
        admin.fill('input[name="capacity"]', "2"); admin.click("text=Create bin")
        check("Admin can create a location and a bin with custom capacity", admin.locator("td:has-text('E2E Bin')").count() == 1)
        glass = sorted(glob.glob(a.images + "/glass/*.jpg"))
        raised = False
        for f in glass[:15]:
            page.goto(B + "/classify"); page.select_option("#location_id", label="E2E Zone")
            page.set_input_files("#image", f); page.click("#submit-btn")
            page.wait_for_selector("#result", state="visible", timeout=90000)
            live = admin.request.get(B + "/admin/api/live").json()
            if any("E2E Bin" in al["message"] for al in live["alerts"]):
                raised = True
                break
        check("Alert raised when a compartment reaches 90% of capacity", raised, f"after {glass.index(f) + 1} items")
        admin.goto(B + "/admin/collections")
        check("Collection request created automatically", admin.locator("tbody tr:has-text('E2E Bin')").count() >= 1)
        admin.screenshot(path=str(shots / "collections.png"), full_page=True)
        admin.locator("tbody tr:has-text('E2E Bin') button:has-text('Mark collected')").first.click()
        check("Admin can mark the bin collected", admin.locator(".flash.success").count() == 1)
        live = admin.request.get(B + "/admin/api/live").json()
        e2e_bin = [b for b in live["bins"] if b["name"] == "E2E Bin"][0]
        check("Capacity reset to 0% after collection", all(c["fill"] == 0 for c in e2e_bin["compartments"]))
        check("Alert resolved after collection", not any("E2E Bin" in al["message"] for al in live["alerts"]))
        admin.goto(B + "/admin/collections")
        check("Completed collection stored with date and time", admin.locator("tbody tr:has-text('E2E Bin')").count() >= 1)
        admin.goto(B + "/admin/alerts"); admin.screenshot(path=str(shots / "alerts.png"))
        admin.goto(B + "/admin/bins/%d" % e2e_bin["id"]); admin.screenshot(path=str(shots / "bin_detail.png"), full_page=True)
        admin.goto(B + "/admin/bins"); admin.screenshot(path=str(shots / "bins.png"), full_page=True)
        # 7. Analytics + export
        admin.goto(B + "/admin/analytics"); admin.wait_for_timeout(1500)
        for tab in ("weekly", "monthly", "daily"):
            admin.click(f'.tabs button[data-p="{tab}"]'); admin.wait_for_timeout(500)
        check("Analytics charts render", admin.locator("canvas").count() == 3)
        admin.screenshot(path=str(shots / "analytics.png"), full_page=True)
        csv = admin.request.get(B + "/admin/reports/export.csv")
        check("CSV export downloads records", csv.ok and "category" in csv.text() and csv.text().count("\n") > 1)
        admin.goto(B + "/admin/history"); admin.screenshot(path=str(shots / "history_admin.png"))

        # 8. Mobile
        m = browser.new_context(viewport={"width": 390, "height": 800}).new_page(); hook(m, "mobile")
        m.goto(B + "/"); m.wait_for_timeout(800)
        check("Mobile layout has no horizontal overflow", m.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))
        m.screenshot(path=str(shots / "mobile_landing.png"))
        browser.close()

    check("No JavaScript errors, failed requests or 5xx responses", not problems, "; ".join(problems[:5]))
    passed = sum(r["passed"] for r in results)
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "e2e-results.json").write_text(json.dumps({"passed": passed, "total": len(results), "results": results}, indent=2), encoding="utf-8")
    print(f"\n{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
