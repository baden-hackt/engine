# STOCKR Engine - Technical Documentation

## 1. Purpose

This repository contains the backend logic of an automated shelf monitoring and reorder system.
It combines:

- a vision pipeline (`engine/pipeline`) that reads camera images, detects AprilTags, estimates fill level, and writes telemetry to SQLite.
- a backend service (`engine/backend`) that exposes REST APIs, evaluates reorder logic, creates CSV purchase orders, and optionally sends supplier emails.

Both modules share one SQLite database (`engine/shelf.db`) and one shared image artifact (`engine/latest_frame.jpg`).

## 2. High-Level Architecture

```text
Camera -> Pipeline (OpenCV + AprilTag + OpenAI Vision) -> shelf.db.

Backend (FastAPI + reorder loop) <- shelf.db.fill_levels
Backend -> shelf.db.orders / shelf.db.products
Backend -> orders_csv/*.csv
Backend -> Supplier Email (Resend, optional)

Dashboard/Client -> FastAPI /api/*
```

## 3. Repository Structure

```text
engine/
  backend/
    api.py            # FastAPI routes
    main.py           # API startup + reorder/simulation background loops
    config.py         # env loading, product config, simulation flags
    orders.py         # DB access for orders + latest fill levels
    csv_gen.py        # order CSV generation
    mailer.py         # email sending through Resend
    requirements.txt

  pipeline/
    main.py           # camera scan loop
    camera.py         # camera init, frame capture, change detection
    tags.py           # AprilTag detection + crop bounds
    vision.py         # OpenAI vision fill-level estimation
    db.py             # DB init + writes + crop settings
    test_pipeline.py  # unit tests for camera/tags/db
    requirements.txt

  shelf.db            # shared SQLite database (runtime-generated)
  latest_frame.jpg    # latest annotated frame (runtime-generated)
  Dokumentation.md
```

## 4. Runtime Data Flow

1. `pipeline/main.py` captures frames from webcam index `0` (1280x720), rotates by 180 degrees.
2. Global frame change detection skips processing when scene is stable.
3. AprilTags are detected (`tag36h11`) and slots are cropped using per-tag crop settings from `crop_settings`.
4. If crop changed (or first time), vision model estimates fill level as integer `0..100`.
5. Pipeline writes each measurement to `fill_levels` and writes scan telemetry to `scan_log`.
6. Pipeline writes an annotated frame to `../latest_frame.jpg`.
7. `backend/main.py` reorder loop polls latest fill level per tag every 10s.
8. For values below/equal reorder threshold:
   - create order CSV in `backend/orders_csv/`
   - insert order with `status='pending'` into `orders`
   - send email with CSV attachment (best effort)
9. If fill level rises above threshold, pending orders for that tag are marked `delivered`.

## 5. Database Model (`engine/shelf.db`)

### 5.1 `fill_levels`

- producer: pipeline (plus simulation mode helper)
- consumer: backend reorder loop + `/api/fill-levels`

Columns:

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `tag_id INTEGER NOT NULL`
- `fill_level INTEGER NOT NULL`
- `timestamp TEXT NOT NULL` (ISO 8601)

### 5.2 `scan_log`

- producer: pipeline
- purpose: operational telemetry (change detected / tags detected)

Columns:

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `timestamp TEXT NOT NULL`
- `tags_detected INTEGER NOT NULL`
- `change_detected INTEGER NOT NULL` (`1` or `0`)

### 5.3 `crop_settings`

- producer: pipeline (default seeding), backend/dashboard (future updates)
- used by: pipeline crop extraction logic

Columns:

- `tag_id INTEGER PRIMARY KEY`
- `crop_width INTEGER NOT NULL`
- `crop_height INTEGER NOT NULL`
- `offset_x INTEGER NOT NULL`
- `offset_y INTEGER NOT NULL`
- `updated_at TEXT NOT NULL`

Seeded defaults for `tag_id` `0` and `1`:

- `crop_width=336`
- `crop_height=448`
- `offset_x=0`
- `offset_y=0`

### 5.4 `products`

- owner: backend
- loaded on every reorder cycle (`load_products()`)

Columns:

- `tag_id INTEGER PRIMARY KEY`
- `product_id TEXT NOT NULL`
- `product_name TEXT NOT NULL`
- `supplier_name TEXT NOT NULL`
- `supplier_email TEXT NOT NULL`
- `reorder_threshold INTEGER NOT NULL`
- `reorder_quantity INTEGER NOT NULL`
- `unit TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

### 5.5 `orders`

- owner: backend reorder loop

Columns:

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `tag_id INTEGER NOT NULL`
- `product_id TEXT NOT NULL`
- `product_name TEXT NOT NULL`
- `supplier_name TEXT NOT NULL`
- `supplier_email TEXT NOT NULL`
- `quantity INTEGER NOT NULL`
- `unit TEXT NOT NULL`
- `status TEXT NOT NULL DEFAULT 'pending'`
- `created_at TEXT NOT NULL`
- `csv_filename TEXT`

## 6. Configuration (`engine/.env`)

The backend and pipeline both read `../.env` relative to their package directories.

### 6.1 Required Keys

- `OPENAI_API_KEY=...` (pipeline vision estimation)
- `RESEND_API_KEY=...` (backend email sending; optional for local tests)
- `SENDER_EMAIL=onboarding@resend.dev` (or verified sender)

### 6.2 Product Config Keys

For each tag (`0`, `1`):

- `PRODUCT_{tag}_ID`
- `PRODUCT_{tag}_NAME`
- `PRODUCT_{tag}_SUPPLIER_NAME`
- `PRODUCT_{tag}_SUPPLIER_EMAIL`
- `PRODUCT_{tag}_THRESHOLD` (alias `REORDER_THRESHOLD`)
- `PRODUCT_{tag}_REORDER_QTY` (alias `REORDER_QUANTITY`)
- `PRODUCT_{tag}_UNIT`

Notes:

- Synonyms are normalized by backend (`THRESHOLD <-> REORDER_THRESHOLD`, `REORDER_QTY <-> REORDER_QUANTITY`).
- Product data is persisted in SQLite (`products` table), not directly edited in `.env` after initialization.

### 6.3 Simulation Mode (Backend)

- `SIMULATION_MODE=true|false` (default `false`)
- `SIMULATION_INTERVAL_SECONDS=10`
- `SIMULATION_LOW_FILL=5`
- `SIMULATION_HIGH_FILL=95`
- `SIMULATION_TAG_ID=0`

Simulation alternates low/high fill levels to test `order -> delivered -> order`.

## 7. Backend API

Base URL (local): `http://localhost:8000`

### 7.1 Health/Docs

- Swagger UI: `GET /docs`

### 7.2 Data Endpoints

- `GET /api/camera-feed`
  - returns `latest_frame.jpg` as `image/jpeg`
  - returns `404` if image not available yet
- `GET /api/fill-levels`
  - latest fill per tag enriched with product metadata and status (`ok|low|critical`)
- `GET /api/orders`
  - all orders, newest first
- `GET /api/products`
  - product master data list

### 7.3 Product Config Endpoints

- `GET /api/product-env`
- `GET /api/product-env/{tag_id}` where `tag_id in {0,1}`
- `PUT /api/product-env/{tag_id}`
- `PUT /api/product-env` (bulk update)

Validation:

- only tag IDs `0` and `1` are accepted
- integer fields must parse to `int`
- unsupported suffix keys return `400`

## 8. Local Setup

## 8.1 Create/Activate Virtual Environments

Pipeline:

```powershell
cd engine\pipeline
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Backend:

```powershell
cd engine\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 8.2 Run Pipeline

```powershell
cd engine\pipeline
python main.py
```

Expected outputs:

- `engine/shelf.db` updated (`fill_levels`, `scan_log`)
- `engine/latest_frame.jpg` refreshed continuously

## 8.3 Run Backend

```powershell
cd engine\backend
python main.py
```

Expected outputs:

- FastAPI on `0.0.0.0:8000`
- reorder loop active in background

## 8.4 Run Unit Tests (Pipeline)

```powershell
cd engine\pipeline
python -m unittest test_pipeline.py
```

## 9. Operational Notes

- Reorder loop interval is fixed at 10 seconds (`CHECK_INTERVAL`).
- Pipeline scan interval is 1 second.
- Pipeline writes `latest_frame.jpg` twice per scan (after tag detect and after fill overlays).
- If email sending fails, order is still persisted (non-blocking warning behavior).
- Backend supports CORS `*` for dashboard integration.

## 10. Failure Modes & Troubleshooting

- `ERROR: Cannot open camera`
  - camera index unavailable or blocked by another app.
- `WARNING: No AprilTags detected`
  - tag not visible, blur/lighting issue, unsupported tag family.
- `Vision API error`
  - invalid/missing `OPENAI_API_KEY`, network error, rate limits.
- `/api/camera-feed` returns 404
  - pipeline has not yet produced `latest_frame.jpg`.
- no rows in `/api/fill-levels`
  - pipeline not running or no successful tag/vision cycle yet.

## 11. Security & Reliability Considerations

- Secrets stay in `.env`; do not commit real keys.
- SQLite is local-file based; no locking strategy beyond sqlite defaults.
- Current design is scoped to two tags/products (`0` and `1`) by validation.
- Email sender domain must be verified in Resend for production usage.

## 12. Extension Ideas

- Add backend endpoints for `crop_settings` CRUD with validation (`width/height >= 50`).
- Add retry/backoff strategy for OpenAI and Resend calls.
- Add migration layer for DB schema evolution.
- Add integration tests covering full loop from simulated fill to order creation.
