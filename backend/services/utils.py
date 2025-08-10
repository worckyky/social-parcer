import re
import tempfile

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from core.config import PROXY_URL

def is_youtube_url(url: str) -> bool:
    if not url:
        return False
    url_lower = url.lower()
    youtube_domains = [
        "youtube.com",
        "youtu.be",
        "m.youtube.com",
        "www.youtube.com",
    ]
    return any(domain in url_lower for domain in youtube_domains)


def extract_video_id_from_url(url: str) -> str:
    if not url:
        raise ValueError("URL не предоставлен")
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'(?:m\.youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Неверный формат YouTube URL: {url}")


def clean_thumbnail_url(thumbnail_url: str) -> str:
    if not thumbnail_url:
        return thumbnail_url
    cleaned_url = thumbnail_url.lstrip('@')
    while cleaned_url and not cleaned_url.startswith('http'):
        cleaned_url = cleaned_url[1:]
    return cleaned_url


def create_cookies_file(sessionid: str, csrftoken: str, ds_user_id: str) -> str:
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
    temp_file.write("# Netscape HTTP Cookie File\n")
    temp_file.write("# This is a generated file! Do not edit.\n\n")
    domain = ".instagram.com"
    cookies = [
        ("sessionid", sessionid),
        ("csrftoken", csrftoken),
        ("ds_user_id", ds_user_id),
    ]
    for name, value in cookies:
        if value.strip():
            temp_file.write(f"{domain}\tTRUE\t/\tTRUE\t0\t{name}\t{value.strip()}\n")
    temp_file.flush()
    temp_file.close()
    return temp_file.name


def create_robust_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    if PROXY_URL:
        session.proxies.update({
            "http": PROXY_URL,
            "https": PROXY_URL,
        })
    return session


