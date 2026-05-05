from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
import markdown

from midi_event_handler.core.config import (
    WHATSNEW_PATH,
    WHATSNEW_SEEN_PATH,
    get_current_version,
)
from midi_event_handler.web import context

router = APIRouter()


@router.get("/meh/ui/help", response_class=HTMLResponse)
async def about_page(request: Request, version: str = Depends(get_current_version)):
    return context.templates.TemplateResponse(request, "help.html", {"version": version})


@router.get("/meh/ui/whatsnew", response_class=HTMLResponse)
async def whatsnew_page(request: Request, version=Depends(get_current_version)):
    if not WHATSNEW_PATH.exists():
        raise HTTPException(status_code=404, detail="Nothing new")

    # WHATSNEW_PATH is author-controlled (ships with the app), so | safe in the
    # template is acceptable. If this ever accepts user content, sanitize first.
    content = markdown.markdown(WHATSNEW_PATH.read_text())
    WHATSNEW_SEEN_PATH.touch()
    return context.templates.TemplateResponse(request, "whatsnew.html", {"content": content, "version": version})
