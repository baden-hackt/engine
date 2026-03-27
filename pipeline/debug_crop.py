import cv2

from camera import init_camera, capture_frame
from tags import detect_tags, get_crop_bounds


def main():
    cap = init_camera()
    frame = capture_frame(cap)
    cap.release()

    if frame is None:
        print("ERROR: Camera read failed.")
        return

    frame = cv2.rotate(frame, cv2.ROTATE_180)

    detections = detect_tags(frame)
    print(f"detections: {len(detections)}")

    debug = frame.copy()

    for detection in detections:
        corners_i = detection.corners.astype(int)
        for i in range(4):
            cv2.line(debug, tuple(corners_i[i]), tuple(corners_i[(i + 1) % 4]), (0, 255, 0), 2)

        bounds = get_crop_bounds(frame, detection)
        if bounds is not None:
            x1, y1, x2, y2 = bounds
            cv2.rectangle(debug, (x1, y1), (x2, y2), (0, 0, 255), 2)

        cv2.putText(
            debug,
            f"ID:{detection.tag_id}",
            (int(detection.center[0]) - 20, int(detection.center[1]) - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )

    cv2.imwrite("../crop_debug.jpg", debug)
    print("saved ../crop_debug.jpg")


if __name__ == "__main__":
    main()
