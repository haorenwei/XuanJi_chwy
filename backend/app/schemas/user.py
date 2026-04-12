import re
import string
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

# 所有可打印标点符号均视为特殊字符: !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
SPECIAL_CHARS = set(string.punctuation)


def validate_username(v: str) -> str:
    """用户名验证：4-20字符，仅字母/数字/下划线，不允许纯数字"""
    if len(v) < 4 or len(v) > 20:
        raise ValueError("用户名长度需为4-20个字符")
    if not re.fullmatch(r"[A-Za-z0-9_]+", v):
        raise ValueError("用户名仅支持字母、数字和下划线")
    if v.isdigit():
        raise ValueError("用户名不能为纯数字")
    return v


def validate_password(v: str) -> str:
    """密码验证：>=8字符，含大写、小写、数字、特殊字符"""
    if len(v) < 8:
        raise ValueError("密码长度至少8个字符")
    missing = []
    if not re.search(r"[A-Z]", v):
        missing.append("大写字母")
    if not re.search(r"[a-z]", v):
        missing.append("小写字母")
    if not re.search(r"[0-9]", v):
        missing.append("数字")
    if not any(c in SPECIAL_CHARS for c in v):
        missing.append("特殊字符")
    if missing:
        raise ValueError(f"密码必须包含{('、').join(missing)}")
    return v


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def check_username(cls, v: str) -> str:
        return validate_username(v)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password(v)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}
