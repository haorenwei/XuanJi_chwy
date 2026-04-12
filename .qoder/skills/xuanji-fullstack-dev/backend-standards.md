# Backend Standards

## Project Setup with Conda

### Create Environment

```bash
conda env create -f environment.yml
conda activate xuanji
```

### environment.yml

```yaml
name: xuanji
channels:
  - defaults
  - conda-forge
dependencies:
  - python=3.11
  - pip
  - pip:
    - fastapi>=0.100
    - uvicorn[standard]
    - sqlalchemy>=2.0
    - pymysql
    - cryptography
    - pydantic>=2.0
    - pydantic-settings
    - alembic
    - httpx
    - python-dotenv
    - python-multipart
    - python-jose[cryptography]
    - passlib[bcrypt]
    - pytest
    - pytest-asyncio
    - httpx  # for TestClient async
```

Update with: `conda env update -f environment.yml --prune`

## FastAPI Application Structure

### Entry Point

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import router as api_v1_router

app = FastAPI(title="XuanJi API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")
```

### Configuration with pydantic-settings

```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "xuanji"

    # AI
    ollama_base_url: str = "http://localhost:11434"
    llm_api_key: str = ""
    llm_api_base_url: str = ""
    llm_model_name: str = ""
    llm_provider: str = "ollama"  # ollama | online

    # App
    secret_key: str = "change-me"
    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            "?charset=utf8mb4"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
```

## SQLAlchemy 2.0 Pattern

### Database Session

```python
# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Model Definition (SQLAlchemy 2.0 Mapped Columns)

```python
# app/models/user.py
from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

### Pydantic Schemas

```python
# app/schemas/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

## API Route Pattern

```python
# app/api/v1/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=dict)
async def create_user(data: UserCreate, db: Session = Depends(get_db)):
    service = UserService(db)
    user = service.create_user(data)
    return {"code": 200, "message": "success", "data": UserResponse.model_validate(user)}

@router.get("/{user_id}", response_model=dict)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    service = UserService(db)
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"code": 200, "message": "success", "data": UserResponse.model_validate(user)}
```

### Router Aggregation

```python
# app/api/v1/__init__.py
from fastapi import APIRouter
from app.api.v1.users import router as users_router
from app.api.v1.chat import router as chat_router

router = APIRouter()
router.include_router(users_router)
router.include_router(chat_router)
```

## Service Layer

Business logic lives in services, not route handlers:

```python
# app/services/user_service.py
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, data: UserCreate) -> User:
        user = User(
            username=data.username,
            email=data.email,
            hashed_password=pwd_context.hash(data.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user(self, user_id: int) -> User | None:
        return self.db.query(User).filter(
            User.id == user_id, User.deleted_at.is_(None)
        ).first()
```

## Alembic Migrations

Initialize: `alembic init migrations`

Configure `alembic.ini`:
```ini
sqlalchemy.url = mysql+pymysql://root@localhost:3306/xuanji?charset=utf8mb4
```

Common commands:
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
alembic history
```

## MySQL Conventions

- Charset: `utf8mb4`, collation: `utf8mb4_unicode_ci`
- Use `BigInteger` for primary keys
- Index frequently queried columns
- Use foreign keys with `ondelete="CASCADE"` or `"SET NULL"` as appropriate
- Store timestamps in UTC

## Testing

Use pytest + pytest-asyncio + httpx:

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)
```

```python
# tests/test_users.py
def test_create_user(client):
    response = client.post("/api/v1/users/", json={
        "username": "test",
        "email": "test@example.com",
        "password": "secure123"
    })
    assert response.status_code == 200
    assert response.json()["data"]["username"] == "test"
```

## Running the Server

```bash
conda activate xuanji
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
