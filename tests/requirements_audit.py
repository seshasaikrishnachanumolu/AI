"""Requirement-by-requirement audit against the project brief (PDF), driven over HTTP.

It creates users, bins and waste records, so run it against a THROWAWAY MySQL database and a server on port 8011:

    $env:MYSQL_DATABASE="smart_waste_audit"; python setup_mysql.py; python seed.py
    $env:MYSQL_DATABASE="smart_waste_audit"; $env:PORT="8011"; python serve.py        # second terminal
    $env:MYSQL_DATABASE="smart_waste_audit"; python tests/requirements_audit.py

Needs the prepared dataset in data/dataset/test (for sample images). Drop the database afterwards.
Includes a concurrency check: 32 simultaneous uploads must leave each compartment's load equal to the sum of its records.
"""
import concurrent.futures as cf
import glob
import re
import statistics
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
B = "http://localhost:8011"
ROOT = Path(__file__).resolve().parent.parent
IMGS = {c: sorted(glob.glob(str(ROOT / "data/dataset/test" / c / "*.jpg"))) for c in ["plastic", "paper", "metal", "glass", "organic"]}
res = []
RUN = str(int(time.time()))
AUDIT_EMAIL, OTHER_EMAIL = f"audit.{RUN}@example.com", f"other.{RUN}@example.com"  # unique per run: re-runnable on one database


def check(req, ok, detail=""):
    res.append((req, bool(ok), detail))
    print(("PASS  " if ok else "FAIL  ") + req + (f"   [{detail}]" if detail else ""))


def tok(html):
    m = re.search(r'name="csrf-token" content="([^"]+)"', html)
    return m.group(1)


def login(email, pw, admin=False):
    s = requests.Session()
    t = tok(s.get(B + ("/admin/login" if admin else "/login")).text)
    r = s.post(B + ("/admin/login" if admin else "/login"), data={"csrf_token": t, "email": email, "password": pw}, allow_redirects=False)
    return s, r.status_code


def classify(s, img, loc):
    t = tok(s.get(B + "/classify").text)
    with open(img, "rb") as f:
        return s.post(B + "/api/classify", headers={"X-CSRFToken": t}, data={"location_id": loc}, files={"image": ("a.jpg", f, "image/jpeg")}, timeout=120)


# ---------------- Module 1: authentication
print("== Module 1: User authentication")
u = requests.Session()
t = tok(u.get(B + "/register").text)
r = u.post(B + "/register", data={"csrf_token": t, "name": "Audit User", "email": AUDIT_EMAIL, "password": "AuditPass#1", "confirm": "AuditPass#1"}, allow_redirects=False)
check("User registration", r.status_code == 302)
user, code = login(AUDIT_EMAIL, "AuditPass#1")
check("User login", code == 302)
check("Admin login (separate, admin role only)", login("admin@smartwaste.local", "Admin@12345", admin=True)[1] == 302 and login(AUDIT_EMAIL, "AuditPass#1", admin=True)[1] == 401)
admin, _ = login("admin@smartwaste.local", "Admin@12345", admin=True)
t = tok(user.get(B + "/dashboard").text)
check("User logout", user.post(B + "/logout", data={"csrf_token": t}, allow_redirects=False).status_code == 302 and user.get(B + "/classify", allow_redirects=False).status_code == 302)
user, _ = login(AUDIT_EMAIL, "AuditPass#1")

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import *  # noqa: E402,F401,F403

app = create_app()
with app.app_context():
    h = User.query.filter_by(email=AUDIT_EMAIL).one().password_hash
    check("Secure password storage (salted hash, not plaintext)", "AuditPass#1" not in h and h.startswith(("scrypt:", "pbkdf2:")), h[:18] + "...")
check("Role-based access (user blocked from admin pages/APIs)", user.get(B + "/admin/", allow_redirects=False).status_code == 403 and user.get(B + "/admin/api/live").status_code == 403)

# ---------------- Module 3: bins
print("== Module 3: Virtual smart bin management")
live = admin.get(B + "/admin/api/live").json()
locs = {b["location"] for b in live["bins"]}
check("Multiple virtual bins", len(live["bins"]) >= 2, f"{len(live['bins'])} bins")
check("Bins assigned to different locations (example locations present)", {"College Block A", "College Block B", "Hostel", "Canteen", "Library"} <= locs, ", ".join(sorted(locs)))
check("Separate compartment per waste category in every bin", all({c["category"] for c in b["compartments"]} == {"plastic", "paper", "metal", "glass", "organic"} for b in live["bins"]))
t = tok(admin.get(B + "/admin/bins").text)
loc_id = int(re.search(r'<option value="(\d+)">Hostel</option>', admin.get(B + "/admin/bins").text).group(1))
admin.post(B + "/admin/bins", data={"csrf_token": t, "name": "Audit New Bin", "location_id": loc_id, "capacity": "7"})
check("Admin can create a bin at a location with chosen capacity", any(b["name"] == "Audit New Bin" for b in admin.get(B + "/admin/api/live").json()["bins"]))

# ---------------- Module 2: classification
print("== Module 2: AI waste classification")
page = user.get(B + "/classify").text
opts = dict((n, int(v)) for v, n in re.findall(r'<option value="(\d+)">([^<]+)</option>', page))
lib = opts["Library"]
t0 = time.time()
r = classify(user, IMGS["glass"][0], lib)
j = r.json()
check("Upload image -> predicted category (one of 5)", r.status_code == 201 and j["category"] in IMGS, j.get("category"))
check("Confidence percentage displayed (0-100)", 0 <= j["confidence"] <= 100, f"{j['confidence']}%")
check("Disposal recommendation provided", len(j["recommendation"]) > 20)
check("Webcam capture (optional): UI control + capture code present", "cam-start" in page and "getUserMedia" in requests.get(B + "/static/js/classify.js").text, "needs a real camera to run; not automatable here")

# ---------------- Module 4: capacity / alerts / reset
print("== Module 4: Bin capacity monitoring")
admin_live = admin.get(B + "/admin/api/live").json()
lib_bin = [b for b in admin_live["bins"] if b["location"] == "Library"][0]
comp = [c for c in lib_bin["compartments"] if c["category"] == j["category"]][0]
check("Classified waste auto-assigned to matching compartment & occupied capacity increased", j["assigned"] and comp["load"] > 0, f"{j['category']} load={comp['load']} L")
check("Filling percentage = load / max capacity", abs(comp["fill"] - round(comp["load"] / comp["max"] * 100, 1)) < 0.11, f"{comp['fill']}%")
check("Bin status displayed (Normal/Almost Full/Collection Required)", lib_bin["status"] in ("Normal", "Almost Full", "Collection Required"), lib_bin["status"])

# configure a small capacity on Block A bin and fill it to cross 90%
blockA = int(opts["College Block A"])
bin_id = [b for b in admin_live["bins"] if b["location"] == "College Block A"][0]["id"]
page = admin.get(B + f"/admin/bins/{bin_id}").text
data = {"csrf_token": tok(page)}
for cid in re.findall(r'name="capacity_(\d+)"', page):
    data[f"capacity_{cid}"] = "2"
admin.post(B + f"/admin/bins/{bin_id}/capacity", data=data)
b0 = [b for b in admin.get(B + "/admin/api/live").json()["bins"] if b["id"] == bin_id][0]
check("Admin can set maximum capacity per compartment", all(c["max"] == 2.0 for c in b0["compartments"]))
statuses = []
for i in range(6):
    jj = classify(user, IMGS["glass"][i + 1], blockA).json()
    if jj["category"] != "glass":
        continue
    bb = [b for b in admin.get(B + "/admin/api/live").json()["bins"] if b["id"] == bin_id][0]
    statuses.append(bb["status"])
    if bb["status"] == "Collection Required":
        break
check("Status moves Normal -> Almost Full -> Collection Required", "Collection Required" in statuses, " > ".join(dict.fromkeys(statuses)))
lv = admin.get(B + "/admin/api/live").json()
check("Alert generated when capacity reaches 90%", any("College Block A" in a["message"] for a in lv["alerts"]), next((a["message"] for a in lv["alerts"] if "College Block A" in a["message"]), ""))

# ---------------- Module 7: collection
print("== Module 7: Waste collection management")
coll = admin.get(B + "/admin/collections").text
check("Bins requiring collection identified, with location shown", "Block A" in coll and "Pending collections (1)" in coll)
t = tok(coll)
admin.post(B + f"/admin/bins/{bin_id}/collect", data={"csrf_token": t})
after = [b for b in admin.get(B + "/admin/api/live").json()["bins"] if b["id"] == bin_id][0]
check("Admin marks collected -> capacity reset to 0%", all(c["fill"] == 0 for c in after["compartments"]))
with app.app_context():
    cr = CollectionRecord.query.filter_by(bin_id=bin_id, status="completed").first()
    check("Collection date/time stored", cr is not None and cr.collected_at is not None, str(cr.collected_at) if cr else "")
    check("Pending and completed collections tracked; alert resolved", CollectionRecord.query.filter_by(status="pending").count() == 0 and Alert.query.filter_by(bin_id=bin_id, resolved=False).count() == 0)
coll = admin.get(B + "/admin/collections").text
check("Collection history page lists the completed collection", "College Block A" in coll and "Completed collections" in coll)

# ---------------- Module 5: dashboard
print("== Module 5: Admin dashboard")
html = admin.get(B + "/admin/").text
for lbl in ["Total waste items detected", "Recyclable waste", "Non-recyclable waste", "Plastic waste", "Paper waste", "Metal waste", "Glass waste", "Organic waste", "Total virtual bins", "Normal bins", "Almost-full bins", "Collection-required bins"]:
    check(f"Dashboard shows '{lbl}'", lbl in html)
with app.app_context():
    total = WasteRecord.query.count()
    rec = WasteRecord.query.filter_by(is_recyclable=True).count()
st = admin.get(B + "/admin/api/live").json()["stats"]
check("Dashboard numbers equal counts in the database (no fabricated data)", st["total"] == total and st["recyclable"] == rec and st["non_recyclable"] == total - rec and sum(st["categories"].values()) == total, f"total={total}")

# ---------------- Module 6: analytics
print("== Module 6: Waste analytics and reports")
for p in ("daily", "weekly", "monthly"):
    a = admin.get(B + f"/admin/api/analytics?period={p}").json()
    check(f"{p.capitalize()} waste statistics", len(a["labels"]) > 0 and sum(a["totals"]) == a["count"] > 0, f"{len(a['labels'])} buckets, {a['count']} items")
check("Location-wise and category-wise analysis", bool(a["by_location"]) and bool(a["by_category"]), str(a["by_location"]))
check("Waste classification history (admin, filterable)", "Waste classification history" in admin.get(B + "/admin/history?category=glass").text)
check("Graphical charts (Chart.js, bundled)", requests.get(B + "/static/vendor/chart.umd.min.js").status_code == 200 and "<canvas" in admin.get(B + "/admin/analytics").text)
csvr = admin.get(B + "/admin/reports/export.csv")
check("Export reports (optional): CSV", csvr.status_code == 200 and csvr.text.count("\n") > 1)

# ---------------- Module 8: user history
print("== Module 8: User waste history")
hh = user.get(B + "/history").text
check("User sees previously uploaded images, categories, confidence, recommendations", "<img" in hh and re.search(r"<b>[\d.]+%</b>", hh) is not None and "Empty and rinse" in hh)
other, _ = (lambda s: (s, 0))(requests.Session())
t = tok(other.get(B + "/register").text)
other.post(B + "/register", data={"csrf_token": t, "name": "Other", "email": OTHER_EMAIL, "password": "OtherPass#1", "confirm": "OtherPass#1"})
other, _ = login(OTHER_EMAIL, "OtherPass#1")
check("History is private per user", "<img" not in other.get(B + "/history").text)

# ---------------- Non-functional
print("== Non-functional requirements")
lat = []
for f in IMGS["paper"][:8]:
    t0 = time.time(); classify(user, f, lib); lat.append(time.time() - t0)
check("Fast image processing (end-to-end upload+classify+store)", statistics.median(lat) < 2.0, f"median {statistics.median(lat)*1000:.0f} ms, max {max(lat)*1000:.0f} ms over {len(lat)} requests")
r = user.post(B + "/api/classify", headers={"X-CSRFToken": tok(user.get(B + "/classify").text)}, data={"location_id": lib}, files={"image": ("x.txt", b"not an image", "text/plain")})
check("Proper error handling (bad file -> clear JSON error, no crash)", r.status_code == 400 and "error" in r.json(), r.json().get("error"))
check("404 handled with friendly page", "Page not found" in requests.get(B + "/nope").text)

# Reliable DB operations: concurrent uploads must not lose capacity updates
hostel = int(opts["Hostel"])
hb = [b for b in admin.get(B + "/admin/api/live").json()["bins"] if b["location"] == "Hostel" and b["name"] != "Audit New Bin"][0]
page = admin.get(B + f"/admin/bins/{hb['id']}").text
data = {"csrf_token": tok(page)}
for cid in re.findall(r'name="capacity_(\d+)"', page):
    data[f"capacity_{cid}"] = "1000"
admin.post(B + f"/admin/bins/{hb['id']}/capacity", data=data)
files = IMGS["glass"][20:36]
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    out = list(ex.map(lambda f: classify(user, f, hostel).status_code, files * 2))
with app.app_context():
    db.session.expire_all()
    lost = []
    for c in BinCompartment.query.filter(BinCompartment.bin_id == hb["id"]).all():
        expected = sum(r.estimated_volume for r in WasteRecord.query.filter_by(compartment_id=c.id).all())
        if abs(expected - c.current_load) > 1e-6:
            lost.append((c.category, round(expected, 3), c.current_load))
check("Reliable DB operations: 32 concurrent uploads, bin load equals sum of stored records", all(s == 201 for s in out) and not lost, f"statuses ok={all(s == 201 for s in out)}; mismatches={lost}")

fails = [r for r in res if not r[1]]
print(f"\n{len(res) - len(fails)}/{len(res)} checks passed")
for f in fails:
    print("  FAILED:", f[0], f[2])
