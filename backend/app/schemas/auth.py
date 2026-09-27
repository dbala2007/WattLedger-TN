"""Request/response shapes for the /auth endpoints."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    security_question_1: str
    security_answer_1: str = Field(min_length=2)
    security_question_2: str
    security_answer_2: str = Field(min_length=2)
    remember_me: bool = False
    device_name: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _questions_must_differ(self) -> "SignupRequest":
        if self.security_question_1 == self.security_question_2:
            raise ValueError("Choose two different security questions.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    # "Keep me logged in on this device". Optional so older app versions,
    # which don't send it, keep working exactly as before.
    remember_me: bool = False
    device_name: str | None = Field(default=None, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # Only present when remember_me was ticked - the device stores it and
    # later sends it to /auth/refresh instead of asking for the password.
    refresh_token: str | None = None


class RefreshTokenRequest(BaseModel):
    """Body for /auth/refresh and /auth/logout."""

    refresh_token: str = Field(min_length=1, max_length=200)


class UserRead(BaseModel):
    id: str
    email: str
    created_at: datetime


class SecurityQuestionsResponse(BaseModel):
    questions: list[str]


class ForgotPasswordQuestionsRequest(BaseModel):
    email: EmailStr


class ForgotPasswordQuestionsResponse(BaseModel):
    security_question_1: str
    security_question_2: str


class ForgotPasswordResetRequest(BaseModel):
    email: EmailStr
    security_answer_1: str
    security_answer_2: str
    new_password: str = Field(min_length=8)
