import aiosmtplib
from email.message import EmailMessage
from app.core.config import SMTP_CONFIG

def format_currency(val):
    return "${:,.2f}".format(float(val or 0))

def generate_mobile_html(data):
    from datetime import datetime, timedelta
    target_date = datetime.strptime(data['date'], '%Y-%m-%d')
    
    cashflow = sum(float(item.get('grandtotal', 0) or 0) for item in data['paid'])
    new_jobs_count = len(data['new_today'])
    new_jobs_total = sum(float(item.get('grandtotal', 0) or 0) for item in data['new_today'])
    
    # Filter In Progress: Due within 10 days from today
    ten_days_later = target_date + timedelta(days=10)
    in_progress_filtered = []
    for item in data['in_progress']:
        due = item.get('wanteddate')
        if due:
            if hasattr(due, 'date'): due_date = due.date()
            else: due_date = datetime.strptime(str(due).split('T')[0], '%Y-%m-%d').date()
            if due_date <= ten_days_later.date():
                in_progress_filtered.append(item)
    
    ready_count = len(data['ready'])
    picked_up_count = len(data['picked_up'])

    def build_cards(items, show_method=False):
        if not items:
            return "<p style='color: #999; font-style: italic; padding-left: 10px;'>No items</p>"
        
        cards_html = ""
        for item in items:
            pay_badge = ""
            if item.get("payment_status") == "PAID":
                pay_badge = '<span style="background: #28a745; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-left: 5px;">PAID</span>'
            elif item.get("payment_status") and "BAL DUE" in item["payment_status"]:
                pay_badge = f'<span style="background: #FFC000; color: #333; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-left: 5px;">{item["payment_status"]}</span>'

            type_badge = ""
            if item.get("transaction_type"):
                color = "#6f42c1" # Mixed/Default
                if item["transaction_type"] == "PAID": color = "#28a745"
                elif item["transaction_type"] == "DEPOSIT": color = "#007bff"
                elif item["transaction_type"] == "AR PAYMENT": color = "#17a2b8"
                type_badge = f'<span style="background: {color}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-right: 5px;">{item["transaction_type"]}</span>'

            method_info = f'<div style="font-size: 11px; color: #888; margin-top: 4px;">Method: {item.get("pay_method_display", "N/A")}</div>' if show_method else ""

            cards_html += f"""
            <div style="background: #ffffff; border: 1px solid #eee; border-radius: 8px; padding: 15px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <table width="100%" cellspacing="0" cellpadding="0">
                    <tr>
                        <td style="font-weight: bold; color: #333; font-size: 16px; text-align: left;">
                            #{item['invoicenumber']} - {item['account_display']}
                        </td>
                        <td style="font-weight: bold; color: #28a745; font-size: 16px; text-align: right; white-space: nowrap; vertical-align: top;">
                            ${float(item.get('grandtotal', 0)):,.2f}
                        </td>
                    </tr>
                </table>
                <div style="color: #555; font-size: 14px; margin-top: 4px;">
                    {type_badge}{item['job_name']}{pay_badge}
                </div>
                {method_info}
            </div>
            """
        return cards_html

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Helvetica', 'Arial', sans-serif; background-color: #f8f9fa; margin: 0; padding: 15px; }}
            .container {{ max-width: 550px; margin: 0 auto; }}
            .summary-card {{ background: #4472C4; color: white; border-radius: 15px; padding: 30px 20px; text-align: center; margin-bottom: 25px; }}
            .section-title {{ font-size: 18px; font-weight: bold; color: #333; margin: 30px 0 15px 5px; border-left: 5px solid #4472C4; padding-left: 12px; }}
            .stat-row {{ background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; display: block; border: 1px solid #eee; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div style="text-align: center; padding-bottom: 20px; color: #666; font-size: 14px;">Daily Summary • {data['date']}</div>
            
            <div class="summary-card">
                <div style="font-size: 16px; opacity: 0.9; margin-bottom: 10px;">TOTAL CASH COLLECTED TODAY</div>
                <div style="font-size: 44px; font-weight: bold;">${cashflow:,.2f}</div>
            </div>

            <div class="stat-row">
                <table width="100%">
                    <tr>
                        <td style="font-size: 16px; color: #4472C4; font-weight: bold;">New Orders Today</td>
                        <td style="text-align: right; font-size: 18px; font-weight: bold;">{new_jobs_count} jobs</td>
                    </tr>
                    <tr>
                        <td colspan="2" style="font-size: 14px; color: #888; padding-top: 5px;">Total Value: ${new_jobs_total:,.2f}</td>
                    </tr>
                </table>
            </div>

            <div class="section-title">Payments Today (Cashflow)</div>
            {build_cards(data['paid'], show_method=True)}

            <div class="section-title">Production (Due in 10 Days)</div>
            {build_cards(in_progress_filtered)}

            <div class="section-title">Ready for Pickup</div>
            {build_cards(data['ready'])}

            <div class="section-title">Completions Today</div>
            {build_cards(data['picked_up'])}

            <div style="text-align: center; margin-top: 40px; padding: 20px; color: #bbb; font-size: 12px; border-top: 1px solid #eee;">
                Generated by PrintSmith Reporting System
            </div>
        </div>
    </body>
    </html>
    """
    return html

from app.services import settings_service

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
