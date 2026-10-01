import aiosmtplib
from email.message import EmailMessage
from html import escape
from app.core.config import SMTP_CONFIG
from app.services import settings_service, spending_service

def format_currency(val):
    return "${:,.2f}".format(float(val or 0))

def generate_mobile_html(data, spending_items=None, title_prefix="Overnight"):
    target_date = data['date']
    cashflow = sum(float(item.get('grandtotal', 0) or 0) for item in data['paid'])
    new_jobs_count = len(data['new_today'])
    new_jobs_total = sum(float(item.get('grandtotal', 0) or 0) for item in data['new_today'])

    # Get spending for this date
    if spending_items is None:
        spending_items = spending_service.get_spending_by_date(target_date)
    total_spending = sum(s['amount'] for s in spending_items)

    def build_cards(items, show_method=False, is_spending=False):
        if not items:
            return "<p style='color: #999; font-style: italic; padding-left: 10px; font-size: 15px;'>No items recorded.</p>"

        cards_html = ""
        for item in items:
            if is_spending:
                title = escape(str(item['vendor']))
                desc = escape(str(item['description']))
                amt = float(item['amount'])
                badges = ""
                extra_info = ""
            else:
                title = escape(f"#{item['invoicenumber']} - {item['account_display']}")
                desc = escape(str(item['job_name']))
                amt = float(item.get('grandtotal', 0) or 0)

                pay_badge = ""
                if item.get("is_partial"):
                    pay_badge = f'<span style="background: #FFC000; color: #333; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-left: 6px; vertical-align: middle;">PARTIAL · BAL DUE: {format_currency(item.get("current_balance"))}</span>'
                elif item.get("payment_status") == "PAID":
                    pay_badge = '<span style="background: #28a745; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-left: 6px; vertical-align: middle;">PAID</span>'
                elif item.get("payment_status") and "BAL DUE" in item["payment_status"]:
                    pay_badge = f'<span style="background: #FFC000; color: #333; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-left: 6px; vertical-align: middle;">{escape(str(item["payment_status"]))}</span>'

                type_badge = ""
                if item.get("transaction_type"):
                    color = "#6f42c1"
                    if item["transaction_type"] == "PAID": color = "#28a745"
                    elif item["transaction_type"] == "DEPOSIT": color = "#007bff"
                    elif item["transaction_type"] == "AR PAYMENT": color = "#17a2b8"
                    type_badge = f'<span style="background: {color}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 6px; vertical-align: middle;">{escape(str(item["transaction_type"]))}</span>'

                badges = f"{type_badge}{pay_badge}"
                extra_info = f'<div style="font-size: 13px; color: #555; margin-top: 5px;">{escape(str(item.get("pay_method_display") or "N/A"))}</div>' if show_method else ""

            cards_html += f"""
            <div style="background: #ffffff; border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse; table-layout: fixed;">
                    <tr>
                        <td width="62%" style="font-weight: bold; color: #222; font-size: 17px; text-align: left; vertical-align: top; padding-bottom: 5px; overflow-wrap: anywhere;">
                            {title}
                        </td>
                        <td width="38%" style="font-weight: bold; color: { '#d9534f' if is_spending else ('#28a745' if show_method else '#0B1B3D') }; font-size: 17px; text-align: right; vertical-align: top; padding-bottom: 5px;">
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
            body {{ font-family: 'Helvetica', 'Arial', sans-serif; background-color: #f4f7f9; margin: 0; padding: 12px; -webkit-text-size-adjust: 100%; }}
            .container {{ max-width: 600px; margin: 0 auto; }}
            .summary-card {{ background: #0B1B3D; color: white; border-radius: 12px; padding: 26px 16px; text-align: center; margin-bottom: 20px; }}
            .section-header {{ margin: 32px 0 16px 0; padding-bottom: 8px; border-bottom: 3px solid #00A3E0; }}
            .section-title {{ font-size: 22px; font-weight: bold; color: #222; text-transform: uppercase; letter-spacing: 1px; }}
            .stat-row {{ background: white; border-radius: 12px; padding: 16px; margin-bottom: 12px; display: block; border: 1px solid #ddd; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div style="text-align: center; padding-bottom: 20px; color: #555; font-size: 18px; font-weight: bold;">{escape(str(title_prefix))} Daily Report • {escape(str(target_date))}</div>

            <div class="summary-card">
                <div style="font-size: 18px; font-weight: bold; opacity: 0.95; margin-bottom: 15px; letter-spacing: 1px;">TOTAL COLLECTED TODAY</div>
                <div style="font-size: 36px; font-weight: 900;">${cashflow:,.2f}</div>
            </div>

            <div class="stat-row">
                <table width="100%" style="table-layout: fixed; border-collapse: collapse;">
                    <tr>
                        <td width="70%" style="font-size: 18px; color: #0B1B3D; font-weight: bold;">New Orders Today</td>
                        <td width="30%" style="text-align: right; font-size: 26px; font-weight: bold; color: #333;">{new_jobs_count}</td>
                    </tr>
                    <tr>
                        <td colspan="2" style="font-size: 16px; color: #555; padding-top: 8px; font-weight: bold;">Order Value: ${new_jobs_total:,.2f}</td>
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
                <span class="section-title">✅ Completed Today</span>
            </div>
            {build_cards(data['picked_up'])}

            <div style="text-align: center; margin-top: 60px; padding: 30px; color: #888; font-size: 14px;">
                Generated by Overnight Printing Reporting System
            </div>
        </div>
    </body>
    </html>
    """
    return html


def generate_plain_text(data, spending_items, title_prefix="Overnight"):
    collected = sum(float(item.get('grandtotal') or 0) for item in data['paid'])
    new_value = sum(float(item.get('grandtotal') or 0) for item in data['new_today'])
    lines = [
        f"{title_prefix} Daily Report • {data['date']}",
        "",
        f"TOTAL COLLECTED TODAY: {format_currency(collected)}",
        f"New Orders Today: {len(data['new_today'])}",
        f"Order Value: {format_currency(new_value)}",
    ]
    for heading, items, kind in (
        ("Payments Today", data['paid'], 'paid'),
        ("Daily Spending", spending_items, 'spending'),
        ("Work In Progress", data['in_progress'], 'orders'),
        ("Ready for Pickup", data['ready'], 'orders'),
        ("Completed Today", data['picked_up'], 'orders'),
    ):
        lines.extend(("", heading))
        if not items:
            lines.append("No items recorded.")
        for item in items:
            if kind == 'spending':
                lines.append(f"{item['vendor']} — {item['description']} — {format_currency(item['amount'])}")
            else:
                line = f"#{item['invoicenumber']} — {item['account_display']} — {item['job_name']} — {format_currency(item['grandtotal'])}"
                if kind == 'paid':
                    line += f" — {item.get('transaction_type') or 'Payment'}"
                    if item.get('pay_method_display') not in (None, '', 'N/A'):
                        line += f" — {item['pay_method_display']}"
                    if item.get('is_partial'):
                        line += f" — PARTIAL · BAL DUE: {format_currency(item.get('current_balance'))}"
                lines.append(line)
        if kind == 'spending' and items:
            lines.append(f"Total Spending: {format_currency(sum(float(item['amount']) for item in items))}")
    return "\n".join(lines) + "\n"


async def send_report_email(data):
    settings = settings_service.load_settings()
    title_prefix = settings.get('report_title_prefix') or 'Overnight'
    spending_items = spending_service.get_spending_by_date(data['date'])
    html_content = generate_mobile_html(data, spending_items, title_prefix)

    message = EmailMessage()
    message["From"] = SMTP_CONFIG["user"]
    # Join list of emails into a comma-separated string for "To" header
    message["To"] = ", ".join(settings["boss_emails"])
    message["Subject"] = f"{title_prefix} {data['date']} Daily Report"
    message.set_content(generate_plain_text(data, spending_items, title_prefix))
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
