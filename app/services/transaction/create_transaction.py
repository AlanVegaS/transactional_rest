from uuid import uuid4

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transactions import Transaction
from app.core.database import get_db
from app.core.redis import get_cached, set_cached
from app.schemas.transactions import TransactionCreateResponse, TransactionBase
from app.core.websocket_manager import manager
from app.workers.producer import get_queue_status

async def create_transaction(body: TransactionBase, key: str, db: AsyncSession):
    # 1. Search in Redis Cache
    cached = await get_cached(key)
    if cached:
        return cached

    # 2. Search in PostgreSQL (in case the cache has expired)
    result = await db.execute(select(Transaction).where(Transaction.idempotency_key == key))
    existing = result.scalar_one_or_none()
    if existing:
        response = TransactionCreateResponse(
            id=existing.id,
            user_id=existing.user_id,
            amount=existing.amount,
            transaction_type=existing.transaction_type,
            state=existing.state,
            created_at=str(existing.created_at),
        )
        await set_cached(key, response.model_dump())
        return response

    # 3. First time -> save in DB
    transaction = Transaction(
        id=str(uuid4()),
        idempotency_key=key,
        user_id=body.user_id,
        amount=body.amount,
        transaction_type=body.transaction_type,
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    response = TransactionCreateResponse(
        id=str(transaction.id),
        user_id=str(transaction.user_id),
        amount=transaction.amount,
        transaction_type=transaction.transaction_type,
        state=transaction.state,
        created_at=str(transaction.created_at),
    )

    # 4. Save in Redis for subsequent requests
    await set_cached(key, response.model_dump())

    # 5. Broadcast all DB records to connected WebSocket clients
    all_transactions = await get_queue_status()
    await manager.broadcast({
        "event": "transaction_created",
        "total": len(all_transactions),
        "data": all_transactions,
    })

    return response
        