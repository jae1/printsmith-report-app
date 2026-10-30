import aiosmtplib
from datetime import date
from email.message import EmailMessage
from email.utils import formataddr
from html import escape
from app.core.config import SMTP_CONFIG
from pathlib import Path
from app.services import settings_service, spending_service

LOGO_CID = "overnight-logo"
LOGO_PATH = Path(__file__).resolve().parent.parent / "static" / "email-logo.png"


REPORT_SECTIONS = (
    ("new_today", "New Today", "#00A3E0"),
    ("in_progress", "In Progress", "#7950ac"),
    ("ready", "Ready for Pickup", "#27805a"),
    ("picked_up", "Completed Today", "#c47835"),
    ("paid", "Paid Today", "#a47a17"),
    ("spending", "Daily Spending", "#b84b4b"),
)


def format_currency(val):
    return "${:,.2f}".format(float(val or 0))


def _display_date(value):
    if not value:
        return "-"
    if isinstance(value, date):
        return value.strftime("%m/%d/%Y")
    try:
        return date.fromisoformat(str(value).split("T")[0]).strftime("%m/%d/%Y")
    except ValueError:
        return "-"


def _summary(data, spending_items):
    collected = sum(float(item.get("grandtotal") or 0) for item in data["paid"])
    new_value = sum(float(item.get("grandtotal") or 0) for item in data["new_today"])
    spent = sum(float(item.get("amount") or 0) for item in spending_items)
    return (
        ("Collected today", format_currency(collected), ""),
        ("New orders", str(len(data["new_today"])), format_currency(new_value) + " order value"),
        ("Recorded spending", format_currency(spent), ""),
    )


def _invoice_notes(item, section):
    notes = [str(item["hold_name"])] if item.get("hold_name") else []
    if section == "paid":
        if item.get("transaction_type"):
            notes.append(str(item["transaction_type"]))
        notes.append("Method: " + str(item.get("pay_method_display") or "N/A"))
    if item.get("is_partial"):
        notes.extend(("PARTIAL", "BAL DUE: " + format_currency(item.get("current_balance"))))
    elif item.get("payment_status"):
        notes.append(str(item["payment_status"]))
    if item.get("contact_display"):
        notes.append("Contact: " + str(item["contact_display"]))
    if section == "in_progress" and item.get("status"):
        notes.append("Status: " + str(item["status"]))
    if section not in ("new_today", "paid") and item.get("ordereddate"):
        notes.append("Ordered: " + _display_date(item["ordereddate"]))
    if section == "picked_up" and item.get("pickupdate"):
        notes.append("Completed: " + _display_date(item["pickupdate"]))
    return notes


def generate_mobile_html(data, spending_items=None, title_prefix="Overnight"):
    if spending_items is None:
        spending_items = spending_service.get_spending_by_date(data["date"])
    metric_cells = ''.join(f'<td class="metric" width="33.33%" valign="top" style="padding:7px 10px;border:1px solid #d8dde3;">'
                           f'<div style="font-size:13px;color:#59677b;">{label}</div>'
                           f'<div style="font-size:19px;font-weight:700;line-height:1.3;color:#0B1B3D;overflow-wrap:anywhere;">{value}</div>'
                           + (f'<div style="font-size:13px;color:#59677b;">{detail}</div>' if detail else '') + '</td>'
                           for label, value, detail in _summary(data, spending_items))
    sections = []
    for key, heading, accent in REPORT_SECTIONS:
        items = spending_items if key == "spending" else data[key]
        rows = []
        amount_color = "#9f3232" if key == "spending" else "#18623e" if key == "paid" else "#0B1B3D"
        for item in items:
            if key == "spending":
                title = str(item["vendor"])
                description = str(item.get("description") or "")
                notes = ["Card: " + str(item["card"])] if item.get("card") else []
                amount = item["amount"]
            else:
                title = " · ".join(str(part) for part in (item["invoicenumber"], item.get("account_display")) if part)
                description = str(item.get("job_name") or "")
                notes = _invoice_notes(item, key)
                amount = item.get("grandtotal") or 0
            rows.append(f'<tr><td style="padding:7px 10px;border-bottom:1px solid #e6ebf1;vertical-align:middle;overflow-wrap:anywhere;word-break:break-word;">'
                        f'<div style="font-weight:600;color:#0B1B3D;">{escape(title)}</div>'
                        f'<div>{escape(description)}</div><div style="font-size:13px;color:#59677b;margin-top:2px;">{escape(" · ".join(notes))}</div></td>'
                        f'<td width="30%" align="right" style="padding:7px 10px;border-bottom:1px solid #e6ebf1;vertical-align:middle;white-space:nowrap;color:{amount_color};font-weight:600;">{format_currency(amount)}</td></tr>')
        if items:
            section_total = sum(float(item.get("amount" if key == "spending" else "grandtotal") or 0) for item in items)
            rows.append(f'<tr style="background:#f2f5f9;"><td align="right" style="padding:7px 10px;font-weight:600;">Total</td>'
                        f'<td align="right" style="padding:7px 10px;white-space:nowrap;font-weight:600;color:{amount_color};">{format_currency(section_total)}</td></tr>')
        else:
            rows.append('<tr><td colspan="2" style="padding:12px 10px;color:#59677b;">No items for this date.</td></tr>')
        sections.append(f'<table class="report-section" width="100%" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;background:white;border:1px solid #d8dde3;border-top:2px solid {accent};margin-top:16px;">'
                        f'<caption style="text-align:left;padding:14px 0 6px;font-size:17px;font-weight:700;color:#0B1B3D;">{heading} <span style="font-size:13px;font-weight:400;color:#59677b;">({len(items)})</span></caption>'
                        '<tbody>' + ''.join(rows) + '</tbody></table>')
    display_date = _display_date(data["date"])
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Daily Report</title>
<style>@media only screen and (max-width:480px) {{ .email-padding {{ padding:12px 8px !important; }} .metric {{ display:block !important; width:auto !important; }} }}</style></head>
<body style="margin:0;background:#f5f6f7;color:#24344d;-webkit-text-size-adjust:100%;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.45;"><tr><td class="email-padding" align="center" style="padding:20px 16px;">
<!--[if mso]><table role="presentation" width="720" align="center"><tr><td><![endif]-->
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:720px;width:100%;border-collapse:collapse;"><tr><td>
<img src="cid:{LOGO_CID}" width="200" height="63" alt="Overnight Printing Seattle" style="display:block;width:200px;height:auto;border:0;margin:0 auto 12px;">
<h1 style="margin:0 0 6px;text-align:center;font-size:25px;line-height:1.2;color:#0B1B3D;">{escape(str(title_prefix))} Daily Report</h1>
<p style="margin:0 0 14px;text-align:center;color:#59677b;font-size:13px;">Report date: {display_date}</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="width:100%;table-layout:fixed;border-collapse:collapse;background:white;"><tr>{metric_cells}</tr></table>
{''.join(sections)}
</td></tr></table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr></table></body></html>'''


def generate_plain_text(data, spending_items, title_prefix="Overnight"):
    lines = [
        "Overnight Printing Seattle", f"{title_prefix} Daily Report · {_display_date(data['date'])}",
        "",
    ] + [f"{label}: {value}" + (f" ({detail})" if detail else "") for label, value, detail in _summary(data, spending_items)]
    for key, heading, _ in REPORT_SECTIONS:
        items = spending_items if key == "spending" else data[key]
        lines.extend(("", f"{heading} ({len(items)})"))
        if not items:
            lines.append("No items for this date.")
        for item in items:
            if key == "spending":
                line = f"{item['vendor']} — {item.get('description') or ''} — {format_currency(item['amount'])}"
                if item.get("card"):
                    line += f" — Card: {item['card']}"
            else:
                line = " — ".join(str(part) for part in (item["invoicenumber"], item.get("account_display"), item.get("job_name"),
                                                         format_currency(item.get("grandtotal"))) if part)
                notes = _invoice_notes(item, key)
                if notes:
                    line += " — " + " · ".join(notes)
            lines.append(line)
        if items:
            total = sum(float(item.get("amount" if key == "spending" else "grandtotal") or 0) for item in items)
            lines.append("Total: " + format_currency(total))
    return "\n".join(lines) + "\n"


async def send_report_email(data):
    settings = settings_service.load_settings()
    title_prefix = settings.get('report_title_prefix') or 'Overnight'
    spending_items = spending_service.get_spending_by_date(data['date'])
    html_content = generate_mobile_html(data, spending_items, title_prefix)

    message = EmailMessage()
    message["From"] = formataddr(("Overnight Printing Seattle", SMTP_CONFIG["user"]))
    # Join list of emails into a comma-separated string for "To" header
    message["To"] = ", ".join(settings["boss_emails"])
    report_date = date.fromisoformat(data['date']).strftime('%m/%d/%Y')
    message["Subject"] = f"Overnight - {report_date} Daily Report"
    message.set_content(generate_plain_text(data, spending_items, title_prefix))
    message.add_alternative(html_content, subtype="html")
    message.get_payload()[1].add_related(LOGO_PATH.read_bytes(), "image", "png", cid=f"<{LOGO_CID}>",
                                         filename="overnight-logo.png", disposition="inline")

    await aiosmtplib.send(
        message,
        hostname=SMTP_CONFIG["host"],
        port=SMTP_CONFIG["port"],
        username=SMTP_CONFIG["user"],
        password=SMTP_CONFIG["password"],
        use_tls=SMTP_CONFIG["port"] == 465,
        start_tls=SMTP_CONFIG["port"] == 587,
    )
