from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import markdown

from midi_event_handler.core.config import (
    WHATSNEW_PATH,
    get_current_version
)

def get_templates_path():
    if "__compiled__" in globals():
        return Path("templates")
    return Path(__file__).parent / "templates"

templates = Jinja2Templates(directory=get_templates_path())

router = APIRouter()

@router.get("/meh.ui/help", response_class=HTMLResponse)
async def about_page(request: Request, version: str = Depends(get_current_version)):
    return templates.TemplateResponse("help.html", {
        "request": request,
        "version": version
    })

@router.get("/meh.ui/whatsnew", response_class=HTMLResponse)
def whatsnew_page(request: Request, version = Depends(get_current_version)):
    if not WHATSNEW_PATH.exists():
        raise HTTPException(status_code=404, detail="Nothing new")
    
    content = markdown.markdown(WHATSNEW_PATH.read_text())
    WHATSNEW_PATH.unlink()
    return templates.TemplateResponse("whatsnew.html", {
        "request": request,
        "content": content,
        "version": version
    })
    