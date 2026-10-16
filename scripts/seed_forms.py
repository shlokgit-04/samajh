"""Load data/forms.json into the Supabase `forms` table.

Usage: python scripts/seed_forms.py
Requires SUPABASE_URL and SUPABASE_SERVICE_KEY in .env.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()

if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
    print("SUPABASE_URL / SUPABASE_SERVICE_KEY are not set in .env. Nothing seeded.")
    sys.exit(1)

from supabase import create_client  # noqa: E402

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "forms.json"
)


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as fh:
        forms = json.load(fh)
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    for form in forms:
        row = {"id": form["id"], "name": form["name"], "data": form}
        client.table("forms").upsert(row, on_conflict="id").execute()
        print(f"seeded: {form['id']} ({form['name']})")
    print(f"Done. {len(forms)} forms in the knowledge base.")


if __name__ == "__main__":
    main()
