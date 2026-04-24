from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.redis import client, STREAM_TRANSACTIONS
from app.models.transactions import Transaction
from app.logger import get_logger

logger = get_logger(__name__)


async def publish_pending_transactions():
    async with SessionLocal() as db:
        result = await db.execute(
            select(Transaction).where(Transaction.state == "pending")
        )
        transactions = result.scalars().all()

        for tx in transactions:
            await client.xadd(
                STREAM_TRANSACTIONS,
                {
                    "id": tx.id,
                    "user_id": tx.user_id,
                    "amount": str(tx.amount),
                    "transaction_type": tx.transaction_type,
                },
            )
            logger.info(f"transaction published: {tx.id}")

    logger.info(f"{len(transactions)} transactions sent to the stream")
    return len(transactions)
