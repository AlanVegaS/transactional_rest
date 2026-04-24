from pydantic import BaseModel

class TransactionBase(BaseModel):
    user_id: str
    amount: float
    transaction_type: str


class TransactionCreateResponse(TransactionBase):
    id: str
    state: str
    created_at: str