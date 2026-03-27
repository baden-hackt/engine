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
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return detector.detect(gray)


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
