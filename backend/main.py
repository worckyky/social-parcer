from fastapi import FastAPI, HTTPException, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import os
import uuid
import tempfile
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

def create_cookies_file(sessionid: str, csrftoken: str, ds_user_id: str) -> str:
    """Создает временный файл с cookies для yt-dlp в формате Netscape"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
    
    # Заголовок файла cookies в формате Netscape
    temp_file.write("# Netscape HTTP Cookie File\n")
    temp_file.write("# This is a generated file! Do not edit.\n\n")
    
    # Записываем каждый cookie в формате Netscape
    domain = ".instagram.com"
    cookies = [
        ("sessionid", sessionid),
        ("csrftoken", csrftoken),
        ("ds_user_id", ds_user_id)
    ]
    
    for name, value in cookies:
        if value.strip():  # Только если значение не пустое
            # Формат Netscape: domain\tTRUE\tpath\tTRUE\texpiry\tname\tvalue
            temp_file.write(f"{domain}\tTRUE\t/\tTRUE\t0\t{name}\t{value.strip()}\n")
    
    temp_file.flush()
    temp_file.close()
    return temp_file.name

def get_video_info(url: str, sessionid: Optional[str] = None, csrftoken: Optional[str] = None, ds_user_id: Optional[str] = None):
    ydl_opts = {"skip_download": True, "quiet": True, "extract_flat": False}
    
    # Добавляем cookies для Instagram
    if sessionid and csrftoken and ds_user_id and "instagram.com" in url.lower():
        cookies_file = create_cookies_file(sessionid, csrftoken, ds_user_id)
        ydl_opts["cookiefile"] = cookies_file
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(url, download=False)
            return result
        finally:
            # Безопасно удаляем временный файл cookies
            try:
                os.unlink(cookies_file)
            except:
                pass
    else:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

@app.post("/parse")
async def parse_url(
    url: str = Form(...), 
    sessionid: Optional[str] = Form(None),
    csrftoken: Optional[str] = Form(None), 
    ds_user_id: Optional[str] = Form(None)
):
    try:
        info = get_video_info(url, sessionid, csrftoken, ds_user_id)
        
        # Безопасное извлечение данных с обработкой None значений
        title = info.get("title") or "Без названия"
        author = info.get("uploader") or info.get("channel") or "Неизвестный автор"
        
        # Для Instagram часто отсутствуют view_count и другие метрики
        views = info.get("view_count")
        likes = info.get("like_count") 
        
        # Обработка комментариев - пытаемся получить и from comments массива, и из comment_count
        comments = info.get("comments", [])
        comment_count_from_array = len(comments) if comments else 0
        comment_count_from_field = info.get("comment_count")
        comment_count = comment_count_from_field if comment_count_from_field is not None else comment_count_from_array
        
        return {
            "title": title,
            "author": author,
            "views": views,  # Может быть None - frontend обработает как 'N/A'
            "likes": likes,  # Может быть None - frontend обработает как 'N/A'
            "comment_count": comment_count,
            "thumbnail": info.get("thumbnail"),
            "description": info.get("description"),
            "comments": comments,
            "url": url
        }
    except Exception as e:
        # Специальная обработка ошибок Instagram авторизации
        error_msg = str(e).lower()
        if "instagram.com" in url.lower() and any(keyword in error_msg for keyword in ["login", "sign in", "bot", "confirm", "cookies"]):
            raise HTTPException(status_code=401, detail="Ошибка авторизации Instagram. Проверьте корректность cookies или обновите их в браузере.")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/download")
async def download_url(
    url: str = Form(...), 
    sessionid: Optional[str] = Form(None),
    csrftoken: Optional[str] = Form(None), 
    ds_user_id: Optional[str] = Form(None)
):
    try:
        filename = f"{uuid.uuid4()}.mp4"
        filepath = os.path.join(MEDIA_DIR, filename)
        ydl_opts = {"outtmpl": filepath, "quiet": True, "format": "best"}
        
        # Добавляем cookies для Instagram
        if sessionid and csrftoken and ds_user_id and "instagram.com" in url.lower():
            cookies_file = create_cookies_file(sessionid, csrftoken, ds_user_id)
            ydl_opts["cookiefile"] = cookies_file
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                return {"filename": filename}
            finally:
                # Безопасно удаляем временный файл cookies
                try:
                    os.unlink(cookies_file)
                except:
                    pass
        else:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return {"filename": filename}
    except Exception as e:
        # Специальная обработка ошибок Instagram авторизации  
        error_msg = str(e).lower()
        if "instagram.com" in url.lower() and any(keyword in error_msg for keyword in ["login", "sign in", "bot", "confirm", "cookies"]):
            raise HTTPException(status_code=401, detail="Ошибка авторизации Instagram. Проверьте корректность cookies или обновите их в браузере.")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/media/{filename}")
def get_media(filename: str):
    filepath = os.path.join(MEDIA_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath) 