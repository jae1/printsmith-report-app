import aiosmtplib
from email.message import EmailMessage
from app.core.config import SMTP_CONFIG

def format_currency(val):
    return "${:,.2f}".format(float(val or 0))

def generate_mobile_html(data):
    cashflow = sum(float(item.get('grandtotal', 0) or 0) for item in data['paid'])
    new_jobs_count = len(data['new_today'])
    in_progress_count = len(data['in_progress'])
    picked_up_count = len(data['picked_up'])

    # Building "Cards" instead of tables for mobile
    def build_cards(items, section_name):
        if not items:
            return "<p style='color: #999; font-style: italic;'>데이터 없음</p>"
        
        cards_html = ""
        for item in items[:10]: # Top 10 for brevity in email
            # Only show status badge for In Progress section
            status_badge = ""
            if section_name == 'in_progress' and item.get('status'):
                status_badge = f'<span style="background: #f0f0f0; padding: 2px 8px; border-radius: 4px; font-size: 11px; color: #555;">{item["status"]}</span>'

            cards_html += f"""
            <div style="background: #ffffff; border: 1px solid #eee; border-radius: 8px; padding: 12px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <table width="100%" cellspacing="0" cellpadding="0">
                    <tr>
                        <td style="font-weight: bold; color: #333; font-size: 16px; text-align: left; padding-bottom: 4px;">
                            #{item['invoicenumber']} - {item['account_display']}
                        </td>
                        <td style="font-weight: bold; color: #28a745; font-size: 16px; text-align: right; white-space: nowrap; padding-bottom: 4px; vertical-align: top;">
                            {format_currency(item.get('grandtotal', 0))}
                        </td>
                    </tr>
                </table>
                <div style="color: #666; font-size: 14px;">{item['job_name']}</div>
                {f'<div style="margin-top: 8px;">{status_badge}</div>' if status_badge else ''}
            </div>
            """
        if len(items) > 10:
            cards_html += f"<p style='font-size: 12px; color: #999; text-align: center;'>...외 {len(items)-10}건 더 있음</p>"
        return cards_html

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; background-color: #f4f7f9; margin: 0; padding: 10px; }}
            .container {{ max-width: 500px; margin: 0 auto; }}
            .header {{ text-align: center; padding: 20px 0; }}
            .summary-box {{ background: #4472C4; color: white; border-radius: 12px; padding: 25px; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .summary-label {{ font-size: 16px; opacity: 0.9; margin-bottom: 8px; }}
            .summary-value {{ font-size: 40px; font-weight: bold; }}
            .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 25px; }}
            .stat-card {{ background: white; border-radius: 10px; padding: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            .stat-num {{ font-size: 22px; font-weight: bold; display: block; }}
            .stat-lbl {{ font-size: 13px; color: #888; text-transform: uppercase; margin-top: 4px; }}
            .section-title {{ font-size: 18px; font-weight: bold; color: #333; margin: 25px 0 15px 5px; border-left: 5px solid #4472C4; padding-left: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div style="font-size: 22px; font-weight: bold; color: #333;">Daily Report Summary</div>
                <div style="font-size: 16px; color: #888;">{data['date']}</div>
            </div>

            <div class="summary-box">
                <div class="summary-label">오늘의 총 수금액</div>
                <div class="summary-value">{format_currency(cashflow)}</div>
            </div>

            <div style="width: 100%; overflow: hidden; margin-bottom: 20px;">
                <table width="100%" cellspacing="0" cellpadding="0">
                    <tr>
                        <td width="32%" style="background: white; border-radius: 8px; padding: 15px; text-align: center;">
                            <span style="font-size: 22px; font-weight: bold; color: #4472C4;">{new_jobs_count}</span>
                            <div style="font-size: 12px; color: #999; margin-top: 5px;">신규 주문</div>
                        </td>
                        <td width="2%"></td>
                        <td width="32%" style="background: white; border-radius: 8px; padding: 15px; text-align: center;">
                            <span style="font-size: 22px; font-weight: bold; color: #7030A0;">{in_progress_count}</span>
                            <div style="font-size: 12px; color: #999; margin-top: 5px;">진행 중</div>
                        </td>
                        <td width="2%"></td>
                        <td width="32%" style="background: white; border-radius: 8px; padding: 15px; text-align: center;">
                            <span style="font-size: 22px; font-weight: bold; color: #ED7D31;">{picked_up_count}</span>
                            <div style="font-size: 12px; color: #999; margin-top: 5px;">출고 완료</div>
                        </td>
                    </tr>
                </table>
            </div>

            <div class="section-title">주요 수금 내역 (Paid)</div>
            {build_cards(data['paid'], 'paid')}

            <div class="section-title">주요 진행 중 (In Progress)</div>
            {build_cards(data['in_progress'], 'in_progress')}

            <div style="text-align: center; margin-top: 30px; padding: 20px; color: #aaa; font-size: 11px; border-top: 1px solid #eee;">
                본 리포트는 PrintSmith 시스템에서 자동으로 생성되었습니다.
            </div>
        </div>
    </body>
    </html>
    """
    return html

async def send_report_email(data):
    html_content = generate_mobile_html(data)
    
    message = EmailMessage()
    message["From"] = SMTP_CONFIG["user"]
    message["To"] = SMTP_CONFIG["to_email"]
    message["Subject"] = f"[{data['date']}] PrintSmith Daily Summary Report"
    message.set_content("이 메일은 HTML 전용입니다. HTML 지원 메일 클라이언트를 사용해 주세요.")
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
