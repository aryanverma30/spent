"""Dashboard route — serves the Chase-like spending tracker web UI."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["dashboard"])

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Serve the main spending dashboard page."""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request},
    )
