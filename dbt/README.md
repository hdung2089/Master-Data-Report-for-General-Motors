# dbt — Analytics Engineering Layer

## Overview

This layer uses [dbt (data build tool)](https://www.getdbt.com/) to transform raw carrier tracking and shipment data loaded into Snowflake into clean, analytics-ready tables.

dbt replaces the manual Python ETL transformation step with version-controlled, tested, and documented SQL models — making the pipeline more maintainable and auditable.

---

## Planned Model Structure

```
dbt/
├── models/
│   ├── staging/
│   │   ├── stg_hlcu_tracking.sql       ← clean + type Hapag events
│   │   ├── stg_maeu_tracking.sql       ← clean + type Maersk events
│   │   └── stg_shipments.sql           ← clean TMS shipment master data
│   │
│   └── analytics/
│       ├── dim_containers.sql          ← one row per container
│       ├── dim_suppliers.sql           ← supplier DUNS reference
│       ├── fct_tracking_events.sql     ← all events, all carriers, unified
│       └── fct_shipment_status.sql     ← current status per shipment
│
├── tests/
│   ├── assert_no_duplicate_events.sql
│   └── assert_valid_tracking_types.sql
│
└── dbt_project.yml
```

---

## Staging Models

### `stg_hlcu_tracking.sql`
- Source: `RAW.HLCU` (loaded from MongoDB via Python)
- Renames fields to snake_case standard
- Casts `Date` + `Time` into a single `event_timestamp` column
- Filters out rows where `Status` is null

### `stg_maeu_tracking.sql`
- Source: `RAW.MAEU`
- Same cleaning logic as HLCU
- Parses Maersk date format (`06 Oct 2025`) into standard `YYYY-MM-DD`
- Extracts vessel name from status field

### `stg_shipments.sql`
- Source: `RAW.SHIPMENTS` (loaded from TMS SQL exports)
- Normalizes STI# key type (handles int/float/string mismatches)
- Deduplicates on STI# keeping most recent record

---

## Analytics Models

### `dim_containers.sql`
One row per unique container number with latest known status.

```sql
SELECT
    container_number,
    carrier,
    vessel_name,
    pol,
    pod,
    MAX(event_timestamp) AS latest_event_time,
    MAX_BY(status, event_timestamp) AS current_status
FROM {{ ref('fct_tracking_events') }}
GROUP BY 1, 2, 3, 4, 5
```

### `fct_tracking_events.sql`
Union of all carrier tracking events in a single unified fact table.

```sql
SELECT
    container_number,
    'HLCU' AS carrier,
    status,
    place_of_activity AS location,
    event_timestamp,
    type_of_tracking,
    transport,
    last_updated
FROM {{ ref('stg_hlcu_tracking') }}

UNION ALL

SELECT
    container_number,
    'MAEU' AS carrier,
    status,
    location,
    event_timestamp,
    type_of_tracking,
    '' AS transport,
    last_updated
FROM {{ ref('stg_maeu_tracking') }}
```

### `fct_shipment_status.sql`
Mirrors the 12-stage waterfall status logic currently in `pipeline/etl_pipeline.py` — implemented as a CASE statement in SQL for better performance and testability.

```sql
SELECT
    sti_number,
    container_number,
    CASE
        WHEN actual_arrival_final_dest IS NOT NULL THEN '12. Delivered'
        WHEN actual_departure_dest_rail IS NOT NULL THEN '11. Outgate Destination Rail'
        WHEN actual_arrival_dest_rail IS NOT NULL   THEN '10. Arrived Destination Rail'
        WHEN actual_outgate_pod IS NOT NULL         THEN '9. Outgate POD'
        WHEN actual_arrival_pod IS NOT NULL         THEN '7. Arrived POD'
        WHEN actual_departure_pol IS NOT NULL       THEN '6. Departed POL'
        WHEN actual_arrival_pol IS NOT NULL         THEN '5. Arrived POL'
        WHEN actual_departure_consol IS NOT NULL    THEN '4. Outgate CFS'
        WHEN ship_date_from_supplier IS NOT NULL    THEN '2. Departed Supplier'
        ELSE NULL
    END AS status_of_container
FROM {{ ref('stg_shipments') }}
```

---

## Tests

### `assert_no_duplicate_events.sql`
Ensures no two tracking events share the same `container_number + status + event_timestamp`.

### `assert_valid_tracking_types.sql`
Ensures `type_of_tracking` is always one of:
- `Historic Tracking`
- `Current Tracking`
- `Future Tracking`

---

## How to Run (once configured)

```bash
# Install dbt with Snowflake adapter
pip install dbt-snowflake

# Run all models
dbt run

# Run tests
dbt test

# Generate documentation
dbt docs generate
dbt docs serve
```

---

## Why dbt

| Without dbt | With dbt |
|---|---|
| Transformations in Python scripts | Transformations in version-controlled SQL |
| No lineage visibility | Full DAG lineage in dbt docs |
| Manual testing | Automated schema + data tests |
| Hard to onboard new team members | Self-documenting models |
| Re-run entire pipeline on change | Incremental models — only process new data |
