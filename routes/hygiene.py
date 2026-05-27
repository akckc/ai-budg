from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from services.hygiene_service import get_orphan_groups, get_known_categories, reclassify_orphan_group

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/hygiene")
def hygiene_page(request: Request):
    return templates.TemplateResponse("hygiene.html", {"request": request})


@router.get("/hygiene/groups")
def hygiene_groups():
    return {
        "orphan_groups": get_orphan_groups(),
        "known_categories": get_known_categories(),
    }


@router.post("/hygiene/reclassify-group")
def reclassify_group(
    current_category: str = Form(...),
    new_category: str = Form(...),
):
    updated = reclassify_orphan_group(current_category, new_category)
    return JSONResponse({"status": "ok", "updated": updated})
