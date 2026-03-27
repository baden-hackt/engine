# AGENT INSTRUCTIONS — Backend Logic + Reorder System

You are building the backend logic and reorder system for a hackathon project. Follow every instruction exactly. Do not deviate, improvise, or add features not listed here.

---

## OBJECTIVE

Build a Python application that:
1. Reads fill-level data from a shared SQLite database (written by Person 1's camera pipeline)
2. Checks each product's fill level against a reorder threshold
3. Prevents duplicate orders (dedup logic)
4. Generates a SAP Business One-compatible CSV file
5. Sends the CSV as an email attachment to the supplier
6. Exposes a simple REST API for the dashboard (Person 3) to read state

The application runs in a loop every 10 seconds. It runs on the same machine as Person 1's camera pipeline.

---

## FULL PROJECT DIRECTORY

Everything lives in one directory. This is the layout for ALL three people:

```
project/
├── docs/
│   ├── said/
│   │   ├── spec.md        ← Person 1's spec — DO NOT TOUCH
│   │   └── todo.md        ← Person 1's todo — DO NOT TOUCH
│   └── dijar/
│       ├── spec.md        ← YOUR SPEC (this document)
│       └── todo.md        ← YOUR TODO LIST
├── pipeline/          ← Person 1 (Said) — DO NOT TOUCH
│   ├── main.py
│   ├── camera.py
│   ├── tags.py
│   ├── vision.py
│   ├── db.py
│   └── requirements.txt
├── backend/           ← Person 2 (Dijar) — YOU BUILD THIS
│   ├── main.py
│   ├── config.py
│   ├── orders.py
│   ├── csv_gen.py
│   ├── mailer.py
│   ├── api.py
│   └── requirements.txt
├── .env               ← SHARED SECRETS (project root, used by both Person 1 and 2)
├── shelf.db           ← SHARED DATABASE (lives at project root)
└── latest_frame.jpg   ← SHARED FRAME (written by Person 1, served by Person 2)
```

The dashboard (Person 3 — Timo) is a separate Next.js app hosted on Vercel. It does NOT live in this repo. It connects to your FastAPI server at `http://<laptop-ip>:8000/api/*` over the local network. Your API is the only bridge between the laptop and the dashboard — that's why CORS is set to allow all origins and uvicorn binds to `0.0.0.0`.

The shared SQLite database `shelf.db` lives at the **project root**, one level above `backend/`. Both Person 1's pipeline and your backend read/write to this same file.

**Database path from your code:** `../shelf.db` (relative to `backend/`)

---

## YOUR PROJECT STRUCTURE

Create exactly these files inside `backend/`:

```
backend/
├── main.py
├── config.py
├── orders.py
├── csv_gen.py
├── mailer.py
├── api.py
└── requirements.txt
```

Do not create any other files. Do not create a README. Do not create tests. Do not create a products.json.

---

## FILE: requirements.txt

```
fastapi>=0.115.0
uvicorn>=0.34.0
resend>=2.26.0
python-dotenv>=1.0.0
```

No other dependencies. `sqlite3`, `csv`, `json`, `os`, `time`, `datetime`, `base64` are all stdlib.

---

## FILE: config.py

This module loads ALL configuration from the shared `.env` file at the project root. There are exactly 2 products. All product values, API keys, and email settings are environment variables.

```python
import os
from dotenv import load_dotenv

load_dotenv("../.env")

# API keys
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")

def load_products() -> dict:
    """
    Load product configuration from environment variables.
    Returns a dict mapping tag_id (int) to product dict.
    Exactly 2 products: tag_id 0 and tag_id 1.
    """
    products = {}

    for i in range(2):
        prefix = f"PRODUCT_{i}_"
        products[i] = {
            "tag_id": i,
            "product_id": os.getenv(f"{prefix}ID", f"MAT-00{i+1}"),
            "product_name": os.getenv(f"{prefix}NAME", f"Product {i+1}"),
            "supplier_name": os.getenv(f"{prefix}SUPPLIER_NAME", "Demo Supplier AG"),
            "supplier_email": os.getenv(f"{prefix}SUPPLIER_EMAIL", "demo@example.com"),
            "reorder_threshold": int(os.getenv(f"{prefix}THRESHOLD", "20")),
            "reorder_quantity": int(os.getenv(f"{prefix}REORDER_QTY", "100")),
            "unit": os.getenv(f"{prefix}UNIT", "Stück"),
        }

    return products
```

### Environment variable naming convention

Each product uses a prefix `PRODUCT_0_` or `PRODUCT_1_` followed by the field name:

| Variable | Type | Description |
|---|---|---|
| `PRODUCT_0_ID` | string | SAP material number, e.g. `MAT-001` |
| `PRODUCT_0_NAME` | string | Human-readable product name |
| `PRODUCT_0_SUPPLIER_NAME` | string | Supplier company name |
| `PRODUCT_0_SUPPLIER_EMAIL` | string | Email address to send orders to |
| `PRODUCT_0_THRESHOLD` | int | Fill level % below which reorder triggers |
| `PRODUCT_0_REORDER_QTY` | int | How many units to order |
| `PRODUCT_0_UNIT` | string | Unit of measure (e.g. "Stück", "Liter") |

Same pattern for `PRODUCT_1_*`.

All values have sensible defaults so the system runs even with a minimal `.env` containing just the API keys. The team fills in real values before the demo.

Do not create a `products.json`. Do not create a separate `.env` inside `backend/`. All config comes from `../.env`.

---

## FILE: orders.py

This module handles order state tracking and dedup logic. It uses the same `../shelf.db` database as Person 1.

### Tables

Create this table on module import if it does not exist:

```sql
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_id INTEGER NOT NULL,
    product_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    supplier_name TEXT NOT NULL,
    supplier_email TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    csv_filename TEXT
);
```

### Status values

Orders have exactly three possible statuses:
- `pending` — order has been created and email sent
- `delivered` — product has been restocked (fill level went back above threshold)
- `cancelled` — manually cancelled (not implemented in code, but the column supports it)

### Functions to implement

```python
import sqlite3
from datetime import datetime

DB_PATH = "../shelf.db"

def init_orders_table() -> None:
    """Create the orders table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_id INTEGER NOT NULL,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            supplier_name TEXT NOT NULL,
            supplier_email TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            csv_filename TEXT
        )
    """)
    conn.commit()
    conn.close()


def has_pending_order(tag_id: int) -> bool:
    """
    Check if there is already a pending order for this tag_id.
    Return True if a row exists with status='pending' for this tag_id.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE tag_id = ? AND status = 'pending'",
        (tag_id,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def create_order(tag_id: int, product: dict, csv_filename: str) -> int:
    """
    Insert a new order row with status='pending'.
    Return the order ID.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        """INSERT INTO orders (tag_id, product_id, product_name, supplier_name,
           supplier_email, quantity, unit, status, created_at, csv_filename)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
        (
            tag_id,
            product["product_id"],
            product["product_name"],
            product["supplier_name"],
            product["supplier_email"],
            product["reorder_quantity"],
            product["unit"],
            datetime.now().isoformat(),
            csv_filename,
        )
    )
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()
    return order_id


def mark_delivered(tag_id: int) -> None:
    """
    Set status='delivered' for all pending orders for this tag_id.
    Called when fill level goes back above the reorder threshold.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE orders SET status = 'delivered' WHERE tag_id = ? AND status = 'pending'",
        (tag_id,)
    )
    conn.commit()
    conn.close()


def get_all_orders() -> list[dict]:
    """
    Return all orders as a list of dicts, ordered by created_at descending.
    Used by the API for the dashboard.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM orders ORDER BY created_at DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_latest_fill_levels() -> list[dict]:
    """
    Read the latest fill level per tag_id from Person 1's fill_levels table.
    Return a list of dicts: [{"tag_id": 0, "fill_level": 25, "timestamp": "..."}, ...]
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT tag_id, fill_level, timestamp
        FROM fill_levels
        WHERE id IN (
            SELECT MAX(id) FROM fill_levels GROUP BY tag_id
        )
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows
```

Use a new `sqlite3.connect()` per function call. Do not keep a persistent connection.

---

## FILE: csv_gen.py

This module generates SAP Business One-compatible purchase order CSVs.

### CSV format

The CSV must use these exact column headers, in this exact order. These match the SAP Business One Data Import Framework format for purchase orders:

```
DocDate,CardCode,CardName,ItemCode,ItemDescription,Quantity,UnitPrice,Currency
```

### Function to implement

```python
import csv
import os
from datetime import datetime

CSV_DIR = "./orders_csv"

def generate_order_csv(product: dict) -> str:
    """
    Generate a CSV file for a single product reorder.
    Save it to ./orders_csv/ directory.
    Return the filename (not full path).

    The CSV contains exactly one data row (plus header).
    """
    os.makedirs(CSV_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"PO_{product['product_id']}_{timestamp}.csv"
    filepath = os.path.join(CSV_DIR, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "DocDate",
            "CardCode",
            "CardName",
            "ItemCode",
            "ItemDescription",
            "Quantity",
            "UnitPrice",
            "Currency"
        ])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d"),
            product["supplier_name"],
            product["supplier_name"],
            product["product_id"],
            product["product_name"],
            product["reorder_quantity"],
            "",
            "CHF"
        ])

    return filename
```

### CSV rules

- Delimiter is `;` (semicolon). SAP B1 expects this for European locales.
- Encoding is UTF-8.
- `UnitPrice` is left empty — the price comes from the SAP material master, not from this system.
- `Currency` is always `CHF`.
- One CSV file per order. Do not batch multiple products into one CSV.
- Files are saved in `./orders_csv/` directory, created automatically.

---

## FILE: mailer.py

This module sends order emails with CSV attachments via Resend.

```python
import resend
import base64
import os

from config import RESEND_API_KEY, SENDER_EMAIL

CSV_DIR = "./orders_csv"

def send_order_email(product: dict, csv_filename: str) -> bool:
    """
    Send an email to the supplier with the CSV attached via Resend.
    Return True if sent successfully, False otherwise.
    """
    resend.api_key = RESEND_API_KEY

    filepath = os.path.join(CSV_DIR, csv_filename)

    try:
        with open(filepath, "rb") as f:
            csv_content = base64.b64encode(f.read()).decode("utf-8")

        params: resend.Emails.SendParams = {
            "from": f"Lagersystem <{SENDER_EMAIL}>",
            "to": [product["supplier_email"]],
            "subject": f"Bestellung: {product['product_name']} ({product['product_id']})",
            "html": (
                f"<p>Guten Tag</p>"
                f"<p>Hiermit bestellen wir:</p>"
                f"<p><strong>Produkt:</strong> {product['product_name']}<br>"
                f"<strong>Materialnummer:</strong> {product['product_id']}<br>"
                f"<strong>Menge:</strong> {product['reorder_quantity']} {product['unit']}</p>"
                f"<p>Die Bestellung ist auch als CSV im Anhang.</p>"
                f"<p>Freundliche Grüsse<br>Automatisches Lagersystem</p>"
            ),
            "attachments": [
                {
                    "filename": csv_filename,
                    "content": csv_content,
                }
            ],
        }

        email = resend.Emails.send(params)
        print(f"  Email sent to {product['supplier_email']} for {product['product_name']} (id: {email['id']})")
        return True

    except Exception as e:
        print(f"  WARNING: Email failed for {product['product_name']}: {e}")
        return False
```

### Email rules

- Subject line is in German: `Bestellung: {product_name} ({product_id})`
- Body is HTML, in German. Exactly as written above.
- The CSV file is base64-encoded and attached.
- Uses the Resend Python SDK. One API call, no SMTP config.
- If email sending fails, log a warning and return False. Do not crash.
- If `RESEND_API_KEY` is an empty string, the email will fail — that's expected during development. The order still gets created in the database.

---

## FILE: api.py

This module runs a minimal FastAPI server for the dashboard (Person 3). Auto-generates interactive API docs at `/docs`.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import os

from orders import get_all_orders, get_latest_fill_levels
from config import load_products

app = FastAPI(title="Lagersystem API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

products = load_products()

FRAME_PATH = "../latest_frame.jpg"


@app.get("/api/camera-feed")
def api_camera_feed():
    """
    Serve the latest annotated camera frame as a JPEG image.
    Person 1's pipeline saves this file every scan cycle.
    The dashboard polls this endpoint every 2 seconds and displays it as an <img>.
    """
    if not os.path.exists(FRAME_PATH):
        return JSONResponse(status_code=404, content={"error": "No frame available yet"})
    return FileResponse(
        os.path.abspath(FRAME_PATH),
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/api/fill-levels")
def api_fill_levels():
    """
    Return latest fill level per tag, enriched with product info.
    Response format:
    [
        {
            "tag_id": 0,
            "fill_level": 25,
            "timestamp": "2026-05-16T14:30:00",
            "product_id": "MAT-001",
            "product_name": "Schrauben M8x30",
            "supplier_name": "Würth AG",
            "reorder_threshold": 20,
            "status": "low"  // "ok", "low", or "critical"
        },
        ...
    ]
    """
    fill_levels = get_latest_fill_levels()
    result = []
    for fl in fill_levels:
        tag_id = fl["tag_id"]
        product = products.get(tag_id, {})
        threshold = product.get("reorder_threshold", 20)

        if fl["fill_level"] <= 5:
            status = "critical"
        elif fl["fill_level"] <= threshold:
            status = "low"
        else:
            status = "ok"

        result.append({
            "tag_id": tag_id,
            "fill_level": fl["fill_level"],
            "timestamp": fl["timestamp"],
            "product_id": product.get("product_id", "UNKNOWN"),
            "product_name": product.get("product_name", "Unknown product"),
            "supplier_name": product.get("supplier_name", "Unknown supplier"),
            "reorder_threshold": threshold,
            "status": status,
        })
    return result


@app.get("/api/orders")
def api_orders():
    """
    Return all orders, newest first.
    Response format:
    [
        {
            "id": 1,
            "tag_id": 2,
            "product_id": "MAT-003",
            "product_name": "Kabelbinder 200mm",
            "supplier_name": "Distrelec AG",
            "supplier_email": "orders@distrelec-demo.ch",
            "quantity": 200,
            "unit": "Stück",
            "status": "pending",
            "created_at": "2026-05-16T14:35:00",
            "csv_filename": "PO_MAT-003_20260516_143500.csv"
        },
        ...
    ]
    """
    return get_all_orders()


@app.get("/api/products")
def api_products():
    """
    Return all product master data.
    """
    return list(products.values())
```

### API rules

- FastAPI runs on `http://localhost:8000` via uvicorn.
- Interactive API docs available at `http://localhost:8000/docs` (Swagger UI).
- CORS is enabled for all origins (the dashboard runs on Vercel or a different port).
- All data responses are JSON. The camera feed endpoint returns `image/jpeg`.
- No authentication. No rate limiting. This is a hackathon.
- The API is read-only. No POST/PUT/DELETE endpoints.

---

## FILE: main.py

This is the entry point. It runs two things:
1. The reorder check loop (in a background thread)
2. The FastAPI server via uvicorn (in the main thread)

```python
import time
import threading
from datetime import datetime
import uvicorn

from config import load_products
from orders import (
    init_orders_table,
    has_pending_order,
    create_order,
    mark_delivered,
    get_latest_fill_levels,
)
from csv_gen import generate_order_csv
from mailer import send_order_email
from api import app

CHECK_INTERVAL = 10  # seconds


def reorder_loop(products: dict) -> None:
    """
    Main reorder check loop. Runs forever in a background thread.
    """
    print("Reorder loop started.")

    while True:
        try:
            fill_levels = get_latest_fill_levels()

            if len(fill_levels) == 0:
                print(f"[{datetime.now().isoformat()}] No fill level data yet. Waiting...")
                time.sleep(CHECK_INTERVAL)
                continue

            for fl in fill_levels:
                tag_id = fl["tag_id"]
                fill_level = fl["fill_level"]

                product = products.get(tag_id)
                if product is None:
                    continue

                threshold = product["reorder_threshold"]

                # If fill level is back above threshold, mark any pending orders as delivered
                if fill_level > threshold:
                    mark_delivered(tag_id)
                    continue

                # Fill level is at or below threshold — check if we need to reorder
                if has_pending_order(tag_id):
                    print(f"  Tag {tag_id} ({product['product_name']}): "
                          f"fill={fill_level}%, already ordered, skipping.")
                    continue

                # No pending order — trigger reorder
                print(f"  Tag {tag_id} ({product['product_name']}): "
                      f"fill={fill_level}% <= threshold={threshold}%, ordering!")

                csv_filename = generate_order_csv(product)
                order_id = create_order(tag_id, product, csv_filename)
                email_sent = send_order_email(product, csv_filename)

                print(f"  Order #{order_id} created. CSV: {csv_filename}. "
                      f"Email: {'sent' if email_sent else 'FAILED'}")

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"ERROR in reorder loop: {e}")
            time.sleep(CHECK_INTERVAL)
            continue


def main():
    init_orders_table()
    products = load_products()

    print(f"Loaded {len(products)} products from .env")

    # Start reorder loop in background thread
    reorder_thread = threading.Thread(target=reorder_loop, args=(products,), daemon=True)
    reorder_thread.start()

    # Start FastAPI via uvicorn in main thread
    print("Starting API server on http://localhost:8000")
    print("API docs available at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
```

### Critical rules for main.py

- The reorder loop runs in a daemon thread. If the main thread (uvicorn) exits, the loop dies too.
- The reorder loop must NEVER crash. Every exception is caught, logged, and the loop continues.
- Uvicorn binds to `0.0.0.0` so Person 3's dashboard on Vercel can connect over the local network.

---

## ENVIRONMENT VARIABLES

All configuration is stored in a shared `.env` file at the project root (`../.env` from `backend/`). The `config.py` module loads it via `python-dotenv`.

The `.env` file contains:

```
# API keys
OPENAI_API_KEY=sk-...
RESEND_API_KEY=re_...
SENDER_EMAIL=onboarding@resend.dev

# Product 0 (AprilTag ID 0)
PRODUCT_0_ID=MAT-001
PRODUCT_0_NAME=Schrauben M8x30
PRODUCT_0_SUPPLIER_NAME=Demo Supplier AG
PRODUCT_0_SUPPLIER_EMAIL=your-email@gmail.com
PRODUCT_0_THRESHOLD=20
PRODUCT_0_REORDER_QTY=100
PRODUCT_0_UNIT=Stück

# Product 1 (AprilTag ID 1)
PRODUCT_1_ID=MAT-002
PRODUCT_1_NAME=Kabelbinder 200mm
PRODUCT_1_SUPPLIER_NAME=Demo Supplier AG
PRODUCT_1_SUPPLIER_EMAIL=your-email@gmail.com
PRODUCT_1_THRESHOLD=20
PRODUCT_1_REORDER_QTY=50
PRODUCT_1_UNIT=Stück
```

Person 2 uses everything except `OPENAI_API_KEY`. Do not create a separate `.env` inside `backend/`.

---

## HOW TO RUN

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Make sure `../.env` exists with `RESEND_API_KEY` set before running. The backend expects Person 1's pipeline to be running (or to have run) so that `fill_levels` table has data in `../shelf.db`.

---

## DATABASE CONTRACT WITH PERSON 1

Person 1 (camera pipeline) writes to these tables in `../shelf.db`:
- `fill_levels` — one row per tag per scan cycle (tag_id, fill_level, timestamp)
- `scan_log` — one row per scan cycle (for debugging)

Person 2 (this backend) reads from:
- `fill_levels` — to get latest fill levels per tag

Person 2 writes to:
- `orders` — to track reorder state

Person 2 NEVER writes to `fill_levels` or `scan_log`.
Person 1 NEVER reads from or writes to `orders`.

---

## API ENDPOINTS SUMMARY (for Person 3)

Person 3 (dashboard) will call these endpoints:

| Endpoint | Method | Returns |
|---|---|---|
| `GET /api/camera-feed` | GET | Latest annotated camera frame as JPEG |
| `GET /api/fill-levels` | GET | Latest fill level per tag, with product info and status |
| `GET /api/orders` | GET | All orders, newest first |
| `GET /api/products` | GET | Product master data loaded from .env |

All data responses are JSON arrays. The camera feed returns `image/jpeg`. No pagination. No auth.

The dashboard should poll `/api/camera-feed` every 2 seconds, `/api/fill-levels` every 5 seconds, and `/api/orders` every 10 seconds.

---

## WHAT THIS APPLICATION DOES NOT DO

Do not implement any of the following. They are handled by other people.

- Camera capture (Person 1)
- AprilTag detection (Person 1)
- Fill-level estimation via AI (Person 1)
- Dashboard / web frontend (Person 3)
- Physical shelf setup (Person 3)

---

## CONSTRAINTS

- Do not add WebSocket support.
- Do not add a database migration system.
- Do not add authentication or authorization.
- Do not add rate limiting.
- Do not save images.
- Do not add logging to a file. Print to stdout only.
- Do not add command-line argument parsing.
- Do not add unit tests.
- Do not create a Dockerfile or docker-compose.
- Do not use any libraries not listed in requirements.txt.
- Do not use asyncio. Use threading only as shown in main.py.
- Do not add a PUT or DELETE endpoint. The API is read-only.
