"""Authentication endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...core.security import create_access_token, hash_password, verify_password
from ...db.models import UserRole
from ...db.repositories.user_repository import UserRepository
from ...schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    if await repo.get_by_email(body.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    count = await repo.count()
    role = UserRole.admin if count == 0 else UserRole.viewer
    user = await repo.create(body.email, hash_password(body.password), role)
    logger.info("User registered email=%s role=%s", user.email, user.role.value)
    token = create_access_token(user.email, user.role.value)
    return TokenResponse(access_token=token, role=user.role.value)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_email(body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(user.email, user.role.value)
    logger.info("User login email=%s", user.email)
    return TokenResponse(access_token=token, role=user.role.value)


@router.get("/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)):
    return UserResponse(email=user.email, role=user.role.value, is_active=user.is_active)
