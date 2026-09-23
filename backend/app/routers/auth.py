from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    StudentRegister, LoginRequest, TokenResponse, UserResponse,
)
from app.middleware.auth import (
    hash_password, verify_password, create_access_token, get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Dummy hash for constant-time comparison on nonexistent user
_DUMMY_HASH = "$2b$12$e80MvQ0wF9vVUk9W2s5bOu6b7aB3x6wQWn3dYqX7bXkP3Z9Wz2Qy2"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_student(data: StudentRegister, db: AsyncSession = Depends(get_db)):
    """Student self-registration. Role is forced to 'student'."""
    clean_email = data.email.strip().lower()
    clean_reg = data.student_reg_no.strip().upper()
    clean_name = data.name.strip()

    # Check if email already exists
    existing = await db.execute(select(User).where(User.email.ilike(clean_email)))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    # Check if student reg number already exists
    existing_reg = await db.execute(
        select(User).where(User.student_reg_no.ilike(clean_reg))
    )
    if existing_reg.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this student registration number already exists."
        )

    user = User(
        email=clean_email,
        name=clean_name,
        student_reg_no=clean_reg,
        hashed_password=hash_password(data.password),
        role=UserRole.STUDENT,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login for all roles (student, agent, admin). Supports email or student registration number."""
    identifier = data.email.strip()

    # Query by email or student registration number (case-insensitive)
    result = await db.execute(
        select(User).where(
            or_(
                User.email.ilike(identifier),
                User.student_reg_no.ilike(identifier),
            )
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        # Constant-time mitigation against user enumeration
        verify_password(data.password, _DUMMY_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/registration number or password. Please try again.",
        )

    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/registration number or password. Please try again.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated. Please contact campus administration.",
        )

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return UserResponse.model_validate(current_user)
