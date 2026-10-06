from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.security import validate_access_token
from app.config import get_settings
from app.services.auth0_service import auth0_service
from app.services.user_service import sync_user_with_user_service


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

settings = get_settings()

bearer_scheme = HTTPBearer()


GOOGLE_CALLBACK_URL = (
    f"{settings.frontend_url.rsplit(':5173', 1)[0]}:8001"
    "/auth/google/callback"
)

MICROSOFT_CALLBACK_URL = (
    f"{settings.frontend_url.rsplit(':5173', 1)[0]}:8001"
    "/auth/microsoft/callback"
)


@router.get("/google/login")
async def google_login():
    url = auth0_service.build_login_url(
        auth0_service.settings.auth0_google_connection,
        GOOGLE_CALLBACK_URL,
    )

    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(code: str = Query(...)):
    return await handle_callback(
        code,
        GOOGLE_CALLBACK_URL,
    )


@router.get("/microsoft/login")
async def microsoft_login():
    url = auth0_service.build_login_url(
        auth0_service.settings.auth0_microsoft_connection,
        MICROSOFT_CALLBACK_URL,
    )

    return RedirectResponse(url=url)


@router.get("/microsoft/callback")
async def microsoft_callback(code: str = Query(...)):
    return await handle_callback(
        code,
        MICROSOFT_CALLBACK_URL,
    )


async def handle_callback(
    code: str,
    redirect_uri: str,
):
    try:
        token_data = await auth0_service.exchange_code(
            code,
            redirect_uri,
        )

        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=400,
                detail="Auth0 did not return an access token",
            )

        user_info = await auth0_service.get_userinfo(
            access_token
        )

        await sync_user_with_user_service(
            access_token,
            user_info,
        )

        callback_url = (
            f"{settings.frontend_url}"
            f"/callback#access_token={access_token}"
        )

        return RedirectResponse(
            url=callback_url,
            status_code=302,
        )

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
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    user_info = await auth0_service.get_userinfo(
        credentials.credentials
    )

    return {
        "authenticated": True,
        "user": {
            **payload,
            **user_info,
        },
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