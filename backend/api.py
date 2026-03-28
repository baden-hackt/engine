from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import os

from orders import get_all_orders, get_latest_fill_levels
from config import (
	PRODUCT_ENV_SUFFIXES,
	get_all_product_env,
	get_product_env,
	load_products,
	update_product_env,
)

app = FastAPI(title="Lagersystem API")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_methods=["*"],
	allow_headers=["*"],
)

FRAME_PATH = "../latest_frame.jpg"


class ProductEnvUpdateRequest(BaseModel):
	values: dict[str, Any] = Field(default_factory=dict)


@app.exception_handler(Exception)
def api_unhandled_exception_handler(request: Request, exc: Exception):
	return JSONResponse(
		status_code=500,
		content={"error": "internal_server_error", "detail": str(exc)},
	)


@app.get("/api/camera-feed")
def api_camera_feed():
	"""
	Serve the latest annotated camera frame as a JPEG image.
	Person 1's pipeline saves this file every scan cycle.
	The dashboard polls this endpoint every 2 seconds and displays it as an <img>.
	"""
	if not os.path.exists(FRAME_PATH):
		return JSONResponse(status_code=404, content={"error": "No frame available yet"})
	return FileResponse(
		os.path.abspath(FRAME_PATH),
		media_type="image/jpeg",
		headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
	)


@app.get("/api/fill-levels")
def api_fill_levels():
	"""
	Return latest fill level per tag, enriched with product info.
	Response format:
	[
		{
			"tag_id": 0,
			"fill_level": 25,
			"timestamp": "2026-05-16T14:30:00",
			"product_id": "MAT-001",
			"product_name": "Schrauben M8x30",
			"supplier_name": "Wurth AG",
			"reorder_threshold": 20,
			"status": "low"  // "ok", "low", or "critical"
		},
		...
	]
	"""
	try:
		products = load_products()
		fill_levels = get_latest_fill_levels()
		result = []
		for fl in fill_levels:
			tag_id = fl["tag_id"]
			product = products.get(tag_id, {})
			threshold = product.get("reorder_threshold", 20)

			if fl["fill_level"] <= 5:
				status = "critical"
			elif fl["fill_level"] <= threshold:
				status = "low"
			else:
				status = "ok"

			result.append(
				{
					"tag_id": tag_id,
					"fill_level": fl["fill_level"],
					"timestamp": fl["timestamp"],
					"product_id": product.get("product_id", "UNKNOWN"),
					"product_name": product.get("product_name", "Unknown product"),
					"supplier_name": product.get("supplier_name", "Unknown supplier"),
					"reorder_threshold": threshold,
					"status": status,
				}
			)
		return result
	except Exception as e:
		return JSONResponse(
			status_code=500,
			content={"error": "fill_levels_read_failed", "detail": str(e)},
		)


@app.get("/api/orders")
def api_orders():
	"""
	Return all orders, newest first.
	Response format:
	[
		{
			"id": 1,
			"tag_id": 2,
			"product_id": "MAT-003",
			"product_name": "Kabelbinder 200mm",
			"supplier_name": "Distrelec AG",
			"supplier_email": "orders@distrelec-demo.ch",
			"quantity": 200,
			"unit": "Stuck",
			"status": "pending",
			"created_at": "2026-05-16T14:35:00",
			"csv_filename": "PO_MAT-003_20260516_143500.csv"
		},
		...
	]
	"""
	return get_all_orders()


@app.get("/api/products")
def api_products():
	"""
	Return all product master data.
	"""
	return list(load_products().values())


@app.get("/api/product-env")
def api_product_env_all():
	"""
	Return raw PRODUCT_0_* and PRODUCT_1_* values from ../.env.
	Useful for dashboard config forms.
	"""
	data = []
	for tag_id in (0, 1):
		data.append(
			{
				"tag_id": tag_id,
				"values": get_product_env(tag_id),
				"product": load_products().get(tag_id, {}),
			}
		)
	return data


@app.get("/api/product-env/{tag_id}")
def api_product_env_one(tag_id: int):
	"""Return all editable PRODUCT_{tag_id}_* values for one product."""
	if tag_id not in (0, 1):
		raise HTTPException(status_code=400, detail="tag_id must be 0 or 1")

	return {
		"tag_id": tag_id,
		"values": get_product_env(tag_id),
		"allowed_fields": sorted(PRODUCT_ENV_SUFFIXES),
		"product": load_products().get(tag_id, {}),
	}


@app.put("/api/product-env/{tag_id}")
def api_update_product_env(tag_id: int, payload: ProductEnvUpdateRequest):
	"""
	Update any subset of PRODUCT_{tag_id}_* variables.
	Input keys must be suffixes only (e.g. NAME, THRESHOLD, REORDER_QTY).
	"""
	if tag_id not in (0, 1):
		raise HTTPException(status_code=400, detail="tag_id must be 0 or 1")

	try:
		updated_values = update_product_env(tag_id, payload.values)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e)) from None

	return {
		"tag_id": tag_id,
		"values": updated_values,
		"product": load_products().get(tag_id, {}),
	}


@app.put("/api/product-env")
def api_update_multiple_product_env(payload: dict[str, dict[str, Any]]):
	"""
	Bulk update endpoint.
	Payload shape:
	{
	  "0": {"NAME": "...", "THRESHOLD": 30},
	  "1": {"SUPPLIER_EMAIL": "..."}
	}
	"""
	updated: dict[str, dict[str, str]] = {}
	for key, values in payload.items():
		try:
			tag_id = int(key)
		except ValueError:
			raise HTTPException(status_code=400, detail=f"Invalid tag_id key: {key}") from None

		if tag_id not in (0, 1):
			raise HTTPException(status_code=400, detail=f"tag_id must be 0 or 1, got {tag_id}")

		if not isinstance(values, dict):
			raise HTTPException(status_code=400, detail=f"Values for tag {tag_id} must be an object")

		try:
			updated[str(tag_id)] = update_product_env(tag_id, values)
		except ValueError as e:
			raise HTTPException(status_code=400, detail=str(e)) from None

	return {"updated": updated, "products": list(load_products().values())}
