from uuid import UUID, uuid4

from fastapi import Header, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.transactions import Transaction
from app.core.store import get_cached, set_cached
from app.logger import get_logger
from app.schemas.transactions import TransactionBase, TransactionCreateResponse

logger = get_logger(__name__)

transactionRouter = APIRouter(prefix="/transactions", tags=["transaction"])


@transactionRouter.post("/create", response_model=TransactionCreateResponse, status_code=201)
async def transaction_create(
    body: TransactionBase,
    idempotency_key: UUID = Header(...),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Creating transaction with idempotency key: {idempotency_key}")
    key = str(idempotency_key)

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

    return response
