"""Create tables, the admin account, the example locations and virtual bins.

Usage:  python seed.py
It does NOT create any waste records: dashboard figures come only from real use.
"""
import os

from app import create_app
from app.extensions import db
from app.models import Location, SmartBin, User
from app.services import bins as bin_service

LOCATIONS = ["College Block A", "College Block B", "Hostel", "Canteen", "Library"]
# (bin name, location)
BINS = [
    ("Block A Bin 1", "College Block A"),
    ("Block B Bin 1", "College Block B"),
    ("Hostel Bin 1", "Hostel"),
    ("Canteen Bin 1", "Canteen"),
    ("Canteen Bin 2", "Canteen"),
    ("Library Bin 1", "Library"),
]


def main():
    app = create_app()
    with app.app_context():
        db.create_all()

        email = os.environ.get("ADMIN_EMAIL", "admin@smartwaste.local").lower()
        password = os.environ.get("ADMIN_PASSWORD", "Admin@12345")
        if not User.query.filter_by(email=email).first():
            admin = User(name="Administrator", email=email, role="admin")
            admin.set_password(password)
            db.session.add(admin)
            print(f"Created admin user: {email}")

        for name in LOCATIONS:
            if not Location.query.filter_by(name=name).first():
                db.session.add(Location(name=name))
        db.session.flush()

        for bin_name, loc_name in BINS:
            if not SmartBin.query.filter_by(name=bin_name).first():
                loc = Location.query.filter_by(name=loc_name).one()
                bin_service.create_bin(bin_name, loc.id)
                print(f"Created bin: {bin_name} @ {loc_name}")

        db.session.commit()
        print("Database ready.")


if __name__ == "__main__":
    main()
