from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")  # user | admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Location(db.Model):
    __tablename__ = "locations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))
    bins = db.relationship("SmartBin", back_populates="location")


class SmartBin(db.Model):
    __tablename__ = "smart_bins"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    location = db.relationship("Location", back_populates="bins")
    compartments = db.relationship(
        "BinCompartment", back_populates="bin", cascade="all, delete-orphan"
    )

    @property
    def max_fill_percent(self):
        return max((c.fill_percent for c in self.compartments), default=0.0)

    def status(self, almost_full, alert):
        pct = self.max_fill_percent
        if pct >= alert:
            return "Collection Required"
        if pct >= almost_full:
            return "Almost Full"
        return "Normal"


class BinCompartment(db.Model):
    __tablename__ = "bin_compartments"
    __table_args__ = (db.UniqueConstraint("bin_id", "category", name="uq_bin_category"),)
    id = db.Column(db.Integer, primary_key=True)
    bin_id = db.Column(db.Integer, db.ForeignKey("smart_bins.id"), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    max_capacity = db.Column(db.Float, nullable=False, default=20.0)  # litres (configured)
    current_load = db.Column(db.Float, nullable=False, default=0.0)  # litres (estimated)

    bin = db.relationship("SmartBin", back_populates="compartments")

    @property
    def fill_percent(self):
        if not self.max_capacity:
            return 0.0
        return round(min(self.current_load / self.max_capacity * 100, 100.0), 1)


class WasteRecord(db.Model):
    __tablename__ = "waste_records"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    image_filename = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(20), nullable=False, index=True)
    confidence = db.Column(db.Float, nullable=False)  # 0-100
    recommendation = db.Column(db.Text, nullable=False)
    is_recyclable = db.Column(db.Boolean, nullable=False, default=False)
    bin_id = db.Column(db.Integer, db.ForeignKey("smart_bins.id"), nullable=True)
    compartment_id = db.Column(
        db.Integer, db.ForeignKey("bin_compartments.id"), nullable=True
    )
    estimated_volume = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User")
    bin = db.relationship("SmartBin")
    compartment = db.relationship("BinCompartment")


class CollectionRecord(db.Model):
    __tablename__ = "collection_records"
    id = db.Column(db.Integer, primary_key=True)
    bin_id = db.Column(db.Integer, db.ForeignKey("smart_bins.id"), nullable=False)
    status = db.Column(db.String(10), nullable=False, default="pending")  # pending | completed
    requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    collected_at = db.Column(db.DateTime, nullable=True)
    collected_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    volume_collected = db.Column(db.Float, nullable=True)  # litres, simulated

    bin = db.relationship("SmartBin")
    collector = db.relationship("User")


class Alert(db.Model):
    __tablename__ = "alerts"
    id = db.Column(db.Integer, primary_key=True)
    bin_id = db.Column(db.Integer, db.ForeignKey("smart_bins.id"), nullable=False)
    compartment_id = db.Column(
        db.Integer, db.ForeignKey("bin_compartments.id"), nullable=True
    )
    message = db.Column(db.String(255), nullable=False)
    resolved = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    bin = db.relationship("SmartBin")
