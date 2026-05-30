# MongoDB Schema Design

## Database: `Tracking`

One database, two collections — one per carrier. Keeping carriers in separate collections makes it easy to query by carrier without filtering, while keeping them in the same database allows cross-carrier aggregations.

```
Cluster0 (M0 Free Tier)
└── Tracking
    ├── HLCU        ← Hapag-Lloyd tracking events
    └── MAEU        ← Maersk tracking events
```

---

## Collection: `HLCU` (Hapag-Lloyd)

### Document Structure

```json
{
  "_id": "TCKU1234567|Departure from|2024-08-28|08:00",
  "Container_Number": "TCKU1234567",
  "Status": "Departure from",
  "Place_of_Activity": "Busan, Korea",
  "Date": "2024-08-28",
  "Time": "08:00",
  "Transport": "EVER GIVEN 123W",
  "Type_of_Tracking": "Historic Tracking",
  "Concat_1": "TCKU1234567Departure fromEVER GIVEN 123WHistoric Tracking",
  "Concat_2": "TCKU1234567Departure fromEVER GIVEN 123W",
  "Concat_3": "TCKU1234567Historic Tracking",
  "Duplicates": "",
  "carrier": "HLCU",
  "last_updated": "2024-09-01T12:00:00.000Z"
}
```

### Field Reference

| Field | Type | Description |
|---|---|---|
| `_id` | String | Composite key: `Container_Number\|Status\|Date\|Time` |
| `Container_Number` | String | ISO container number e.g. `TCKU1234567` |
| `Status` | String | Tracking event description |
| `Place_of_Activity` | String | Port or location of the event |
| `Date` | String | Event date `YYYY-MM-DD` |
| `Time` | String | Event time `HH:MM` |
| `Transport` | String | Vessel name and voyage number |
| `Type_of_Tracking` | String | `Historic Tracking`, `Current Tracking`, or `Future Tracking` |
| `Concat_1` | String | Container + Status + Transport + Type (dedup key with type) |
| `Concat_2` | String | Container + Status + Transport (dedup key without type) |
| `Concat_3` | String | Container + Type (used for filtering) |
| `Duplicates` | String | `Latest` if this is the most recent duplicate event, else blank |
| `carrier` | String | Always `HLCU` |
| `last_updated` | String | ISO timestamp of last upsert |

---

## Collection: `MAEU` (Maersk)

### Document Structure

```json
{
  "_id": "MRKU9876543|Discharge|06 Oct 2025|20:19",
  "Container_Number": "MRKU9876543",
  "Status": "Discharge",
  "Location": "Port of Baltimore - Dundalk Marine Terminal",
  "Date": "06 Oct 2025",
  "Time": "20:19",
  "Vessel_Name": "MAERSK EMDEN",
  "Transport": "",
  "Type_of_Tracking": "Current Tracking",
  "Concat_1": "MRKU9876543DischargeCurrent Tracking",
  "Concat_2": "MRKU9876543Discharge",
  "Concat_3": "MRKU9876543Current Tracking",
  "Duplicates": "",
  "carrier": "MAEU",
  "last_updated": "2024-09-01T12:00:00.000Z"
}
```

### Field Reference

| Field | Type | Description |
|---|---|---|
| `_id` | String | Composite key: `Container_Number\|Status\|Date\|Time` |
| `Container_Number` | String | ISO container number |
| `Status` | String | Tracking event e.g. `Discharge`, `Gate out`, `Load on` |
| `Location` | String | Port or terminal name |
| `Date` | String | Event date `DD Mon YYYY` |
| `Time` | String | Event time `HH:MM` |
| `Vessel_Name` | String | Vessel name extracted from status |
| `Transport` | String | Reserved for future use |
| `Type_of_Tracking` | String | `Historic Tracking`, `Current Tracking`, or `Future Tracking` |
| `Concat_1` | String | Container + Status + Type |
| `Concat_2` | String | Container + Status |
| `Concat_3` | String | Container + Type |
| `Duplicates` | String | `Latest` if most recent duplicate, else blank |
| `carrier` | String | Always `MAEU` |
| `last_updated` | String | ISO timestamp of last upsert |

---

## Upsert Strategy

Every daily scrape runs a **bulk upsert** — not an insert. This means:

- If a tracking event already exists → fields are updated (e.g. `last_updated`)
- If a tracking event is new → document is inserted
- Re-running the scraper on the same day **never creates duplicates**

The `_id` is a pipe-delimited composite of the fields that uniquely identify a tracking event:

```python
_id = f"{Container_Number}|{Status}|{Date}|{Time}"
```

---

## Index Strategy

For production scale, add these indexes in Atlas:

```javascript
// Query by container number (most common query)
db.HLCU.createIndex({ "Container_Number": 1 })
db.MAEU.createIndex({ "Container_Number": 1 })

// Query current status only
db.HLCU.createIndex({ "Container_Number": 1, "Type_of_Tracking": 1 })
db.MAEU.createIndex({ "Container_Number": 1, "Type_of_Tracking": 1 })

// Query by last updated (for incremental loads)
db.HLCU.createIndex({ "last_updated": -1 })
db.MAEU.createIndex({ "last_updated": -1 })
```

---

## Why MongoDB for This Use Case

| Requirement | How MongoDB handles it |
|---|---|
| Schema varies by carrier | Document model — HLCU and MAEU have different field names, no rigid schema required |
| Daily upserts | Native `updateOne` with `upsert=True` — atomic and efficient |
| Tracking events are append-heavy | Write-optimized document store |
| Need to query by container | Single-field index on `Container_Number` |
| Free tier sufficient | M0 cluster handles thousands of daily documents well within 512MB |
