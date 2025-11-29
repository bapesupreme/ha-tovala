"""API client for Tovala Smart Oven."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
from aiohttp import ClientSession, ClientError, ClientTimeout
import time
import logging
import json
import base64

_LOGGER = logging.getLogger(__name__)

# Prefer beta, fall back to prod if needed
DEFAULT_BASES: Sequence[str] = (
    "https://api.beta.tovala.com",
    "https://api.tovala.com",
)

LOGIN_PATH = "/v0/getToken"


class TovalaAuthError(Exception):
    """Authentication failed (bad credentials or denied)."""


class TovalaApiError(Exception):
    """Other API/HTTP failures."""


class TovalaClient:
    """Client for interacting with Tovala API."""

    def __init__(
        self,
        session: ClientSession,
        email: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None,
        api_bases: Optional[Sequence[str]] = None,
    ):
        """Initialize the Tovala API client."""
        self._session = session
        self._email = email
        self._password = password
        self._token = token
        self._token_exp = 0
        self._bases: Sequence[str] = api_bases or DEFAULT_BASES
        self._base: Optional[str] = None  # set on successful login
        self._user_id: Optional[int] = None  # extracted from JWT token

    @property
    def base_url(self) -> Optional[str]:
        """Return the active base URL."""
        return self._base

    @property
    def user_id(self) -> Optional[int]:
        """Return the user ID."""
        return self._user_id

    def _decode_jwt_user_id(self, token: str) -> Optional[int]:
        """Extract userId from JWT token payload without verification."""
        try:
            # JWT format: header.payload.signature
            parts = token.split('.')
            if len(parts) != 3:
                _LOGGER.warning("Invalid JWT format")
                return None

            # Decode payload (add padding if needed)
            payload = parts[1]
            # Add padding to make it a multiple of 4
            padding = len(payload) % 4
            if padding:
                payload += '=' * (4 - padding)

            decoded = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded)
            user_id = data.get("userId")

            if user_id:
                _LOGGER.debug("Extracted userId %s from JWT", user_id)
                return int(user_id)
            else:
                _LOGGER.warning("No userId field in JWT payload")
                return None
        except Exception as e:
            _LOGGER.error("Failed to decode JWT: %s", e, exc_info=True)
            return None

    async def login(self) -> None:
        """Ensure we have a valid bearer token. Tries beta then prod."""
        if self._token and self._token_exp > time.time() + 60:
            _LOGGER.debug("Token still valid, skipping login")
            return
        
        if not (self._token or (self._email and self._password)):
            raise TovalaAuthError("Missing credentials")

        # If we already have a token but exp unknown, assume 1 hour left
        if self._token and not self._token_exp:
            self._token_exp = int(time.time()) + 3600
            self._base = self._bases[0]
            self._user_id = self._decode_jwt_user_id(self._token)
            _LOGGER.debug("Using provided token with assumed expiry")
            return

        # CRITICAL: X-Tovala-AppID header is required!
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "HomeAssistant-Tovala/1.0",
            "X-Tovala-AppID": "MAPP",
        }

        last_err: Optional[Exception] = None
        for base in self._bases:
            url = f"{base}{LOGIN_PATH}"
            _LOGGER.debug("Attempting login to %s", url)
            
            try:
                timeout = ClientTimeout(total=10)
                async with self._session.post(
                    url,
                    headers=headers,
                    json={"email": self._email, "password": self._password, "type": "user"},
                    timeout=timeout,
                ) as r:
                    txt = await r.text()
                    _LOGGER.debug("Login response from %s: status=%s", base, r.status)
                    
                    if r.status == 429:
                        # Rate limited - stop immediately
                        _LOGGER.error("Rate limited by Tovala API: %s", txt)
                        raise TovalaApiError(f"Rate limited (HTTP 429): {txt}")
                    
                    if r.status in (401, 403):
                        # Stop immediately on explicit auth failure
                        _LOGGER.error("Authentication failed: HTTP %s", r.status)
                        raise TovalaAuthError(f"Invalid auth (HTTP {r.status}): {txt}")
                    
                    if r.status >= 400:
                        last_err = TovalaApiError(f"Login failed (HTTP {r.status}): {txt}")
                        _LOGGER.warning("Login failed for %s: %s", base, last_err)
                        continue
                    
                    data = await r.json()
                    _LOGGER.debug("Login JSON response keys: %s", list(data.keys()))

                # Support both 'token' and 'accessToken' response formats
                token = data.get("token") or data.get("accessToken") or data.get("jwt")
                if not token:
                    last_err = TovalaAuthError("No token returned from getToken")
                    _LOGGER.warning("No token in response from %s", base)
                    continue

                self._token = token
                self._token_exp = int(time.time()) + int(data.get("expiresIn", 3600))
                self._base = base

                # Extract userId from JWT token
                self._user_id = self._decode_jwt_user_id(token)
                if not self._user_id:
                    _LOGGER.warning("Could not extract userId from token")

                _LOGGER.info("Successfully logged in to %s (userId: %s)", base, self._user_id)
                return
                
            except TovalaAuthError:
                # Do not try other bases if credentials are wrong
                raise
            except TovalaApiError:
                # Also stop on rate limits
                raise
            except ClientError as e:
                last_err = e
                _LOGGER.error("Connection error for %s: %s", base, str(e))
                # Try next base
            except Exception as e:
                last_err = e
                _LOGGER.error("Unexpected error for %s: %s", base, str(e), exc_info=True)
                # Try next base

        # If we reach here, all bases failed
        _LOGGER.error("All login attempts failed. Last error: %s", last_err)
        if isinstance(last_err, Exception):
            raise TovalaApiError(f"Connection failed: {str(last_err)}")
        raise TovalaApiError("Login failed")

    async def _auth_headers(self) -> Dict[str, str]:
        """Get authenticated headers."""
        await self.login()
        return {
            "Authorization": f"Bearer {self._token}",
            "X-Tovala-AppID": "MAPP",
        }

    async def _get_json(self, path: str, **fmt) -> Any:
        """Make a GET request and return JSON."""
        if not self._base:
            # Ensure login determined the base URL
            await self.login()
        assert self._base, "Base URL not set after login"
        headers = await self._auth_headers()
        url = f"{self._base}{path.format(**fmt)}"
        _LOGGER.debug("GET %s", url)
        
        try:
            timeout = ClientTimeout(total=10)
            async with self._session.get(url, headers=headers, timeout=timeout) as r:
                txt = await r.text()
                _LOGGER.debug("GET %s -> %s", url, r.status)
                
                if r.status == 404:
                    raise TovalaApiError("not_found")
                if r.status >= 400:
                    raise TovalaApiError(f"HTTP {r.status}: {txt}")
                try:
                    return await r.json()
                except Exception:
                    # Some endpoints may return empty body
                    return {}
        except ClientError as e:
            _LOGGER.error("Connection error for %s: %s", url, str(e))
            raise TovalaApiError(f"Connection failed: {str(e)}")

    async def _post_json(self, path: str, data: dict, **fmt) -> Any:
        """Make a POST request and return JSON."""
        if not self._base:
            await self.login()
        assert self._base, "Base URL not set after login"
        headers = await self._auth_headers()
        headers["Content-Type"] = "application/json"
        url = f"{self._base}{path.format(**fmt)}"
        _LOGGER.debug("POST %s", url)
        
        try:
            timeout = ClientTimeout(total=10)
            async with self._session.post(url, headers=headers, json=data, timeout=timeout) as r:
                txt = await r.text()
                _LOGGER.debug("POST %s -> %s", url, r.status)
                
                if r.status >= 400:
                    raise TovalaApiError(f"HTTP {r.status}: {txt}")
                try:
                    return await r.json()
                except Exception:
                    return {}
        except ClientError as e:
            _LOGGER.error("Connection error for %s: %s", url, str(e))
            raise TovalaApiError(f"Connection failed: {str(e)}")

    async def list_ovens(self) -> List[Dict[str, Any]]:
        """Get user's ovens list."""
        if not self._user_id:
            raise TovalaApiError("No user_id available - login first")

        _LOGGER.debug("Fetching ovens for user %s", self._user_id)

        try:
            path = f"/v0/users/{self._user_id}/ovens"
            data = await self._get_json(path)
            _LOGGER.debug("Ovens endpoint returned: %s", data)

            if isinstance(data, list):
                _LOGGER.info("Found %d ovens", len(data))
                return data
            else:
                _LOGGER.warning("Unexpected ovens response format: %s", type(data))
                return []
        except Exception as e:
            _LOGGER.error("Failed to list ovens: %s", e, exc_info=True)
            raise TovalaApiError(f"Failed to list ovens: {str(e)}")

    async def oven_status(self, oven_id: str) -> Dict[str, Any]:
        """Fetch oven cooking status."""
        if not oven_id:
            _LOGGER.warning("oven_status called with empty oven_id")
            return {}

        if not self._user_id:
            raise TovalaApiError("No user_id available - login first")

        _LOGGER.debug("Fetching status for oven %s (user %s)", oven_id, self._user_id)

        try:
            path = f"/v0/users/{self._user_id}/ovens/{oven_id}/cook/status"
            data = await self._get_json(path)
            _LOGGER.debug("Status endpoint returned: %s", data)
            return data
        except Exception as e:
            _LOGGER.error("Failed to fetch oven status: %s", e, exc_info=True)
            raise TovalaApiError(f"Failed to fetch oven status: {str(e)}")

    async def meal_details(self, meal_id: str) -> Optional[Dict[str, Any]]:
        """Fetch meal details by ID."""
        if not meal_id:
            _LOGGER.warning("meal_details called with empty meal_id")
            return None

        if not self._user_id:
            raise TovalaApiError("No user_id available - login first")

        _LOGGER.debug("Fetching meal details for meal %s (user %s)", meal_id, self._user_id)

        try:
            path = f"/v1/users/{self._user_id}/meals/{meal_id}"
            data = await self._get_json(path)
            _LOGGER.debug("Meal details endpoint returned keys: %s", list(data.keys()) if isinstance(data, dict) else "not a dict")

            # Response format: {"meal": {...}}
            if isinstance(data, dict) and "meal" in data:
                return data["meal"]
            return data
        except Exception as e:
            _LOGGER.warning("Failed to fetch meal details for meal_id %s: %s", meal_id, e)
            return None

    async def cooking_history(self, oven_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch cooking history for an oven."""
        if not oven_id:
            _LOGGER.warning("cooking_history called with empty oven_id")
            return []

        if not self._user_id:
            raise TovalaApiError("No user_id available - login first")

        _LOGGER.debug("Fetching cooking history for oven %s (user %s)", oven_id, self._user_id)

        try:
            path = f"/v0/users/{self._user_id}/ovens/{oven_id}/cook/history"
            data = await self._get_json(path)
            _LOGGER.debug("Cooking history endpoint returned %s entries", len(data) if isinstance(data, list) else "unknown")

            if isinstance(data, list):
                # Return limited results (most recent first)
                return data[:limit]
            return []
        except Exception as e:
            _LOGGER.warning("Failed to fetch cooking history: %s", e)
            return []

    async def get_custom_recipes(self) -> List[Dict[str, Any]]:
        """Fetch custom recipes for the user."""
        if not self._user_id:
            raise TovalaApiError("No user_id available - login first")

        _LOGGER.debug("Fetching custom recipes for user %s", self._user_id)

        try:
            path = f"/v0/users/{self._user_id}/customMealDataJSON"
            data = await self._get_json(path)
            _LOGGER.debug("Custom recipes endpoint returned keys: %s", list(data.keys()) if isinstance(data, dict) else "not a dict")

            # Extract userRecipes array
            if isinstance(data, dict) and "userRecipes" in data:
                recipes = [
                    {"title": recipe.get("title"), "barcode": recipe.get("barcode")}
                    for recipe in data["userRecipes"]
                    if recipe.get("title") and recipe.get("barcode")
                ]
                _LOGGER.info("Found %d custom recipes", len(recipes))
                return recipes
            return []
        except Exception as e:
            _LOGGER.error("Failed to fetch custom recipes: %s", e, exc_info=True)
            raise TovalaApiError(f"Failed to fetch custom recipes: {str(e)}")

    async def start_cooking(self, oven_id: str, barcode: str) -> None:
        """Start cooking with a specific barcode."""
        if not oven_id:
            raise TovalaApiError("oven_id is required")
        if not barcode:
            raise TovalaApiError("barcode is required")

        if not self._user_id:
            raise TovalaApiError("No user_id available - login first")

        _LOGGER.info("Starting cooking: oven=%s, barcode=%s", oven_id, barcode)

        try:
            path = f"/v0/users/{self._user_id}/ovens/{oven_id}/cook/start"
            await self._post_json(path, {"barcode": barcode})
            _LOGGER.info("Successfully started cooking")
        except Exception as e:
            _LOGGER.error("Failed to start cooking: %s", e, exc_info=True)
            raise TovalaApiError(f"Failed to start cooking: {str(e)}")

    async def cancel_cook(self, oven_id: str) -> None:
        """Cancel current cooking session."""
        if not oven_id:
            raise TovalaApiError("oven_id is required")

        if not self._user_id:
            raise TovalaApiError("No user_id available - login first")

        _LOGGER.info("Canceling cook: oven=%s", oven_id)

        try:
            path = f"/v0/users/{self._user_id}/ovens/{oven_id}/cook/cancel"
            await self._post_json(path, {})
            _LOGGER.info("Successfully canceled cooking")
        except Exception as e:
            _LOGGER.error("Failed to cancel cooking: %s", e, exc_info=True)
            raise TovalaApiError(f"Failed to cancel cooking: {str(e)}")
