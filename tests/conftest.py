import io

import cv2
import numpy as np
import pytest

from app import create_app
from app.extensions import db
from app.models import Location, User
from app.services import bins as bin_service
from app.services import classifier
from config import TestConfig


@pytest.fixture()
def app(tmp_path):
    # Each test gets its own upload folder, so parallel or overlapping test runs cannot interfere.
    class IsolatedConfig(TestConfig):
        UPLOAD_FOLDER = str(tmp_path / "uploads")

    app = create_app(IsolatedConfig)
    with app.app_context():
        db.create_all()
        admin = User(name="Admin", email="admin@test.com", role="admin")
        admin.set_password("adminpass1")
        user = User(name="Alice", email="alice@test.com", role="user")
        user.set_password("alicepass1")
        loc = Location(name="Canteen")
        db.session.add_all([admin, user, loc])
        db.session.flush()
        bin_service.create_bin("Canteen Bin 1", loc.id, capacity=2.0)  # small: fills fast
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def fake_model(monkeypatch):
    state = {"category": "plastic", "confidence": 93.5}
    monkeypatch.setattr(
        classifier, "classify", lambda path, cfg: (state["category"], state["confidence"])
    )
    return state


def login(client, email, password, admin=False):
    return client.post("/admin/login" if admin else "/login", data={"email": email, "password": password})


def png_bytes():
    img = np.random.randint(0, 255, (40, 40, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    return io.BytesIO(buf.tobytes())


def upload(client, location_id=1, name="item.png"):
    return client.post(
        "/classify",
        data={"location_id": location_id, "image": (png_bytes(), name)},
        content_type="multipart/form-data",
    )
