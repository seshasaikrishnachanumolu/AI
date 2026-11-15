"""Create the MySQL database (if missing) using the MYSQL_* settings in .env.
Tables are then created by `python seed.py`."""
import os
import re
import sys

import pymysql

import config  # noqa: F401  (loads .env)

user = os.environ.get("MYSQL_USER")
password = os.environ.get("MYSQL_PASSWORD")
if not user or password is None:
    sys.exit("Set MYSQL_USER and MYSQL_PASSWORD in .env first.")
db = os.environ.get("MYSQL_DATABASE", "smart_waste")
if not re.fullmatch(r"[A-Za-z0-9_]+", db):
    sys.exit("MYSQL_DATABASE may only contain letters, digits and underscores.")

conn = pymysql.connect(
    host=os.environ.get("MYSQL_HOST", "localhost"),
    port=int(os.environ.get("MYSQL_PORT", "3306")),
    user=user,
    password=password,
)
with conn.cursor() as cur:
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
conn.close()
print(f"Database '{db}' is ready. Now run: python seed.py")
