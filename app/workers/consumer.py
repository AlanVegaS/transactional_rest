import json
import asyncio

from sqlalchemy import select, update

from app.core.database import SessionLocal
from app.core.redis import client, STREAM_TRANSACTIONS, GROUP_NAME
from app.models.transactions import Transaction
from app.logger import get_logger
from app.core.websocket_manager import manager

logger = get_logger(__name__)


async def create_group():
    try:
        await client.xgroup_create(STREAM_TRANSACTIONS, GROUP_NAME, id="0", mkstream=True)
        logger.info("Group created")
    except Exception:
        logger.info("Group already exists")


def _serialize_transactions(transactions) -> list[dict]:
    return [
        {
            "id": tx.id,
            "user_id": tx.user_id,
            "amount": tx.amount,
            "state": tx.state,
            "transaction_type": tx.transaction_type,
            "created_at": str(tx.created_at),
        }
        for tx in transactions
    ]


async def process_transaction(data: dict) -> bool:
    logger.info(f"Processing transaction {data['id']} — amount: {data['amount']}")
    async with SessionLocal() as db:
        await db.execute(
            update(Transaction).where(Transaction.id == data['id']).values(state="running")
        )
        await db.commit()
        result = await db.execute(select(Transaction))
        transactions = _serialize_transactions(result.scalars().all())
    await client.publish(STREAM_TRANSACTIONS, json.dumps({
        "event": "transaction_updated",
        "total": len(transactions),
        "data":  transactions,
    }))
    await asyncio.sleep(4)
    return True


async def update_state(tx_id: str, state: str):
    async with SessionLocal() as db:
        result = await db.execute(
            select(Transaction).where(Transaction.id == tx_id)
        )
        tx = result.scalar_one_or_none()
        if tx:
            tx.state = state
            await db.commit()
        result = await db.execute(select(Transaction))
        queue = _serialize_transactions(result.scalars().all())

    await client.publish(STREAM_TRANSACTIONS, json.dumps({
        "event": "transaction_updated",
        "transaction_updated": {
            "id": tx_id,
            "state": state,
        },
        "total": len(queue),
        "data":  queue,
    }))


async def consume():
    await create_group()
    logger.info("Worker listening...")

    while True:
        transactions = await client.xreadgroup(
            groupname=GROUP_NAME,
            consumername="worker-1",
            streams={STREAM_TRANSACTIONS: ">"},
            count=10,
            block=2000,
        )

        if not transactions:
            continue

        for stream, entries in transactions:
            for transaction_id, data in entries:
                try:
                    success = await process_transaction(data)
                    new_state = "completed" if success else "failed"

                    await update_state(data["id"], new_state)

                    await client.xack(STREAM_TRANSACTIONS, GROUP_NAME, transaction_id)

                except Exception as e:
                    logger.error(f"Error processing {data['id']}: {e}")
                    await update_state(data["id"], "failed")

if __name__ == "__main__":
    asyncio.run(consume())
