from fastapi import APIRouter, UploadFile, File
from fastapi.responses import HTMLResponse
from services.csv_ingest_service import ingest_csv

router = APIRouter()


@router.get("/upload", response_class=HTMLResponse)
def upload_page():
    return """
        ... same HTML ...
    """


@router.post("/upload")
def upload_csv(file: UploadFile = File(...)):
    contents_bytes = file.file.read()

    try:
        contents = contents_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return {"success": False, "error": "File must be UTF-8 encoded CSV"}

    return ingest_csv(contents)