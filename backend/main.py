from fastapi import FastAPI, HTTPException, UploadFile, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import os
import uuid
import tempfile
import requests
import re
import json
from urllib.parse import urlparse, parse_qs, unquote
from typing import Optional
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

# Функция для детекции Likee URL
def is_likee_url(url):
    url_lower = url.lower()
    return (url_lower.startswith('https://likee.video/') or
            url_lower.startswith('https://www.likee.video/') or
            url_lower.startswith('https://l.likee.video/') or  # сокращенные ссылки
            url_lower.startswith('https://likee.com/') or
            'likee.video' in url_lower or
            'likee.com' in url_lower)

def extract_video_id_from_likee_url(url: str) -> str:
    """Извлекает ID видео из Likee URL"""
    patterns = [
        r'/video/(\d+)',  # Улучшен для поиска только цифровых ID
        r'postId=(\d+)',
        r'/v/([a-zA-Z0-9]+)',  # Для коротких ссылок
        r'@[\w.]+/video/(\d+)',
        r'l\.likee\.video/v/([^/?&]+)',
        r'postid=(\d+)',  # Добавлен lowercase вариант
    ]

    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)

    return None

def get_mobile_headers():
    """Возвращает мобильные заголовки для Likee с ротацией User-Agent"""
    user_agents = [
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.79 Mobile Safari/537.36'
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

def create_robust_session():
    """Создает сессию с retry логикой"""
    session = requests.Session()

    # Настройка retry стратегии
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session

def extract_likee_via_mobile_request(url: str) -> dict:
    """Улучшенное извлечение данных Likee через мобильный запрос"""
    try:
        print(f"Пробуем мобильный запрос для: {url}")

        session = create_robust_session()
        headers = get_mobile_headers()
        session.headers.update(headers)

        # Добавляем задержку для имитации человеческого поведения
        time.sleep(random.uniform(1, 3))

        # Получаем страницу
        response = session.get(url, allow_redirects=True, timeout=30)

        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")

        # Проверяем, не перенаправило ли на главную
        final_url_lower = response.url.lower()
        if (any(keyword in final_url_lower for keyword in ['trending', 'm_index', '/home']) or
            response.url.rstrip('/') in ['https://likee.video', 'https://www.likee.video']):
            print("Редирект на главную страницу обнаружен")
            return None

        content = response.text

        # Улучшенные паттерны для поиска данных с более точными регулярными выражениями
        patterns = [
            # Основной паттерн для window.data
            (r'window\.data\s*=\s*(\{[^;]+\});', 'window.data'),
            # Альтернативные варианты
            (r'__INITIAL_STATE__\s*=\s*(\{.+?\});', '__INITIAL_STATE__'),
            (r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});', 'window.__INITIAL_STATE__'),
            (r'window\.__NUXT__\s*=\s*(\{.+?\});', 'window.__NUXT__'),
            # JSON-LD структурированные данные
            (r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>\s*(\{.+?\})\s*</script>', 'json-ld'),
            # Встроенные данные
            (r'"videoUrl"\s*:\s*"([^"]+)"', 'videoUrl'),
            (r'"playUrl"\s*:\s*"([^"]+)"', 'playUrl'),
            (r'"video_url"\s*:\s*"([^"]+)"', 'video_url'),
        ]

        for pattern, name in patterns:
            try:
                matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    print(f"Найден паттерн {name}")

                    if 'Url' in name or 'url' in name.lower():
                        # Это прямая ссылка на видео
                        video_url = match.group(1)
                        if video_url and ('http' in video_url or video_url.startswith('//')):
                            clean_url = video_url.replace('\\/', '/').replace('\\u0026', '&')
                            if not clean_url.startswith('http'):
                                clean_url = 'https:' + clean_url
                            return {
                                'video_url': clean_url,
                                'title': 'Likee Video',
                                'source': name
                            }
                    else:
                        # Это JSON данные
                        json_str = match.group(1)
                        # Очищаем экранированные символы
                        json_str = json_str.replace('\\"', '"').replace('\\/', '/')

                        try:
                            data = json.loads(json_str)
                            result = parse_likee_json_data(data)
                            if result and result.get('video_url'):
                                result['source'] = name
                                return result
                        except json.JSONDecodeError as e:
                            print(f"Ошибка JSON парсинга для {name}: {e}")
                            continue

            except Exception as e:
                print(f"Ошибка обработки паттерна {name}: {e}")
                continue

        # Попробуем извлечь данные из meta тегов
        meta_result = extract_from_meta_tags(content)
        if meta_result:
            return meta_result

        print("Данные видео не найдены в HTML")
        return None

    except requests.RequestException as e:
        print(f"Ошибка сетевого запроса: {e}")
        return None
    except Exception as e:
        print(f"Ошибка мобильного запроса: {e}")
        return None

def extract_from_meta_tags(content: str) -> dict:
    """Извлекает данные из meta тегов Open Graph и Twitter"""
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
            ]
        }

        result = {}

        for field, patterns in meta_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    if value:
                        result[field] = value
                        break

        # Если есть video_url, считаем что нашли данные
        if result.get('video_url'):
            result['source'] = 'meta_tags'
            result.setdefault('title', 'Likee Video')
            result.setdefault('author', 'Unknown')
            return result

        return None

    except Exception as e:
        print(f"Ошибка извлечения meta тегов: {e}")
        return None

def extract_likee_via_api(url: str) -> dict:
    """Улучшенная попытка извлечения через API Likee"""
    try:
        video_id = extract_video_id_from_likee_url(url)
        if not video_id:
            print("Не удалось извлечь video_id из URL")
            return None

        print(f"Пробуем API для video_id: {video_id}")

        # Заголовки как от мобильного приложения с ротацией
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
            }
        ]

        # Различные API endpoints
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
                    print(f"Пробуем API endpoint: {api_url}")
                    time.sleep(random.uniform(0.5, 2.0))  # Увеличена задержка

                    response = session.get(api_url, headers=headers, timeout=15)
                    print(f"API Response status: {response.status_code}")

                    if response.status_code == 200:
                        try:
                            data = response.json()
                            result = parse_likee_api_response(data, video_id)
                            if result and result.get('video_url'):
                                result['source'] = f'api_{api_url.split("/")[2]}'
                                return result
                        except json.JSONDecodeError:
                            print(f"Не JSON ответ от {api_url}")
                            continue

                except requests.RequestException as e:
                    print(f"API endpoint {api_url} failed: {e}")
                    continue

        return None

    except Exception as e:
        print(f"Ошибка API извлечения: {e}")
        return None

def parse_short_number(value) -> int:
    """Преобразует сокращенные числа типа '165.88K', '1.75M' в обычные числа"""
    if not value:
        return 0

    # Если это уже число
    if isinstance(value, (int, float)):
        return int(value)

    # Преобразуем в строку и очищаем
    value_str = str(value).strip().upper()

    # Если это обычное число
    if value_str.isdigit():
        return int(value_str)

    # Проверяем наличие суффиксов
    multipliers = {
        'K': 1000,
        'M': 1000000,
        'B': 1000000000,
        'Т': 1000,      # кириллическая Т (тысяча)
        'М': 1000000,   # кириллическая М (миллион)
        'Б': 1000000000 # кириллическая Б (миллиард)
    }

    # Ищем суффикс в конце строки
    for suffix, multiplier in multipliers.items():
        if value_str.endswith(suffix):
            try:
                # Убираем суффикс и преобразуем число
                number_part = value_str[:-1].replace(',', '.')
                number = float(number_part)
                return int(number * multiplier)
            except (ValueError, TypeError):
                continue

    # Пытаемся преобразовать как обычное число
    try:
        return int(float(value_str.replace(',', '.')))
    except (ValueError, TypeError):
        return 0

def parse_likee_json_data(data) -> dict:
    """Улучшенный рекурсивный парсер JSON данных Likee"""
    try:
        def find_in_object(obj, path="", depth=0):
            # Ограничиваем глубину рекурсии
            if depth > 10:
                return None

            if isinstance(obj, dict):
                result = {}

                # Приоритетные поля для поиска
                priority_mappings = {
                    'video_url': ['video_url', 'videoUrl', 'playUrl', 'video', 'playAddr', 'videoAddr', 'mp4Url'],
                    'title': ['title', 'content', 'caption', 'desc', 'description', 'msg_text'],
                    'thumbnail': ['coverUrl', 'thumbnail', 'cover', 'thumbUrl', 'imageUrl', 'image1'],
                    'author': ['nick_name', 'nickname', 'name', 'username', 'displayName', 'user_name'],
                    'author_id': ['poster_uid', 'uid', 'userId', 'user_id'],
                    'author_username': ['user_name', 'likeeId', 'username'],
                    'post_id': ['post_id', 'postId', 'id', 'video_id'],
                    'likes': ['like_count', 'likeCount', 'likes'],
                    'views': ['video_count', 'playCount', 'viewCount', 'views'],  # video_count - это просмотры в Likee
                    'comments': ['comment_count', 'commentCount', 'comments'],
                    'shares': ['share_count', 'shareCount', 'shares'],
                    'upload_date': ['uploadDate', 'createTime', 'createdAt'],
                    'duration': ['duration', 'ISO8601_duration'],
                    'country': ['post_country', 'country'],
                    'downloads': ['download_count', 'downloadCount', 'downloads'],
                    'music_name': ['music_name', 'musicName', 'sound_name'],
                    'music_owner': ['musicOwnerName', 'music_owner'],
                }

                # Ищем поля по приоритету
                for result_key, field_variants in priority_mappings.items():
                    for field in field_variants:
                        if field in obj and obj[field]:
                            value = obj[field]

                            # Специальная обработка для разных типов полей
                            if result_key == 'video_url':
                                if isinstance(value, str) and ('http' in value or value.startswith('//')):
                                    clean_url = value.replace('\\/', '/').replace('\\u0026', '&')
                                    if not clean_url.startswith('http'):
                                        clean_url = 'https:' + clean_url
                                    result[result_key] = clean_url
                                    break
                            elif result_key in ['likes', 'views', 'comments', 'shares', 'downloads']:
                                # Используем новую функцию для парсинга сокращенных чисел
                                result[result_key] = parse_short_number(value)
                                break
                            else:
                                result[result_key] = str(value).strip() if value else ''
                                break

                # Обработка nested объектов пользователя
                user_objects = ['user', 'userInfo', 'author', 'creator']
                for user_field in user_objects:
                    if user_field in obj and isinstance(obj[user_field], dict):
                        user_info = obj[user_field]
                        if not result.get('author'):
                            for author_field in ['nickname', 'name', 'username', 'displayName']:
                                if author_field in user_info and user_info[author_field]:
                                    result['author'] = user_info[author_field]
                                    break

                # Если нашли video_url, возвращаем результат
                if result.get('video_url'):
                    # Устанавливаем значения по умолчанию
                    result.setdefault('title', 'Likee Video')
                    result.setdefault('author', 'Unknown')
                    result.setdefault('likes', 0)
                    result.setdefault('views', 0)
                    result.setdefault('comments', 0)
                    result.setdefault('shares', 0)
                    result.setdefault('downloads', 0)

                    # Отладочный вывод
                    print(f"Извлечены данные: views={result.get('views')}, likes={result.get('likes')}, comments={result.get('comments')}")

                    return result

                # Рекурсивный поиск в дочерних объектах
                for k, v in obj.items():
                    if (k not in ['toString', 'valueOf'] and
                        not k.startswith('_') and
                        not k.startswith('$')):
                        sub_result = find_in_object(v, f"{path}.{k}", depth + 1)
                        if sub_result and sub_result.get('video_url'):
                            # Объединяем результаты
                            for key, value in result.items():
                                if key not in sub_result:
                                    sub_result[key] = value
                            return sub_result

            elif isinstance(obj, list) and len(obj) > 0:
                # Ограничиваем поиск в массивах
                for i, item in enumerate(obj[:5]):
                    sub_result = find_in_object(item, f"{path}[{i}]", depth + 1)
                    if sub_result and sub_result.get('video_url'):
                        return sub_result

            return None

        result = find_in_object(data)
        return result

    except Exception as e:
        print(f"Ошибка парсинга JSON данных: {e}")
        return None

def parse_likee_api_response(data, video_id) -> dict:
    """Улучшенный парсер ответа от API Likee"""
    try:
        print(f"Парсим API ответ для {video_id}")

        # Различные структуры ответа API
        possible_paths = [
            data,
            data.get('data'),
            data.get('result'),
            data.get('response'),
            data.get('videos'),
            data.get('videoInfo'),
        ]

        # Обработка массивов данных
        for key in ['data', 'videos', 'items']:
            if isinstance(data.get(key), list) and len(data[key]) > 0:
                possible_paths.extend(data[key][:3])  # Первые 3 элемента

        for response_data in possible_paths:
            if not response_data:
                continue

            result = parse_likee_json_data(response_data)
            if result and result.get('video_url'):
                return result

        return None

    except Exception as e:
        print(f"Ошибка парсинга API ответа: {e}")
        return None

def extract_likee_info(url: str) -> dict:
    """Основная функция для извлечения информации из Likee с улучшенной логикой"""
    print(f"Начинаем извлечение данных Likee: {url}")

    # Нормализуем URL
    url = url.strip()
    if not url.startswith('http'):
        url = 'https://' + url

    methods = [
        ("Mobile Request", extract_likee_via_mobile_request),
        ("API Request", extract_likee_via_api),
    ]

    for method_name, method_func in methods:
        try:
            print(f"Пробуем метод: {method_name}")
            result = method_func(url)

            if result and result.get('video_url'):
                print(f"Успех с методом {method_name}")
                print(f"Источник: {result.get('source', 'unknown')}")

                # Валидация результата
                video_url = result['video_url']
                if video_url and ('http' in video_url and ('mp4' in video_url or 'video' in video_url)):
                    return result
                else:
                    print(f"Невалидный video_url: {video_url}")
                    continue
            else:
                print(f"Метод {method_name} не дал результата")

        except Exception as e:
            print(f"Ошибка в методе {method_name}: {e}")
            continue

    print("Все методы извлечения Likee не сработали")
    return None

def resolve_likee_url(url: str) -> str:
    """Улучшенная проверка Likee URL"""
    try:
        headers = get_mobile_headers()
        session = create_robust_session()

        response = session.head(url, headers=headers, allow_redirects=True, timeout=30)
        final_url = response.url

        print(f"Resolve Likee URL: {url} -> {final_url}")

        # Улучшенная проверка главной страницы
        final_url_lower = final_url.lower()
        is_main_page = (
            final_url.rstrip('/') in ['https://likee.video', 'https://www.likee.video'] or
            any(keyword in final_url_lower for keyword in ['trending', 'm_index', '/home', '/explore'])
        )

        if is_main_page:
            # Попробуем извлечь информацию другими способами
            info = extract_likee_info(url)
            if info and info.get('video_url'):
                return url  # Возвращаем оригинальный URL, если нашли данные

            raise HTTPException(
                status_code=404,
                detail="Видео Likee не найдено. Возможные причины: видео удалено, аккаунт заблокирован, неверный URL или видео недоступно в вашем регионе."
            )

        return final_url
    except HTTPException:
        raise
    except requests.RequestException as e:
        print(f"Ошибка при проверке URL: {e}")
        return url

def is_vk_url(url: str) -> bool:
    """Проверяет, является ли URL ссылкой на VK Video"""
    url_lower = url.lower()
    return any(domain in url_lower for domain in [
        "vk.com/video",
        "vk.com/clip",
        "vk.ru/video",
        "vk.ru/clip",
        "m.vk.com/video",
        "m.vk.ru/video"
    ])

def is_instagram_url(url: str) -> bool:
    """Проверяет, является ли URL ссылкой на Instagram"""
    return "instagram.com" in url.lower()

def get_video_info(url: str, sessionid: str = "", csrftoken: str = "", ds_user_id: str = ""):
    """Улучшенная функция получения информации о видео"""
    try:
        # Специальная обработка для Likee
        if is_likee_url(url):
            print(f"Обрабатываем Likee URL: {url}")

            # Проверяем URL и пытаемся извлечь данные
            try:
                url = resolve_likee_url(url)
            except HTTPException:
                pass

            # Пытаемся извлечь информацию о видео кастомными методами
            likee_info = extract_likee_info(url)

            if likee_info and likee_info.get('video_url'):
                # Обрабатываем статистику с помощью новой функции
                views = parse_short_number(likee_info.get('views', 0))
                likes = parse_short_number(likee_info.get('likes', 0))
                comments = parse_short_number(likee_info.get('comments', 0))

                return {
                    "title": likee_info.get('title', 'Likee Video'),
                    "uploader": likee_info.get('author', 'Unknown'),
                    "channel": likee_info.get('author', 'Unknown'),
                    "view_count": views,
                    "like_count": likes,
                    "comment_count": comments,
                    "thumbnail": likee_info.get('thumbnail'),
                    "description": likee_info.get('title', ''),  # Используем title как description
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
                raise HTTPException(
                    status_code=404,
                    detail="Видео Likee не найдено или недоступно. Проверьте корректность ссылки и убедитесь что видео не удалено."
                )

        # Для остальных сайтов используем yt-dlp как обычно
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writeinfojson': False,
            'writesubtitles': False,
        }

        # Добавляем cookies для Instagram
        if sessionid and csrftoken and ds_user_id and "instagram.com" in url.lower():
            cookies_file = create_cookies_file(sessionid, csrftoken, ds_user_id)
            ydl_opts["cookiefile"] = cookies_file

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    result = ydl.extract_info(url, download=False)
                return result
            finally:
                try:
                    os.unlink(cookies_file)
                except:
                    pass
        else:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()

        # Instagram авторизация
        if is_instagram_url(url) and any(keyword in error_msg for keyword in ["login", "sign in", "bot", "confirm", "cookies"]):
            raise HTTPException(status_code=401, detail="Ошибка авторизации Instagram. Проверьте корректность cookies или обновите их в браузере.")

        # VK специфичные ошибки
        if is_vk_url(url):
            if any(keyword in error_msg for keyword in ["private", "access denied", "blocked", "forbidden"]):
                raise HTTPException(status_code=403, detail="Видео VK недоступно: возможно приватное или заблокированное в регионе.")
            elif any(keyword in error_msg for keyword in ["not found", "removed", "deleted"]):
                raise HTTPException(status_code=404, detail="Видео VK не найдено или было удалено.")

        # Likee специфичные ошибки
        if is_likee_url(url):
            if any(keyword in error_msg for keyword in ["unable to extract", "regexnotfounderror", "unsupported url"]):
                raise HTTPException(status_code=503, detail="Экстрактор Likee временно не работает. Попробуйте позже.")
            elif any(keyword in error_msg for keyword in ["private", "blocked", "restricted"]):
                raise HTTPException(status_code=403, detail="Видео Likee недоступно: возможно приватное или заблокированное.")

        # Общая ошибка
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/parse")
async def parse_url(url: str = Form(...), sessionid: str = Form(""), csrftoken: str = Form(""), ds_user_id: str = Form("")):
    try:
        info = get_video_info(url, sessionid, csrftoken, ds_user_id)

        # Извлекаем основную информацию
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

        result = {
            "title": title,
            "author": author,
            "views": views,
            "likes": likes,
            "comment_count": comment_count,
            "thumbnail": info.get("thumbnail"),
            "description": info.get("description"),
            "comments": comments,
            "url": url
        }

        # Добавляем дополнительную информацию для Likee
        if is_likee_url(url):
            result.update({
                "post_id": info.get("_likee_post_id"),
                "author_id": info.get("_likee_author_id"),
                "upload_date": info.get("_likee_upload_date"),
                "shares": info.get("_likee_shares", 0),
                "downloads": info.get("_likee_downloads", 0),
                "platform": "likee"
            })

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")

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

        # Специальная обработка для Likee
        if is_likee_url(url):
            print(f"Скачиваем Likee видео: {url}")

            # Получаем информацию о видео
            info = get_video_info(url)
            video_url = info.get("_likee_video_url")

            if not video_url:
                raise HTTPException(status_code=400, detail="Не удалось получить прямую ссылку на видео Likee")

            # Скачиваем видео по прямой ссылке с улучшенной обработкой
            headers = get_mobile_headers()
            session = create_robust_session()

            print(f"Скачиваем с URL: {video_url}")

            response = session.get(video_url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()

            # Проверяем тип контента
            content_type = response.headers.get('content-type', '').lower()
            if 'video' not in content_type and 'application/octet-stream' not in content_type:
                print(f"Неожиданный content-type: {content_type}")

            # Скачиваем с прогрессом
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Логируем прогресс каждые 1MB
                        if downloaded % (1024 * 1024) == 0:
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                print(f"Скачано: {progress:.1f}%")

            # Проверяем размер файла
            file_size = os.path.getsize(filepath)
            if file_size == 0:
                os.remove(filepath)
                raise HTTPException(status_code=400, detail="Скачанный файл пуст")

            print(f"Файл успешно скачан: {filename}, размер: {file_size} байт")
            return {"filename": filename, "size": file_size}

        # Для остальных сайтов используем yt-dlp
        ydl_opts = {
            "outtmpl": filepath,
            "quiet": True,
            "format": "best[ext=mp4]/best"  # Предпочитаем mp4
        }

        # Добавляем cookies для Instagram
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
                except:
                    pass
        else:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            file_size = os.path.getsize(filepath)
            return {"filename": filename, "size": file_size}

    except HTTPException:
        raise
    except Exception as e:
        # Очищаем файл в случае ошибки
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Ошибка скачивания: {str(e)}")

@app.get("/media/{filename}")
def get_media(filename: str):
    filepath = os.path.join(MEDIA_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath)

# Дополнительный endpoint для получения информации о Likee видео
@app.post("/likee/info")
async def get_likee_info(url: str = Form(...)):
    """Специальный endpoint для получения подробной информации о Likee видео"""
    try:
        if not is_likee_url(url):
            raise HTTPException(status_code=400, detail="Это не ссылка на Likee")

        info = extract_likee_info(url)
        if not info:
            raise HTTPException(status_code=404, detail="Информация о видео не найдена")

        return {
            "success": True,
            "data": info,
            "video_available": bool(info.get('video_url')),
            "extraction_source": info.get('source', 'unknown')
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения информации: {str(e)}")

# Endpoint для проверки здоровья сервиса
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "supported_platforms": ["Instagram", "VK", "Likee", "YouTube", "TikTok"],
        "likee_extractors": ["mobile_request", "api_request", "meta_tags"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)