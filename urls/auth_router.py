from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from async_database import get_db
from auth.security import hash_password, verify_password
from models.users.models import User
from schemas.users.schemas import UserLoginSchema, UserSignupSchema
from auth.security import create_access_token, create_refresh_token
from async_database import settings

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserSignupSchema, db: AsyncSession = Depends(get_db)):
    email_taken = await db.execute(select(User).where(User.email == user.email.lower()))
    if email_taken.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    username_taken = await db.execute(select(User).where(User.username == user.username))
    if username_taken.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    db_user = User(
        username=user.username,
        email=user.email,
        password=hash_password(user.password),
        role=user.user_role,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return {
        "id": db_user.id,
        "username": db_user.username,
        "email": db_user.email,
        "role": getattr(db_user.role, "value", db_user.role),
    }

# conventional login but doesn't support swagger login so i changed it.
# @auth_router.post("/login", status_code=status.HTTP_200_OK)
# async def login_user(user: UserLoginSchema, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(User).where(User.email == user.email))
#     db_user = result.scalars().first()
#     if db_user is None or not verify_password(user.password, db_user.password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect email or password",
#         )
#     if not db_user.is_active:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Account is inactive",
#         )
#     access_token = create_access_token({"sub": str(db_user.id)})
#     refresh_token = create_refresh_token({"sub": str(db_user.id)})
#     return {
#         "access_token": access_token,
#         "refresh_token": refresh_token,
#     }


# gotta install python-multipart for this to work
from fastapi.security import OAuth2PasswordRequestForm
@auth_router.post("/login", status_code=status.HTTP_200_OK)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(
        or_(User.email == form_data.username, User.username == form_data.username)
        )
    )
    db_user = result.scalars().first()

    if db_user is None or not verify_password(form_data.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    access_token = create_access_token({"sub": str(db_user.id)})
    refresh_token = create_refresh_token({"sub": str(db_user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@auth_router.post("/login/refresh/", status_code=status.HTTP_200_OK)
async def refresh_user_token(refresh_token: str):
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token type!")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token payload")
    except JWTError as e:
        print("JWTError detial", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired refresh token")

    new_access_token = create_access_token({"sub": user_id})
    return {
        "access_token": new_access_token,
        "type": "Bearer"
    }
