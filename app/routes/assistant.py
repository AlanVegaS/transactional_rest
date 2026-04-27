from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.assistant import SummaryBase
from app.services.assistant.summarize import create_summary


assistantRouter = APIRouter(prefix="/assistant", tags=["assistant"])

@assistantRouter.post("/summarize", status_code=200)
async def summary(
    body: SummaryBase,
    db: AsyncSession = Depends(get_db),
):
    try:
        summary = await create_summary(body, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error generating summary")
    return summary
