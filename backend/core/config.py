import os
from dotenv import load_dotenv


# Загружаем переменные окружения из .env файла
load_dotenv()


MEDIA_DIR: str = os.getenv("MEDIA_DIR", "media")
YOUTUBE_API_KEY: str | None = os.getenv("YOUTUBE_KEY")
PROXY_URL: str | None = os.getenv("PROXY_URL")


