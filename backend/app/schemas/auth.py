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

    @model_validator(mode="after")
    def _questions_must_differ(self) -> "SignupRequest":
        if self.security_question_1 == self.security_question_2:
            raise ValueError("Choose two different security questions.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
