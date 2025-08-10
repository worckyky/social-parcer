from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from core.config import MEDIA_DIR
from routers.parse import router as parse_router
from routers.info import router as info_router
from routers.system import router as system_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# гарантируем существование директории для медиа
os.makedirs(MEDIA_DIR, exist_ok=True)

# Подключение роутеров
app.include_router(parse_router)
app.include_router(info_router)
app.include_router(system_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


