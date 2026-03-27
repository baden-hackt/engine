import csv
import os
from datetime import datetime

CSV_DIR = "./orders_csv"


def generate_order_csv(product: dict) -> str:
	"""
	Generate a CSV file for a single product reorder.
	Save it to ./orders_csv/ directory.
	Return the filename (not full path).

	The CSV contains exactly one data row (plus header).
	"""
	os.makedirs(CSV_DIR, exist_ok=True)

	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	filename = f"PO_{product['product_id']}_{timestamp}.csv"
	filepath = os.path.join(CSV_DIR, filename)

	with open(filepath, "w", newline="", encoding="utf-8") as f:
		writer = csv.writer(f, delimiter=";")
		writer.writerow([
			"DocDate",
			"CardCode",
			"CardName",
			"ItemCode",
			"ItemDescription",
			"Quantity",
			"UnitPrice",
			"Currency",
		])
		writer.writerow([
			datetime.now().strftime("%Y-%m-%d"),
			product["supplier_name"],
			product["supplier_name"],
			product["product_id"],
			product["product_name"],
			product["reorder_quantity"],
			"",
			"CHF",
		])

	return filename
