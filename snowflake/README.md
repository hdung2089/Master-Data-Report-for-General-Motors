# Snowflake — Data Warehouse Layer

## Overview

Snowflake serves as the central data warehouse for this pipeline. Raw data from MongoDB (carrier tracking) and SQL Server (TMS shipment data) is loaded into Snowflake and transformed through three layers before serving the Power BI dashboard.

---

## Three-Layer Schema

```
Snowflake
└── GM_SUPPLY_CHAIN_DB
    ├── RAW          ← mirrors source data as-is
    ├── STAGING      ← cleaned, typed, deduplicated
    └── ANALYTICS    ← business-ready, serves Power BI
```

---

## RAW Layer

Direct copies of source data — no transformations applied. Append-only.

### `RAW.HLCU_TRACKING`
Mirrors documents from MongoDB `HLCU` collection.

```sql
CREATE TABLE RAW.HLCU_TRACKING (
    _id                 VARCHAR,
    container_number    VARCHAR,
    status              VARCHAR,
    place_of_activity   VARCHAR,
    date                VARCHAR,
    time                VARCHAR,
    transport           VARCHAR,
    type_of_tracking    VARCHAR,
    concat_1            VARCHAR,
    concat_2            VARCHAR,
    concat_3            VARCHAR,
    duplicates          VARCHAR,
    carrier             VARCHAR,
    last_updated        TIMESTAMP_NTZ,
    _loaded_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

### `RAW.MAEU_TRACKING`
Mirrors documents from MongoDB `MAEU` collection.

```sql
CREATE TABLE RAW.MAEU_TRACKING (
    _id                 VARCHAR,
    container_number    VARCHAR,
    status              VARCHAR,
    location            VARCHAR,
    date                VARCHAR,
    time                VARCHAR,
    vessel_name         VARCHAR,
    transport           VARCHAR,
    type_of_tracking    VARCHAR,
    concat_1            VARCHAR,
    concat_2            VARCHAR,
    concat_3            VARCHAR,
    duplicates          VARCHAR,
    carrier             VARCHAR,
    last_updated        TIMESTAMP_NTZ,
    _loaded_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

### `RAW.SHIPMENTS`
Mirrors TMS SQL Server export — one row per shipment.

```sql
CREATE TABLE RAW.SHIPMENTS (
    sti_number                      VARCHAR,
    shipment_id_number              VARCHAR,
    container_number                VARCHAR,
    hbl                             VARCHAR,
    mbl                             VARCHAR,
    scac_code                       VARCHAR,
    vessel_name                     VARCHAR,
    pol                             VARCHAR,
    pod                             VARCHAR,
    origin_dun                      VARCHAR,
    dest_dun                        VARCHAR,
    lane_id                         VARCHAR,
    ship_date_from_supplier         TIMESTAMP_NTZ,
    actual_arrival_pod              TIMESTAMP_NTZ,
    actual_departure_pol            TIMESTAMP_NTZ,
    actual_outgate_pod              TIMESTAMP_NTZ,
    actual_arrival_dest_rail        TIMESTAMP_NTZ,
    actual_departure_dest_rail      TIMESTAMP_NTZ,
    actual_arrival_final_dest       TIMESTAMP_NTZ,
    _loaded_at                      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

---

## STAGING Layer

dbt models clean and type the RAW tables. See `dbt/README.md` for full model definitions.

Key transformations:
- Parse date strings into proper `TIMESTAMP_NTZ`
- Normalize container number format
- Deduplicate on natural keys
- Standardize `type_of_tracking` values

---

## ANALYTICS Layer

Business-ready tables consumed by Power BI.

### `ANALYTICS.FCT_TRACKING_EVENTS`
All carrier tracking events unified into one table.

| Column | Type | Description |
|---|---|---|
| `event_id` | VARCHAR | Surrogate key |
| `container_number` | VARCHAR | ISO container number |
| `carrier` | VARCHAR | `HLCU` or `MAEU` |
| `status` | VARCHAR | Tracking event description |
| `location` | VARCHAR | Port or terminal |
| `event_timestamp` | TIMESTAMP_NTZ | Combined date + time |
| `type_of_tracking` | VARCHAR | Historic / Current / Future |
| `vessel_name` | VARCHAR | Vessel name |
| `last_updated` | TIMESTAMP_NTZ | Last upsert timestamp |

### `ANALYTICS.FCT_SHIPMENT_STATUS`
One row per shipment with current status and all milestone dates.

| Column | Type | Description |
|---|---|---|
| `sti_number` | VARCHAR | GM shipment tracking ID |
| `container_number` | VARCHAR | ISO container number |
| `carrier` | VARCHAR | Ocean carrier SCAC |
| `status_of_container` | VARCHAR | 12-stage waterfall status |
| `pol` | VARCHAR | Port of Loading code |
| `pod` | VARCHAR | Port of Destination code |
| `vessel_name` | VARCHAR | Vessel name |
| `eta` | TIMESTAMP_NTZ | Expected arrival at POD |
| `actual_arrival_pod` | TIMESTAMP_NTZ | Actual arrival at POD |
| `cbm` | FLOAT | Volume in cubic meters |
| `weight_kg` | FLOAT | Weight in kilograms |

---

## Load Strategy

| Source | Method | Frequency |
|---|---|---|
| MongoDB HLCU/MAEU | Python → Snowflake connector or COPY INTO | Daily |
| SQL Server TMS | Export to CSV → COPY INTO RAW | Daily |
| RAW → STAGING | dbt run | Daily after load |
| STAGING → ANALYTICS | dbt run | Daily after staging |
