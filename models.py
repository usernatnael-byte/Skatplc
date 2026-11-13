from pydantic import BaseModel
from typing import Optional

class ItemModel(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    complete: bool = False
