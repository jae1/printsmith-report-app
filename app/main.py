from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import endpoints, views
import asyncio
from datetime import datetime
from app.services import settings_service, email_service, report_service

def create_app() -> FastAPI:
    app = FastAPI(title="PrintSmith Report App")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(views.router)
    app.include_router(endpoints.router)

    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task(schedule_email_task())

    return app

async def schedule_email_task():
    last_sent_date = None
    while True:
        try:
            now = datetime.now()
            settings = settings_service.load_settings()
            
            if settings.get("auto_send_enabled"):
                target_time = settings.get("auto_send_time", "17:00")
                target_days = settings.get("auto_send_days", [])
                
                current_time_str = now.strftime("%H:%M")
                current_day = now.weekday() # 0 = Monday, 6 = Sunday
                current_date_str = now.strftime("%Y-%m-%d")
                
                if current_day in target_days and current_time_str == target_time:
                    if last_sent_date != current_date_str:
                        print(f"[{now}] Triggering auto-report email...")
                        data = report_service.get_report_data()
                        await email_service.send_report_email(data)
                        last_sent_date = current_date_str
                        print("Auto-report email sent successfully.")
        except Exception as e:
            print(f"Error in auto-send task: {e}")
            
        await asyncio.sleep(30) # Check every 30 seconds

app = create_app()
