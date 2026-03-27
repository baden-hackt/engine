import sys
import time

import cv2
import numpy as np


def init_camera() -> cv2.VideoCapture:
    """
    Open webcam at index 0.
    Set resolution to 1280x720.
    If camera fails to open, print "ERROR: Cannot open camera" and call sys.exit(1).
    Return the VideoCapture object.
    """
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print("ERROR: Cannot open camera")
        sys.exit(1)

    return cap


def capture_frame(cap: cv2.VideoCapture) -> np.ndarray | None:
    """
    Read one frame. If read fails, retry up to 5 times with 1 second sleep between retries.
    If all retries fail, return None.
    """
    for _ in range(5):
        ok, frame = cap.read()
        if ok:
            return frame
        time.sleep(1)
    return None


def has_changed(current_frame: np.ndarray, previous_frame: np.ndarray, threshold: float = 0.01) -> bool:
    """
    Convert both frames to grayscale.
    Compute absolute difference.
    Apply binary threshold at 30.
    Count non-zero pixels.
    If ratio of non-zero pixels to total pixels >= threshold, return True.
    Otherwise return False.
    """
    gray_current = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    gray_previous = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(gray_current, gray_previous)
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    change_ratio = cv2.countNonZero(thresh) / (current_frame.shape[0] * current_frame.shape[1])
    return change_ratio >= threshold
