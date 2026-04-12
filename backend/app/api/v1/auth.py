from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(data: UserCreate, db: Session = Depends(get_db)):
    service = UserService(db)
    if service.get_by_username(data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )
    user = service.create_user(data)
    token = create_access_token({"sub": str(user.id)})
    return {
        "code": 200,
        "message": "success",
        "data": {
            "token": token,
            "user": UserResponse.model_validate(user).model_dump(),
        },
    }


@router.post("/login")
async def login(data: UserLogin, db: Session = Depends(get_db)):
    service = UserService(db)
    user = service.authenticate(data.username, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_access_token({"sub": str(user.id)})
    return {
        "code": 200,
        "message": "success",
        "data": {
            "token": token,
            "user": UserResponse.model_validate(user).model_dump(),
        },
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "code": 200,
        "message": "success",
        "data": UserResponse.model_validate(current_user).model_dump(),
    }
