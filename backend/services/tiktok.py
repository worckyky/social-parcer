def is_tiktok_url(url: str) -> bool:
    url_lower = url.lower()
    return any(domain in url_lower for domain in [
        "tiktok.com/",
        "vm.tiktok.com/",
        "m.tiktok.com/",
    ])


