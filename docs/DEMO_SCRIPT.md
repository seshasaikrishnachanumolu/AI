# Demo Script (8–10 minutes)

**Goal:** show the full loop from a photo to a collected bin, and the live dashboard reacting in real time.

## Before the demo (5 minutes)
1. Start MySQL (service `MySQL92`). In `.env` set `MYSQL_USER`, `MYSQL_PASSWORD`, `SECRET_KEY`.
2. `python setup_mysql.py` then `python seed.py` (first time only).
3. Start the server: `python serve.py` (http://localhost:8000).
4. Open two browser windows side by side:
   - **Window A (admin):** http://localhost:8000/admin/login → `admin@smartwaste.local` / your admin password → *Live dashboard*.
   - **Window B (user):** http://localhost:8000 (private window) → register a user.
5. Have 6–8 test images ready (`data/dataset/test/<category>/`) or real photos of bottles, paper, cans, food.
6. Optional: for a fully automatic run, `python scripts/demo_traffic.py --count 30 --delay 3` generates traffic with real
   dataset images. Afterwards `python scripts/demo_traffic.py --cleanup` removes it.

## Walkthrough
| Min | Say | Do |
|----:|-----|----|
| 0:00 | *Problem:* campus bins get mixed waste and are emptied on a fixed schedule, not when full. | Show the **landing page**; point at the counters (real records) and the "simulated, no sensors" note. |
| 1:00 | *AI:* a CNN classifies waste photos into five categories. | Window B: **Classify waste**, choose *Library*, drop a plastic bottle image, **Classify**. Point at category, confidence ring, disposal tip, assigned bin. |
| 2:30 | *Routing:* each location has bins with one compartment per category. | Classify a paper image and a metal can. Show "Assigned to: Library Bin 1, paper compartment". |
| 3:30 | *Real time:* the admin sees every item as it happens. | Window A: watch the **Live activity** feed and the fill bars rise without refreshing (5 s poll). |
| 4:30 | *Alerts:* at 90% of a compartment's capacity an alert and a collection request are created. | Admin → **Smart bins** → open a bin → lower a compartment's capacity to a small value (e.g. 2 L); classify 3–4 items of that type. Show the toast, **Alerts**, **Collections**. |
| 6:00 | *Collection:* admin marks the bin collected; capacity resets; history is stored. | **Collections** → *Mark collected*. Show the bin back at 0% and the completed row with date/time. |
| 7:00 | *Analytics:* daily/weekly/monthly, by category and location. | **Analytics** tabs, then **Export CSV**. |
| 8:00 | *Quality:* model accuracy and testing. | Open `docs/MODEL_REPORT.md` (87.2% test accuracy, baseline 74.3%) and `docs/TESTING.md` (25 unit tests, 28 browser checks). |
| 9:00 | *Honesty slide:* fullness is simulated; weak spots are metal/plastic. | Mention limits and next steps (campus photos, "unknown" class). |

## If something goes wrong
- *"The AI model has not been trained yet"* → `ml/model/waste_cnn.keras` is missing; re-run `ml/train.py` or restore from Git.
- Dashboard shows *Reconnecting…* → the server stopped or the admin session expired; reload and log in.
- Wrong prediction on stage → say so. It is a known weakness (metal/plastic confusion, ~87% overall); show the confusion matrix.
- Webcam blocked → use file upload; browsers require HTTPS or `localhost` for camera access.

## Q&A cheat sheet
- **Why simulated fullness?** The brief says no hardware. Each classified item adds an estimated volume (config in `config.py`) to a compartment with a configured capacity.
- **Why polling, not WebSockets?** Simple, robust under Waitress, and 5 s latency is enough here.
- **Why MobileNetV2?** Transfer learning gave 87.2% vs 74.3% for a CNN trained from scratch on the same ~4.6k training images.
- **Is the dashboard data real?** Yes, all numbers are SQL aggregates over stored records; `seed.py` never creates waste records.
