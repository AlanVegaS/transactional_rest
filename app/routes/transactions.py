from uuid import UUID

from fastapi import WebSocket, Header, Depends, APIRouter, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.websocket_manager import manager
from app.services.transaction.create_transaction import create_transaction
from app.workers.producer import publish_pending_transactions, get_queue_status
from app.schemas.transactions import TransactionBase, TransactionCreateResponse
from app.logger import get_logger

logger = get_logger(__name__)

transactionRouter = APIRouter(prefix="/transactions", tags=["transaction"])


@transactionRouter.post("/create", response_model=TransactionCreateResponse, status_code=201)
async def transaction_create(
    body: TransactionBase,
    idempotency_key: UUID = Header(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        key = str(idempotency_key)
    except Exception as e:
        logger.error(f"Error creating transaction: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating transaction")

    return await create_transaction(body, key, db)


@transactionRouter.post("/async-process")
async def async_process():
    try:
        transactions_count = await publish_pending_transactions()
    except Exception as e:
        logger.error(f"Error processing transactions: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing transactions")

    return {"message": f"{transactions_count} Transactions published to stream"}


@transactionRouter.websocket("/stream")
async def queue_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        queue = await get_queue_status()
        await websocket.send_json({
            "event": "queue_status",
            "total": len(queue),
            "data":  queue,
        })

        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)