from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import router as api_v1_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    # Start background memory decay scheduler
    from app.services.scheduler import (
        start_scheduler, stop_scheduler,
        start_ji_scheduler, stop_ji_scheduler,
    )
    start_scheduler()
    start_ji_scheduler()
    yield
    stop_ji_scheduler()
    stop_scheduler()


app = FastAPI(title="XuanJi API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """将 Pydantic 验证错误转换为用户友好的中文提示。"""
    messages: list[str] = []
    for err in exc.errors():
        msg = err.get("msg", "")
        # Pydantic v2 validator 错误格式: "Value error, 具体中文提示"
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        messages.append(msg)
    detail = "；".join(messages) if messages else "请求参数验证失败"
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": detail, "data": None},
    )


@app.get("/health")
async def health_check():
    return {"code": 200, "message": "ok", "data": {"status": "healthy"}}


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        # 显式列出需要监控的子目录，不包含 app/tools（工具文件变更不触发重载）
        reload_dirs=["app/ai", "app/api", "app/core", "app/models", "app/schemas", "app/services", "app/sandbox"],
    )
