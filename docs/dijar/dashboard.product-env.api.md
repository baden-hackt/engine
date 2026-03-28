# Dashboard API - Product Config (DB-backed)

This document describes the API endpoints for reading and updating all product-related settings.

Storage model:

- Product settings are stored in SQLite table `products` in `../shelf.db`.
- API keys and secrets remain in `.env`.

All endpoints below are prefixed with `/api`.

## Supported Product IDs

Only two product tag IDs are supported:

- `0`
- `1`

## Editable Fields

For each product, these suffix-style keys are supported:

- `TAG_ID`
- `ID`
- `NAME`
- `SUPPLIER_NAME`
- `SUPPLIER_EMAIL`
- `THRESHOLD`
- `REORDER_THRESHOLD`
- `REORDER_QTY`
- `REORDER_QUANTITY`
- `UNIT`

Notes:

- `THRESHOLD` and `REORDER_THRESHOLD` are kept in sync automatically.
- `REORDER_QTY` and `REORDER_QUANTITY` are kept in sync automatically.
- Numeric fields must be valid integers.

## 1) Get all product config values

### Request

`GET /api/product-env`

### Response (200)

```json
[
  {
    "tag_id": 0,
    "values": {
      "ID": "MAT-001",
      "NAME": "Schrauben M8x30",
      "REORDER_QTY": "100",
      "REORDER_QUANTITY": "100",
      "REORDER_THRESHOLD": "20",
      "SUPPLIER_EMAIL": "demo@example.com",
      "SUPPLIER_NAME": "Demo Supplier AG",
      "TAG_ID": "0",
      "THRESHOLD": "20",
      "UNIT": "Stuck"
    },
    "product": {
      "tag_id": 0,
      "product_id": "MAT-001",
      "product_name": "Schrauben M8x30",
      "supplier_name": "Demo Supplier AG",
      "supplier_email": "demo@example.com",
      "reorder_threshold": 20,
      "reorder_quantity": 100,
      "unit": "Stuck"
    }
  },
  {
    "tag_id": 1,
    "values": {
      "ID": "MAT-002",
      "NAME": "Kabelbinder 200mm",
      "REORDER_QTY": "50",
      "REORDER_QUANTITY": "50",
      "REORDER_THRESHOLD": "20",
      "SUPPLIER_EMAIL": "demo@example.com",
      "SUPPLIER_NAME": "Demo Supplier AG",
      "TAG_ID": "1",
      "THRESHOLD": "20",
      "UNIT": "Stuck"
    },
    "product": {
      "tag_id": 1,
      "product_id": "MAT-002",
      "product_name": "Kabelbinder 200mm",
      "supplier_name": "Demo Supplier AG",
      "supplier_email": "demo@example.com",
      "reorder_threshold": 20,
      "reorder_quantity": 50,
      "unit": "Stuck"
    }
  }
]
```

## 2) Get config values for one product

### Request

`GET /api/product-env/{tag_id}`

Example:

`GET /api/product-env/0`

### Response (200)

```json
{
  "tag_id": 0,
  "values": {
    "ID": "MAT-001",
    "NAME": "Schrauben M8x30",
    "REORDER_QTY": "100",
    "REORDER_QUANTITY": "100",
    "REORDER_THRESHOLD": "20",
    "SUPPLIER_EMAIL": "demo@example.com",
    "SUPPLIER_NAME": "Demo Supplier AG",
    "TAG_ID": "0",
    "THRESHOLD": "20",
    "UNIT": "Stuck"
  },
  "allowed_fields": [
    "ID",
    "NAME",
    "REORDER_QTY",
    "REORDER_QUANTITY",
    "REORDER_THRESHOLD",
    "SUPPLIER_EMAIL",
    "SUPPLIER_NAME",
    "TAG_ID",
    "THRESHOLD",
    "UNIT"
  ],
  "product": {
    "tag_id": 0,
    "product_id": "MAT-001",
    "product_name": "Schrauben M8x30",
    "supplier_name": "Demo Supplier AG",
    "supplier_email": "demo@example.com",
    "reorder_threshold": 20,
    "reorder_quantity": 100,
    "unit": "Stuck"
  }
}
```

### Error (400)

If tag ID is not `0` or `1`.

## 3) Update config values for one product

### Request

`PUT /api/product-env/{tag_id}`

Body shape:

```json
{
  "values": {
    "NAME": "Schrauben M8x30 NEW",
    "SUPPLIER_EMAIL": "orders@example.com",
    "THRESHOLD": 25,
    "REORDER_QTY": 120,
    "UNIT": "Stuck"
  }
}
```

### Response (200)

```json
{
  "tag_id": 0,
  "values": {
    "ID": "MAT-001",
    "NAME": "Schrauben M8x30 NEW",
    "REORDER_QTY": "120",
    "REORDER_QUANTITY": "120",
    "REORDER_THRESHOLD": "25",
    "SUPPLIER_EMAIL": "orders@example.com",
    "SUPPLIER_NAME": "Demo Supplier AG",
    "TAG_ID": "0",
    "THRESHOLD": "25",
    "UNIT": "Stuck"
  },
  "product": {
    "tag_id": 0,
    "product_id": "MAT-001",
    "product_name": "Schrauben M8x30 NEW",
    "supplier_name": "Demo Supplier AG",
    "supplier_email": "orders@example.com",
    "reorder_threshold": 25,
    "reorder_quantity": 120,
    "unit": "Stuck"
  }
}
```

### Errors (400)

- Invalid `tag_id`
- Unsupported field name
- Integer field contains non-integer value
- Empty `values` object

## 4) Bulk update both products

### Request

`PUT /api/product-env`

Body shape:

```json
{
  "0": {
    "NAME": "Prod 0 New",
    "THRESHOLD": 15
  },
  "1": {
    "NAME": "Prod 1 New",
    "SUPPLIER_EMAIL": "supplier@example.com",
    "REORDER_QTY": 80
  }
}
```

### Response (200)

```json
{
  "updated": {
    "0": {
      "ID": "MAT-001",
      "NAME": "Prod 0 New",
      "REORDER_QTY": "100",
      "REORDER_QUANTITY": "100",
      "REORDER_THRESHOLD": "15",
      "SUPPLIER_EMAIL": "demo@example.com",
      "SUPPLIER_NAME": "Demo Supplier AG",
      "TAG_ID": "0",
      "THRESHOLD": "15",
      "UNIT": "Stuck"
    },
    "1": {
      "ID": "MAT-002",
      "NAME": "Prod 1 New",
      "REORDER_QTY": "80",
      "REORDER_QUANTITY": "80",
      "REORDER_THRESHOLD": "20",
      "SUPPLIER_EMAIL": "supplier@example.com",
      "SUPPLIER_NAME": "Demo Supplier AG",
      "TAG_ID": "1",
      "THRESHOLD": "20",
      "UNIT": "Stuck"
    }
  },
  "products": [
    {
      "tag_id": 0,
      "product_id": "MAT-001",
      "product_name": "Prod 0 New",
      "supplier_name": "Demo Supplier AG",
      "supplier_email": "demo@example.com",
      "reorder_threshold": 15,
      "reorder_quantity": 100,
      "unit": "Stuck"
    },
    {
      "tag_id": 1,
      "product_id": "MAT-002",
      "product_name": "Prod 1 New",
      "supplier_name": "Demo Supplier AG",
      "supplier_email": "supplier@example.com",
      "reorder_threshold": 20,
      "reorder_quantity": 80,
      "unit": "Stuck"
    }
  ]
}
```

## Frontend Integration Notes

- Use `GET /api/product-env` to initialize form state.
- Use `PUT /api/product-env/{tag_id}` for per-product save.
- Use `PUT /api/product-env` for one-click save-all.
- Refresh UI from response body after save to reflect auto-sync fields.
- Updated values are persisted to the `products` table in `../shelf.db` and applied live.
- Reorder loop now reloads products each cycle, so changes take effect without backend restart.
