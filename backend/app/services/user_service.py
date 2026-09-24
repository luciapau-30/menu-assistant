from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


def create_user(db: Session, user_data: UserCreate):

    # 1. Check if email already exists
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")

    # 2. Hash password
    hashed_password = hash_password(user_data.password)

    # 3. Create database model
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password
    )

    # 4. Add to database session
    db.add(new_user)

    # 5. Save changes to PostgreSQL
    db.commit()

    # 6. Refresh with database-generated fields
    db.refresh(new_user)

    # 7. Return created user
    return new_user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()

    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return user