import httpx

from app.config import get_settings


settings = get_settings()


async def sync_user_with_user_service(
    access_token: str,
    user_info: dict,
) -> dict:
    payload = {
        "auth0_user_id": user_info.get("sub"),
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
        "provider": (
            user_info.get("sub", "").split("|", 1)[0]
            if "|" in user_info.get("sub", "")
            else "unknown"
        ),
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.user_service_url}/users/",
            json=payload,
            headers=headers,
            timeout=15.0,
        )

    response.raise_for_status()

    return response.json()