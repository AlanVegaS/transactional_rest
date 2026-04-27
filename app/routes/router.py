from fastapi import APIRouter
from app.routes.transactions import transactionRouter
from app.routes.assistant import assistantRouter


router = APIRouter()
router.include_router(transactionRouter)
router.include_router(assistantRouter)