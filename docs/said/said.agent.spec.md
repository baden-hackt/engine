# AGENT INSTRUCTIONS — Camera + Vision Pipeline

You are building the camera and vision pipeline for a hackathon project. Follow every instruction exactly. Do not deviate, improvise, or add features not listed here.

---

## OBJECTIVE

Build a Python application that:
1. Captures frames from a webcam
2. Detects AprilTags in each frame
3. Crops the shelf region above each tag
4. Sends each crop to the GPT-4o Vision API to estimate fill level (0–100%)
5. Writes results to a shared SQLite database

The application runs in a loop every 5 seconds. It runs on the same machine as the backend (Person 2). The only interface between this pipeline and the backend is the SQLite database file at `../shelf.db` (one level up, at the project root).

---

## FULL PROJECT DIRECTORY

Everything lives in one directory. This is the layout for ALL three people:

```
project/
├── docs/
│   ├── said/
│   │   ├── spec.md        ← YOUR SPEC (this document)
│   │   └── todo.md        ← YOUR TODO LIST
│   └── dijar/
│       ├── spec.md        ← Person 2's spec — DO NOT TOUCH
│       └── todo.md        ← Person 2's todo — DO NOT TOUCH
├── pipeline/          ← Person 1 (Said) — YOU BUILD THIS
│   ├── main.py
│   ├── camera.py
│   ├── tags.py
│   ├── vision.py
│   ├── db.py
│   └── requirements.txt
├── backend/           ← Person 2 (Dijar) — DO NOT TOUCH
│   └── ...
├── .env               ← SHARED SECRETS (project root, used by both Person 1 and 2)
├── shelf.db           ← SHARED DATABASE (lives at project root)
└── latest_frame.jpg   ← SHARED FRAME (overwritten every cycle by Person 1)
```

The dashboard (Person 3 — Timo) is a separate Next.js app hosted on Vercel. It does NOT live in this repo. It connects to Person 2's API at `http://<laptop-ip>:8000/api/*` over the local network. Person 1 does not interact with the dashboard directly — the only connection is through `shelf.db` and `latest_frame.jpg`, which Person 2's API serves to the dashboard.

**Database path from your code:** `../shelf.db` (relative to `pipeline/`)
**Frame output path from your code:** `../latest_frame.jpg` (relative to `pipeline/`)

---

## PROJECT STRUCTURE

Create exactly these files:

```
pipeline/
├── main.py
├── camera.py
├── tags.py
├── vision.py
├── db.py
└── requirements.txt
```

Do not create any other files. Do not create a config file. Do not create a README. Do not create tests.

---

## FILE: requirements.txt

```
opencv-python>=4.13.0
pupil-apriltags>=1.0.4
openai>=2.30.0
python-dotenv>=1.0.0
Pillow>=10.0.0
numpy
```

---

## FILE: db.py

This module handles all SQLite operations.

### Database path

Hardcode the database path as `../shelf.db`. Do not make this configurable.

### Tables

Create both tables on module import if they do not exist.

**Table `fill_levels`:**

```sql
CREATE TABLE IF NOT EXISTS fill_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_id INTEGER NOT NULL,
    fill_level INTEGER NOT NULL,
    timestamp TEXT NOT NULL
);
```

**Table `scan_log`:**

```sql
CREATE TABLE IF NOT EXISTS scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    tags_detected INTEGER NOT NULL,
    change_detected INTEGER NOT NULL
);
```

### Functions to implement

```python
def init_db() -> None:
    """Create tables if they don't exist. Call once at startup."""

def write_fill_level(tag_id: int, fill_level: int) -> None:
    """Insert one row into fill_levels. Timestamp is datetime.now().isoformat()."""

def write_scan_log(tags_detected: int, change_detected: bool) -> None:
    """Insert one row into scan_log. change_detected stored as 1 or 0."""
```

Use a new `sqlite3.connect('../shelf.db')` connection per function call. Do not keep a persistent connection. Close the connection after each call.

---

## FILE: camera.py

This module handles webcam capture and change detection.

### Camera initialization

```python
import cv2

def init_camera() -> cv2.VideoCapture:
    """
    Open webcam at index 0.
    Set resolution to 1280x720.
    If camera fails to open, print "ERROR: Cannot open camera" and call sys.exit(1).
    Return the VideoCapture object.
    """
```

Set these properties after opening:
```python
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
```

### Frame capture

```python
def capture_frame(cap: cv2.VideoCapture) -> np.ndarray | None:
    """
    Read one frame. If read fails, retry up to 5 times with 1 second sleep between retries.
    If all retries fail, return None.
    """
```

### Change detection

```python
def has_changed(current_frame: np.ndarray, previous_frame: np.ndarray, threshold: float = 0.01) -> bool:
    """
    Convert both frames to grayscale.
    Compute absolute difference.
    Apply binary threshold at 30.
    Count non-zero pixels.
    If ratio of non-zero pixels to total pixels >= threshold, return True.
    Otherwise return False.
    """
```

Implementation:
```python
gray_current = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
gray_previous = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
diff = cv2.absdiff(gray_current, gray_previous)
_, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
change_ratio = cv2.countNonZero(thresh) / (current_frame.shape[0] * current_frame.shape[1])
return change_ratio >= threshold
```

---

## FILE: tags.py

This module handles AprilTag detection and crop region extraction.

### Tag detection

```python
from pupil_apriltags import Detector
import cv2
import numpy as np

detector = Detector(families="tag36h11")

def detect_tags(frame: np.ndarray) -> list:
    """
    Convert frame to grayscale.
    Run detector.detect() on it.
    Return the list of detections.
    """
```

Implementation:
```python
def detect_tags(frame: np.ndarray) -> list:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return detector.detect(gray)
```

The detector must use family `tag36h11`. No other family. Initialize the detector once at module level, not per call. The `detect()` method MUST receive a grayscale uint8 numpy array — passing a BGR color frame will produce incorrect results.

### Crop region extraction

```python
def crop_slot(frame: np.ndarray, detection) -> np.ndarray | None:
    """
    Given a frame and a single AprilTag detection, return the cropped image
    of the shelf slot above the tag.

    Crop definition:
    - Compute tag_width as the distance between corner[0] and corner[1]
    - crop_width = tag_width * 3
    - crop_height = tag_width * 4
    - Center the crop horizontally on the tag center
    - The crop extends upward from the top edge of the tag

    Clamp all coordinates to frame boundaries.
    If the resulting crop is smaller than 50x50 pixels, return None.
    """
```

Implementation:
```python
def crop_slot(frame: np.ndarray, detection) -> np.ndarray | None:
    corners = detection.corners
    tag_width = int(np.linalg.norm(corners[1] - corners[0]))
    tag_center_x = int(detection.center[0])
    tag_top_y = int(min(c[1] for c in corners))

    crop_w = tag_width * 3
    crop_h = tag_width * 4

    x1 = max(0, tag_center_x - crop_w // 2)
    x2 = min(frame.shape[1], tag_center_x + crop_w // 2)
    y1 = max(0, tag_top_y - crop_h)
    y2 = tag_top_y

    crop = frame[y1:y2, x1:x2]

    if crop.shape[0] < 50 or crop.shape[1] < 50:
        return None

    return crop
```

---

## FILE: vision.py

This module handles GPT-4o Vision API calls.

### Fill level estimation

```python
import openai
import base64
import cv2
import numpy as np
from dotenv import load_dotenv

load_dotenv("../.env")

client = openai.OpenAI()  # reads OPENAI_API_KEY from env

def estimate_fill_level(crop: np.ndarray) -> int | None:
    """
    Encode the crop as JPEG.
    Send it to GPT-4o's vision API.
    Parse the response as an integer.
    Return the integer if valid (0-100), otherwise return None.
    """
```

Implementation:

```python
def estimate_fill_level(crop: np.ndarray) -> int | None:
    _, buffer = cv2.imencode('.jpg', crop)
    image_b64 = base64.standard_b64encode(buffer).decode('utf-8')

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=16,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Look at this shelf compartment. Estimate how full it is as a percentage from 0 to 100, where 0 is completely empty and 100 is completely full. Respond with ONLY a single integer number, nothing else."
                        }
                    ]
                }
            ]
        )

        text = response.choices[0].message.content.strip()
        value = int(text)

        if value < 0:
            value = 0
        if value > 100:
            value = 100

        return value

    except Exception as e:
        print(f"WARNING: Vision API error: {e}")
        return None
```

### Exact parameters — do not change

- **Model:** `gpt-4o`
- **max_tokens:** `16`
- **Prompt:** Exactly as written above. Do not modify the prompt text.
- **Image format:** JPEG, sent as base64 data URL
- **Response parsing:** `response.choices[0].message.content.strip()`

---

## FILE: main.py

This is the entry point. It runs the main loop.

### Imports

```python
import sys
import time
import cv2
from datetime import datetime

from camera import init_camera, capture_frame, has_changed
from tags import detect_tags, crop_slot
from vision import estimate_fill_level
from db import init_db, write_fill_level, write_scan_log
```

### Main function

Implement exactly this logic:

```python
def main():
    init_db()
    cap = init_camera()
    previous_frame = None
    SCAN_INTERVAL = 5  # seconds
    FRAME_OUTPUT_PATH = "../latest_frame.jpg"

    print("Pipeline started. Press Ctrl+C to stop.")

    while True:
        try:
            frame = capture_frame(cap)
            if frame is None:
                print("ERROR: Camera read failed after retries. Exiting.")
                sys.exit(1)

            # Rotate frame 180 degrees if camera is mounted upside down
            frame = cv2.rotate(frame, cv2.ROTATE_180)

            # Change detection (skip on first frame)
            if previous_frame is not None:
                if not has_changed(frame, previous_frame):
                    print(f"[{datetime.now().isoformat()}] No change detected, skipping.")
                    write_scan_log(tags_detected=0, change_detected=False)
                    time.sleep(SCAN_INTERVAL)
                    continue

            # Detect AprilTags
            detections = detect_tags(frame)
            if len(detections) == 0:
                print(f"[{datetime.now().isoformat()}] WARNING: No AprilTags detected.")
                write_scan_log(tags_detected=0, change_detected=True)
                previous_frame = frame
                time.sleep(SCAN_INTERVAL)
                continue

            print(f"[{datetime.now().isoformat()}] Detected {len(detections)} tags.")

            # Draw overlays on a copy of the frame for the dashboard
            display_frame = frame.copy()

            # Process each tag
            for detection in detections:
                tag_id = detection.tag_id

                # Draw bounding box around tag
                corners = detection.corners.astype(int)
                for i in range(4):
                    cv2.line(display_frame, tuple(corners[i]), tuple(corners[(i+1) % 4]), (0, 255, 0), 2)

                # Draw tag ID label
                center = detection.center
                cv2.putText(display_frame, f"ID:{tag_id}", (int(center[0]) - 20, int(center[1]) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                crop = crop_slot(frame, detection)
                if crop is None:
                    print(f"  Tag {tag_id}: crop too small, skipping.")
                    continue

                fill_level = estimate_fill_level(crop)
                if fill_level is None:
                    print(f"  Tag {tag_id}: API call failed, skipping.")
                    continue

                write_fill_level(tag_id, fill_level)
                print(f"  Tag {tag_id}: fill level = {fill_level}%")

                # Draw fill level on display frame
                cv2.putText(display_frame, f"{fill_level}%", (int(center[0]) - 20, int(center[1]) + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            # Save annotated frame for dashboard
            cv2.imwrite(FRAME_OUTPUT_PATH, display_frame)

            write_scan_log(tags_detected=len(detections), change_detected=True)
            previous_frame = frame
            time.sleep(SCAN_INTERVAL)

        except KeyboardInterrupt:
            print("\nStopping pipeline.")
            cap.release()
            sys.exit(0)
        except Exception as e:
            print(f"ERROR: Unhandled exception: {e}")
            time.sleep(SCAN_INTERVAL)
            continue


if __name__ == "__main__":
    main()
```

### Critical rules for main.py

- The outer `while True` loop must NEVER crash. Every exception is caught, logged, and the loop continues.
- The only exception that exits is `KeyboardInterrupt`.
- `previous_frame` is set to `frame` ONLY after a successful processing cycle (after tag detection), not after a skipped cycle.
- `cap.release()` is called on exit.
- The dashboard overlay should show both the green AprilTag bounds and the red projected compartment cuboid used to derive the GPT crop.

---

## ENVIRONMENT VARIABLES

All secrets are stored in a shared `.env` file at the project root (`../.env` from `pipeline/`). The `vision.py` module loads it via `python-dotenv`.

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

Person 1 only uses `OPENAI_API_KEY`. Everything else is for Person 2. Do not create a separate `.env` inside `pipeline/`.

No command-line arguments. No other config files.

---

## HOW TO RUN

```bash
cd pipeline
pip install -r requirements.txt
python main.py
```

Make sure `../.env` exists with `OPENAI_API_KEY` set before running.

---

## DATABASE CONTRACT WITH PERSON 2

Person 2 (backend/reorder logic) reads from the same `../shelf.db` file. The contract:

- Person 1 (this pipeline) ONLY writes to `fill_levels` and `scan_log`.
- Person 1 NEVER reads from any table that Person 2 creates.
- Person 1 NEVER deletes or updates rows. Insert only.
- Person 2 reads the latest `fill_level` per `tag_id` using:

```sql
SELECT tag_id, fill_level, timestamp
FROM fill_levels
WHERE id IN (
    SELECT MAX(id) FROM fill_levels GROUP BY tag_id
);
```

Person 1 does not need to know or care about this query. Just keep inserting rows.

---

## WHAT THIS APPLICATION DOES NOT DO

Do not implement any of the following. They are handled by other people.

- Product/supplier mapping (Person 2)
- Reorder threshold logic (Person 2)
- Order deduplication (Person 2)
- CSV generation (Person 2)
- Email sending (Person 2)
- Dashboard / web frontend (Person 3)
- AprilTag printing or shelf setup (Person 3)

---

## CONSTRAINTS

- Do not add a web server or API endpoints.
- Do not add a GUI or display window. No `cv2.imshow()`.
- Do not save images to disk.
- Do not add logging to a file. Print to stdout only.
- Do not add command-line argument parsing.
- Do not add type hints beyond what is shown above.
- Do not add docstrings beyond what is shown above.
- Do not add unit tests.
- Do not create a Dockerfile or docker-compose.
- Do not use asyncio or threading.
- Do not use any libraries not listed in requirements.txt.
