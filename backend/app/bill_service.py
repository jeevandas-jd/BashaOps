# backend/app/bill_service.py
from app.catalogue_service import get_product
from datetime import datetime
import urllib.parse
from sqlalchemy.orm import Session

def generate_upi_string(total_rupees: float, merchant_name: str = "BhashaOps Kirana", merchant_vpa: str = "shop@upi") -> str:
    params = {"pa": merchant_vpa, "pn": merchant_name, "am": f"{total_rupees:.2f}", "cu": "INR", "tn": "Order Payment"}
    return f"upi://pay?{urllib.parse.urlencode(params)}"

def generate_html_bill(order: dict, db: Session) -> str:
    order_id = str(order.get("id", "UNKNOWN"))
    
    raw_date = order.get("created_at")
    if isinstance(raw_date, datetime):
        date_str = raw_date.strftime("%Y-%m-%d")
    else:
        date_str = str(raw_date)[:10] if raw_date else "Unknown"
        
    subtotal = order.get("subtotal_minor", 0) / 100.0
    total = order.get("total_minor", 0) / 100.0
    
    items_html = ""
    for item in order.get("items", []):
        if item.get("resolved_product_id"):
            # Pass db to get_product!
            product = get_product(item["resolved_product_id"], db)
            name = product.name if product else item.get("product_mention", "Unknown")
            qty = item.get("requested_quantity", 1)
            unit = item.get("requested_unit", "piece")
            line_total = (product.unit_price_minor * qty) / 100.0 if product else 0
            
            items_html += f"<tr><td style='padding:8px;border-bottom:1px solid #eee;'>{name}</td><td style='padding:8px;border-bottom:1px solid #eee;text-align:center;'>{qty} {unit}</td><td style='padding:8px;border-bottom:1px solid #eee;text-align:right;'>₹{line_total:.2f}</td></tr>"
        else:
            items_html += f"<tr><td style='padding:8px;border-bottom:1px solid #eee;color:red;'>{item.get('product_mention')} (Unresolved)</td><td style='padding:8px;border-bottom:1px solid #eee;text-align:center;'>{item.get('requested_quantity')}</td><td style='padding:8px;border-bottom:1px solid #eee;text-align:right;'>-</td></tr>"

    upi_string = generate_upi_string(total)
    qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(upi_string)}"

    return f"""<!DOCTYPE html><html><head><title>Bill {order_id}</title><style>body{{font-family:monospace;max-width:400px;margin:20px auto;padding:20px;border:1px solid #ccc;}} table{{width:100%;border-collapse:collapse;}} .qr-section{{text-align:center;margin-top:20px;}}</style></head><body>
    <h2 style="text-align:center;">BHASHAOPS KIRANA</h2>
    <div style="text-align:center;color:#666;margin-bottom:20px;">Order: {order_id[:8]} | Date: {date_str}</div>
    <table><thead><tr><th>Item</th><th>Qty</th><th>Price</th></tr></thead><tbody>{items_html}</tbody></table>
    <div style="text-align:right;font-weight:bold;font-size:1.2em;border-top:2px solid #333;padding-top:10px;">TOTAL: ₹{total:.2f}</div>
    <div class="qr-section"><p><strong>Scan to Pay via UPI</strong></p><img src="{qr_code_url}" alt="UPI QR" width="200" height="200"><p style="font-size:0.8em;color:#888;">{upi_string}</p></div>
    <div style="text-align:center;margin-top:20px;"><button onclick="window.print()" style="padding:10px 20px;cursor:pointer;background:#333;color:white;border:none;border-radius:4px;">Print Bill</button></div>
    </body></html>"""