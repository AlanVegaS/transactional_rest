from fastapi import FastAPI

from app.core.database import init_db
from app.logger import get_logger
from app.routes.router import router
from app.workers.consumer import create_group

logger = get_logger(__name__)

app = FastAPI()


@app.on_event("startup")
async def startup():
    logger.info("Starting up...")
    await init_db()
    logger.info("Database initialized")
    await create_group()
    logger.info("Group created")


app.include_router(router)
