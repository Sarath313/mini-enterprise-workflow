from urllib.parse import urlencode

import httpx

from app.config import get_settings


class Auth0Service:
    def __init__(self):
        self.settings = get_settings()

    @property
    def base_url(self) -> str:
        return f"https://{self.settings.auth0_domain}"

    def build_login_url(self, connection: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.settings.auth0_client_id,
            "redirect_uri": self.settings.auth0_callback_url,
            "scope": "openid profile email",
            "audience": self.settings.auth0_audience,
            "connection": connection,
        }

        return f"{self.base_url}/authorize?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.settings.auth0_client_id,
            "client_secret": self.settings.auth0_client_secret,
            "code": code,
            "redirect_uri": self.settings.auth0_callback_url,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/oauth/token",
                json=payload,
                timeout=15.0,
            )

        response.raise_for_status()
        return response.json()

    async def get_userinfo(self, access_token: str) -> dict:
        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/userinfo",
                headers=headers,
                timeout=15.0,
            )

        response.raise_for_status()
        return response.json()

    def build_logout_url(self) -> str:
        params = {
            "client_id": self.settings.auth0_client_id,
            "returnTo": self.settings.auth0_logout_url,
        }

        return f"{self.base_url}/v2/logout?{urlencode(params)}"


auth0_service = Auth0Service()