# SmartWaste AI: AI-Powered Smart Waste Management and Monitoring System

Users upload or capture a photo of waste. A CNN (TensorFlow/Keras, MobileNetV2 transfer learning) classifies it as
**plastic, paper, metal, glass or organic**, shows the confidence and a disposal tip, and assigns the item to a
**virtual** smart bin compartment. Administrators watch bins, alerts, collections and analytics on a **live
dashboard** that refreshes every 5 seconds.

> **Bin fullness is simulated** from configured compartment capacity and an estimated volume per item
> (`ESTIMATED_VOLUME_LITRES` in `config.py`). No sensors are used. Every dashboard number is calculated from
> stored records; `seed.py` never creates waste records.

| | |
|---|---|
| Model accuracy | **87.2 %** on 984 held-out images (baseline CNN: 74.3 %). See `docs/MODEL_REPORT.md` |
| Tests | 25 unit/integration tests + 28 browser end-to-end checks. See `docs/TESTING.md` |
| Stack | Python 3, Flask, SQLAlchemy, MySQL, TensorFlow/Keras, OpenCV, Chart.js, Waitress, Docker |

## Documentation
- `docs/ARCHITECTURE.md`: components, request flow, data model, security, deployment
- `docs/MODEL_REPORT.md`: dataset, training method, results, confusion matrix, limitations
- `docs/TESTING.md`: generated test report (`python scripts/make_test_report.py`)
- `docs/DEMO_SCRIPT.md`: 10-minute demonstration walkthrough and Q&A cheat sheet
- `docs/SmartWaste_AI_Presentation.pptx`: slide deck (`python scripts/make_presentation.py`)
- `docs/screenshots/`: UI screenshots captured by the end-to-end test

## Modules (from the project brief)
| # | Module | Where |
|---|--------|-------|
| 1 | Authentication: register, login/logout, admin login, hashed passwords, roles | `app/auth.py`, `app/utils.py` |
| 2 | AI classification: upload, webcam, category, confidence %, disposal tips | `app/main.py`, `app/services/classifier.py`, `ml/` |
| 3 | Virtual bins: locations, per-category compartments, automatic assignment | `app/services/bins.py`, `app/admin.py` |
| 4 | Capacity monitoring: max capacity, fill %, status, alert at 90%, reset | `app/services/bins.py` |
| 5 | Admin dashboard (live) | `/admin/` |
| 6 | Analytics and reports: daily/weekly/monthly, location, category, history, CSV | `/admin/analytics`, `/admin/history` |
| 7 | Collection management: pending/completed, mark collected, history | `/admin/collections` |
| 8 | User history | `/history` |

Bin status: highest compartment fill below 70 % is **Normal**, 70 % to under 90 % is **Almost Full**, 90 % or more
is **Collection Required** (thresholds in `config.py`). If a compartment has no room at the chosen location the item
is saved as *unassigned* and the user is warned.

## Quick start (local)
**Windows shortcut:** after the one-time setup below, double-click `start_app.bat`. It starts MySQL if needed, runs the
server and opens http://localhost:8000. Keep its window open while you use the app.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt            # add requirements-dev.txt for training, tests and docs tools
copy .env.example .env                     # then edit SECRET_KEY, MYSQL_* and admin credentials
python setup_mysql.py                      # creates the MySQL database from the MYSQL_* values in .env
python seed.py                             # tables, admin user, 5 locations, 6 virtual bins (idempotent)
python run.py                              # development server  http://127.0.0.1:5000
python serve.py                            # production server (Waitress)  http://localhost:8000
```
Without `MYSQL_*` or `DATABASE_URL` the app falls back to a local SQLite file, which is handy for development.
Admin login is at `/admin/login` using `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env`. **Change the defaults.**

## Docker
```powershell
# .env (or shell) must define SECRET_KEY; DB_PASSWORD, ADMIN_EMAIL and ADMIN_PASSWORD are optional
docker compose up --build
```
Starts MySQL 8.4 and the web app on http://localhost:8000. Tables, the admin user, locations and bins are created on
first start. Uploads, logs and the database persist in Docker volumes. The image uses CPU-only TensorFlow and runs as
an unprivileged user; `/health` is the container health check.

## The AI model
The trained model `ml/model/waste_cnn.keras` is included. To retrain:
1. Put a dataset in `data/raw/` with one folder per class (we used the Hugging Face copy of the Kaggle
   "Garbage Classification" set: `UdaraChamidu/Garbage-Classification-with-12-classes`). TrashNet has no organic class.
2. Run:
```powershell
python ml/prepare_dataset.py --raw data/raw --out data/dataset --size 128   # map classes, resize, split 70/15/15
python ml/train.py --data data/dataset --arch mobilenet                     # or --arch custom for the baseline CNN
python ml/evaluate.py --data data/dataset                                   # test accuracy, report, confusion matrix
```
If the model file is missing, classification returns a clear "model not trained" error (HTTP 503) instead of guessing.

## Testing
```powershell
python -m pytest -q                        # 25 tests (SQLite in memory, classifier stubbed except one smoke test)
python tests/e2e/run_e2e.py --url http://localhost:8010   # 28 browser checks; use a THROWAWAY database (see file header)
python scripts/make_test_report.py         # regenerates docs/TESTING.md
```
GitHub Actions (`.github/workflows/ci.yml`) runs the unit tests and builds the Docker image on every push.

## Demo helper
`python scripts/demo_traffic.py --count 30 --delay 3` sends real dataset images through the running app so the live
dashboard has activity (records are produced by the real model and app logic; the traffic is scripted).
`python scripts/demo_traffic.py --cleanup` removes the demo user and its records.

## API
- `POST /api/classify`: logged-in session, `X-CSRFToken` header, multipart `image` + `location_id`; returns category,
  confidence, recommendation, bin and location as JSON.
- `GET /admin/api/live`: admin only; everything the dashboard shows (polled every 5 s).
- `GET /admin/api/analytics?period=daily|weekly|monthly`: admin only; chart data.
- `GET /api/public-stats`: aggregate counters for the landing page.
- `GET /health`: database check for monitoring.

## Security notes
Password hashing (Werkzeug), CSRF protection on all forms and the AJAX endpoint, role-based route guards, upload type
and size limits with random filenames, uploads served only to the owner or an admin, open-redirect check on `next`,
CSV formula escaping, security headers, HttpOnly/SameSite cookies (set `SESSION_COOKIE_SECURE=1` behind HTTPS).
Keep `.env` out of Git (it is in `.gitignore`) and set a strong `SECRET_KEY`.

## Project layout
```
app/            Flask app: routes, models, services, templates, static assets
ml/             dataset preparation, training, evaluation, trained model
database/       MySQL schema
tests/          pytest suite and Playwright end-to-end test
scripts/        demo traffic, test report and presentation generators
docs/           documentation, screenshots, presentation
```

## Team split (from the requirements)
Member 1 dataset and CNN (`ml/`), Member 2 frontend (`app/templates`, `app/static`), Member 3 Flask backend and AI
integration (`app/main.py`, `app/services/classifier.py`), Member 4 MySQL and bin management (`database/`,
`app/models.py`, `app/services/bins.py`), Member 5 dashboard, analytics, testing (`app/admin.py`, `tests/`).
