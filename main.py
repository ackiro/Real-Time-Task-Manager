from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

from app.api.endpoints.tasks import router as tasks_router
from app.api.endpoints.users import router as users_router
from app.core.config import DATABASE_URL
from app.db.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await asyncpg.create_pool(DATABASE_URL)
    await create_tables(app.state.db)
    yield
    await app.state.db.close()


app = FastAPI(lifespan=lifespan)
app.include_router(users_router)
app.include_router(tasks_router)
