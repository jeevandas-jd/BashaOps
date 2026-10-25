# backend/app/bill_service.py
from app.catalogue_service import get_product
from datetime import datetime

def generate_html_bill(order: dict) -> str:
    """
    Generates a simple, print-friendly HTML bill for a confirmed order.
    Uses the price snapshot stored on the order.
    """
    order_id = str(order.get("id", "UNKNOWN"))
    
    # Safely handle created_at which might be a datetime object or a string
    created_at_raw = order.get("created_at", datetime.utcnow())
    if isinstance(created_at_raw, datetime):
        created_at_str = created_at_raw.isoformat()
    else:
        created_at_str = str(created_at_raw)
        
    subtotal = order.get("subtotal_minor", 0) / 100.0
    discount = order.get("discount_minor", 0) / 100.0
    total = order.get("total_minor", 0) / 100.0
    
    items_html = ""
    for item in order.get("items", []):
        if item.get("resolved_product_id"):
            product = get_product(item["resolved_product_id"])
            name = product.name if product else item.get("product_mention", "Unknown")
            qty = item.get("requested_quantity", 1)
            unit = item.get("requested_unit", "piece")
            
            # Calculate line total for display (using snapshot logic)
            line_total = 0
            if product:
                line_total = (product.unit_price_minor * qty) / 100.0
                
            items_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{name}</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">{qty} {unit}</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">₹{line_total:.2f}</td>
            </tr>
            """
        else:
            # Unresolved item (shouldn't happen in CONFIRMED, but safe fallback)
            items_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee; color: red;">{item.get('product_mention')} (Unresolved)</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">{item.get('requested_quantity')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">-</td>
            </tr>
            """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Order Bill - {order_id}</title>
        <style>
            body {{ font-family: 'Courier New', Courier, monospace; max-width: 400px; margin: 20px auto; padding: 20px; border: 1px solid #ccc; }}
            h2 {{ text-align: center; margin-bottom: 5px; }}
            .meta {{ text-align: center; color: #666; font-size: 0.9em; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th {{ text-align: left; border-bottom: 2px solid #333; padding: 8px; }}
            .totals {{ text-align: right; font-weight: bold; }}
            .totals div {{ margin: 5px 0; }}
            .footer {{ text-align: center; margin-top: 30px; font-size: 0.8em; color: #666; }}
            @media print {{ body {{ border: none; }} .no-print {{ display: none; }} }}
        </style>
    </head>
    <body>
        <h2>BHASHAOPS KIRANA</h2>
        <div class="meta">Order ID: {order_id[:8]}<br>Date: {created_at_str[:10]}</div>
        
        <table>
            <thead>
                <tr>
                    <th>Item</th>
                    <th style="text-align: center;">Qty</th>
                    <th style="text-align: right;">Price</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>
        
        <div class="totals">
            <div>Subtotal: ₹{subtotal:.2f}</div>
            <div>Discount: -₹{discount:.2f}</div>
            <div style="font-size: 1.2em; border-top: 2px solid #333; padding-top: 10px; margin-top: 10px;">
                TOTAL: ₹{total:.2f}
            </div>
        </div>
        
        <div class="footer">
            Thank you for your order!<br>
            <span class="no-print"><br><button onclick="window.print()" style="padding: 10px 20px; cursor: pointer;">Print Bill</button></span>
        </div>
    </body>
    </html>
    """
    return html