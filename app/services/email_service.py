from email.message import EmailMessage
from html import escape

import aiosmtplib

from app.core.config import SMTP_CONFIG
from app.services import settings_service, spending_service


def format_currency(value):
    return "${:,.2f}".format(float(value or 0))


def render_email_content(data, title_prefix="Overnight"):
    target_date = str(data["date"])
    title = f"{title_prefix} {target_date} Daily Report".strip()
    spending = spending_service.get_spending_by_date(target_date)
    collected = sum(float(item.get("grandtotal") or 0) for item in data["paid"])
    spent = sum(float(item.get("amount") or 0) for item in spending)
    new_value = sum(float(item.get("grandtotal") or 0) for item in data["new_today"])
    partial_count = sum(bool(item.get("is_partial")) for item in data["paid"])

    summary = [
        ("Collected today", format_currency(collected)),
        ("Recorded spending", format_currency(spent)),
        ("New orders", f"{len(data['new_today'])} · {format_currency(new_value)} order value"),
        ("Ready for pickup", str(len(data["ready"]))),
        ("Paid today with balance due", str(partial_count)),
    ]
    sections = [
        ("Payments Today", data["paid"], "paid"),
        ("Daily Spending", spending, "spending"),
        ("New Orders Today", data["new_today"], "orders"),
        ("Work In Progress", data["in_progress"], "orders"),
        ("Ready for Pickup", data["ready"], "orders"),
        ("Completed Today", data["picked_up"], "orders"),
    ]

    def card(item, kind):
        if kind == "spending":
            heading = item.get("vendor") or "Unknown vendor"
            description = item.get("description") or ""
            amount = item.get("amount")
            label, color = "Spent", "#B42318"
            details = ""
        else:
            heading = f"#{item.get('invoicenumber') or ''} · {item.get('account_display') or '-'}"
            description = item.get("job_name") or ""
            amount = item.get("grandtotal")
            label, color = ("Collected", "#176B43") if kind == "paid" else ("Order value", "#0B1B3D")
            details = ""
            if kind == "paid":
                parts = [f"Transaction: {item.get('transaction_type') or 'Payment'}"]
                method = item.get("pay_method_display")
                if method and method != "N/A":
                    parts.append(method)
                if item.get("is_partial"):
                    parts.append(f"Balance due: {format_currency(item.get('current_balance'))}")
                details = " · ".join(escape(str(part)) for part in parts)
            elif item.get("status"):
                details = escape(str(item["status"]))

        return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;background:#FFFFFF;border:1px solid #DCE4EA;margin:0 0 10px 0;">
          <tr><td style="padding:12px 14px 4px;color:#0B1B3D;font-size:16px;font-weight:bold;">{escape(str(heading))}</td></tr>
          <tr><td style="padding:0 14px 6px;color:#344054;font-size:14px;">{escape(str(description))}</td></tr>
          {f'<tr><td style="padding:0 14px 6px;color:#475467;font-size:13px;">{details}</td></tr>' if details else ''}
          <tr><td style="padding:0 14px 12px;text-align:right;color:{color};font-size:16px;font-weight:bold;">{label}: {format_currency(amount)}</td></tr>
        </table>"""

    summary_html = "".join(
        f'<tr><td style="padding:8px 12px;border-bottom:1px solid #E6EBF0;color:#344054;font-size:14px;">{escape(label)}</td>'
        f'<td style="padding:8px 12px;border-bottom:1px solid #E6EBF0;text-align:right;color:#0B1B3D;font-size:14px;font-weight:bold;">{escape(value)}</td></tr>'
        for label, value in summary
    )
    sections_html = "".join(
        f'<h2 style="margin:26px 0 10px;color:#0B1B3D;font-size:18px;border-bottom:2px solid #00A3E0;padding-bottom:8px;">{escape(name)} · {len(items)}</h2>'
        + ("".join(card(item, kind) for item in items) if items else '<p style="color:#475467;font-size:14px;">No items recorded.</p>')
        for name, items, kind in sections
    )
    html = f"""<!DOCTYPE html><html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="margin:0;padding:16px;background:#F3F6F9;font-family:Arial,Helvetica,sans-serif;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;border-collapse:collapse;">
        <tr><td style="padding:18px 16px;background:#0B1B3D;color:#FFFFFF;font-size:22px;font-weight:bold;">{escape(title)}</td></tr>
        <tr><td style="padding:16px;background:#FFFFFF;">
          <p style="margin:0 0 12px;color:#0B1B3D;font-size:16px;font-weight:bold;">Management summary</p>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border:1px solid #DCE4EA;">{summary_html}</table>
          {sections_html}
          <p style="margin:28px 0 0;color:#667085;font-size:12px;">Generated by Overnight Printing Reporting System</p>
        </td></tr>
      </table>
    </body></html>"""

    text_lines = [title, "", "Management summary"]
    text_lines.extend(f"{label}: {value}" for label, value in summary)
    for name, items, kind in sections:
        text_lines.extend(("", f"{name} ({len(items)})"))
        if not items:
            text_lines.append("No items recorded.")
        for item in items:
            if kind == "spending":
                text_lines.append(f"{item.get('vendor') or 'Unknown vendor'} | {item.get('description') or ''} | Spent: {format_currency(item.get('amount'))}")
            else:
                line = f"#{item.get('invoicenumber') or ''} | {item.get('account_display') or '-'} | {item.get('job_name') or ''} | {'Collected' if kind == 'paid' else 'Order value'}: {format_currency(item.get('grandtotal'))}"
                if kind == "paid":
                    line += f" | Transaction: {item.get('transaction_type') or 'Payment'}"
                    if item.get("pay_method_display") not in (None, "", "N/A"):
                        line += f" | {item['pay_method_display']}"
                    if item.get("is_partial"):
                        line += f" | Balance due: {format_currency(item.get('current_balance'))}"
                elif item.get("status"):
                    line += f" | {item['status']}"
                text_lines.append(line)
    return html, "\n".join(text_lines) + "\n"


def generate_mobile_html(data):
    return render_email_content(data)[0]


async def send_report_email(data):
    settings = settings_service.load_settings()
    html_content, text_content = render_email_content(data, settings.get("report_title_prefix") or "Overnight")

    message = EmailMessage()
    message["From"] = SMTP_CONFIG["user"]
    message["To"] = ", ".join(settings["boss_emails"])
    message["Subject"] = f"{settings.get('report_title_prefix') or 'Overnight'} {data['date']} Daily Report"
    message.set_content(text_content)
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
