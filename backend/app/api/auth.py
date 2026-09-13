"""HTTP endpoints for signup, login, 'who am I', and forgot-password."""

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.seed_data import seed_default_meters_if_missing
from app.db.session import get_session
from app.domain.auth import SECURITY_QUESTIONS
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordQuestionsRequest,
    ForgotPasswordQuestionsResponse,
    ForgotPasswordResetRequest,
    LoginRequest,
    SecurityQuestionsResponse,
    SignupRequest,
    TokenResponse,
    UserRead,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/security-questions", response_model=SecurityQuestionsResponse)
def list_security_questions() -> SecurityQuestionsResponse:
    return SecurityQuestionsResponse(questions=SECURITY_QUESTIONS)


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, session: Session = Depends(get_session)) -> TokenResponse:
    _user, token = auth_service.signup(
        session,
        email=payload.email,
        password=payload.password,
        security_question_1=payload.security_question_1,
        security_answer_1=payload.security_answer_1,
        security_question_2=payload.security_question_2,
        security_answer_2=payload.security_answer_2,
    )
    # Covers signing up as the household's own account on a database that's
    # already running (not just freshly started) - see app/db/seed_data.py.
    seed_default_meters_if_missing(session)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    _user, token = auth_service.login(session, email=payload.email, password=payload.password)
    seed_default_meters_if_missing(session)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead(id=current_user.id, email=current_user.email, created_at=current_user.created_at)


@router.post("/forgot-password/questions", response_model=ForgotPasswordQuestionsResponse)
def forgot_password_questions(
    payload: ForgotPasswordQuestionsRequest, session: Session = Depends(get_session)
) -> ForgotPasswordQuestionsResponse:
    q1, q2 = auth_service.get_security_questions(session, email=payload.email)
    return ForgotPasswordQuestionsResponse(security_question_1=q1, security_question_2=q2)


@router.post("/forgot-password/reset", response_model=TokenResponse)
def forgot_password_reset(
    payload: ForgotPasswordResetRequest, session: Session = Depends(get_session)
) -> TokenResponse:
    _user, token = auth_service.reset_password(
        session,
        email=payload.email,
        security_answer_1=payload.security_answer_1,
        security_answer_2=payload.security_answer_2,
        new_password=payload.new_password,
    )
    return TokenResponse(access_token=token)
