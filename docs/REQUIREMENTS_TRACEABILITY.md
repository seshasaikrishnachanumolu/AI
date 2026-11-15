# Requirements Traceability

Maps every item in the project brief ("AI-Powered Smart Waste Management and Monitoring System: Complete Project
Requirements") to its implementation and the evidence that it works.

**Evidence key:** `AUDIT` = `tests/requirements_audit.py` (51 HTTP checks against a throwaway MySQL database, all
passing) · `E2E` = `tests/e2e/run_e2e.py` (28 browser checks) · `UNIT` = pytest suite (25 tests) ·
`REVIEW` = inspected directly (code, database or UI), not an automated test.

## 1. Software requirements
| Requirement | Status | Evidence |
|---|---|---|
| Python 3, Flask backend | Done | `app/`, `serve.py` |
| TensorFlow/Keras, CNN | Done | `ml/train.py` (MobileNetV2 transfer learning; baseline CNN from scratch also kept) |
| HTML, CSS, JavaScript | Done | `app/templates`, `app/static` (vanilla JS, no framework) |
| MySQL | Done | App runs on MySQL 9.2; `database/schema.sql`; AUDIT ran on MySQL |
| OpenCV image processing | Done | `app/services/classifier.py`, `ml/prepare_dataset.py` |
| Chart.js dashboard charts | Done | `app/static/vendor/chart.umd.min.js`, `dashboard.js`, `analytics.js` |
| Git and GitHub | **Partly** | Git repository with commits exists; **not yet pushed to GitHub** |
| VS Code | n/a | Editor choice |

## 2. Modules
### Module 1: User authentication
| Requirement | Status | Evidence |
|---|---|---|
| User registration | Done | AUDIT, E2E, UNIT |
| User login and logout | Done | AUDIT, E2E |
| Admin login | Done | Separate `/admin/login`; a user account cannot sign in there (AUDIT) |
| Secure password storage | Done | scrypt salted hash verified in the database (AUDIT) |
| Role-based access | Done | User gets 403 on `/admin/*` and admin APIs (AUDIT, E2E, UNIT) |

### Module 2: AI waste classification
| Requirement | Status | Evidence |
|---|---|---|
| Collect dataset | Done | 6,576 images from the Garbage Classification dataset (`docs/MODEL_REPORT.md`) |
| Train CNN | Done | 87.2 % test accuracy on 984 held-out images (baseline CNN 74.3 %) |
| Upload images | Done | AUDIT, E2E |
| Webcam capture (optional) | Done in code, **not tested with a real camera** | `classify.js` (`getUserMedia`); REVIEW only |
| Classify into plastic, paper, metal, glass, organic | Done | AUDIT, E2E, `ml/model/class_names.json` |
| Display predicted category, confidence %, disposal recommendation | Done | AUDIT, E2E |

### Module 3: Virtual smart bin management
| Requirement | Status | Evidence |
|---|---|---|
| Create multiple virtual bins | Done | 6 seeded; admin can add more in the UI (AUDIT, E2E) |
| Assign bins to locations | Done | Block A, Block B, Hostel, Canteen, Library (AUDIT) |
| Separate compartments per category | Done | Each bin gets 5 compartments (AUDIT) |
| Auto-assign classified waste to the right compartment | Done | AUDIT, E2E, UNIT |
| Maintain individual bin information | Done | Bin detail page with compartments, history, recent items |

### Module 4: Bin capacity monitoring
| Requirement | Status | Evidence |
|---|---|---|
| Set max capacity per compartment | Done | Bin detail page (AUDIT, UNIT) |
| Increase occupied capacity when waste is assigned | Done | AUDIT, UNIT |
| Calculate filling percentage | Done | load ÷ capacity (AUDIT) |
| Display bin status | Done | Normal / Almost Full / Collection Required |
| Alert at 90 % | Done | AUDIT, E2E, UNIT |
| Admin resets capacity after collection | Done | AUDIT, E2E, UNIT |

### Module 5: Admin dashboard
All 12 figures are shown and match database counts: total items, recyclable, non-recyclable (rule configurable in
`config.py`: organic is non-recyclable), plastic/paper/metal/glass/organic counts, total bins, normal, almost-full and
collection-required bins. Status: **Done** (AUDIT checks each label and compares totals with SQL counts).

### Module 6: Analytics and reports
| Requirement | Status | Evidence |
|---|---|---|
| Daily, weekly, monthly statistics | Done | AUDIT, UNIT |
| Location-wise and category-wise analysis | Done | AUDIT, UNIT |
| Classification history | Done | Admin log with filters (AUDIT) |
| Charts | Done | E2E (3 charts render) |
| Export reports (optional) | Done | CSV export (AUDIT, E2E) |

### Module 7: Waste collection management
| Requirement | Status | Evidence |
|---|---|---|
| Identify bins requiring collection; display location | Done | AUDIT |
| Admin marks bins collected; capacity reset | Done | AUDIT, E2E, UNIT |
| Store collection date and time | Done | AUDIT |
| Collection history; pending and completed tracking | Done | AUDIT, E2E |

### Module 8: User waste history
Previously uploaded images, predicted categories, confidence scores and disposal recommendations are listed per user
and are private to that user. Status: **Done** (AUDIT, E2E).

## 3. Database (7 required tables)
`users`, `locations`, `smart_bins`, `bin_compartments`, `waste_records`, `collection_records`, `alerts`: all present
with exactly these names in MySQL (REVIEW of the live schema, and AUDIT).

## 4. AI model requirements (10 steps)
| # | Step | Status |
|---|---|---|
| 1-2 | Find, download and organise dataset | Done (`ml/prepare_dataset.py`) |
| 3 | Preprocess with Python | Done (OpenCV resize, RGB conversion) |
| 4 | Train/validation/test split | Done (70/15/15) |
| 5-6 | Build and train CNN with TensorFlow/Keras | Done |
| 7 | Evaluate accuracy and performance | Done (accuracy, per-class precision/recall/F1, confusion matrix) |
| 8 | Save trained model | Done (`ml/model/waste_cnn.keras`) |
| 9-10 | Connect with Flask; show predictions on the website | Done (AUDIT, E2E) |

## 5. Functional requirements
All 11 are met: register and authenticate, accept uploads, predict, display results, assign to virtual bins, update
capacity automatically, generate alerts, show dashboard statistics, keep classification history, manage collection,
generate reports. See the module tables above.

## 6. Non-functional requirements
| Requirement | Status | Evidence |
|---|---|---|
| Easy-to-use interface | Done (subjective) | REVIEW of UI; no usability study with real users |
| Responsive website | Done | All 15 pages checked at 390 px width: no horizontal overflow; mobile menu works |
| Secure authentication | Done, one caveat | Hashing, CSRF, role guards, safe redirects. **No login rate limiting.** Change the default admin password |
| Accurate classification | Partly | 87.2 % overall. Metal and plastic weakest (F1 about 0.77 and 0.74). Accuracy on photos outside the dataset is unknown |
| Fast image processing | Done | Median 193 to 327 ms per upload including classification and storage (AUDIT, 8 requests, CPU only) |
| Reliable database operations | Done after a fix | See "Defect found and fixed" below |
| Proper error handling | Done | Bad file type, oversize, missing model, unknown location, 403/404/500 pages (AUDIT, UNIT) |
| Easy maintenance and expansion | Done | Layered code, config in `config.py`, docs, CI, Docker |

### Defect found and fixed during this audit
Under concurrent uploads the capacity update could be lost. 32 simultaneous uploads left a compartment at 5.4 L when
the stored records summed to 16.2 L, because each request read the load, added in Python and wrote the total back. It
could also let a compartment overfill. `app/services/bins.py` now uses one conditional database update
(`current_load = current_load + v WHERE current_load + v <= max_capacity`) and row locks around alert creation. After the
fix the same test shows no mismatch. This check is part of `tests/requirements_audit.py`.

## 7. Development checklist (34 items)
| Section | Items | Status |
|---|---|---|
| 1. Planning (scope, categories, bin locations, workflow) | 4 | Done (`docs/ARCHITECTURE.md`, README) |
| 2. AI model (dataset, preprocess, train, test, save) | 5 | Done |
| 3. Frontend (home, login/registration, upload, result, admin dashboard) | 5 | Done |
| 4. Backend (Flask, upload API, integrate model, classification API, bin assignment) | 5 | Done. One endpoint, `/api/classify`, serves both the upload and classification API items |
| 5. Database (create DB, tables, connect, store classification, store capacity and collections) | 5 | Done |
| 6. Smart bins and analytics (bins, capacity, alerts, charts, collection) | 5 | Done |
| 7. Integration and testing (connect all, test classification, capacity, alerts/reset, demo and docs) | 5 | Done; the live demonstration itself is for the team |

## 8. Workflow check
The brief's flow is: user logs in → uploads or captures an image → CNN predicts category and confidence → disposal tip
shown → waste assigned to a virtual bin compartment → capacity rises → alert at 90 % → admin sees it on the dashboard →
admin collects and resets → history and analytics updated. Every step was executed end to end by AUDIT and E2E.

## 9. Final deliverables
| # | Deliverable | Status |
|---|---|---|
| 1 | Working web application | Done |
| 2 | Trained AI model | Done (`ml/model/waste_cnn.keras`) |
| 3 | MySQL database | Done (`database/schema.sql`, live database) |
| 4 | Multiple virtual smart bins | Done |
| 5 | Admin monitoring dashboard | Done |
| 6 | Analytics and reports | Done |
| 7 | Source code on GitHub | **Not complete: committed locally, not pushed** |
| 8 | Project documentation | Done (`README.md`, `docs/`) |
| 9 | Software testing results | Done (`docs/TESTING.md`, this file) |
| 10 | Final presentation and demonstration | Slide deck done (`docs/SmartWaste_AI_Presentation.pptx`); demo script in `docs/DEMO_SCRIPT.md`. Replace "Member 1-5" with real names |

## 10. The brief's two "important" rules
- **Fullness is simulated, not sensor-based.** Stated on the landing page, in the app footer, on the dashboard, in alert
  messages, and in the documentation. Two phrases that could be read as sensor measurement were reworded during this audit.
- **Dashboard statistics come from real records.** `seed.py` creates no waste records, an empty database shows zeros, and
  AUDIT compares every dashboard figure with SQL counts.

## Open items for the team
1. Push the repository to GitHub (deliverable 7).
2. Try the webcam on a machine with a camera.
3. Change the default admin password; consider login rate limiting.
4. Test the classifier on photos from the real campus bins before relying on the accuracy figure.
