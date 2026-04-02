from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["admin-ui-page"])
admin_index = Path("static/admin/index.html")


@router.get("/cs-server/admin-ui")
def admin_ui_page():
    return FileResponse(admin_index)


@router.get("/cs-server/admin-ui/")
def admin_ui_page_slash():
    return FileResponse(admin_index)
