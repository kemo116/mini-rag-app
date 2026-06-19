from pydantic import BaseModel
from typing import Optional


class PushRequest(BaseModel):
    do_request: Optional[int]= 0


class SearchRequest(BaseModel):
    text: str
    limit: Optional[int]= 5

