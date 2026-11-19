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

## Quick start for new users (Windows, about 15 minutes, no database to install)

> Detailed illustrated guide with troubleshooting: **[docs/SmartWaste_AI_Setup_and_User_Guide.pdf](docs/SmartWaste_AI_Setup_and_User_Guide.pdf)**

**You need:** Windows 10/11, an internet connection, about 3 GB of free disk space, and **Python 3.12** (3.10 to 3.13, 64-bit) from
<https://www.python.org/downloads/windows/>. In the Python installer tick **"Add python.exe to PATH"**.
You do **not** need MySQL, the image dataset, or any AI training: the trained model is already in the repository.

1. **Download the project.** Click the green **Code** button on GitHub, then **Download ZIP**, and unzip it (for example to `C:\SmartWaste`).
   With Git instead: `git clone https://github.com/seshasaikrishnachanumolu/AI.git`
2. **Set it up (once).** Open the folder and double-click **`setup_windows.bat`**. Wait 5 to 15 minutes while packages download.
   At the end it prints your **admin email and admin password**: copy them (they are also saved in the file `.env`).
3. **Start it.** Double-click **`start_app.bat`**. Your browser opens at **http://localhost:8000**. Keep the black window open while you use the app;
   close it to stop.

Then:
- **Normal user:** click **Get started**, register, then **Classify waste** and upload any photo of plastic, paper, metal, glass or food waste.
- **Administrator:** open <http://localhost:8000/admin/login> and use the email and password printed in step 2.
  Change that password later with `.venv\Scripts\python scripts\manage_admin.py <admin-email>`.

Something went wrong? See [Troubleshooting](#troubleshooting) below.

### macOS / Linux (not tested by the authors; commands are standard)
```bash
python3 -m venv .venv && source .venv/bin/activate     # Python 3.10 to 3.13
pip install -r requirements.txt
python scripts/first_run.py                            # creates .env, the database, admin account, locations and bins
python serve.py                                        # open http://localhost:8000
```

## Manual setup (with MySQL)
The quick start above uses a built-in SQLite file. To use **MySQL** (what the project brief asks for) instead:
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt            # add requirements-dev.txt for training, tests and docs tools
copy .env.example .env                     # then edit .env: set SECRET_KEY, uncomment the MYSQL_ lines and type your MySQL password
python setup_mysql.py                      # creates the MySQL database from the MYSQL_* values in .env
python seed.py                             # tables, admin user, 5 locations, 6 virtual bins (safe to repeat)
python serve.py                            # http://localhost:8000   (python run.py = development server on port 5000)
```
Without `MYSQL_*` or `DATABASE_URL` in `.env` the app uses SQLite. Admin login is `/admin/login` with `ADMIN_EMAIL` / `ADMIN_PASSWORD`
from `.env` (the example file uses `Admin@12345`: **change it**). The server listens on this computer only; to reach it from a phone on the
same Wi-Fi run `$env:HOST="0.0.0.0"; python serve.py` (trusted networks only).

## Troubleshooting
| Problem | Fix |
|---|---|
| `setup_windows.bat` says **No suitable Python found** | Install Python 3.12 (64-bit) from python.org and tick **Add python.exe to PATH**. Python 3.14 is too new for TensorFlow. Close the window and run it again. |
| Setup stops during **package installation** | Usually the internet dropped. Run `setup_windows.bat` again: it continues. The download is large (about 500 MB). |
| `start_app.bat` says **not set up yet** | Run `setup_windows.bat` first. |
| Browser shows **"can't connect"** | The black server window was closed. Start `start_app.bat` again and wait about 15 seconds. |
| **Port 8000 is already in use** | Close the other program, or start with another port: `set PORT=8001` then `start_app.bat`, and open `http://localhost:8001`. |
| **Admin login fails** | Use the page `/admin/login` (not the user login). The password is the one printed at the end of setup, also stored in `.env` as `ADMIN_PASSWORD`. Reset it with `.venv\Scripts\python scripts\manage_admin.py <admin-email>`. |
| "The AI model has not been trained yet" | The files `ml/model/waste_cnn.keras` and `class_names.json` are missing. Download the project again completely. |
| First classification takes 10 to 30 seconds | Normal: the AI model loads on first use. Later ones take under a second. |
| Webcam button does nothing | Allow the camera when the browser asks, or upload a photo instead. The webcam only works on `localhost`. |
| MySQL errors (`Access denied`, `Can't connect`) | Only for the MySQL setup: check `MYSQL_USER` / `MYSQL_PASSWORD` in `.env`, and that the MySQL service is running. Or put `#` in front of the `MYSQL_` lines to use SQLite. |

## Documentation
- **`docs/SmartWaste_AI_Setup_and_User_Guide.pdf`: start here.** Installation, first-time user guide, administrator guide, roles and permissions, troubleshooting (source: `docs/guide/guide.html`, rebuild with `python scripts/make_guide_pdf.py`)
- `docs/REQUIREMENTS_TRACEABILITY.md`: every item of the project brief mapped to its implementation and test evidence
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
python tests/requirements_audit.py          # 51 requirement checks over HTTP incl. a concurrency test; needs a THROWAWAY MySQL DB (see file header)
python -m pytest -q                        # 25 tests (SQLite in memory, classifier stubbed except one smoke test)
python tests/e2e/run_e2e.py --url http://localhost:8010   # 28 browser checks; use a THROWAWAY database (see file header)
python scripts/make_test_report.py         # regenerates docs/TESTING.md
```
GitHub Actions (`.github/workflows/ci.yml`) runs the unit tests and builds the Docker image on every push.

## Accounts and passwords
Anyone can register on the website (always a normal **User**). **Admins cannot be created on the website.** Use `python scripts/manage_admin.py` to change the admin password, add another administrator, or reset a user's forgotten password (see the guide, Part 4.11).

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

## Team
| Name | Roll number |
|---|---|
| Madhuri | 2300032809 |
| Keerthi | 2300033635 |
| Sana | 2300033102 |
| Sandhyana | 2300033182 |

## Suggested work areas (from the requirements)
Member 1 dataset and CNN (`ml/`), Member 2 frontend (`app/templates`, `app/static`), Member 3 Flask backend and AI
integration (`app/main.py`, `app/services/classifier.py`), Member 4 MySQL and bin management (`database/`,
`app/models.py`, `app/services/bins.py`), Member 5 dashboard, analytics, testing (`app/admin.py`, `tests/`).
