import sys
import time
import cv2
from datetime import datetime

from camera import init_camera, capture_frame, has_changed
from tags import detect_tags, crop_slot, get_crop_bounds
from vision import estimate_fill_level
from db import init_db, write_fill_level, write_scan_log


def main():
    init_db()
    cap = init_camera()
    previous_frame = None
    previous_crops = {}
    last_fill_levels = {}
    CROP_CHANGE_THRESHOLD = 0.003
    SCAN_INTERVAL = 1  # seconds
    FRAME_OUTPUT_PATH = "../latest_frame.jpg"

    print("Pipeline started. Press Ctrl+C to stop.")

    while True:
        try:
            frame = capture_frame(cap)
            if frame is None:
                print("ERROR: Camera read failed after retries. Exiting.")
                sys.exit(1)

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
                    cv2.line(display_frame, tuple(corners[i]), tuple(corners[(i + 1) % 4]), (0, 255, 0), 2)

                # Draw tag ID label
                center = detection.center
                cv2.putText(display_frame, f"ID:{tag_id}", (int(center[0]) - 20, int(center[1]) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                bounds = get_crop_bounds(frame, detection)
                if bounds is not None:
                    x1, y1, x2, y2 = bounds
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

                if tag_id in last_fill_levels:
                    cv2.putText(display_frame, f"{last_fill_levels[tag_id]}%", (int(center[0]) - 20, int(center[1]) + 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            # Save annotated frame for dashboard immediately after detection
            cv2.imwrite(FRAME_OUTPUT_PATH, display_frame)

            # Process each tag
            for detection in detections:
                tag_id = detection.tag_id
                center = detection.center

                crop = crop_slot(frame, detection)
                if crop is None:
                    print(f"  Tag {tag_id}: crop too small, skipping.")
                    continue

                crop_changed = True
                if tag_id in previous_crops:
                    crop_changed = has_changed(crop, previous_crops[tag_id], threshold=CROP_CHANGE_THRESHOLD)

                previous_crops[tag_id] = crop

                if crop_changed or tag_id not in last_fill_levels:
                    fill_level = estimate_fill_level(crop)
                    if fill_level is None:
                        print(f"  Tag {tag_id}: API call failed, skipping.")
                        continue

                    last_fill_levels[tag_id] = fill_level
                    write_fill_level(tag_id, fill_level)
                    print(f"  Tag {tag_id}: fill level = {fill_level}%")
                else:
                    fill_level = last_fill_levels[tag_id]
                    print(f"  Tag {tag_id}: unchanged, keeping {fill_level}%")

                # Draw fill level on display frame
                cv2.putText(display_frame, f"{fill_level}%", (int(center[0]) - 20, int(center[1]) + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            # Save annotated frame again with the latest fill values
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
