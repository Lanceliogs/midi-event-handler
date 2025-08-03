from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

def get_templates_path():
    if "__compiled__" in globals():
        return Path("templates")
    return Path(__file__).parent / "templates"

templates = Jinja2Templates(directory=get_templates_path())

router = APIRouter()

@router.get("/help", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse("help.html", {"request": request})
