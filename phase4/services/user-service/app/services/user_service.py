from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def get_user_by_auth0_id(
    db: Session,
    auth0_user_id: str,
):
    return (
        db.query(User)
        .filter(User.auth0_user_id == auth0_user_id)
        .first()
    )


def get_user_by_id(
    db: Session,
    user_id: int,
):
    return (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )


def create_or_update_user(
    db: Session,
    user_data: UserCreate,
):
    user = get_user_by_auth0_id(
        db,
        user_data.auth0_user_id,
    )

    if user:
        user.email = user_data.email
        user.name = user_data.name
        user.picture = user_data.picture
        user.provider = user_data.provider

        db.commit()
        db.refresh(user)

        return user

    user = User(
        auth0_user_id=user_data.auth0_user_id,
        email=user_data.email,
        name=user_data.name,
        picture=user_data.picture,
        provider=user_data.provider,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def update_user(
    db: Session,
    user: User,
    user_data: UserUpdate,
):
    if user_data.name is not None:
        user.name = user_data.name

    if user_data.picture is not None:
        user.picture = user_data.picture

    db.commit()
    db.refresh(user)

    return user