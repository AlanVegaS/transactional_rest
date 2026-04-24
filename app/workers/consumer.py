import asyncio
from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.redis import client, STREAM_TRANSACTIONS, GROUP_NAME
from app.models.transactions import Transaction
from app.logger import get_logger

logger = get_logger(__name__)


async def create_group():
    try:
        await client.xgroup_create(STREAM_TRANSACTIONS, GROUP_NAME, id="0", mkstream=True)
        logger.info("Group created")
    except Exception:
        logger.info("Group already exists")


async def process_transaction(data: dict) -> bool:
    logger.info(f"Processing transaction {data['id']} — amount: {data['amount']}")
    await asyncio.sleep(3)
    return True


async def update_state(tx_id: str, state: str):
    logger.info(f"Updating state of transaction {tx_id} to {state}")
    async with SessionLocal() as db:
        result = await db.execute(
            select(Transaction).where(Transaction.id == tx_id)
        )
        tx = result.scalar_one_or_none()
        if tx:
            tx.state = state
            await db.commit()
            logger.info(f"Transaction {tx}")


async def consume():
    await create_group()
    logger.info("Worker listening...")

    while True:
        messages = await client.xreadgroup(
            groupname=GROUP_NAME,
            consumername="worker-1",
            streams={STREAM_TRANSACTIONS: ">"},
            count=10,
            block=2000,
        )

        if not messages:
            continue

        for stream, entries in messages:
            for message_id, data in entries:
                try:
                    success = await process_transaction(data)
                    new_state = "completed" if success else "failed"

                    await update_state(data["id"], new_state)

                    await client.xack(STREAM_TRANSACTIONS, GROUP_NAME, message_id)

                except Exception as e:
                    logger.error(f"Error processing {data['id']}: {e}")
                    await update_state(data["id"], "failed")

if __name__ == "__main__":
    asyncio.run(consume())
