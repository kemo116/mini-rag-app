from pydantic import BaseModel
from typing import Optional


class PushRequest(BaseModel):
    do_request: Optional[int]= 0

