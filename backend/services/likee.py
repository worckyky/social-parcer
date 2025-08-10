import json
import random
import re
import time
from typing import Optional

import requests
from fastapi import HTTPException

from services.utils import create_robust_session


def is_likee_url(url: str) -> bool:
    url_lower = url.lower()
    return (
        url_lower.startswith('https://likee.video/')
        or url_lower.startswith('https://www.likee.video/')
        or url_lower.startswith('https://l.likee.video/')
        or url_lower.startswith('https://likee.com/')
        or 'likee.video' in url_lower
        or 'likee.com' in url_lower
    )


def extract_video_id_from_likee_url(url: str) -> Optional[str]:
    patterns = [
        r'/video/(\d+)',
        r'postId=(\d+)',
        r'/v/([a-zA-Z0-9]+)',
        r'@[\w.]+/video/(\d+)',
        r'l\.likee\.video/v/([^/?&]+)',
        r'postid=(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def get_mobile_headers() -> dict:
    user_agents = [
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.79 Mobile Safari/537.36',
    ]
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
        'DNT': '1',
    }


def extract_from_meta_tags(content: str) -> Optional[dict]:
    try:
        meta_patterns = {
            'title': [
                r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']*)["\']',
                r'<title[^>]*>([^<]*)</title>',
            ],
            'description': [
                r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']*)["\']',
                r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
            ],
            'video_url': [
                r'<meta[^>]*property=["\']og:video["\'][^>]*content=["\']([^"\']*)["\']',
                r'<meta[^>]*property=["\']og:video:url["\'][^>]*content=["\']([^"\']*)["\']',
            ],
            'thumbnail': [
                r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']*)["\']',
                r'<meta[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']*)["\']',
            ],
        }
        result: dict = {}
        for field, patterns in meta_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value:
                        result[field] = value
                        break
        if result.get('video_url'):
            result['source'] = 'meta_tags'
            result.setdefault('title', 'Likee Video')
            result.setdefault('author', 'Unknown')
            return result
        return None
    except Exception:
        return None


def parse_short_number(value) -> int:
    if not value:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    value_str = str(value).strip().upper()
    if value_str.isdigit():
        return int(value_str)
    multipliers = {
        'K': 1000,
        'M': 1000000,
        'B': 1000000000,
        'Т': 1000,
        'М': 1000000,
        'Б': 1000000000,
    }
    for suffix, multiplier in multipliers.items():
        if value_str.endswith(suffix):
            try:
                number_part = value_str[:-1].replace(',', '.')
                number = float(number_part)
                return int(number * multiplier)
            except (ValueError, TypeError):
                continue
    try:
        return int(float(value_str.replace(',', '.')))
    except (ValueError, TypeError):
        return 0


def parse_likee_json_data(data) -> Optional[dict]:
    try:
        def find_in_object(obj, depth=0):
            if depth > 10:
                return None
            if isinstance(obj, dict):
                result: dict = {}
                priority_mappings = {
                    'video_url': ['video_url', 'videoUrl', 'playUrl', 'video', 'playAddr', 'videoAddr', 'mp4Url'],
                    'title': ['title', 'content', 'caption', 'desc', 'description', 'msg_text'],
                    'thumbnail': ['coverUrl', 'thumbnail', 'cover', 'thumbUrl', 'imageUrl', 'image1'],
                    'author': ['nick_name', 'nickname', 'name', 'username', 'displayName', 'user_name'],
                    'author_id': ['poster_uid', 'uid', 'userId', 'user_id'],
                    'author_username': ['user_name', 'likeeId', 'username'],
                    'post_id': ['post_id', 'postId', 'id', 'video_id'],
                    'likes': ['like_count', 'likeCount', 'likes'],
                    'views': ['video_count', 'playCount', 'viewCount', 'views'],
                    'comments': ['comment_count', 'commentCount', 'comments'],
                    'shares': ['share_count', 'shareCount', 'shares'],
                    'upload_date': ['uploadDate', 'createTime', 'createdAt'],
                    'duration': ['duration', 'ISO8601_duration'],
                    'country': ['post_country', 'country'],
                    'downloads': ['download_count', 'downloadCount', 'downloads'],
                    'music_name': ['music_name', 'musicName', 'sound_name'],
                    'music_owner': ['musicOwnerName', 'music_owner'],
                }
                for result_key, field_variants in priority_mappings.items():
                    for field in field_variants:
                        if field in obj and obj[field]:
                            value = obj[field]
                            if result_key == 'video_url':
                                if isinstance(value, str) and ('http' in value or value.startswith('//')):
                                    clean_url = value.replace('\\/', '/').replace('\\u0026', '&')
                                    if not clean_url.startswith('http'):
                                        clean_url = 'https:' + clean_url
                                    result[result_key] = clean_url
                                    break
                            elif result_key in ['likes', 'views', 'comments', 'shares', 'downloads']:
                                result[result_key] = parse_short_number(value)
                                break
                            else:
                                result[result_key] = str(value).strip() if value else ''
                                break
                user_objects = ['user', 'userInfo', 'author', 'creator']
                for user_field in user_objects:
                    if user_field in obj and isinstance(obj[user_field], dict):
                        user_info = obj[user_field]
                        if not result.get('author'):
                            for author_field in ['nickname', 'name', 'username', 'displayName']:
                                if author_field in user_info and user_info[author_field]:
                                    result['author'] = user_info[author_field]
                                    break
                if result.get('video_url'):
                    result.setdefault('title', 'Likee Video')
                    result.setdefault('author', 'Unknown')
                    result.setdefault('likes', 0)
                    result.setdefault('views', 0)
                    result.setdefault('comments', 0)
                    result.setdefault('shares', 0)
                    result.setdefault('downloads', 0)
                    return result
                for _, v in obj.items():
                    sub_result = find_in_object(v, depth + 1)
                    if sub_result and sub_result.get('video_url'):
                        for key, value in result.items():
                            if key not in sub_result:
                                sub_result[key] = value
                        return sub_result
            elif isinstance(obj, list) and len(obj) > 0:
                for item in obj[:5]:
                    sub_result = find_in_object(item, depth + 1)
                    if sub_result and sub_result.get('video_url'):
                        return sub_result
            return None

        return find_in_object(data)
    except Exception:
        return None


def parse_likee_api_response(data, video_id: str) -> Optional[dict]:
    try:
        possible_paths = [
            data,
            data.get('data') if isinstance(data, dict) else None,
            data.get('result') if isinstance(data, dict) else None,
            data.get('response') if isinstance(data, dict) else None,
            data.get('videos') if isinstance(data, dict) else None,
            data.get('videoInfo') if isinstance(data, dict) else None,
        ]
        for key in ['data', 'videos', 'items']:
            if isinstance(data, dict) and isinstance(data.get(key), list) and len(data[key]) > 0:
                possible_paths.extend(data[key][:3])
        for response_data in possible_paths:
            if not response_data:
                continue
            result = parse_likee_json_data(response_data)
            if result and result.get('video_url'):
                return result
        return None
    except Exception:
        return None


def extract_likee_via_mobile_request(url: str) -> Optional[dict]:
    try:
        session = create_robust_session()
        headers = get_mobile_headers()
        session.headers.update(headers)
        time.sleep(random.uniform(1, 3))
        response = session.get(url, allow_redirects=True, timeout=30)
        final_url_lower = response.url.lower()
        if (
            any(keyword in final_url_lower for keyword in ['trending', 'm_index', '/home'])
            or response.url.rstrip('/') in ['https://likee.video', 'https://www.likee.video']
        ):
            return None
        content = response.text
        patterns = [
            (r'window\.data\s*=\s*(\{[^;]+\});', 'window.data'),
            (r'__INITIAL_STATE__\s*=\s*(\{.+?\});', '__INITIAL_STATE__'),
            (r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});', 'window.__INITIAL_STATE__'),
            (r'window\.__NUXT__\s*=\s*(\{.+?\});', 'window.__NUXT__'),
            (r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>\s*(\{.+?\})\s*</script>', 'json-ld'),
            (r'"videoUrl"\s*:\s*"([^"]+)"', 'videoUrl'),
            (r'"playUrl"\s*:\s*"([^"]+)"', 'playUrl'),
            (r'"video_url"\s*:\s*"([^"]+)"', 'video_url'),
        ]
        for pattern, name in patterns:
            try:
                matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    if 'Url' in name or 'url' in name.lower():
                        video_url = match.group(1)
                        if video_url and ('http' in video_url or video_url.startswith('//')):
                            clean_url = video_url.replace('\\/', '/').replace('\\u0026', '&')
                            if not clean_url.startswith('http'):
                                clean_url = 'https:' + clean_url
                            return {
                                'video_url': clean_url,
                                'title': 'Likee Video',
                                'source': name,
                            }
                    else:
                        json_str = match.group(1)
                        json_str = json_str.replace('\\"', '"').replace('\\/', '/')
                        try:
                            data = json.loads(json_str)
                            result = parse_likee_json_data(data)
                            if result and result.get('video_url'):
                                result['source'] = name
                                return result
                        except json.JSONDecodeError:
                            continue
            except Exception:
                continue
        meta_result = extract_from_meta_tags(content)
        if meta_result:
            return meta_result
        return None
    except requests.RequestException:
        return None
    except Exception:
        return None


def extract_likee_via_api(url: str) -> Optional[dict]:
    try:
        video_id = extract_video_id_from_likee_url(url)
        if not video_id:
            return None
        headers_variants = [
            {
                'User-Agent': 'Likee/4.0.0 (iPhone; iOS 15.0; Scale/3.00)',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': 'https://likee.video',
                'Referer': 'https://likee.video/',
            },
            {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': url,
            },
        ]
        api_endpoints = [
            f"https://api.like-video.com/likee-activity-flow-proxy/videoApi/getVideoInfo?postIds={video_id}",
            f"https://likee.video/official_website/videoinfo/get?postId={video_id}",
            f"https://api.likee.video/rest/n/video/info?postId={video_id}",
            f"https://likee.video/rest/n/video/info?postId={video_id}",
        ]
        session = create_robust_session()
        for headers in headers_variants:
            for api_url in api_endpoints:
                try:
                    time.sleep(random.uniform(0.5, 2.0))
                    response = session.get(api_url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            result = parse_likee_api_response(data, video_id)
                            if result and result.get('video_url'):
                                result['source'] = f'api_{api_url.split("/")[2]}'
                                return result
                        except json.JSONDecodeError:
                            continue
                except requests.RequestException:
                    continue
        return None
    except Exception:
        return None


def resolve_likee_url(url: str) -> str:
    try:
        headers = get_mobile_headers()
        session = create_robust_session()
        response = session.head(url, headers=headers, allow_redirects=True, timeout=30)
        final_url = response.url
        final_url_lower = final_url.lower()
        is_main_page = (
            final_url.rstrip('/') in ['https://likee.video', 'https://www.likee.video']
            or any(keyword in final_url_lower for keyword in ['trending', 'm_index', '/home', '/explore'])
        )
        if is_main_page:
            info = extract_likee_info(url)
            if info and info.get('video_url'):
                return url
            raise HTTPException(status_code=404, detail="Видео Likee не найдено. Возможные причины: видео удалено, аккаунт заблокирован, неверный URL или видео недоступно в вашем регионе.")
        return final_url
    except HTTPException:
        raise
    except requests.RequestException:
        return url


def extract_likee_info(url: str) -> Optional[dict]:
    url = url.strip()
    if not url.startswith('http'):
        url = 'https://' + url
    methods = [
        ("Mobile Request", extract_likee_via_mobile_request),
        ("API Request", extract_likee_via_api),
    ]
    for _, method_func in methods:
        try:
            result = method_func(url)
            if result and result.get('video_url'):
                video_url = result['video_url']
                if video_url and ('http' in video_url and ('mp4' in video_url or 'video' in video_url)):
                    return result
                else:
                    continue
        except Exception:
            continue
    return None


