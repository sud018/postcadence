"""Sign in to LinkedIn once and get an access token."""

from __future__ import annotations

import secrets as randomness
import webbrowser
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from agent.linkedin.errors import LinkedInError

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
REDIRECT_URI = "http://localhost:8000/callback"
SCOPES = "openid profile w_member_social"

class _CallbackHandler(BaseHTTPRequestHandler):
    """Handles the single browser request LinkedIn sends us."""

    result: dict = {}
    def do_GET(self)->None:
        parsed = urlparse(self.path)
        if parsed.path!="/callback":
            self.send_error(404)
            return

        _CallbackHandler.result = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h2>PostCadence is connected. You can close this tab.</h2>")

    def log_message(self, *args) -> None:
        """Silence the default request logging."""

def _wait_for_redirect(timeout: int = 180) -> dict:
    _CallbackHandler.result={}
    server = HTTPServer(("localhost", 8000), _CallbackHandler)
    server.timeout = timeout
    server.handle_request()
    server.server_close()
    return _CallbackHandler.result

def exchange_code(code: str, client_id: str, client_secret: str,
                  redirect_uri: str = REDIRECT_URI) -> dict:
    """Swap a one-time code for an access token. redirect_uri must match the one used to start."""
    response = requests.post(
        TOKEN_URL,
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret
        }, timeout=30,
    )

    if response.status_code != 200:
        raise LinkedInError(f"Token exchange failed ({response.status_code}): {response.text[:300]}")
    return response.json()

def fetch_member_id(access_token: str) -> str:
    response = requests.get(
        USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30
    )
    if response.status_code != 200:
        raise LinkedInError(f"Could not read your profile ({response.status_code}): {response.text[:300]}")
    return response.json()["sub"]

def authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
    """Where to send the browser to ask the user for permission."""
    return AUTH_URL + "?" + urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": SCOPES,
    })


def finish(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    """Everything after the redirect: token, member id and expiry date."""
    token = exchange_code(code, client_id, client_secret, redirect_uri)
    access_token = token["access_token"]
    expires_on = date.today() + timedelta(seconds=int(token.get("expires_in", 0)))
    return {
        "access_token": access_token,
        "member_id": fetch_member_id(access_token),
        "expires_on": expires_on.isoformat(),
    }


def new_state() -> str:
    return randomness.token_urlsafe(16)


def connect(client_id: str, client_secret: str) -> dict:
    """Run the whole sign-in flow. Returns token, member id and expiry date."""

    state = new_state()
    url = authorize_url(client_id, REDIRECT_URI, state)

    print("Opening your browser to sign in to LinkedIn...")
    webbrowser.open(url)
    print(f"If nothing opened, paste this into your browser:\n{url}\n")

    result = _wait_for_redirect()
    if not result:
        raise LinkedInError("Timed out waiting for LinkedIn to redirect back.")
    if "error" in result:
        raise LinkedInError(f"LinkedIn said: {result.get('error_description', result['error'])}")
    if result.get("state") != state:
        raise LinkedInError("State did not match - ignoring this response.")

    return finish(result["code"], client_id, client_secret, REDIRECT_URI)
