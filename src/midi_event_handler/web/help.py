from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_path)

router = APIRouter()

@router.get("/help", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse("help.html", {"request": request})
