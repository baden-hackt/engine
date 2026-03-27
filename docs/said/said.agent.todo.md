# Said — Agent TODO

> **Spec:** Read `/docs/said/said.agent.spec.md` before starting any TODO.
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
- Create `pipeline/` directory with empty files: `main.py`, `camera.py`, `tags.py`, `vision.py`, `db.py`, `requirements.txt`
- Write `requirements.txt` contents exactly as specified in spec
- Run `pip install -r requirements.txt`
- Create `../.env` at project root if it doesn't exist, and ensure it contains `OPENAI_API_KEY=sk-...`. Do NOT remove any other variables that may already be in the file.
**Acceptance Criteria:**
- `pipeline/` exists with exactly 6 files
- `import cv2`, `import pupil_apriltags`, `import openai`, `from dotenv import load_dotenv` all succeed
- `../.env` exists and contains `OPENAI_API_KEY`

---

## TODO 2 — DONE
**Goal:** Implement `db.py`
**Tasks:**
- Set `DB_PATH = "../shelf.db"`
- Implement `init_db()` — creates `fill_levels` and `scan_log` tables if they don't exist
- Implement `write_fill_level(tag_id, fill_level)` — inserts one row with `datetime.now().isoformat()` timestamp
- Implement `write_scan_log(tags_detected, change_detected)` — inserts one row, `change_detected` stored as 1 or 0
- Use a new `sqlite3.connect()` per function call, close after each call
**Acceptance Criteria:**
- `python -c "from db import init_db; init_db()"` creates `../shelf.db` with both tables
- `python -c "from db import write_fill_level; write_fill_level(0, 75)"` inserts a row without error

---

## TODO 3 — DONE
**Goal:** Implement `camera.py`
**Tasks:**
- Implement `init_camera()` — opens webcam index 0, sets 1280x720, calls `sys.exit(1)` if camera fails
- Implement `capture_frame(cap)` — reads one frame, retries up to 5 times with 1s sleep, returns None if all fail
- Implement `has_changed(current_frame, previous_frame, threshold=0.01)` — grayscale diff, binary threshold at 30, returns True if change ratio >= threshold
**Acceptance Criteria:**
- `cap = init_camera(); f = capture_frame(cap); print(f.shape); cap.release()` prints `(720, 1280, 3)`

---

## TODO 4 — DONE
**Goal:** Implement `tags.py`
**Tasks:**
- Create module-level detector: `Detector(families="tag36h11")`
- Implement `detect_tags(frame)` — converts frame to grayscale, runs `detector.detect(gray)`, returns list
- Implement `crop_slot(frame, detection)` — computes crop region (3x tag width wide, 4x tag width tall, above the tag), clamps to frame boundaries, returns None if crop < 50x50 pixels
**Acceptance Criteria:**
- With a printed AprilTag (tag36h11) visible to the camera, `detect_tags(frame)` returns a non-empty list with valid `tag_id` and `corners`
- `crop_slot(frame, detection)` returns a numpy array of reasonable size

---

## TODO 5 — DONE
**Goal:** Implement `vision.py`
**Tasks:**
- Call `load_dotenv("../.env")` at module level
- Create `client = openai.OpenAI()` at module level
- Implement `estimate_fill_level(crop)` — encodes crop as JPEG, base64 encodes, sends to GPT-4o with the exact prompt from the spec, parses response as int, clamps to 0–100, returns None on any error
- Model: `gpt-4o`, max_tokens: `16`
**Acceptance Criteria:**
- With a valid API key, `estimate_fill_level(some_image)` returns an integer between 0 and 100
- With an invalid API key, it prints a warning and returns None (does not crash)

---

## TODO 6 — LOCKED
**Goal:** Implement `main.py`
**Tasks:**
- Import `sys`, `time`, `cv2`, `datetime`, and all functions from the 4 modules
- Call `init_db()` and `init_camera()` on startup
- Set `SCAN_INTERVAL = 5` and `FRAME_OUTPUT_PATH = "../latest_frame.jpg"`
- Implement the main loop exactly as specified:
  1. Capture frame (exit if None)
  2. Change detection (skip if no change, except first frame)
  3. Detect AprilTags (skip if none found)
  4. Copy frame for display overlays
  5. For each detection: draw green bounding box + `ID:X` label, crop slot, call API, write fill level to DB, draw `X%` on display frame
  6. Save display frame to `../latest_frame.jpg`
  7. Write scan log
  8. Sleep 5 seconds
- `KeyboardInterrupt` → release camera, exit
- All other exceptions → log, continue (never crash the loop)
**Acceptance Criteria:**
- `python main.py` starts the loop and prints log messages to stdout
- `../shelf.db` contains rows in `fill_levels` and `scan_log`
- `../latest_frame.jpg` exists with green bounding boxes and fill % overlays

---

## TODO 7 — LOCKED
**Goal:** Verify database output
**Tasks:**
- Run the pipeline for at least 2 scan cycles
- Query `sqlite3 ../shelf.db "SELECT * FROM fill_levels ORDER BY id DESC LIMIT 5;"`
- Query `sqlite3 ../shelf.db "SELECT * FROM scan_log ORDER BY id DESC LIMIT 5;"`
**Acceptance Criteria:**
- `fill_levels` rows have valid `tag_id` (0 or 1), `fill_level` (0–100), and ISO timestamp
- `scan_log` rows have correct `tags_detected` count and `change_detected` values

---

## TODO 8 — LOCKED
**Goal:** Verify frame output
**Tasks:**
- With the pipeline running, open `../latest_frame.jpg`
- Visually confirm the annotated frame
**Acceptance Criteria:**
- Image shows the camera view of the shelf
- Green bounding boxes around detected AprilTags
- Tag ID labels (`ID:0`, `ID:1`) visible near each tag
- Fill level percentages (`75%`) visible near each tag

---

## TODO 9 — LOCKED
**Goal:** Stability test
**Tasks:**
- Run `python main.py` for 10+ minutes without touching the shelf
- Then interact with the shelf — add and remove items
**Acceptance Criteria:**
- No crashes or unhandled exceptions during the entire run
- Change detection skips idle cycles ("No change detected, skipping.")
- Fill levels update in the database when items are added/removed
- `latest_frame.jpg` updates after shelf changes

---

## TODO 10 — LOCKED
**Goal:** Error handling test
**Tasks:**
- Test camera disconnect: unplug webcam while running
- Test no tags visible: cover or remove all AprilTags
- Test API failure: set `OPENAI_API_KEY` to an invalid value, restart pipeline
**Acceptance Criteria:**
- Camera disconnect: pipeline retries and exits gracefully (no hang)
- No tags visible: logs warning and continues (no crash)
- API failure: logs warning per tag and continues (no crash), `scan_log` rows still written

---

## TODO 11 — LOCKED
**Goal:** Final handoff
**Tasks:**
- Verify `pipeline/` contains exactly 6 files (no `__pycache__`, no extras)
- Verify `../.env` exists with `OPENAI_API_KEY`
- Verify `../shelf.db` is created automatically on first run
- Verify `../latest_frame.jpg` is created on first successful scan
- Verify `pip install -r requirements.txt` works on fresh Python 3.10+
- Verify `python main.py` starts without error
**Acceptance Criteria:**
- All 6 checks pass
- Person 1's pipeline is ready for integration with Person 2's backend
