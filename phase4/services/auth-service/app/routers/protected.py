from fastapi import APIRouter, Depends

from app.auth.security import validate_access_token


router = APIRouter(
    prefix="/api",
    tags=["Protected API"],
)


@router.get("/protected")
async def protected_endpoint(
    payload: dict = Depends(validate_access_token),
):
    return {
        "message": "Protected API access granted",
        "authenticated": True,
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
    }