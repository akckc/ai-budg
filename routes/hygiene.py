from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse
from routes.dashboard import templates
from services.hygiene_service import get_orphan_groups, get_known_categories, reclassify_orphan_group

router = APIRouter()


@router.get("/hygiene")
def hygiene_page(request: Request):
    return templates.TemplateResponse(request, "hygiene.html")


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
