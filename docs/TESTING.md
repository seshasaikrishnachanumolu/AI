# Software Testing Results

Generated 2026-11-15 14:47 by `scripts/make_test_report.py` from real test runs.

## 1. Automated unit and integration tests (pytest)

**Result: 25 passed in 29.91s**

The suite runs against an in-memory SQLite database. TensorFlow is stubbed except in the one real-model smoke test.

| # | File | Test | What it verifies | Result |
|--:|------|------|------------------|:------:|
| 1 | test_app.py | `test_register_and_login` | Register a user, password stored hashed, then log in | PASSED |
| 2 | test_app.py | `test_register_validation` | Reject invalid email, short password and duplicate email | PASSED |
| 3 | test_app.py | `test_wrong_password_and_role_separation` | Wrong password rejected; admin and user logins are separate | PASSED |
| 4 | test_app.py | `test_role_based_access` | Anonymous redirected; normal user gets 403 on admin pages and APIs | PASSED |
| 5 | test_app.py | `test_open_redirect_blocked` | Malicious `next` redirect target is ignored | PASSED |
| 6 | test_app.py | `test_classification_assigns_bin_and_updates_capacity` | Classified item is stored, assigned to the right compartment, capacity rises | PASSED |
| 7 | test_app.py | `test_organic_is_non_recyclable` | Recyclable rule: organic counts as non-recyclable | PASSED |
| 8 | test_app.py | `test_invalid_uploads` | Bad file type and unknown location are rejected; nothing stored | PASSED |
| 9 | test_app.py | `test_model_missing_gives_503` | Missing model returns a clear 503, nothing stored | PASSED |
| 10 | test_app.py | `test_api_classify_json` | `/api/classify` returns category, confidence, bin and location as JSON | PASSED |
| 11 | test_app.py | `test_user_cannot_see_others_image` | Users cannot open another user's image or result | PASSED |
| 12 | test_app.py | `test_alert_at_90_percent_then_collect_resets` | Alert + collection at 90%; full compartment leaves item unassigned; collect resets capacity | PASSED |
| 13 | test_app.py | `test_dashboard_counts_come_from_records` | Dashboard totals match the stored records | PASSED |
| 14 | test_app.py | `test_empty_dashboard_is_zero` | Empty database shows zeros (no fabricated data) | PASSED |
| 15 | test_app.py | `test_analytics_api_and_csv` | Daily/weekly/monthly analytics, location/category breakdown, CSV export | PASSED |
| 16 | test_app.py | `test_admin_can_create_bin_and_set_capacity` | Admin creates a bin; invalid capacity rejected, valid accepted | PASSED |
| 17 | test_app.py | `test_landing_page_and_health` | Landing page, `/health`, and public stats endpoint | PASSED |
| 18 | test_app.py | `test_all_pages_render_for_each_role` | Every page renders for anonymous, user and admin | PASSED |
| 19 | test_app.py | `test_live_endpoint_reflects_new_items_and_is_admin_only` | Live endpoint is admin-only and reflects new items, fill level and alerts | PASSED |
| 20 | test_classifier.py | `test_preprocess_shape_dtype_and_range` | Preprocessing returns a 128x128x3 float32 batch in the 0-255 range | PASSED |
| 21 | test_classifier.py | `test_preprocess_converts_bgr_to_rgb` | OpenCV BGR is converted to RGB | PASSED |
| 22 | test_classifier.py | `test_unreadable_file_raises` | Corrupt image raises a clear error | PASSED |
| 23 | test_classifier.py | `test_missing_model_raises` | Missing model raises ModelNotAvailable | PASSED |
| 24 | test_classifier.py | `test_every_category_has_a_recommendation` | Each category has a disposal recommendation | PASSED |
| 25 | test_classifier.py | `test_real_model_sanity_on_held_out_images` | Real model: >= 60% correct on 30 held-out images (smoke test) | PASSED |

## 2. Browser end-to-end tests (Playwright + Microsoft Edge)

**Result: 28/28 checks passed.** Run with the real trained model against a throwaway database through the real UI (`tests/e2e/run_e2e.py`).

| # | Check | Result | Detail |
|--:|-------|:------:|--------|
| 1 | Landing page renders hero and features | PASS |  |
| 2 | Health endpoint reports database up | PASS | {'database': 'up', 'status': 'ok'} |
| 3 | Anonymous user is redirected to login | PASS |  |
| 4 | Anonymous user cannot open admin area | PASS |  |
| 5 | Registration rejects mismatched passwords | PASS |  |
| 6 | Registration succeeds | PASS |  |
| 7 | Login rejects a wrong password | PASS |  |
| 8 | Login succeeds and opens user overview | PASS |  |
| 9 | Normal user is forbidden from the admin area | PASS |  |
| 10 | Classify form validates a missing location | PASS |  |
| 11 | Image classified by the model with confidence and bin assignment | PASS | glass 56% |
| 12 | Invalid file type is rejected with a clear message | PASS |  |
| 13 | History lists the classified image | PASS |  |
| 14 | Admin login rejects a wrong password | PASS |  |
| 15 | Live dashboard connected | PASS | Live · updated 2:31:31 pm |
| 16 | Dashboard updated in real time without reload | PASS | 1 -> 13 |
| 17 | Activity feed shows new items | PASS |  |
| 18 | Admin can create a location and a bin with custom capacity | PASS |  |
| 19 | Alert raised when a compartment reaches 90% of capacity | PASS | after 5 items |
| 20 | Collection request created automatically | PASS |  |
| 21 | Admin can mark the bin collected | PASS |  |
| 22 | Capacity reset to 0% after collection | PASS |  |
| 23 | Alert resolved after collection | PASS |  |
| 24 | Completed collection stored with date and time | PASS |  |
| 25 | Analytics charts render | PASS |  |
| 26 | CSV export downloads records | PASS |  |
| 27 | Mobile layout has no horizontal overflow | PASS |  |
| 28 | No JavaScript errors, failed requests or 5xx responses | PASS |  |

## 3. AI model evaluation (held-out test set)

```
Test accuracy: 0.8720 (984 images)

              precision    recall  f1-score   support

       glass      0.926     0.825     0.872       302
       metal      0.714     0.826     0.766       115
     organic      0.893     0.966     0.928       147
       paper      0.955     0.938     0.946       291
     plastic      0.723     0.767     0.744       129

    accuracy                          0.872       984
   macro avg      0.842     0.864     0.851       984
weighted avg      0.878     0.872     0.873       984

Confusion matrix:
[[249  20  11   4  18]
 [  3  95   1   1  15]
 [  1   0 142   2   2]
 [  2  10   3 273   3]
 [ 14   8   2   6  99]]
```

See `docs/MODEL_REPORT.md` for dataset, method and comparison with the baseline CNN.

## 4. Not covered by automated tests

- Webcam capture needs a physical camera and permission prompt, so it was not automated (the code path that feeds the captured frame into the same upload form is exercised by file upload).
- Load and concurrency testing was not performed.
- The MySQL schema was checked by running the application against MySQL 9.2 (create tables, register, classify, alert, collect). The automated suite itself uses SQLite.
- Accuracy on photos from outside the training dataset (cluttered scenes, other bins) is unknown; see the data limitations in `docs/MODEL_REPORT.md`.
