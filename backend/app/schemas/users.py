from pydantic import BaseModel

class Monitoreduser(BaseModel):
    id: int
    username: str
    department: str | None

class UserPage(BaseModel):
    items: list[Monitoreduser]
    total: int
    limit: int
    offset: int