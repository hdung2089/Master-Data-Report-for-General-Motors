# GM Automotive Import/Export Supply Chain Pipeline

> ⚠️ This project uses synthetic data for demonstration purposes. The original dataset is proprietary to the client (General Motors). The structure, data model, and pipeline logic reflect the real production system.

---

## Overview

This project is a full end-to-end data engineering pipeline built to track all ocean freight shipments for a large US-based global automotive manufacturer — from supplier departure through final delivery at GM assembly plants across North America.

The pipeline processes **daily shipment data** across multiple ocean carriers (Hapag-Lloyd, Maersk), consolidates it with TMS (Transportation Management System) data, and produces a clean master report used by the GM supply chain operations team.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                             │
│  Hapag-Lloyd Website  │  Maersk Website  │  SQL Server TMS DB  │
└──────────┬────────────┴────────┬─────────┴─────────┬───────────┘
           │                    │                     │
           ▼                    ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      INGESTION LAYER                            │
│         Selenium Scrapers  →  JSON  →  MongoDB Atlas            │
│              ingestion/hapag_scraper.py                         │
│              ingestion/maersk_scraper.py                        │
│              ingestion/mongodb_insert.py                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TRANSFORMATION LAYER                         │
│         Python ETL  →  Lookup merges  →  Business logic         │
│              pipeline/etl_pipeline.py                           │
│              sql/query3_shipment_data.sql                       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                              │
│         MongoDB Atlas (raw tracking events)                     │
│         Snowflake (planned — RAW → STAGING → ANALYTICS)         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SERVING LAYER (planned)                      │
│         dbt models  →  Snowflake ANALYTICS schema               │
│         Power BI dashboard (4 tabs)                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| Ingestion | Python + Selenium | Scrape carrier tracking websites daily |
| Raw Storage | MongoDB Atlas (M0) | Store tracking events as JSON documents |
| SQL Extraction | SQL Server | Pull shipment master data from TMS |
| Transformation | Python + pandas | Merge, clean, apply business logic |
| Warehouse | Snowflake (planned) | Three-layer schema for analytics |
| Transform | dbt (planned) | Model raw data into analytics-ready tables |
| Serving | Power BI (planned) | Dashboard for GM supply chain team |
| CI/CD | GitHub Actions | Validate code on every push |

---

## Pipeline Components

### 1. Ingestion — Carrier Tracking Scrapers
**Location:** `ingestion/`

Selenium-based scrapers that run daily against Hapag-Lloyd and Maersk tracking portals. Each scraper:
- Reads a list of container numbers from an Excel input file
- Navigates the carrier website and extracts all tracking events per container
- Classifies each event as `Historic`, `Current`, or `Future` tracking
- Outputs both Excel (for Power BI) and JSON (for MongoDB)

Anti-detection features are implemented to avoid bot blocking (shadow DOM access, randomized delays, CDP script injection).

**Carriers supported:**
- `HLCU` — Hapag-Lloyd
- `MAEU` — Maersk

### 2. MongoDB — Raw Event Storage
**Location:** `mongodb/`

All tracking events are upserted daily into MongoDB Atlas. Each document represents one tracking event for one container. Upsert logic ensures re-running the scraper never creates duplicates.

See `mongodb/schema.md` for full collection design and index strategy.

### 3. SQL — TMS Data Extraction
**Location:** `sql/`

Complex SQL queries against an internal SQL Server TMS database (Infor Nexus) to extract shipment master data including:
- Shipment IDs, container numbers, HBL/MBL
- Port of Loading / Port of Destination codes
- Vessel name, SCAC code, lane ID
- Origin/destination DUNS numbers

### 4. ETL Pipeline — Python Transformation
**Location:** `pipeline/`

The core transformation script that:
- Merges TMS data with carrier tracking data
- Applies 20+ lookup tables for supplier names, locations, plant names
- Computes CBM and weight from container type references
- Calculates shipment status (12-stage waterfall logic from "Departed Supplier" to "Delivered")
- Outputs the final master Excel report for Power BI

### 5. Snowflake — Data Warehouse (Planned)
**Location:** `snowflake/`

Three-layer schema design:
- `RAW` — mirrors MongoDB documents as-is
- `STAGING` — cleaned, typed, deduplicated
- `ANALYTICS` — business-ready tables for reporting

### 6. dbt — Analytics Engineering (Planned)
**Location:** `dbt/`

dbt models to transform RAW → ANALYTICS in Snowflake, replacing the manual Python ETL step with version-controlled, tested SQL models.

---

## CI/CD

GitHub Actions workflow runs on every push to `main`:
- Checks Python syntax on all scripts
- Validates JSON output structure
- Confirms required columns exist in pipeline output

See `.github/workflows/validate_pipeline.yml`

---

## Daily Workflow

```
1. Run ingestion/hapag_scraper.py     → hapag_lloyd_tracking_YYYYMMDD.json
2. Run ingestion/maersk_scraper.py    → maersk_tracking_YYYYMMDD.json
3. Run ingestion/mongodb_insert.py    → upserts both files into MongoDB Atlas
4. Run SQL queries in TMS             → exports to Excel input files
5. Run pipeline/etl_pipeline.py       → produces FinalReplicate.xlsx
```

---

## Domain Glossary

| Term | Meaning |
|---|---|
| STI# | Shipment Tracking ID — internal GM shipment identifier |
| MBL | Master Bill of Lading — issued by the ocean carrier |
| HBL | House Bill of Lading — issued by the freight forwarder |
| POL | Port of Loading — origin port |
| POD | Port of Destination — destination port |
| SCAC | Standard Carrier Alpha Code — carrier identifier |
| DUNS | Data Universal Numbering System — supplier/location identifier |
| CCA | Customs Consolidation Area — GM cross-dock facility |
| TEU | Twenty-foot Equivalent Unit — container size measure |
| CFS | Container Freight Station — consolidation warehouse |
