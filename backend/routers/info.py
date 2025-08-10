from fastapi import APIRouter, Form, HTTPException

from core.config import YOUTUBE_API_KEY
from services.utils import extract_video_id_from_url
from services.likee import is_likee_url, extract_video_id_from_likee_url
from services.youtube import get_youtube_video_info_via_api


router = APIRouter()


@router.post("/extract-video-id")
async def extract_video_id_endpoint(url: str = Form(...)):
    video_url = url.strip()
    if not video_url:
        raise HTTPException(status_code=400, detail='URL not provided. Send POST request with {"url": "https://youtube.com/watch?v=VIDEO_ID"}')
    # YouTube
    try:
        video_id = extract_video_id_from_url(video_url)
        return {
            "video_id": video_id,
            "original_url": video_url,
            "api_key": YOUTUBE_API_KEY if YOUTUBE_API_KEY else None,
            "platform": "youtube",
        }
    except ValueError:
        pass
    # Likee
    if is_likee_url(video_url):
        likee_id = extract_video_id_from_likee_url(video_url)
        return {
            "video_id": likee_id,
            "original_url": video_url,
            "platform": "likee",
        }
    # Other
    return {
        "video_id": None,
        "original_url": video_url,
        "platform": "other",
    }


@router.post("/youtube/info")
async def get_youtube_info_api(video_id: str = Form(...)):
    if not YOUTUBE_API_KEY:
        raise HTTPException(status_code=500, detail="YouTube API ключ не настроен")
    info = get_youtube_video_info_via_api(video_id)
    return {"success": True, "data": info, "source": "youtube_api"}


@router.post("/likee/info")
async def get_likee_info(url: str = Form(...)):
    from services.likee import extract_likee_info, is_likee_url
    if not is_likee_url(url):
        raise HTTPException(status_code=400, detail="Это не ссылка на Likee")
    info = extract_likee_info(url)
    if not info:
        raise HTTPException(status_code=404, detail="Информация о видео не найдена")
    return {
        "success": True,
        "data": info,
        "video_available": bool(info.get('video_url')),
        "extraction_source": info.get('source', 'unknown'),
    }


