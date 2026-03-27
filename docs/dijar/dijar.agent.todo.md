# Dijar — Agent TODO

> **Spec:** Read `/docs/dijar/dijar.agent.spec.md` before starting any TODO.
>
> **Rules:**
> - Work ONLY on the TODO marked `ACTIVE`.
> - Do NOT modify LOCKED TODOs.
> - Do NOT create new TODOs.
> - Do NOT change architecture or tooling unless the TODO explicitly requires it.
> - Do NOT refactor unrelated code.
> - Do NOT guess if something is ambiguous — STOP and ask for clarification.
> - When a TODO is complete, change its state from `ACTIVE` to `DONE`.

---

## TODO 1 — DONE
**Goal:** Create project structure and install dependencies
**Tasks:**
- Create `backend/` directory with empty files: `main.py`, `config.py`, `orders.py`, `csv_gen.py`, `mailer.py`, `api.py`, `requirements.txt`
- Write `requirements.txt` contents exactly as specified in spec
- Run `pip install -r requirements.txt`
- Ensure `../.env` at project root contains `RESEND_API_KEY`, `SENDER_EMAIL`, and all `PRODUCT_0_*` / `PRODUCT_1_*` variables as specified in spec. Do NOT remove any other variables that may already be in the file (e.g. `OPENAI_API_KEY` from Person 1).
**Acceptance Criteria:**
- `backend/` exists with exactly 7 files
- `import fastapi`, `import uvicorn`, `import resend`, `from dotenv import load_dotenv` all succeed
- `../.env` contains `RESEND_API_KEY`, `SENDER_EMAIL`, and all 14 `PRODUCT_*` variables

---

## TODO 2 — DONE
**Goal:** Implement `config.py`
**Tasks:**
- Call `load_dotenv("../.env")` at module level
- Load `RESEND_API_KEY` and `SENDER_EMAIL` from env with `os.getenv()`
- Implement `load_products()` — loops `range(2)`, reads `PRODUCT_0_*` and `PRODUCT_1_*` env vars, returns dict mapping `tag_id` (int) to product dict
- Each product dict has: `tag_id`, `product_id`, `product_name`, `supplier_name`, `supplier_email`, `reorder_threshold` (int), `reorder_quantity` (int), `unit`
- All fields have sensible defaults as specified in spec
**Acceptance Criteria:**
- `python -c "from config import load_products; p = load_products(); print(len(p), p[0]['product_name'])"` prints `2` and the product name from `.env`
- `python -c "from config import RESEND_API_KEY; print(RESEND_API_KEY)"` prints the key from `.env`

---

## TODO 3 — DONE
**Goal:** Implement `orders.py`
**Tasks:**
- Set `DB_PATH = "../shelf.db"`
- Implement `init_orders_table()` — creates `orders` table if it doesn't exist (schema exactly as specified in spec)
- Implement `has_pending_order(tag_id)` — returns True if any row exists with `status='pending'` for this tag_id
- Implement `create_order(tag_id, product, csv_filename)` — inserts row with `status='pending'`, returns order ID
- Implement `mark_delivered(tag_id)` — sets `status='delivered'` on all pending orders for this tag_id
- Implement `get_all_orders()` — returns all orders as list of dicts, ordered by `created_at` DESC
- Implement `get_latest_fill_levels()` — reads latest fill level per tag_id from Person 1's `fill_levels` table
- Use a new `sqlite3.connect()` per function call, close after each call
**Acceptance Criteria:**
- `python -c "from orders import init_orders_table; init_orders_table()"` creates the `orders` table in `../shelf.db`
- `python -c "from orders import has_pending_order; print(has_pending_order(0))"` returns False (no orders yet)

---

## TODO 4 — DONE
**Goal:** Implement `csv_gen.py`
**Tasks:**
- Set `CSV_DIR = "./orders_csv"`
- Implement `generate_order_csv(product)` — creates `orders_csv/` dir if needed, generates a CSV file with SAP B1 purchase order headers, semicolon delimiter, UTF-8 encoding, one data row
- Column headers exactly: `DocDate;CardCode;CardName;ItemCode;ItemDescription;Quantity;UnitPrice;Currency`
- `UnitPrice` left empty, `Currency` always `CHF`
- Filename format: `PO_{product_id}_{YYYYMMDD_HHMMSS}.csv`
- Returns the filename (not full path)
**Acceptance Criteria:**
- `generate_order_csv(product)` creates a file in `./orders_csv/` with correct headers and one data row
- File opens correctly in a text editor with semicolon-separated values

---

## TODO 5 — DONE
**Goal:** Implement `mailer.py`
**Tasks:**
- Import `RESEND_API_KEY` and `SENDER_EMAIL` from `config`
- Implement `send_order_email(product, csv_filename)` — sets `resend.api_key`, reads CSV file, base64 encodes it, sends email via `resend.Emails.send()` with attachment
- Subject line in German: `Bestellung: {product_name} ({product_id})`
- HTML body in German exactly as specified in spec
- Returns True on success, False on failure
- Never crashes — catches all exceptions, prints warning, returns False
**Acceptance Criteria:**
- With a valid `RESEND_API_KEY` and a CSV file in `./orders_csv/`, `send_order_email(product, filename)` sends an email and returns True
- With an empty `RESEND_API_KEY`, it prints a warning and returns False (does not crash)

---

## TODO 6 — DONE
**Goal:** Implement `api.py`
**Tasks:**
- Create FastAPI app with title `"Lagersystem API"`
- Add CORS middleware allowing all origins
- Set `FRAME_PATH = "../latest_frame.jpg"`
- Implement `GET /api/camera-feed` — serves `../latest_frame.jpg` as `image/jpeg` with no-cache headers, returns 404 if file doesn't exist
- Implement `GET /api/fill-levels` — returns latest fill levels enriched with product info and status (`ok`/`low`/`critical`)
- Implement `GET /api/orders` — returns all orders from `get_all_orders()`
- Implement `GET /api/products` — returns product master data from `load_products()`
- Status logic: `critical` if fill <= 5, `low` if fill <= threshold, `ok` otherwise
**Acceptance Criteria:**
- `uvicorn api:app --port 8000` starts without error
- `http://localhost:8000/docs` shows Swagger UI with all 4 endpoints
- `curl http://localhost:8000/api/products` returns JSON array with 2 products

---

## TODO 7 — DONE
**Goal:** Implement `main.py`
**Tasks:**
- Import `uvicorn`, `threading`, `time`, `datetime`, and all functions from modules
- `init_orders_table()` on startup
- `load_products()` on startup
- Implement `reorder_loop(products)` — runs forever in background thread:
  1. Read latest fill levels from DB
  2. For each tag: look up product, check threshold
  3. If fill > threshold → `mark_delivered(tag_id)`
  4. If fill <= threshold AND no pending order → generate CSV, create order, send email
  5. If fill <= threshold AND pending order → skip (log message)
  6. Sleep 10 seconds
  7. Catch all exceptions, log, continue (never crash)
- Start reorder loop as daemon thread
- Start uvicorn on `0.0.0.0:8000` in main thread
**Acceptance Criteria:**
- `python main.py` starts both the reorder loop and the API server
- Console shows "Reorder loop started." and "Starting API server on http://localhost:8000"
- API is reachable at `http://localhost:8000/docs`

---

## TODO 8 — DONE
**Goal:** Verify reorder flow end-to-end
**Tasks:**
- Ensure Person 1's pipeline has written fill level data to `../shelf.db` (or manually insert test data: `INSERT INTO fill_levels (tag_id, fill_level, timestamp) VALUES (0, 15, '2026-01-01T00:00:00');`)
- Run `python main.py`
- Wait for the reorder loop to trigger (within 10 seconds)
**Acceptance Criteria:**
- Console shows ordering message for the low-fill product
- A CSV file is created in `./orders_csv/` with correct SAP B1 format
- A row is inserted into the `orders` table with `status='pending'`
- Email is sent (or warning logged if `RESEND_API_KEY` is not set)
- On next loop cycle, the same product is skipped ("already ordered, skipping.")

---

## TODO 9 — DONE
**Goal:** Verify dedup and mark-delivered logic
**Tasks:**
- With a pending order in the DB, insert a new fill level above the threshold: `INSERT INTO fill_levels (tag_id, fill_level, timestamp) VALUES (0, 80, '2026-01-01T01:00:00');`
- Wait for the reorder loop to process
- Then insert a fill level below threshold again: `INSERT INTO fill_levels (tag_id, fill_level, timestamp) VALUES (0, 10, '2026-01-01T02:00:00');`
- Wait for the reorder loop to process
**Acceptance Criteria:**
- After fill goes above threshold: pending order is marked `delivered` in DB
- After fill drops below threshold again: a NEW order is created (not blocked by the old delivered one)
- Two separate CSV files exist in `./orders_csv/`

---

## TODO 10 — LOCKED
**Goal:** Verify API responses
**Tasks:**
- With the backend running and some data in the DB, test all 4 endpoints:
  - `curl http://localhost:8000/api/fill-levels`
  - `curl http://localhost:8000/api/orders`
  - `curl http://localhost:8000/api/products`
  - `curl http://localhost:8000/api/camera-feed -o test_frame.jpg` (if `latest_frame.jpg` exists)
**Acceptance Criteria:**
- `/api/fill-levels` returns JSON array with `status` field per product (`ok`, `low`, or `critical`)
- `/api/orders` returns JSON array sorted by `created_at` descending
- `/api/products` returns JSON array with exactly 2 products
- `/api/camera-feed` returns a JPEG image (or 404 if no frame exists)

---

## TODO 11 — LOCKED
**Goal:** Stability test
**Tasks:**
- Run `python main.py` for 10+ minutes
- Periodically insert test fill-level data to simulate Person 1's pipeline
**Acceptance Criteria:**
- No crashes or unhandled exceptions during the entire run
- API remains responsive throughout
- Reorder loop correctly processes new data each cycle
- No duplicate orders for the same product while a pending order exists

---

## TODO 12 — LOCKED
**Goal:** Final handoff
**Tasks:**
- Verify `backend/` contains exactly 7 files: `main.py`, `config.py`, `orders.py`, `csv_gen.py`, `mailer.py`, `api.py`, `requirements.txt` (no `__pycache__`, no extras, no `products.json`)
- Verify `../.env` contains all required variables
- Verify `../shelf.db` `orders` table is created automatically on first run
- Verify `./orders_csv/` is created automatically when first order triggers
- Verify `pip install -r requirements.txt` works on fresh Python 3.10+
- Verify `python main.py` starts both reorder loop and API server
- Verify `http://localhost:8000/docs` shows all 4 endpoints
**Acceptance Criteria:**
- All 7 checks pass
- Person 2's backend is ready for integration with Person 3's dashboard
