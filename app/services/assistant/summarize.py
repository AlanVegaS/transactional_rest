from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assistant import Assistant
from app.schemas.assistant import SummaryBase
from app.services.gemini.getSummary import get_summary


async def create_summary(body: SummaryBase, db: AsyncSession):
    try:
        summary = await get_summary(body.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error generating summary")

    try:
        assistant = Assistant(
            id=str(uuid4()),
            user_id=body.user_id,
            full_text=body.text,
            summary=summary,
        )
        db.add(assistant)
        await db.commit()
        await db.refresh(assistant)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error saving summary")

    return {
        "message": "Summary generated successfully",
        "summary": summary
    }
