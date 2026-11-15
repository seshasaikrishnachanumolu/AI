"""Generate docs/TESTING.md from real test output.

Runs the pytest suite, then merges the latest browser E2E results (docs/e2e-results.json, produced by
tests/e2e/run_e2e.py) and the model evaluation (ml/model/evaluation.txt).
    python scripts/make_test_report.py
"""
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PYTEST_DESCRIPTIONS = {
    "test_register_and_login": "Register a user, password stored hashed, then log in",
    "test_register_validation": "Reject invalid email, short password and duplicate email",
    "test_wrong_password_and_role_separation": "Wrong password rejected; admin and user logins are separate",
    "test_role_based_access": "Anonymous redirected; normal user gets 403 on admin pages and APIs",
    "test_open_redirect_blocked": "Malicious `next` redirect target is ignored",
    "test_classification_assigns_bin_and_updates_capacity": "Classified item is stored, assigned to the right compartment, capacity rises",
    "test_organic_is_non_recyclable": "Recyclable rule: organic counts as non-recyclable",
    "test_invalid_uploads": "Bad file type and unknown location are rejected; nothing stored",
    "test_model_missing_gives_503": "Missing model returns a clear 503, nothing stored",
    "test_api_classify_json": "`/api/classify` returns category, confidence, bin and location as JSON",
    "test_user_cannot_see_others_image": "Users cannot open another user's image or result",
    "test_alert_at_90_percent_then_collect_resets": "Alert + collection at 90%; full compartment leaves item unassigned; collect resets capacity",
    "test_dashboard_counts_come_from_records": "Dashboard totals match the stored records",
    "test_empty_dashboard_is_zero": "Empty database shows zeros (no fabricated data)",
    "test_analytics_api_and_csv": "Daily/weekly/monthly analytics, location/category breakdown, CSV export",
    "test_admin_can_create_bin_and_set_capacity": "Admin creates a bin; invalid capacity rejected, valid accepted",
    "test_landing_page_and_health": "Landing page, `/health`, and public stats endpoint",
    "test_all_pages_render_for_each_role": "Every page renders for anonymous, user and admin",
    "test_live_endpoint_reflects_new_items_and_is_admin_only": "Live endpoint is admin-only and reflects new items, fill level and alerts",
    "test_preprocess_shape_dtype_and_range": "Preprocessing returns a 128x128x3 float32 batch in the 0-255 range",
    "test_preprocess_converts_bgr_to_rgb": "OpenCV BGR is converted to RGB",
    "test_unreadable_file_raises": "Corrupt image raises a clear error",
    "test_missing_model_raises": "Missing model raises ModelNotAvailable",
    "test_every_category_has_a_recommendation": "Each category has a disposal recommendation",
    "test_real_model_sanity_on_held_out_images": "Real model: >= 60% correct on 30 held-out images (smoke test)",
}


def main():
    proc = subprocess.run([sys.executable, "-m", "pytest", "-v", "-p", "no:warnings"], cwd=ROOT, capture_output=True, text=True)
    out = proc.stdout
    rows = re.findall(r"tests/(\w+)\.py::(\w+) (PASSED|FAILED|ERROR|SKIPPED)", out)
    summary = re.findall(r"=+ (.*?) =+\s*$", out, re.M)[-1]
    lines = [
        "# Software Testing Results", "",
        f"Generated {datetime.now():%Y-%m-%d %H:%M} by `scripts/make_test_report.py` from real test runs.", "",
        "## 1. Automated unit and integration tests (pytest)", "",
        f"**Result: {summary}**", "",
        "The suite runs against an in-memory SQLite database. TensorFlow is stubbed except in the one real-model smoke test.", "",
        "| # | File | Test | What it verifies | Result |", "|--:|------|------|------------------|:------:|",
    ]
    for i, (f, name, res) in enumerate(rows, 1):
        lines.append(f"| {i} | {f}.py | `{name}` | {PYTEST_DESCRIPTIONS.get(name, '')} | {res} |")

    e2e = ROOT / "docs" / "e2e-results.json"
    lines += ["", "## 2. Browser end-to-end tests (Playwright + Microsoft Edge)", ""]
    if e2e.exists():
        d = json.loads(e2e.read_text(encoding="utf-8"))
        lines += [f"**Result: {d['passed']}/{d['total']} checks passed.** Run with the real trained model against a throwaway "
                  "database through the real UI (`tests/e2e/run_e2e.py`).", "", "| # | Check | Result | Detail |", "|--:|-------|:------:|--------|"]
        for i, r in enumerate(d["results"], 1):
            lines.append(f"| {i} | {r['test']} | {'PASS' if r['passed'] else 'FAIL'} | {r['detail'].replace('|', '/')} |")
    else:
        lines.append("_Not run yet. See `tests/e2e/run_e2e.py`._")

    ev = ROOT / "ml" / "model" / "evaluation.txt"
    lines += ["", "## 3. AI model evaluation (held-out test set)", ""]
    if ev.exists():
        lines += ["```", ev.read_text(encoding="utf-8").strip(), "```", "", "See `docs/MODEL_REPORT.md` for dataset, method and comparison with the baseline CNN."]

    lines += ["", "## 4. Not covered by automated tests", "",
              "- Webcam capture needs a physical camera and permission prompt, so it was not automated (the code path that feeds the captured frame into the same upload form is exercised by file upload).",
              "- Load and concurrency testing was not performed.",
              "- The MySQL schema was checked by running the application against MySQL 9.2 (create tables, register, classify, alert, collect, cleanup via `scripts/demo_traffic.py`). The automated suite itself uses SQLite.",
              "- Docker: the image builds, starts, passes its health check, runs as a non-root user and classifies real images with the bundled model (verified manually, SQLite fallback inside the container). The `docker-compose.yml` file validates (`docker compose config`), but the full stack with the `mysql:8.4` service was not started because the image was not available locally.",
              "- GitHub Actions (`.github/workflows/ci.yml`) has not run yet because the repository has not been pushed to GitHub.",
              "- Accuracy on photos from outside the training dataset (cluttered scenes, other bins) is unknown; see the data limitations in `docs/MODEL_REPORT.md`."]
    (ROOT / "docs" / "TESTING.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote docs/TESTING.md: {summary}")
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
