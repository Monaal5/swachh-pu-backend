"""
One-time database setup for a fresh Postgres / Neon database.

    pip install -r requirements.txt
    set DATABASE_URL=postgresql://...        (Windows)   |  export DATABASE_URL=...  (macOS/Linux)
    python scripts/init_db.py --admin-email admin@pu.ac.in --admin-password "Admin@12345" --demo-workers

What it does (all steps are safe to re-run):
  1. Creates every table from db/schema.sql
  2. Loads the UIET location hierarchy from the room spreadsheets
  3. Creates (or resets the password of) an admin account
  4. With --demo-workers, adds three sample sanitation workers for testing
"""

import argparse
import io
import os
import sys
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(ROOT, ".env"))

from app.services.auth_service import hash_password  # noqa: E402
from app.utils.db import get_db  # noqa: E402

DEMO_WORKERS = [
    {"worker_id": "EMP101", "full_name": "Ramesh Kumar", "department": "Sanitation", "phone": "9876543210",
     "designation": "Senior Sanitation Officer", "email": "ramesh.kumar@swachh.pu", "password": "Ramesh@101"},
    {"worker_id": "EMP102", "full_name": "Suresh Singh", "department": "Maintenance", "phone": "9876543211",
     "designation": "Maintenance Technician", "email": "suresh.singh@swachh.pu", "password": "Suresh@102"},
    {"worker_id": "EMP103", "full_name": "Anita Devi", "department": "Sanitation", "phone": "9876543212",
     "designation": "Sanitation Worker", "email": "anita.devi@swachh.pu", "password": "Anita@103"},
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--admin-email")
    ap.add_argument("--admin-password")
    ap.add_argument("--admin-name", default="Swachh Admin")
    ap.add_argument("--demo-workers", action="store_true")
    args = ap.parse_args()

    db = get_db()

    print("1/4 Creating tables ...")
    with open(os.path.join(ROOT, "db", "schema.sql"), encoding="utf-8") as f:
        db.run(f.read())

    print("2/4 Loading UIET location hierarchy ...")
    from scripts.seed_location_hierarchy import seed_hierarchy
    log = io.StringIO()
    with redirect_stdout(log):
        seed_hierarchy()
    counts = db.run("SELECT (SELECT count(*) FROM blocks) b, (SELECT count(*) FROM floors) f, (SELECT count(*) FROM rooms) r")[0]
    print(f"    {counts['b']} blocks, {counts['f']} floors, {counts['r']} rooms")

    if args.admin_email and args.admin_password:
        print(f"3/4 Admin account {args.admin_email} ...")
        existing = db.table("users").select("*").eq("email", args.admin_email).execute().data
        if existing:
            db.table("users").update({"password_hash": hash_password(args.admin_password), "role": "admin",
                                      "is_email_verified": True}).eq("id", existing[0]["id"]).execute()
            uid = existing[0]["id"]
        else:
            uid = db.table("users").insert({"name": args.admin_name, "email": args.admin_email,
                                            "password_hash": hash_password(args.admin_password),
                                            "role": "admin", "is_email_verified": True}).execute().data[0]["id"]
        db.table("profiles").upsert({"id": uid, "user_id": uid, "name": args.admin_name, "role": "admin"},
                                    on_conflict="id").execute()
    else:
        print("3/4 Skipped admin (pass --admin-email and --admin-password)")

    if args.demo_workers:
        print("4/4 Adding demo workers EMP101–EMP103 ...")
        db.table("master_workers").upsert(DEMO_WORKERS, on_conflict="worker_id").execute()
    else:
        print("4/4 Skipped demo workers (pass --demo-workers)")
    print("Done.")


if __name__ == "__main__":
    main()
