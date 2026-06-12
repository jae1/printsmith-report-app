import aiosmtplib
from email.message import EmailMessage
from app.core.config import SMTP_CONFIG
from app.services import settings_service

def format_currency(val):
    return "${:,.2f}".format(float(val or 0))

def generate_mobile_html(data):
    from datetime import datetime
    from app.services import spending_service
    
    target_date = data['date']
    cashflow = sum(float(item.get('grandtotal', 0) or 0) for item in data['paid'])
    new_jobs_count = len(data['new_today'])
    new_jobs_total = sum(float(item.get('grandtotal', 0) or 0) for item in data['new_today'])
    
    # Get spending for this date
    spending_items = spending_service.get_spending_by_date(target_date)
    total_spending = sum(s['amount'] for s in spending_items)

    def build_cards(items, show_method=False, is_spending=False):
        if not items:
            return "<p style='color: #999; font-style: italic; padding-left: 10px; font-size: 15px;'>No items recorded.</p>"
        
        cards_html = ""
        for item in items:
            if is_spending:
                title = item['vendor']
                desc = item['description']
                amt = item['amount']
                badges = ""
                extra_info = ""
            else:
                title = f"#{item['invoicenumber']} - {item['account_display']}"
                desc = item['job_name']
                amt = float(item.get('grandtotal', 0) or 0)
                
                pay_badge = ""
                if item.get("payment_status") == "PAID":
                    pay_badge = '<span style="background: #28a745; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-left: 6px; vertical-align: middle;">PAID</span>'
                elif item.get("payment_status") and "BAL DUE" in item["payment_status"]:
                    pay_badge = f'<span style="background: #FFC000; color: #333; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-left: 6px; vertical-align: middle;">{item["payment_status"]}</span>'

                type_badge = ""
                if item.get("transaction_type"):
                    color = "#6f42c1"
                    if item["transaction_type"] == "PAID": color = "#28a745"
                    elif item["transaction_type"] == "DEPOSIT": color = "#007bff"
                    elif item["transaction_type"] == "AR PAYMENT": color = "#17a2b8"
                    type_badge = f'<span style="background: {color}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 6px; vertical-align: middle;">{item["transaction_type"]}</span>'
                
                badges = f"{type_badge}{pay_badge}"
                extra_info = f'<div style="font-size: 13px; color: #888; margin-top: 5px;">{item.get("pay_method_display", "N/A")}</div>' if show_method else ""

            cards_html += f"""
            <div style="background: #ffffff; border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse;">
                    <tr>
                        <td style="font-weight: bold; color: #222; font-size: 18px; text-align: left; vertical-align: top; padding-bottom: 5px;">
                            {title}
                        </td>
                        <td style="font-weight: bold; color: { '#d9534f' if is_spending else '#28a745' }; font-size: 18px; text-align: right; white-space: nowrap; vertical-align: top; padding-bottom: 5px;">
                            ${amt:,.2f}
                        </td>
                    </tr>
                    <tr>
                        <td style="color: #444; font-size: 16px; text-align: left; vertical-align: top;">
                            <div style="margin-top: 5px;">{badges}{desc}</div>
                        </td>
                        <td style="text-align: right; vertical-align: bottom;">
                            {extra_info}
                        </td>
                    </tr>
                </table>
            </div>
            """
        return cards_html

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Helvetica', 'Arial', sans-serif; background-color: #f4f7f9; margin: 0; padding: 20px; -webkit-text-size-adjust: 100%; }}
            .container {{ max-width: 600px; margin: 0 auto; }}
            .summary-card {{ background: #4472C4; color: white; border-radius: 18px; padding: 35px 20px; text-align: center; margin-bottom: 30px; box-shadow: 0 6px 15px rgba(68,114,196,0.3); }}
            .section-header {{ margin: 40px 0 20px 0; padding-bottom: 10px; border-bottom: 3px solid #4472C4; }}
            .section-title {{ font-size: 22px; font-weight: bold; color: #222; text-transform: uppercase; letter-spacing: 1px; }}
            .stat-row {{ background: white; border-radius: 12px; padding: 20px; margin-bottom: 12px; display: block; border: 1px solid #ddd; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        </style>
    </head>
    <body>
        <div class="container">
            <div style="text-align: center; padding-bottom: 25px; color: #555; font-size: 16px; font-weight: bold;">{target_date} • PrintSmith Daily Report</div>
            
            <div class="summary-card">
                <div style="font-size: 18px; font-weight: bold; opacity: 0.95; margin-bottom: 15px; letter-spacing: 1px;">TOTAL CASH COLLECTED TODAY</div>
                <div style="font-size: 52px; font-weight: 900;">${cashflow:,.2f}</div>
            </div>

            <div class="stat-row">
                <table width="100%">
                    <tr>
                        <td style="font-size: 20px; color: #4472C4; font-weight: bold;">New Orders Today</td>
                        <td style="text-align: right; font-size: 22px; font-weight: bold; color: #333;">{new_jobs_count}</td>
                    </tr>
                    <tr>
                        <td colspan="2" style="font-size: 16px; color: #666; padding-top: 10px; font-weight: bold;">Total Value: ${new_jobs_total:,.2f}</td>
                    </tr>
                </table>
            </div>

            <div class="section-header">
                <span class="section-title">💰 Payments Today</span>
            </div>
            {build_cards(data['paid'], show_method=True)}

            <div class="section-header">
                <span class="section-title">💸 Daily Spending</span>
            </div>
            {build_cards(spending_items, is_spending=True)}
            {f'<div style="text-align: right; padding: 10px 15px; font-weight: bold; color: #d9534f; font-size: 20px; background: #fff; border-radius: 10px; margin-top: 5px; border: 1px solid #ddd;">Total Spending: ${total_spending:,.2f}</div>' if spending_items else ''}

            <div class="section-header">
                <span class="section-title">⚙️ Work In Progress</span>
            </div>
            {build_cards(data['in_progress'])}

            <div class="section-header">
                <span class="section-title">📦 Ready for Pickup</span>
            </div>
            {build_cards(data['ready'])}

            <div class="section-header">
                <span class="section-title">✅ Jobs Completed Today</span>
            </div>
            {build_cards(data['picked_up'])}

            <div style="text-align: center; margin-top: 60px; padding: 30px; color: #888; font-size: 14px; border-top: 2px solid #ddd;">
                <strong>PrintSmith Reporting System</strong><br>
                High-Readability Executive View
            </div>
        </div>
    </body>
    </html>
    """
    return html

async def send_report_email(data):
    settings = settings_service.load_settings()
    html_content = generate_mobile_html(data)
    
    message = EmailMessage()
    message["From"] = SMTP_CONFIG["user"]
    # Join list of emails into a comma-separated string for "To" header
    message["To"] = ", ".join(settings["boss_emails"])
    message["Subject"] = f"Overnight {data['date']} Daily Report"
    message.set_content("This is an HTML-only email. Please use an HTML-capable email client.")
    message.add_alternative(html_content, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=SMTP_CONFIG["host"],
        port=SMTP_CONFIG["port"],
        username=SMTP_CONFIG["user"],
        password=SMTP_CONFIG["password"],
        use_tls=SMTP_CONFIG["port"] == 465,
        start_tls=SMTP_CONFIG["port"] == 587,
    )
