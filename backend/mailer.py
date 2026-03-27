import resend
import base64
import os

from config import RESEND_API_KEY, SENDER_EMAIL

CSV_DIR = "./orders_csv"


def send_order_email(product: dict, csv_filename: str) -> bool:
	"""
	Send an email to the supplier with the CSV attached via Resend.
	Return True if sent successfully, False otherwise.
	"""
	resend.api_key = RESEND_API_KEY

	filepath = os.path.join(CSV_DIR, csv_filename)

	try:
		with open(filepath, "rb") as f:
			csv_content = base64.b64encode(f.read()).decode("utf-8")

		params: resend.Emails.SendParams = {
			"from": f"Lagersystem <{SENDER_EMAIL}>",
			"to": [product["supplier_email"]],
			"subject": f"Bestellung: {product['product_name']} ({product['product_id']})",
			"html": (
				f"<p>Guten Tag</p>"
				f"<p>Hiermit bestellen wir:</p>"
				f"<p><strong>Produkt:</strong> {product['product_name']}<br>"
				f"<strong>Materialnummer:</strong> {product['product_id']}<br>"
				f"<strong>Menge:</strong> {product['reorder_quantity']} {product['unit']}</p>"
				f"<p>Die Bestellung ist auch als CSV im Anhang.</p>"
				f"<p>Freundliche Grüsse<br>Automatisches Lagersystem</p>"
			),
			"attachments": [
				{
					"filename": csv_filename,
					"content": csv_content,
				}
			],
		}

		email = resend.Emails.send(params)
		print(f"  Email sent to {product['supplier_email']} for {product['product_name']} (id: {email['id']})")
		return True

	except Exception as e:
		print(f"  WARNING: Email failed for {product['product_name']}: {e}")
		return False
