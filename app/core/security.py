from datetime import UTC, datetime, timedelta

import asyncpg
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext

from app.api.schemas.user import UserCreate
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from app.db.database import get_db_connection

hasher = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_user_from_db(db: asyncpg.Connection, username: str):
    return await db.fetchrow(
        """
        SELECT *
        FROM users
        WHERE username = $1
        """,
        username,
    )


async def insert_user(db: asyncpg.Connection, user: UserCreate):
    password = hasher.hash(user.password)
    return await db.fetchrow(
        """
        INSERT INTO users (username, hashed_password)
        VALUES ($1, $2)
        RETURNING id, username, created_at
        """,
        user.username,
        password,
    )


async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: asyncpg.Connection = Depends(get_db_connection),
):
    user = await get_user_from_db(db, form_data.username)
    if user is None or not hasher.verify(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return create_jwt_token({"sub": user["username"]})


def create_jwt_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.now(UTC) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_user_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: asyncpg.Connection = Depends(get_db_connection),
):
    username = get_user_from_token(token)
    user = await get_user_from_db(db, username)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user
