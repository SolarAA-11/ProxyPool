
from pydantic import BaseModel

class ProxyItem(BaseModel):
    ip: str
    port: int
    https: bool