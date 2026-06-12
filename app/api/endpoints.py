from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from datetime import date, datetime
from app.services.report_service import get_report_data
from app.services.export_service import generate_report_xlsx
from app.services.email_service import send_report_email
from app.core.config import SMTP_CONFIG
from app.services import hide_service, spending_service, settings_service
from pydantic import BaseModel

router = APIRouter(prefix="/api")

class SettingsUpdate(BaseModel):
    boss_emails: list[str]
    auto_send_enabled: bool
    auto_send_time: str
    report_title_prefix: str

@router.get("/settings")
def get_settings():
    return settings_service.load_settings()

@router.post("/settings")
def update_settings(settings: SettingsUpdate):
    settings_service.save_settings(settings.dict())
    return {"status": "success"}

class SpendingCreate(BaseModel):
    vendor: str
    description: str
    amount: float

@router.get("/spending")
def get_spending(target_date: str):
    return spending_service.get_spending_by_date(target_date)

@router.post("/spending")
def add_spending(target_date: str, item: SpendingCreate):
    spending_service.add_spending(target_date, item.vendor, item.description, item.amount)
    return {"status": "success"}

@router.delete("/spending/{target_date}/{spending_id}")
def delete_spending(target_date: str, spending_id: str):
    spending_service.delete_spending(target_date, spending_id)
    return {"status": "success"}

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
