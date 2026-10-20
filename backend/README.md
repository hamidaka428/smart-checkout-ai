# Backend (PHP + MariaDB)

A small REST backend used by the Python application on the Raspberry Pi. It serves the product catalogue, stores completed orders and shows a sales dashboard.

> This is a clean **reference implementation** written to match the requests made by `main.py` and `utils/receipt.py`. Product prices are demo values (EUR, VAT included); `RPI_JOYSTICK` has a placeholder name and price.

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api.php?barcode=<LABEL>` | GET | Returns `{"barcode", "name", "price"}`. Errors return `{"error": "..."}` with status 400 / 404 / 500. |
| `/save_order.php` | POST (JSON) | Body `{"total_amount", "vat_amount", "items_count"}`. Returns `{"success": true, "order_id": N}`. |
| `/dashboard.php` | GET | Orders, revenue, VAT, items sold, daily totals and recent orders (auto-refreshes). |

`<LABEL>` is a class label from `ai/model/labels.txt` (for example `RPI_MOUSE`).

## Setup (Raspberry Pi OS)

```bash
# 1. Install the web server, PHP and MariaDB
sudo apt update
sudo apt install apache2 php libapache2-mod-php php-mysql mariadb-server

# 2. Create the database, tables and demo catalogue
sudo mariadb < backend/schema.sql

# 3. Create a least-privilege database user (choose your own password)
sudo mariadb -e "CREATE USER 'smart_checkout'@'localhost' IDENTIFIED BY 'CHANGE_ME';
                 GRANT SELECT, INSERT ON smart_checkout.* TO 'smart_checkout'@'localhost';
                 FLUSH PRIVILEGES;"

# 4. Publish the backend files
sudo cp backend/*.php /var/www/html/
sudo cp backend/config.local.php.example /var/www/html/config.local.php
sudo nano /var/www/html/config.local.php      # set the password from step 3
```

The Python client uses `http://localhost`, so no changes are needed on the Python side when everything runs on the same Pi. (Alternatively, set the `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS` environment variables instead of using `config.local.php`.)

## Quick test

```bash
curl "http://localhost/api.php?barcode=RPI_MOUSE"
# {"barcode":"RPI_MOUSE","name":"Wireless Computer Mouse","price":9.2}

curl -X POST -H "Content-Type: application/json" \
     -d '{"total_amount":55.22,"vat_amount":9.20,"items_count":3}' \
     http://localhost/save_order.php
# {"success":true,"order_id":1}
```

Then open `http://localhost/dashboard.php` in a browser.

## Notes

- All queries use prepared statements; barcodes and order values are validated.
- The database user only has `SELECT` and `INSERT` rights.
- The dashboard has no authentication – keep it on the local network or add authentication before exposing it.
