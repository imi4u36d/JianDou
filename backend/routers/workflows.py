from __future__ import annotations
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v3/workflows", tags=["workflows"])

_workflows: dict[str, dict] = {}
_next_id = 1


@router.get("")
async def list_workflows():
    return list(_workflows.values())


@router.post("")
async def create_workflow():
    global _next_id
    wid = str(_next_id)
    _next_id += 1
    wf = {
        "workflow_id": wid,
        "title": "stub",
        "status": "DRAFT",
        "storyboardVersions": [],
        "keyframeVersions": [],
        "videoVersions": [],
    }
    _workflows[wid] = wf
    return wf


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    wf = _workflows.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="workflow_not_found")
    return wf


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    if workflow_id not in _workflows:
        raise HTTPException(status_code=404, detail="workflow_not_found")
    del _workflows[workflow_id]
    return {"success": True, "workflow_id": workflow_id}


@router.patch("/{workflow_id}/settings")
async def update_workflow_settings(workflow_id: str):
    wf = _workflows.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="workflow_not_found")
    return {"workflow_id": workflow_id, "status": wf.get("status", "DRAFT")}


# --- Storyboard endpoints ---


@router.post("/{workflow_id}/storyboard")
async def generate_storyboard(workflow_id: str):
    return {"message": "not yet implemented", "workflow_id": workflow_id}


@router.get("/{workflow_id}/storyboard/versions")
async def list_storyboard_versions(workflow_id: str):
    return []


@router.get("/{workflow_id}/storyboard/versions/{version_id}")
async def get_storyboard_version(workflow_id: str, version_id: str):
    return {"workflow_id": workflow_id, "version_id": version_id, "message": "not yet implemented"}


@router.post("/{workflow_id}/storyboard/adjust")
async def adjust_storyboard(workflow_id: str):
    return {"message": "not yet implemented", "workflow_id": workflow_id}


@router.post("/{workflow_id}/storyboard/versions/{version_id}/select")
async def select_storyboard_version(workflow_id: str, version_id: str):
    return {"message": "not yet implemented", "workflow_id": workflow_id, "version_id": version_id}


# --- Character sheet endpoints ---


@router.get("/{workflow_id}/character-sheets")
async def list_character_sheets(workflow_id: str):
    return []


@router.post("/{workflow_id}/character-sheets/generate")
async def generate_character_sheets(workflow_id: str):
    return {"message": "not yet implemented", "workflow_id": workflow_id}


@router.post("/{workflow_id}/character-sheets/versions/{version_id}/select")
async def select_character_sheet_version(workflow_id: str, version_id: str):
    return {"message": "not yet implemented", "workflow_id": workflow_id, "version_id": version_id}


# --- Keyframe endpoints ---


@router.post("/{workflow_id}/keyframes")
async def generate_keyframes(workflow_id: str):
    return {"message": "not yet implemented", "workflow_id": workflow_id}


@router.get("/{workflow_id}/keyframes/versions")
async def list_keyframe_versions(workflow_id: str):
    return []


@router.get("/{workflow_id}/keyframes/versions/{version_id}")
async def get_keyframe_version(workflow_id: str, version_id: str):
    return {"workflow_id": workflow_id, "version_id": version_id, "message": "not yet implemented"}


@router.post("/{workflow_id}/keyframes/versions/{version_id}/select")
async def select_keyframe_version(workflow_id: str, version_id: str):
    return {"message": "not yet implemented", "workflow_id": workflow_id, "version_id": version_id}


# --- Video endpoints ---


@router.post("/{workflow_id}/videos")
async def generate_videos(workflow_id: str):
    return {"message": "not yet implemented", "workflow_id": workflow_id}


@router.get("/{workflow_id}/videos/versions")
async def list_video_versions(workflow_id: str):
    return []


@router.get("/{workflow_id}/videos/versions/{version_id}")
async def get_video_version(workflow_id: str, version_id: str):
    return {"workflow_id": workflow_id, "version_id": version_id, "message": "not yet implemented"}


@router.post("/{workflow_id}/videos/versions/{version_id}/select")
async def select_video_version(workflow_id: str, version_id: str):
    return {"message": "not yet implemented", "workflow_id": workflow_id, "version_id": version_id}


# --- Workflow rating ---


@router.post("/{workflow_id}/effect-rating")
async def rate_workflow(workflow_id: str):
    return {"message": "not yet implemented", "workflow_id": workflow_id}


# --- Retry ---


@router.post("/{workflow_id}/retry")
async def retry_workflow(workflow_id: str):
    return {"message": "not yet implemented", "workflow_id": workflow_id}
