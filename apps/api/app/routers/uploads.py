from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from backend_core.schemas import UploadResponse


router = APIRouter(tags=["uploads"])


@router.post("/uploads/videos", response_model=UploadResponse)
def upload_video(request: Request, file: UploadFile = File(...)) -> UploadResponse:
    if file.filename is None:
        raise HTTPException(status_code=400, detail="file is required")
    runtime = request.app.state.runtime
    payload = runtime.service.upload_video(file.file, file.filename, file.content_type)
    return payload


@router.post("/uploads/texts", response_model=UploadResponse)
def upload_text(request: Request, file: UploadFile = File(...)) -> UploadResponse:
    if file.filename is None:
        raise HTTPException(status_code=400, detail="file is required")
    runtime = request.app.state.runtime
    payload = runtime.service.upload_text(file.file, file.filename, file.content_type)
    return payload
