import requests
from fastapi import HTTPException

from core.config import YOUTUBE_API_KEY


def get_youtube_video_info_via_api(video_id: str) -> dict:
    if not YOUTUBE_API_KEY:
        raise ValueError("YouTube API ключ не найден в переменных окружения")
    api_url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        'part': 'snippet,statistics,contentDetails',
        'id': video_id,
        'key': YOUTUBE_API_KEY,
    }
    try:
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not data.get('items'):
            raise HTTPException(status_code=404, detail=f"YouTube видео с ID {video_id} не найдено или недоступно")
        video_data = data['items'][0]
        snippet = video_data.get('snippet', {})
        statistics = video_data.get('statistics', {})
        view_count = int(statistics.get('viewCount', 0))
        like_count = int(statistics.get('likeCount', 0))
        comment_count = int(statistics.get('commentCount', 0))
        # thumbnail url
        thumbnail_url = snippet.get('thumbnails', {}).get('maxres', {}).get('url') or \
                        snippet.get('thumbnails', {}).get('high', {}).get('url')
        return {
            'title': snippet.get('title', 'YouTube Video'),
            'uploader': snippet.get('channelTitle', 'Unknown Channel'),
            'channel': snippet.get('channelTitle', 'Unknown Channel'),
            'view_count': view_count,
            'like_count': like_count,
            'comment_count': comment_count,
            'thumbnail': thumbnail_url,
            'description': snippet.get('description', ''),
            'upload_date': snippet.get('publishedAt'),
            'duration': video_data.get('contentDetails', {}).get('duration'),
            'tags': snippet.get('tags', []),
            'category_id': snippet.get('categoryId'),
            'url': f"https://youtube.com/watch?v={video_id}",
            'webpage_url': f"https://youtube.com/watch?v={video_id}",
            '_youtube_video_id': video_id,
            '_youtube_channel_id': snippet.get('channelId'),
            'comments': [],
        }
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обращении к YouTube API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки YouTube данных: {str(e)}")


