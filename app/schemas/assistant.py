from pydantic import BaseModel

class SummaryBase(BaseModel):
    text: str
    user_id: str
