import os
import json
import urllib.request
from datetime import datetime

class ReceiptManager:
    """Generates receipts and registers orders into MariaDB via PHP API."""
    def __init__(self, output_dir="receipts"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def save_order_to_db(self, total_amount, vat_amount, items_count):
        """Sends order statistics to save_order.php backend."""
        url = "http://localhost/save_order.php"
        payload = json.dumps({
            "total_amount": total_amount,
            "vat_amount": vat_amount,
            "items_count": items_count
        }).encode('utf-8')

        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                if "success" in result:
                    print(f"[Database] Order #{result['order_id']} saved to database.")
        except Exception as e:
            print(f"[Database Error] Could not save order: {e}")

    def generate_receipt(self, items):
        if not items:
            print("[Receipt] No items scanned in this session.")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.output_dir, f"receipt_{filename_time}.txt")

        total = sum(float(item['price']) for item in items)
        subtotal = total / 1.20
        vat = total - subtotal

        # Save order info to DB for dashboard
        self.save_order_to_db(total, vat, len(items))

        receipt_lines = [
            "===========================================",
            "             SMART CHECKOUT AI             ",
            "          Autonomous Retail System         ",
            "===========================================",
            f" Date/Time: {timestamp}",
            "-------------------------------------------",
            f"{'Item Description':<28} {'Price (€)':>12}",
            "-------------------------------------------"
        ]

        for item in items:
            name = item['name'][:27]
            price = f"€{float(item['price']):.2f}"
            receipt_lines.append(f"{name:<28} {price:>12}")

        receipt_lines.extend([
            "-------------------------------------------",
            f"{'Subtotal (Excl. VAT):':<28} €{subtotal:>11.2f}",
            f"{'VAT (20%):':<28} €{vat:>11.2f}",
            "-------------------------------------------",
            f"{'TOTAL AMOUNT:':<28} €{total:>11.2f}",
            "===========================================",
            "         Thank you for your purchase!      ",
            "===========================================\n"
        ])

        receipt_content = "\n".join(receipt_lines)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(receipt_content)

        print(f"\n[Receipt] File generated: {filepath}")
        print(receipt_content)