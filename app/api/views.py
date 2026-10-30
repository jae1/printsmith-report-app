from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse
import os

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def index():
    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


@router.get("/logo.png")
def logo():
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "static", "email-logo.png"), media_type="image/png")
