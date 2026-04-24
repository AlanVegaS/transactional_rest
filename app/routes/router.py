from fastapi import APIRouter
from app.routes.transactions import transactionRouter


router = APIRouter()
router.include_router(transactionRouter)