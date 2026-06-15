from __future__ import annotations
from fastapi import APIRouter

router = APIRouter(prefix="/api/v3/material-center", tags=["material-center"])


@router.get("/categories")
async def list_categories():
    return []


@router.get("/library")
async def list_library():
    return []


@router.get("/search")
async def search_materials():
    return []
