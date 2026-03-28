# STOCKR Engine - Vollständige Dokumentation

## 1) Projektüberblick
Dieses Repository enthält den Engine-Teil des STOCKR-Systems. Es gibt zwei Python-Services, die zusammenarbeiten:

- Pipeline-Service in pipeline/
  - Liest Kamerabilder
  - Erkennt AprilTags
  - Schneidet pro Fach ein Bildsegment aus
  - Fragt OpenAI Vision für den Füllstand in Prozent an
  - Schreibt Messdaten in SQLite
  - Schreibt ein derzeitiges Dashboard-Bild auf die Festplatte

- Backend-Service in backend/
  - Liest Füllstände aus der gleichen SQLite-Datenbank
  - Führt Nachbestell-Logik aus
  - Erzeugt SAP-kompatible CSV-Dateien
  - Versendet Bestellmails per Resend
  - Stellt REST-API-Endpunkte für das Dashboard bereit

Das Dashboard läuft separat (zum Beispiel auf Vercel) und ruft die Backend-API auf.

## 2) Verzeichnisstruktur

~~~text
/home/std/engine
├── backend/
│   ├── api.py
│   ├── config.py
│   ├── csv_gen.py
│   ├── mailer.py
│   ├── main.py
│   ├── orders.py
│   └── requirements.txt
├── pipeline/
│   ├── camera.py
│   ├── db.py
│   ├── debug_crop.py
│   ├── main.py
│   ├── requirements.txt
│   ├── tags.py
│   ├── test_pipeline.py
│   └── vision.py
├── docs/
│   ├── dijar/
│   └── said/
├── .env
├── latest_frame.jpg
├── shelf.db
└── crop_debug.jpg
~~~

## 3) Gesamtarchitektur und Datenfluss

1. pipeline/main.py erzeugt in einer Schleife Kameraframes.
2. AprilTags werden erkannt.
3. Pro Tag wird ein Crop berechnet.
4. OpenAI Vision liefert einen Füllstand von 0 bis 100.
5. Pipeline schreibt in fill_levels und scan_log.
6. Pipeline schreibt latest_frame.jpg für das Dashboard.
7. backend/main.py liest die derzeitigen Füllstände.
8. Bei Unterschreitung des Schwellwertes: CSV + Order + Email.
9. backend/api.py stellt JSON-Endpunkte und den Kamera-Feed bereit.

## 4) Gemeinsame Ressourcen

### 4.1 SQLite-Datenbank
Pfad: /home/std/engine/shelf.db

Beide Services verwenden dieselbe Datei.

### 4.2 Kamera-Frame für Dashboard
Pfad: /home/std/engine/latest_frame.jpg

Wird von der Pipeline aktualisiert und vom Backend als image/jpeg ausgeliefert.

### 4.3 Umgebungsdatei
Pfad: /home/std/engine/.env

Enthält API-Keys und Laufzeit-Konfiguration.

## 5) Pipeline im Detail

### 5.1 camera.py
- init_camera(): Öffnet Kamera Index 0, setzt 1280x720
- capture_frame(): Liest Frame mit Retry
- has_changed(): Pixel-Differenz für Veränderungserkennung

### 5.2 tags.py
- detect_tags(): AprilTag-Erkennung (tag36h11)
- get_crop_bounds(): Ermittelt Crop-Rechteck mit crop_settings
- crop_slot(): Schneidet das Crop aus dem Frame

### 5.3 vision.py
- Lädt .env
- Kodiert Crop als JPEG und base64
- Sendet Anfrage an OpenAI Chat Completions (Vision)
- Parst Antwort als Integer 0 bis 100

### 5.4 db.py
Erstellt und nutzt Tabellen:
- fill_levels
- scan_log
- crop_settings

Seedet Standard-crop_settings für tag_id 0 und 1.

### 5.5 main.py
Loop mit SCAN_INTERVAL = 1 Sekunde:
1. Frame lesen
2. Change Detection
3. Tag Detection
4. Overlay zeichnen
5. Vision + DB-Write
6. latest_frame.jpg schreiben
7. scan_log schreiben

## 6) Backend im Detail

### 6.1 config.py
- Lädt .env
- Verwaltet DB-Pfad
- Verwendet products-Tabelle als Source of Truth für Produktdaten
- Seedet Standardprodukte für tag_id 0 und 1

### 6.2 orders.py
- Erstellt und nutzt orders-Tabelle
- has_pending_order(), create_order(), mark_delivered()
- get_latest_fill_levels() liest derzeitige Werte pro Tag

### 6.3 csv_gen.py
- Erzeugt pro Bestellung eine CSV in backend/orders_csv/
- Semikolon als Trennzeichen
- SAP-orientierte Spaltenstruktur

### 6.4 mailer.py
- Liest CSV
- Kodiert Attachment in base64
- Versendet Email via Resend

### 6.5 api.py
- FastAPI mit offenem CORS
- Wichtige Endpunkte:
  - GET /api/camera-feed
  - GET /api/fill-levels
  - GET /api/orders
  - GET /api/products
  - GET /api/product-env
  - GET /api/product-env/{tag_id}
  - PUT /api/product-env/{tag_id}
  - PUT /api/product-env

### 6.6 main.py
Startet:
- reorder_loop in einem Hintergrund-Thread
- FastAPI/Uvicorn im Hauptthread

## 7) Datenbanktabellen

### 7.1 fill_levels
- id
- tag_id
- fill_level
- timestamp

### 7.2 scan_log
- id
- timestamp
- tags_detected
- change_detected

### 7.3 crop_settings
- tag_id (Primary Key)
- crop_width
- crop_height
- offset_x
- offset_y
- updated_at

### 7.4 orders
- id
- tag_id
- product_id
- product_name
- supplier_name
- supplier_email
- quantity
- unit
- status
- created_at
- csv_filename

### 7.5 products
- tag_id (Primary Key)
- product_id
- product_name
- supplier_name
- supplier_email
- reorder_threshold
- reorder_quantity
- unit
- updated_at

## 8) Produktkonfiguration über API

Das Dashboard kann Produktdaten per API lesen und schreiben:

- GET /api/product-env
- GET /api/product-env/{tag_id}
- PUT /api/product-env/{tag_id}
- PUT /api/product-env

Hinweise:
- Werte werden in products gespeichert.
- Synonyme werden synchron gehalten:
  - THRESHOLD und REORDER_THRESHOLD
  - REORDER_QTY und REORDER_QUANTITY

Detaildokumentation: docs/dijar/dashboard.product-env.api.md

## 9) Installation und Start

### 9.1 Abhängigkeiten installieren

Pipeline:
~~~bash
cd /home/std/engine/pipeline
python3 -m pip install --break-system-packages -r requirements.txt
~~~

Backend:
~~~bash
cd /home/std/engine/backend
python3 -m pip install --break-system-packages -r requirements.txt
~~~

### 9.2 Services starten

Backend:
~~~bash
cd /home/std/engine/backend
python3 main.py
~~~

Pipeline:
~~~bash
cd /home/std/engine/pipeline
python3 main.py
~~~

Optional ngrok:
~~~bash
cd /home/std/engine
/home/std/.local/bin/ngrok http 8000
~~~

## 10) Linux Kamera-Berechtigung

Wenn die Kamera nicht geöffnet werden kann:
- Benutzer muss in der Gruppe video sein
- Für sofortigen Start:

~~~bash
sg video -c 'cd /home/std/engine/pipeline && python3 main.py'
~~~

## 11) Typische Fehlerbilder

### 11.1 Intermittierende 503
Häufige Ursachen:
- Tunnel/Proxy-Instabilität (ngrok free)
- Vercel Proxy Function Fehler
- Zu hohe Polling-Rate im Frontend
- Binary Endpoint (camera-feed) ist empfindlicher als JSON-Endpunkte

### 11.2 CORS-Meldungen im Browser
In diesem Setup sind CORS-Meldungen oft Folgefehler, wenn Upstream bereits 502/503 liefert.

## 12) Diagnose-Kommandos

Backend up?
~~~bash
ss -ltnp | grep :8000
curl -i http://127.0.0.1:8000/api/products
~~~

Kamera-Feed lokal?
~~~bash
curl -i http://127.0.0.1:8000/api/camera-feed
~~~

Ngrok Status?
~~~bash
curl -sS http://127.0.0.1:4040/api/tunnels
~~~

DB Status?
~~~bash
sqlite3 /home/std/engine/shelf.db ".tables"
sqlite3 /home/std/engine/shelf.db "SELECT * FROM fill_levels ORDER BY id DESC LIMIT 5;"
sqlite3 /home/std/engine/shelf.db "SELECT * FROM orders ORDER BY id DESC LIMIT 5;"
~~~

## 13) Wichtige Betriebsregeln

1. Backend, Pipeline und ngrok für Demo möglichst ohne Unterbruch laufen lassen.
2. Dashboard muss auf die gültige ngrok-URL zeigen.
3. Keine Secrets in Git committen.
4. Bei gelöschter DB initialisieren die Services die Tabellen automatisch neu.

## 14) Zusammenfassung

- Pipeline erstellt Messdaten und Bild.
- Backend macht Nachbestellung und API.
- Beide Services nutzen dieselbe SQLite-Datenbank.
- Dashboard spricht nur mit der Backend-API.
- Stabilität hängt stark von Polling-Strategie und Tunnel-Qualität ab.
