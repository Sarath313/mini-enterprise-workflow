from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.auth.security import validate_access_token
from app.services.auth0_service import auth0_service
from app.services.user_service import sync_user_with_user_service


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.get("/google/login")
async def google_login():
    url = auth0_service.build_login_url(
        auth0_service.settings.auth0_google_connection
    )

    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
):
    return await handle_callback(code)


@router.get("/microsoft/login")
async def microsoft_login():
    url = auth0_service.build_login_url(
        auth0_service.settings.auth0_microsoft_connection
    )

    return RedirectResponse(url=url)


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str = Query(...),
):
    return await handle_callback(code)


async def handle_callback(code: str):
    try:
        # Exchange authorization code for Auth0 tokens
        token_data = await auth0_service.exchange_code(code)

        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=400,
                detail="Auth0 did not return an access token",
            )

        # Retrieve authenticated user information
        user_info = await auth0_service.get_userinfo(
            access_token
        )

        # Create/update the local user through User Service
        user_service_user = await sync_user_with_user_service(
            access_token,
            user_info,
        )

        return {
            "message": "Authentication successful",
            "access_token": access_token,
            "token_type": token_data.get("token_type"),
            "expires_in": token_data.get("expires_in"),
            "user": user_info,
            "user_service_profile": user_service_user,
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Authentication failed: {str(exc)}",
        )


@router.get("/google/logout")
async def google_logout():
    return RedirectResponse(
        url=auth0_service.build_logout_url()
    )


@router.get("/microsoft/logout")
async def microsoft_logout():
    return RedirectResponse(
        url=auth0_service.build_logout_url()
    )


@router.get("/me")
async def get_current_user(
    payload: dict = Depends(validate_access_token),
):
    return {
        "authenticated": True,
        "user": payload,
    }


@router.get("/provider")
async def get_provider(
    payload: dict = Depends(validate_access_token),
):
    subject = payload.get("sub", "")

    if subject.startswith("google-oauth2"):
        provider = "google"
    elif subject.startswith("azuread"):
        provider = "microsoft"
    elif "|" in subject:
        provider = subject.split("|", 1)[0]
    else:
        provider = "unknown"

    return {
        "provider": provider,
        "subject": subject,
    }