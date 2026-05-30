"""
mongodb_insert.py
─────────────────
Reads the latest Hapag-Lloyd and Maersk JSON scrape files from the output
directory and upserts all records into MongoDB Atlas.

Run this in Jupyter after either scraper finishes — no arguments needed.
It auto-picks the most recently modified JSON file for each carrier.
"""

import json
import glob
import os
from datetime import datetime
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from urllib.parse import quote_plus

# ==================== CONFIGURATION ====================
username   = "hdung2089_db_user"
password   = "your_password_here"        # ← fill in before running
MONGO_URI  = f"mongodb+srv://{quote_plus(username)}:{quote_plus(password)}@cluster0.krlrk77.mongodb.net/?appName=Cluster0"
MONGO_DB   = "Tracking"
OUTPUT_DIR = r"C:\Users\ngodu\OneDrive - CEVA Logistics\Desktop\Report\AP-GMNA rep\Base reports\Webscraping"

CARRIERS = [
    {"pattern": "hapag_lloyd_tracking_*.json", "collection": "HLCU", "carrier": "HLCU"},
    {"pattern": "maersk_tracking_*.json",       "collection": "MAEU", "carrier": "MAEU"},
]
ID_FIELDS = ["Container_Number", "Status", "Date", "Time"]
# =======================================================


def main():
    print("="*70)
    print("🍃 MONGODB INSERT SCRIPT")
    print("="*70)
    print(f"   Database : {MONGO_DB}")
    print(f"   URI      : {MONGO_URI[:40]}...")

    # Connect
    print("\n🔌 Connecting to MongoDB...")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
        client.admin.command("ping")
        print("   ✓ Connected successfully")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        print("\n💡 Check your password and that your IP is whitelisted in Atlas.")
        return

    # Process each carrier
    for carrier_cfg in CARRIERS:
        pattern    = os.path.join(OUTPUT_DIR, carrier_cfg["pattern"])
        col_name   = carrier_cfg["collection"]
        carrier    = carrier_cfg["carrier"]

        # Auto-pick latest file
        matches = glob.glob(pattern)
        if not matches:
            print(f"\n⚠ No file found for {carrier} — skipping")
            continue

        latest_file = max(matches, key=os.path.getmtime)
        print(f"\n🔍 Auto-picking latest {carrier} JSON from:\n   {OUTPUT_DIR}")
        print(f"\n📂 Loading: {latest_file}")

        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = data.get("records", [])
        print(f"   ✓ carrier={data.get('carrier')}  |  scraped_at={data.get('scraped_at')}  |  events={data.get('total_events')}")

        # Build upsert operations
        insert_timestamp = datetime.now(datetime.UTC).isoformat()
        operations = []
        for rec in records:
            doc_id = "|".join([str(rec.get(f, "")).strip() for f in ID_FIELDS])
            rec["carrier"]      = carrier
            rec["last_updated"] = insert_timestamp
            operations.append(
                UpdateOne({"_id": doc_id}, {"$set": rec}, upsert=True)
            )

        # Upsert
        print(f"\n🍃 Upserting {len(records)} records → {MONGO_DB}.{col_name}")
        try:
            db     = client[MONGO_DB]
            col    = db[col_name]
            result = col.bulk_write(operations, ordered=False)
            print(f"   ✅ Done:")
            print(f"      • Inserted (new):     {result.upserted_count}")
            print(f"      • Updated (existing): {result.modified_count}")
            print(f"      • Total processed:    {len(operations)}")
        except BulkWriteError as bwe:
            details = bwe.details
            print(f"   ⚠ BulkWriteError — {len(details.get('writeErrors', []))} records failed")
            print(f"      Inserted: {details.get('nUpserted', 0)}, Modified: {details.get('nModified', 0)}")

    client.close()
    print("\n" + "="*70)
    print("✅ ALL DONE — MongoDB connection closed.")
    print("="*70)


if __name__ == "__main__":
    main()
