# Architecture

## Overview
SmartWaste AI is a Flask web application with a TensorFlow/Keras CNN for image classification and a MySQL
database. A user uploads or captures a waste photo; the CNN predicts the material; the item is routed to the
matching compartment of a virtual smart bin; administrators monitor fill levels, alerts and collections on a
live dashboard. Bin fullness is **simulated** from configured capacity and estimated per-item volume, not
measured by sensors. All dashboard figures come from stored records.

## Request flow (classification)
```
Browser (classify.js)
  │  POST /api/classify  (multipart: image + location_id, X-CSRFToken header)
  ▼
main.process_upload()
  ├─ validate type/size, save with a random filename       (app/main.py)
  ├─ classifier.classify(path)                               (app/services/classifier.py)
  │     ├─ preprocess_image() — OpenCV read, BGR→RGB, resize to 128×128
  │     └─ model.predict() — cached Keras model             (ml/model/waste_cnn.keras)
  ├─ bins.find_compartment() — pick emptiest with room       (app/services/bins.py)
  ├─ bins.add_waste() — raise load; alert + collection at 90%
  └─ persist WasteRecord                                     (app/models.py → MySQL)
  ▼
JSON result → classify.js renders the confidence ring, tip and bin assignment (no page reload)
```

## Real-time dashboard
The admin dashboard (`dashboard.js`) polls `GET /admin/api/live` every 5 seconds and updates stat cards, the
category chart, bin fill bars, the activity feed and alert toasts in place. It pauses while the tab is hidden
and shows a "Reconnecting…" state if a request fails. Polling was chosen over WebSockets because it is simple,
survives the stateless Waitress/WSGI model, and a few-second latency is fine for this use case.

## Layers
| Layer | Files | Responsibility |
|-------|-------|----------------|
| Routes / views | `app/auth.py`, `app/main.py`, `app/admin.py` | HTTP, validation, auth, JSON + HTML |
| Services | `app/services/classifier.py`, `app/services/bins.py` | Model inference; bin assignment, capacity, alerts |
| Models | `app/models.py` | SQLAlchemy ORM for the 7 tables |
| Templates | `app/templates/` | Jinja2: public shell + app shell, admin pages |
| Static | `app/static/` | CSS design system, vanilla JS, bundled Chart.js |
| ML | `ml/prepare_dataset.py`, `ml/train.py`, `ml/evaluate.py` | Dataset prep, training, evaluation |

## Data model
`users (1─*) waste_records`, `locations (1─*) smart_bins (1─*) bin_compartments`,
`waste_records (*─1) smart_bins / bin_compartments`, `smart_bins (1─*) collection_records / alerts`.
See `database/schema.sql` for the MySQL DDL; `app/models.py` is the source of truth and can create the tables
directly via `python seed.py`.

## Key decisions
- **Normalisation inside the model.** Training and inference both feed raw 0–255 RGB pixels; the model's first
  layer rescales. This removes a class of train/serve skew bugs.
- **Lazy TensorFlow import + model cache.** The web app and unit tests run without TensorFlow loaded; the model
  is loaded once and reloaded only if the file changes on disk (`classifier._load`).
- **SQLite fallback.** With no `MYSQL_*`/`DATABASE_URL` set, the app uses a local SQLite file so it runs with
  zero database setup; production uses MySQL via `MYSQL_*` in `.env`.
- **No fabricated data.** `seed.py` creates only users, locations and bins — never waste records — so every
  statistic is earned by real classification.

## Security
Werkzeug password hashing, Flask-WTF CSRF on every form and the AJAX endpoint, role-based route guards
(`admin_required`), upload type/size validation with random filenames, per-owner access to uploaded images,
same-site open-redirect check, CSV formula-injection escaping, security headers and `no-store` on sensitive
routes, HttpOnly/SameSite cookies (Secure when `SESSION_COOKIE_SECURE=1`).

## Deployment
Waitress WSGI server (`serve.py`), a `/health` check, rotating logs in `logs/app.log`, a multi-stage-free
`Dockerfile` (CPU-only TensorFlow) and `docker-compose.yml` that runs the app with a MySQL 8.4 container.
CI (`.github/workflows/ci.yml`) runs the unit tests (TensorFlow excluded, classifier stubbed) and builds the
Docker image.
