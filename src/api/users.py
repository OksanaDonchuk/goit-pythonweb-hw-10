from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.schemas.user_schema import UserResponse
from src.services.auth_services import AuthService, oauth2_scheme

router = APIRouter(prefix="/users", tags=["users"])
limiter = Limiter(key_func=get_remote_address)


def get_auth_service(db: AsyncSession = Depends(get_db)):
    return AuthService(db)


@router.get(
    "/me",
    response_model=UserResponse,
    name="Отримання поточного користувача",
    description="Не більше 5 запитів в хвилину",
)
@limiter.limit("5/minute")
async def me(
    request: Request,
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.get_current_user(token)
