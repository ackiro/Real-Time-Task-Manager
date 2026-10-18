from datetime import datetime
from pydantic import BaseModel

class TaskCreate(BaseModel):
    title: str
    description: str | None = None

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None

class TaskRead(BaseModel):
    id: int
    title: str
    description: str | None
    status: str
    priority: str
    owner_id: int
    created_at: datetime
    updated_at: datetime
