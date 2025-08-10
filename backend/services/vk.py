from fastapi import HTTPException


def is_vk_url(url: str) -> bool:
    url_lower = url.lower()
    return any(domain in url_lower for domain in [
        "vk.com/video",
        "vk.com/clip",
        "vk.ru/video",
        "vk.ru/clip",
        "vkvideo.ru/clip",
        "vkvideo.ru/video",
        "m.vk.com/video",
        "m.vk.ru/video",
    ])


def raise_vk_specific_http_if_any(error_message_lower: str) -> None:
    if any(keyword in error_message_lower for keyword in ["private", "access denied", "blocked", "forbidden"]):
        raise HTTPException(status_code=403, detail="Видео VK недоступно: возможно приватное или заблокированное в регионе.")
    if any(keyword in error_message_lower for keyword in ["not found", "removed", "deleted"]):
        raise HTTPException(status_code=404, detail="Видео VK не найдено или было удалено.")


