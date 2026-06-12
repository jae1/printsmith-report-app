from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from datetime import date, datetime
from app.services.report_service import get_report_data
from app.services.export_service import generate_report_xlsx
from app.services.email_service import send_report_email
from app.core.config import SMTP_CONFIG
from app.services import hide_service

router = APIRouter(prefix="/api")

@router.get("/hidden")
def get_hidden():
    return hide_service.get_hidden_invoices()

@router.post("/hide/{invoice_number}")
def hide_invoice(invoice_number: str):
    hide_service.hide_invoice(invoice_number)
    return {"status": "success"}

@router.post("/unhide/{invoice_number}")
def unhide_invoice(invoice_number: str):
    hide_service.unhide_invoice(invoice_number)
    return {"status": "success"}

@router.get("/report/email")
async def report_email(target_date: str = None):
    if target_date:
        d = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        d = date.today()

    data = get_report_data(d)
    try:
        await send_report_email(data)
        return {"status": "success", "message": f"Email sent to {SMTP_CONFIG['to_email']}"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@router.get("/report")
def report(target_date: str = None):
    if target_date:
        d = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        d = date.today()
    return get_report_data(d)

@router.get("/export")
def export(target_date: str = None):
    if target_date:
        d = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        d = date.today()

    data = get_report_data(d)
    output = generate_report_xlsx(data)

    filename = f"report_{data['date']}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
