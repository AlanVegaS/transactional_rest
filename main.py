import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db
from app.logger import get_logger
from app.routes.router import router
from app.core.websocket_manager import manager
from app.workers.consumer import create_group

logger = get_logger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    logger.info("Starting up...")
    await init_db()
    logger.info("Database initialized")
    await create_group()
    logger.info("Group created")
    asyncio.create_task(manager.listen_redis())
    logger.info("Redis listener started")


app.include_router(router)
