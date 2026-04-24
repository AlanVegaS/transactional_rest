from fastapi import FastAPI

from app.core.database import init_db
from app.logger import get_logger
from app.routes.router import router

logger = get_logger(__name__)

app = FastAPI()


@app.on_event("startup")
async def startup():
    await init_db()


app.include_router(router)
