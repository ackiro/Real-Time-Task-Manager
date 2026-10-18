import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.api.schemas.user import Token, UserCreate, UserRead
from app.core.security import get_current_user, get_user_from_db, insert_user, login
from app.db.database import get_db_connection

router = APIRouter(prefix="/auth", tags=["Users"])


@router.post("/register", status_code=201)
async def register_user(
    user: UserCreate,
    db: asyncpg.Connection = Depends(get_db_connection),
):
    existing_user = await get_user_from_db(db, user.username)
    if existing_user is not None:
        raise HTTPException(status_code=400, detail="Username already exists")

    created_user = await insert_user(db, user)
    return UserRead(**dict(created_user))


@router.post("/login")
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: asyncpg.Connection = Depends(get_db_connection),
):
    access_token = await login(form_data, db)
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me")
async def read_current_user(current_user = Depends(get_current_user)):
    return UserRead(**dict(current_user))
