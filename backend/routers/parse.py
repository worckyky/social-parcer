from typing import Optional
import os
import uuid

import yt_dlp
from fastapi import APIRouter, Form, HTTPException

from core.config import MEDIA_DIR, YOUTUBE_API_KEY
from services.utils import (
    is_youtube_url,
    extract_video_id_from_url,
    clean_thumbnail_url,
    create_cookies_file,
)
from services.instagram import is_instagram_url
from services.vk import is_vk_url, raise_vk_specific_http_if_any
from services.tiktok import is_tiktok_url
from services.likee import (
    is_likee_url,
    resolve_likee_url,
    extract_likee_info,
    parse_short_number,
    get_mobile_headers,
)
from services.youtube import get_youtube_video_info_via_api
from services.utils import create_robust_session


router = APIRouter()


def _get_video_info(url: str, sessionid: str = "", csrftoken: str = "", ds_user_id: str = ""):
    try:
        if is_youtube_url(url):
            try:
                video_id = extract_video_id_from_url(url)
                if YOUTUBE_API_KEY:
                    try:
                        youtube_info = get_youtube_video_info_via_api(video_id)
                        return youtube_info
                    except Exception:
                        pass
            except ValueError:
                pass

        if is_likee_url(url):
            try:
                url = resolve_likee_url(url)
            except HTTPException:
                pass
            likee_info = extract_likee_info(url)
            if likee_info and likee_info.get('video_url'):
                views = parse_short_number(likee_info.get('views', 0))
                likes = parse_short_number(likee_info.get('likes', 0))
                comments = parse_short_number(likee_info.get('comments', 0))
                thumbnail_url = likee_info.get('thumbnail')
                if thumbnail_url:
                    thumbnail_url = clean_thumbnail_url(thumbnail_url)
                return {
                    "title": likee_info.get('title', 'Likee Video'),
                    "uploader": likee_info.get('author', 'Unknown'),
                    "channel": likee_info.get('author', 'Unknown'),
                    "view_count": views,
                    "like_count": likes,
                    "comment_count": comments,
                    "thumbnail": thumbnail_url,
                    "description": likee_info.get('title', ''),
                    "comments": [],
                    "url": url,
                    "webpage_url": url,
                    "_likee_video_url": likee_info.get('video_url'),
                    "_likee_post_id": likee_info.get('post_id'),
                    "_likee_author_id": likee_info.get('author_id'),
                    "_likee_upload_date": likee_info.get('upload_date'),
                    "_likee_shares": parse_short_number(likee_info.get('shares', 0)),
                    "_likee_downloads": parse_short_number(likee_info.get('downloads', 0)),
                }
            else:
                raise HTTPException(status_code=404, detail="Видео Likee не найдено или недоступно. Проверьте корректность ссылки и убедитесь что видео не удалено.")

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writeinfojson': False,
            'writesubtitles': False,
        }
        from core.config import PROXY_URL
        if PROXY_URL:
            ydl_opts['proxy'] = PROXY_URL
        if sessionid and csrftoken and ds_user_id and is_instagram_url(url):
            cookies_file = create_cookies_file(sessionid, csrftoken, ds_user_id)
            ydl_opts["cookiefile"] = cookies_file
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    result = ydl.extract_info(url, download=False)
                return result
            finally:
                try:
                    os.unlink(cookies_file)
                except Exception:
                    pass
        else:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if is_youtube_url(url):
            if any(keyword in error_msg for keyword in ["private", "deleted", "unavailable"]):
                raise HTTPException(status_code=404, detail="YouTube видео не найдено, удалено или недоступно.")
            elif any(keyword in error_msg for keyword in ["quota", "api key", "forbidden"]):
                raise HTTPException(status_code=403, detail="Ошибка доступа к YouTube API. Проверьте квоту и ключ API.")
        if is_instagram_url(url) and any(keyword in error_msg for keyword in ["login", "sign in", "bot", "confirm", "cookies"]):
            raise HTTPException(status_code=401, detail="Ошибка авторизации Instagram. Проверьте корректность cookies или обновите их в браузере.")
        if is_vk_url(url):
            raise_vk_specific_http_if_any(error_msg)
        if is_likee_url(url):
            if any(keyword in error_msg for keyword in ["unable to extract", "regexnotfounderror", "unsupported url"]):
                raise HTTPException(status_code=503, detail="Экстрактор Likee временно не работает. Попробуйте позже.")
            elif any(keyword in error_msg for keyword in ["private", "blocked", "restricted"]):
                raise HTTPException(status_code=403, detail="Видео Likee недоступно: возможно приватное или заблокированное.")
        if is_tiktok_url(url) and any(keyword in error_msg for keyword in ["captcha", "login", "forbidden", "signature"]):
            raise HTTPException(status_code=403, detail="TikTok может требовать авторизацию/капчу. Попробуйте позже или используйте другой источник.")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/parse")
async def parse_url(url: str = Form(...), sessionid: str = Form(""), csrftoken: str = Form(""), ds_user_id: str = Form("")):
    info = _get_video_info(url, sessionid, csrftoken, ds_user_id)
    title = info.get("title") or "Без названия"
    author = info.get("uploader") or info.get("channel") or "Неизвестный автор"
    views = info.get("view_count")
    likes = info.get("like_count")
    comments = info.get("comments", [])
    comment_count_from_array = len(comments) if comments else 0
    comment_count_from_field = info.get("comment_count")
    comment_count = comment_count_from_field if comment_count_from_field is not None else comment_count_from_array
    thumbnail_url = info.get("thumbnail")
    if thumbnail_url:
        thumbnail_url = clean_thumbnail_url(thumbnail_url)
    result = {
        "title": title,
        "author": author,
        "views": views,
        "likes": likes,
        "comment_count": comment_count,
        "thumbnail": thumbnail_url,
        "description": info.get("description"),
        "comments": comments,
        "url": url,
    }
    if is_youtube_url(url):
        result.update({
            "video_id": info.get("_youtube_video_id"),
            "channel_id": info.get("_youtube_channel_id"),
            "upload_date": info.get("upload_date"),
            "duration": info.get("duration"),
            "tags": info.get("tags", []),
            "category_id": info.get("category_id"),
            "platform": "youtube",
        })
    elif is_likee_url(url):
        result.update({
            "post_id": info.get("_likee_post_id"),
            "author_id": info.get("_likee_author_id"),
            "upload_date": info.get("_likee_upload_date"),
            "shares": info.get("_likee_shares", 0),
            "downloads": info.get("_likee_downloads", 0),
            "platform": "likee",
        })
    return result


@router.post("/download")
async def download_url(
    url: str = Form(...),
    sessionid: Optional[str] = Form(None),
    csrftoken: Optional[str] = Form(None),
    ds_user_id: Optional[str] = Form(None),
):
    filename = f"{uuid.uuid4()}.mp4"
    filepath = os.path.join(MEDIA_DIR, filename)
    try:
        if is_likee_url(url):
            info = _get_video_info(url)
            video_url = info.get("_likee_video_url")
            if not video_url:
                raise HTTPException(status_code=400, detail="Не удалось получить прямую ссылку на видео Likee")
            session = create_robust_session()
            headers = get_mobile_headers()
            response = session.get(video_url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            file_size = os.path.getsize(filepath)
            if file_size == 0:
                os.remove(filepath)
                raise HTTPException(status_code=400, detail="Скачанный файл пуст")
            return {"filename": filename, "size": file_size}
        ydl_opts = {
            "outtmpl": filepath,
            "quiet": True,
            "format": "best[ext=mp4]/best",
        }
        if sessionid and csrftoken and ds_user_id and is_instagram_url(url):
            cookies_file = create_cookies_file(sessionid, csrftoken, ds_user_id)
            ydl_opts["cookiefile"] = cookies_file
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                file_size = os.path.getsize(filepath)
                return {"filename": filename, "size": file_size}
            finally:
                try:
                    os.unlink(cookies_file)
                except Exception:
                    pass
        else:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            file_size = os.path.getsize(filepath)
            return {"filename": filename, "size": file_size}
    except HTTPException:
        raise
    except Exception as e:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Ошибка скачивания: {str(e)}")


