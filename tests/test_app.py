from app.extensions import db
from app.models import Alert, BinCompartment, CollectionRecord, SmartBin, User, WasteRecord

from .conftest import login, upload


# ---------------------------------------------------------------- auth
def test_register_and_login(client):
    r = client.post(
        "/register",
        data={"name": "Bob", "email": "bob@test.com", "password": "bobpass123", "confirm": "bobpass123"},
    )
    assert r.status_code == 302
    u = User.query.filter_by(email="bob@test.com").one()
    assert u.role == "user"
    assert u.password_hash != "bobpass123"
    assert login(client, "bob@test.com", "bobpass123").status_code == 302


def test_register_validation(client):
    r = client.post("/register", data={"name": "x", "email": "bad", "password": "short", "confirm": "short"})
    assert r.status_code == 400
    r = client.post(
        "/register",
        data={"name": "x", "email": "alice@test.com", "password": "password123", "confirm": "password123"},
    )
    assert r.status_code == 400  # duplicate


def test_wrong_password_and_role_separation(client):
    assert login(client, "alice@test.com", "nope").status_code == 401
    assert login(client, "admin@test.com", "adminpass1").status_code == 401  # admin cannot use user login
    assert login(client, "alice@test.com", "alicepass1", admin=True).status_code == 401


def test_role_based_access(client):
    assert client.get("/admin/").status_code == 302  # anonymous -> login
    login(client, "alice@test.com", "alicepass1")
    assert client.get("/admin/").status_code == 403
    assert client.get("/admin/api/analytics").status_code == 403


def test_open_redirect_blocked(client):
    r = client.post("/login?next=//evil.com", data={"email": "alice@test.com", "password": "alicepass1"})
    assert r.headers["Location"] == "/dashboard"


# ------------------------------------------------------ classification
def test_classification_assigns_bin_and_updates_capacity(client, fake_model):
    login(client, "alice@test.com", "alicepass1")
    r = upload(client)
    assert r.status_code == 302
    rec = WasteRecord.query.one()
    assert rec.category == "plastic" and rec.confidence == 93.5 and rec.is_recyclable
    comp = db.session.get(BinCompartment, rec.compartment_id)
    assert comp.category == "plastic" and comp.current_load == 0.5
    assert comp.fill_percent == 25.0
    assert client.get(f"/result/{rec.id}").status_code == 200


def test_organic_is_non_recyclable(client, fake_model):
    fake_model["category"] = "organic"
    login(client, "alice@test.com", "alicepass1")
    upload(client)
    assert WasteRecord.query.one().is_recyclable is False


def test_invalid_uploads(client, fake_model):
    login(client, "alice@test.com", "alicepass1")
    assert upload(client, name="x.txt").status_code == 400
    assert upload(client, location_id=999).status_code == 400
    assert WasteRecord.query.count() == 0


def test_model_missing_gives_503(client, app):
    app.config["MODEL_PATH"] = "does/not/exist.keras"
    login(client, "alice@test.com", "alicepass1")
    assert upload(client).status_code == 503
    assert WasteRecord.query.count() == 0


def test_api_classify_json(client, fake_model):
    login(client, "alice@test.com", "alicepass1")
    from .conftest import png_bytes

    r = client.post(
        "/api/classify",
        data={"location_id": 1, "image": (png_bytes(), "a.png")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 201
    j = r.get_json()
    assert j["category"] == "plastic" and j["assigned"] is True


def test_user_cannot_see_others_image(client, fake_model, app):
    login(client, "alice@test.com", "alicepass1")
    upload(client)
    rec = WasteRecord.query.one()
    client.post("/logout")
    other = User(name="Eve", email="eve@test.com", role="user")
    other.set_password("evepass123")
    db.session.add(other)
    db.session.commit()
    login(client, "eve@test.com", "evepass123")
    assert client.get(f"/uploads/{rec.image_filename}").status_code == 404
    assert client.get(f"/result/{rec.id}").status_code == 404


# ------------------------------------------- alerts / collection / reset
def test_alert_at_90_percent_then_collect_resets(client, fake_model):
    # plastic compartment capacity 2.0 L, 0.5 L per item: 4 items = 100%, 3 items = 75%
    login(client, "alice@test.com", "alicepass1")
    for _ in range(3):
        upload(client)
    assert Alert.query.count() == 0
    b = SmartBin.query.one()
    assert b.status(70, 90) == "Almost Full"

    upload(client)  # 100%
    assert Alert.query.filter_by(resolved=False).count() == 1
    assert CollectionRecord.query.filter_by(status="pending").count() == 1
    assert b.status(70, 90) == "Collection Required"

    # compartment full: a further item is stored but unassigned
    upload(client)
    assert WasteRecord.query.filter_by(bin_id=None).count() == 1

    client.post("/logout")
    login(client, "admin@test.com", "adminpass1", admin=True)
    r = client.post(f"/admin/bins/{b.id}/collect")
    assert r.status_code == 302
    comp = BinCompartment.query.filter_by(category="plastic").one()
    assert comp.current_load == 0
    c = CollectionRecord.query.one()
    assert c.status == "completed" and c.collected_at is not None and c.volume_collected == 2.0
    assert Alert.query.filter_by(resolved=False).count() == 0


# --------------------------------------------------- dashboard/analytics
def test_dashboard_counts_come_from_records(client, fake_model):
    login(client, "alice@test.com", "alicepass1")
    upload(client)
    fake_model["category"] = "organic"
    upload(client)
    client.post("/logout")
    login(client, "admin@test.com", "adminpass1", admin=True)
    html = client.get("/admin/").get_data(as_text=True)
    assert client.get("/admin/").status_code == 200
    assert 'class="num">2</div><div class="lbl">Total waste items detected' in html
    assert 'class="num">1</div><div class="lbl">Recyclable waste' in html
    assert 'class="num">1</div><div class="lbl">Non-recyclable waste' in html


def test_empty_dashboard_is_zero(client):
    login(client, "admin@test.com", "adminpass1", admin=True)
    html = client.get("/admin/").get_data(as_text=True)
    assert 'class="num">0</div><div class="lbl">Total waste items detected' in html


def test_analytics_api_and_csv(client, fake_model):
    login(client, "alice@test.com", "alicepass1")
    upload(client)
    client.post("/logout")
    login(client, "admin@test.com", "adminpass1", admin=True)
    for period, n in (("daily", 7), ("weekly", 8), ("monthly", 12)):
        j = client.get(f"/admin/api/analytics?period={period}").get_json()
        assert len(j["labels"]) == n
        assert sum(j["totals"]) == 1
        assert j["by_location"] == {"Canteen": 1}
        assert j["by_category"] == {"plastic": 1}
    assert client.get("/admin/api/analytics?period=bad").status_code == 400
    csv = client.get("/admin/reports/export.csv")
    assert csv.status_code == 200 and b"plastic" in csv.data


def test_admin_can_create_bin_and_set_capacity(client):
    login(client, "admin@test.com", "adminpass1", admin=True)
    client.post("/admin/bins", data={"name": "New Bin", "location_id": 1, "capacity": "10"})
    b = SmartBin.query.filter_by(name="New Bin").one()
    assert len(b.compartments) == 5 and all(c.max_capacity == 10 for c in b.compartments)
    comp = b.compartments[0]
    client.post(f"/admin/bins/{b.id}/capacity", data={f"capacity_{comp.id}": "-3"})
    assert db.session.get(BinCompartment, comp.id).max_capacity == 10
    client.post(f"/admin/bins/{b.id}/capacity", data={f"capacity_{comp.id}": "15"})
    assert db.session.get(BinCompartment, comp.id).max_capacity == 15


# ------------------------------------------- landing / live / health
def test_landing_page_and_health(client):
    r = client.get("/")
    assert r.status_code == 200 and b"smarter waste" in r.data
    h = client.get("/health").get_json()
    assert h == {"status": "ok", "database": "up"}
    assert client.get("/api/public-stats").get_json() == {
        "items": 0, "bins": 1, "locations": 1, "recyclable_pct": 0}


def test_all_pages_render_for_each_role(client, fake_model):
    for url in ("/login", "/register", "/admin/login"):
        assert client.get(url).status_code == 200
    login(client, "alice@test.com", "alicepass1")
    upload(client)
    for url in ("/dashboard", "/classify", "/history", "/"):
        assert client.get(url).status_code == 200, url
    client.post("/logout")
    login(client, "admin@test.com", "adminpass1", admin=True)
    assert client.get("/dashboard").status_code == 302  # admins go to the console
    for url in ("/admin/", "/admin/bins", "/admin/bins/1", "/admin/collections", "/admin/alerts",
                "/admin/locations", "/admin/analytics", "/admin/history"):
        assert client.get(url).status_code == 200, url


def test_live_endpoint_reflects_new_items_and_is_admin_only(client, fake_model):
    assert client.get("/admin/api/live").status_code == 302
    login(client, "alice@test.com", "alicepass1")
    assert client.get("/admin/api/live").status_code == 403
    for _ in range(4):  # 4 x 0.5 L fills the 2 L plastic compartment
        upload(client)
    client.post("/logout")
    login(client, "admin@test.com", "adminpass1", admin=True)
    d = client.get("/admin/api/live").get_json()
    assert d["stats"]["total"] == 4 and d["stats"]["bins_collect"] == 1
    assert d["bins"][0]["status"] == "Collection Required"
    plastic = [c for c in d["bins"][0]["compartments"] if c["category"] == "plastic"][0]
    assert plastic["fill"] == 100.0
    assert len(d["recent"]) == 4 and len(d["alerts"]) == 1 and d["latest_alert_id"] >= 1
