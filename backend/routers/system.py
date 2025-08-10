import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from core.config import MEDIA_DIR, YOUTUBE_API_KEY


router = APIRouter()


@router.get("/media/{filename}")
def get_media(filename: str):
    filepath = os.path.join(MEDIA_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath)


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "supported_platforms": ["Instagram", "VK", "Likee", "YouTube", "TikTok"],
        "youtube_api_available": bool(YOUTUBE_API_KEY),
        "likee_extractors": ["mobile_request", "api_request", "meta_tags"],
    }


@router.get("/config")
def get_config():
    return {
        "youtube_api_configured": bool(YOUTUBE_API_KEY),
        "media_directory": MEDIA_DIR,
        "supported_platforms": {
            "youtube": True,
            "instagram": True,
            "likee": True,
            "vk": True,
            "tiktok": True,
        },
    }


