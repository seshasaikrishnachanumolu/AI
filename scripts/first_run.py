"""One-time setup helper (called by setup_windows.bat; you can also run it by hand).

    python scripts/first_run.py

What it does (safe to run again, it never deletes anything):
  1. creates .env from .env.example if it does not exist (random SECRET_KEY, random admin password, SQLite database)
  2. checks that the trained AI model files are present
  3. if MySQL is configured in .env, creates the MySQL database
  4. creates the tables, the administrator account, 5 locations and 6 virtual bins
"""
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

ENV, EXAMPLE = ROOT / ".env", ROOT / ".env.example"
ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no look-alike characters
created_password = None

# 1. settings file
if not ENV.exists():
    if not EXAMPLE.exists():
        sys.exit("ERROR: .env.example is missing. Download the project again (git clone or the ZIP).")
    created_password = "".join(secrets.choice(ALPHABET) for _ in range(12))
    text = EXAMPLE.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^SECRET_KEY=.*$", lambda m: "SECRET_KEY=" + secrets.token_hex(32), text)
    text = re.sub(r"(?m)^ADMIN_PASSWORD=.*$", lambda m: "ADMIN_PASSWORD=" + created_password, text)
    ENV.write_text(text, encoding="utf-8")
    print("Created .env (SQLite database, random secret key, random admin password).")
else:
    print(".env already exists: keeping it.")

# 2. model files
missing = [f for f in ("ml/model/waste_cnn.keras", "ml/model/class_names.json") if not (ROOT / f).exists()]
if missing:
    sys.exit(f"ERROR: the trained model is missing: {', '.join(missing)}.\n"
             "Download the project again completely (git clone or the ZIP). The model is part of the repository.")
print("Trained model files found.")

import config  # noqa: E402,F401  (loads .env)

# 3. MySQL database (only when configured)
if os.environ.get("MYSQL_PASSWORD") is not None and os.environ.get("MYSQL_USER"):
    print("MySQL is configured in .env: creating the database...")
    r = subprocess.run([sys.executable, str(ROOT / "setup_mysql.py")])
    if r.returncode != 0:
        sys.exit("\nERROR: could not create the MySQL database. Check that MySQL is running and that MYSQL_USER / "
                 "MYSQL_PASSWORD in .env are correct (the same login you use in MySQL Workbench).\n"
                 "To use the built-in SQLite database instead, put a # in front of every MYSQL_ line in .env.")

# 4. tables + admin + locations + bins
import seed  # noqa: E402

seed.main()

email = os.environ.get("ADMIN_EMAIL", "admin@smartwaste.local")
print("\n" + "=" * 60)
print("Setup finished.")
print(f"  Admin email   : {email}")
if created_password:
    print(f"  Admin password: {created_password}   (also saved in the file .env)")
else:
    print("  Admin password: the one in your .env file (or the one you set later)")
print("=" * 60)
