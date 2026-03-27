from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import os

from orders import get_all_orders, get_latest_fill_levels
from config import load_products

app = FastAPI(title="Lagersystem API")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_methods=["*"],
	allow_headers=["*"],
)

products = load_products()

FRAME_PATH = "../latest_frame.jpg"


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
	return list(products.values())
