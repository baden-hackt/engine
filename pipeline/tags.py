from pupil_apriltags import Detector
import cv2
import numpy as np

from db import get_crop_settings


detector = Detector(families="tag36h11")


def detect_tags(frame: np.ndarray) -> list:
    """
    Convert frame to grayscale.
    Run detector.detect() on it.
    Return the list of detections.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return detector.detect(gray)


def get_crop_bounds(frame: np.ndarray, detection) -> tuple[int, int, int, int] | None:
    crop_w, crop_h, offset_x, offset_y = get_crop_settings(detection.tag_id)
    tag_center_x = int(detection.center[0]) + offset_x
    tag_top_y = int(min(c[1] for c in detection.corners)) + offset_y

    x1 = max(0, tag_center_x - crop_w // 2)
    x2 = min(frame.shape[1], tag_center_x + crop_w // 2)
    y1 = max(0, tag_top_y - crop_h)
    y2 = min(frame.shape[0], tag_top_y)

    if (y2 - y1) < 50 or (x2 - x1) < 50:
        return None

    return x1, y1, x2, y2


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
    bounds = get_crop_bounds(frame, detection)
    if bounds is None:
        return None

    x1, y1, x2, y2 = bounds
    return frame[y1:y2, x1:x2]
