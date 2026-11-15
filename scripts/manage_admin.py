"""Reset an account password or create/promote an administrator.

Normal users register themselves on the website. Administrators can NOT be created from the website
(by design), so use this script.

Examples (run from the project folder, with the virtual environment active):
    python scripts/manage_admin.py admin@smartwaste.local
        -> asks for a new password for that existing account
    python scripts/manage_admin.py manager@college.edu --name "Facility Manager"
        -> creates a NEW administrator (asks for a password)
    python scripts/manage_admin.py asha@example.com --make-admin
        -> turns an existing user into an administrator (also asks for a new password)
    python scripts/manage_admin.py asha@example.com --reset-user
        -> resets the password of a NORMAL user who forgot it (the account stays a normal user)

The password is typed at a hidden prompt (it never appears in the command history).
For automation you may set the environment variable ADMIN_NEW_PASSWORD instead.
"""
import argparse
import getpass
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User  # noqa: E402

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def ask_password():
    pw = os.environ.get("ADMIN_NEW_PASSWORD")
    if pw is None:
        pw = getpass.getpass("New password (min 8 characters): ")
        if pw != getpass.getpass("Repeat password: "):
            sys.exit("Passwords do not match. Nothing was changed.")
    if len(pw) < 8:
        sys.exit("Password must be at least 8 characters. Nothing was changed.")
    return pw


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("email")
    ap.add_argument("--name", help="full name (required when creating a new administrator)")
    ap.add_argument("--make-admin", action="store_true", help="promote an existing user to administrator")
    ap.add_argument("--reset-user", action="store_true", help="reset the password of an existing normal user (role unchanged)")
    a = ap.parse_args()

    email = a.email.strip().lower()
    if not EMAIL_RE.match(email):
        sys.exit("That does not look like a valid email address.")

    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user is None:
            if not a.name or not a.name.strip():
                sys.exit(f"No account with {email}. To create a new administrator add:  --name \"Full Name\"")
            user = User(name=a.name.strip()[:100], email=email, role="admin")
            user.set_password(ask_password())
            db.session.add(user)
            action = "Created administrator"
        else:
            if user.role != "admin" and not (a.make_admin or a.reset_user):
                sys.exit(f"{email} is a normal user. Add --reset-user to reset their password, or --make-admin to make them an administrator.")
            user.set_password(ask_password())
            if a.make_admin:
                user.role = "admin"
            action = "Updated password for"
        db.session.commit()
        print(f"{action}: {email} (role: {user.role})")


if __name__ == "__main__":
    main()
