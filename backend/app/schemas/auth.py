from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    organization: str = Field(min_length=1, max_length=120)
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserOut(BaseModel):
    id: int
    organization_id: int
    username: str
    department: str | None
    roles: list[str]