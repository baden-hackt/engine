import os
import tempfile
import unittest
from unittest import mock

import numpy as np

import camera
import db
import tags


class FakeDetection:
    def __init__(self, tag_id, center, corners):
        self.tag_id = tag_id
        self.center = np.array(center, dtype=np.float32)
        self.corners = np.array(corners, dtype=np.float32)


class CameraTests(unittest.TestCase):
    def test_has_changed_returns_false_for_identical_frames(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.assertFalse(camera.has_changed(frame, frame.copy()))

    def test_has_changed_returns_true_when_difference_exceeds_threshold(self):
        previous = np.zeros((100, 100, 3), dtype=np.uint8)
        current = previous.copy()
        current[:20, :20] = 255
        self.assertTrue(camera.has_changed(current, previous, threshold=0.01))


class CropTests(unittest.TestCase):
    def setUp(self):
        self.frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.detection = FakeDetection(
            tag_id=0,
            center=(640, 620),
            corners=[
                (600, 600),
                (680, 600),
                (680, 680),
                (600, 680),
            ],
        )

    def test_get_crop_bounds_uses_database_settings(self):
        with mock.patch.object(tags, "get_crop_settings", return_value=(300, 400, 10, -20)):
            bounds = tags.get_crop_bounds(self.frame, self.detection)

        self.assertEqual(bounds, (500, 180, 800, 580))

    def test_get_crop_bounds_returns_none_when_result_is_too_small(self):
        with mock.patch.object(tags, "get_crop_settings", return_value=(40, 40, 0, 0)):
            bounds = tags.get_crop_bounds(self.frame, self.detection)

        self.assertIsNone(bounds)

    def test_crop_slot_returns_expected_shape(self):
        with mock.patch.object(tags, "get_crop_settings", return_value=(300, 400, 0, 0)):
            crop = tags.crop_slot(self.frame, self.detection)

        self.assertIsNotNone(crop)
        self.assertEqual(crop.shape, (400, 300, 3))


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.tempdir.name, "test_shelf.db")
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def test_init_db_seeds_default_crop_settings(self):
        self.assertEqual(
            db.get_crop_settings(0),
            (db.DEFAULT_CROP_WIDTH, db.DEFAULT_CROP_HEIGHT, db.DEFAULT_OFFSET_X, db.DEFAULT_OFFSET_Y),
        )
        self.assertEqual(
            db.get_crop_settings(1),
            (db.DEFAULT_CROP_WIDTH, db.DEFAULT_CROP_HEIGHT, db.DEFAULT_OFFSET_X, db.DEFAULT_OFFSET_Y),
        )

    def test_upsert_crop_settings_updates_row(self):
        db.upsert_crop_settings(1, 420, 360, 15, -10)
        self.assertEqual(db.get_crop_settings(1), (420, 360, 15, -10))


if __name__ == "__main__":
    unittest.main()
