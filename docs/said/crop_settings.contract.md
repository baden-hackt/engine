# Crop Settings Contract

This document defines how the backend and dashboard should read and update crop rectangle settings for the vision pipeline.

## Table

The shared SQLite table is:

```sql
CREATE TABLE IF NOT EXISTS crop_settings (
    tag_id INTEGER PRIMARY KEY,
    crop_width INTEGER NOT NULL,
    crop_height INTEGER NOT NULL,
    offset_x INTEGER NOT NULL,
    offset_y INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
```

## Purpose

- Store per-tag crop rectangle settings for the vision pipeline.
- Let the backend expose these values through an API.
- Let the dashboard tune crop rectangles without editing Python files.

## Ownership

- Person 1 reads `crop_settings` in `crop_slot()`.
- Person 1 seeds default rows for tag IDs `0` and `1` if they do not exist.
- Person 1 does not delete rows from `crop_settings`.
- Person 2 may expose `crop_settings` through the backend API.
- Person 2 may update rows in `crop_settings`.

## Field Meanings

- `tag_id`: AprilTag ID for the compartment.
- `crop_width`: crop width in pixels.
- `crop_height`: crop height in pixels.
- `offset_x`: horizontal pixel offset added to the tag center before cropping.
- `offset_y`: vertical pixel offset added to the tag top edge before cropping.
- `updated_at`: ISO timestamp of the latest settings change.

## Default Rows

The pipeline seeds defaults for tag IDs `0` and `1` on startup if rows do not exist:

- `crop_width = 336`
- `crop_height = 448`
- `offset_x = 0`
- `offset_y = 0`

## Read Query

```sql
SELECT tag_id, crop_width, crop_height, offset_x, offset_y, updated_at
FROM crop_settings
ORDER BY tag_id;
```

## Update Query

```sql
INSERT INTO crop_settings (tag_id, crop_width, crop_height, offset_x, offset_y, updated_at)
VALUES (0, 336, 448, 0, 0, '2026-03-27T18:30:00')
ON CONFLICT(tag_id) DO UPDATE SET
    crop_width = excluded.crop_width,
    crop_height = excluded.crop_height,
    offset_x = excluded.offset_x,
    offset_y = excluded.offset_y,
    updated_at = excluded.updated_at;
```

## Backend API Guidance

- Expose one row per `tag_id`.
- Validate all numeric values as integers.
- Keep `crop_width` and `crop_height` greater than or equal to `50`.
- Let the dashboard edit `crop_width`, `crop_height`, `offset_x`, and `offset_y`.
- The pipeline picks up new values automatically on the next scan because it reads `crop_settings` from SQLite for each crop.
