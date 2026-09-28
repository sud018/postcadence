"""Say exactly which LinkedIn setup step is missing, instead of guessing.

Two probes, both cheap:

1. `probe_authorize` asks LinkedIn's sign-in page a question without signing in.
   A wrong Client ID, a redirect URL that does not match, or a product that has
   not been approved each come back as a different error - which is precisely
   the information a half-finished setup needs.

2. `introspect` asks LinkedIn what an access token can actually do. It answers
   with the granted scopes, so "Share on LinkedIn was never approved" stops
   being a mystery that only shows up at 09:00 when a post fails.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import requests

from agent.linkedin.oauth import AUTH_URL, SCOPES

INTROSPECT_URL = "https://www.linkedin.com/oauth/v2/introspectToken"
TIMEOUT = 20

# The scope that lets the app publish. Without it everything else works and
# nothing ever posts.
POST_SCOPE = "w_member_social"

OK, BAD, WARN, UNKNOWN = "ok", "bad", "warn", "unknown"


@dataclass
class Result:
    """One answer, in words a person can act on."""

    state: str          # ok / bad / warn / unknown
    detail: str         # what LinkedIn said, in plain English
    fix: str = ""       # what to do about it


# Markers LinkedIn puts in its error responses, and what each one really means.
# Checked in order, so the specific ones come before the general ones.
MARKERS: list[tuple[str, str, str, str]] = [
    ("unauthorized_scope_error", BAD,
     "Your app is not allowed to post yet.",
     "Products tab - request access to 'Share on LinkedIn', then try again."),
    ("redirect_uri does not match", BAD,
     "The redirect URL on LinkedIn does not match this app's.",
     "Auth tab - paste the redirect URL below exactly, then press Update."),
    ("invalid_redirect_uri", BAD,
     "LinkedIn will not accept that redirect URL.",
     "Auth tab - paste the redirect URL below exactly, then press Update."),
    ("invalid_client_id", BAD,
     "LinkedIn does not recognise that Client ID.",
     "Auth tab - copy the Client ID again; it is easy to grab one character too few."),
    ("invalid_request", BAD,
     "LinkedIn rejected the sign-in request.",
     "Check the Client ID and the redirect URL on the Auth tab."),
]


def _classify(text: str) -> Result | None:
    lowered = text.lower()
    for marker, state, detail, fix in MARKERS:
        if marker.lower() in lowered:
            return Result(state, detail, fix)
    return None


def probe_authorize(client_id: str, redirect_uri: str, scopes: str = SCOPES) -> Result:
    """Ask the sign-in page whether this app could sign someone in.

    Nobody signs in: we stop at the first response and read the error, if any.
    """
    if not client_id:
        return Result(UNKNOWN, "No Client ID saved yet.", "Paste it below and press Save.")

    query = urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": "postcadence-check",
    })

    try:
        response = requests.get(f"{AUTH_URL}?{query}", timeout=TIMEOUT, allow_redirects=False)
    except requests.RequestException as exc:
        return Result(UNKNOWN, f"Could not reach LinkedIn: {exc}", "Check your internet connection.")

    # An error can arrive as a redirect back to us, or as an error page.
    where = response.headers.get("location", "")
    found = _classify(where) or _classify(response.text[:4000])
    if found:
        return found

    # Sent to LinkedIn's login page, or shown one: the app itself is fine.
    if response.status_code in (301, 302, 303, 307) or "login" in response.text.lower():
        return Result(OK, "LinkedIn accepts this app and redirect URL.", "")

    return Result(UNKNOWN, f"LinkedIn answered with {response.status_code}.",
                  "Try Recheck in a moment.")


def introspect(token: str, client_id: str, client_secret: str) -> dict:
    """What this token is allowed to do, straight from LinkedIn."""
    response = requests.post(
        INTROSPECT_URL,
        data={"client_id": client_id, "client_secret": client_secret, "token": token},
        timeout=TIMEOUT,
    )
    if response.status_code >= 300:
        return {}
    return response.json()


def check_token(token: str, client_id: str, client_secret: str) -> Result:
    """Is the token alive, and may it actually publish?"""
    if not token:
        return Result(UNKNOWN, "Not connected yet.", "Press Connect LinkedIn.")
    if not (client_id and client_secret):
        return Result(UNKNOWN, "Save the Client ID and secret first.", "")

    try:
        data = introspect(token, client_id, client_secret)
    except requests.RequestException as exc:
        return Result(UNKNOWN, f"Could not reach LinkedIn: {exc}", "Check your internet connection.")

    if not data:
        return Result(WARN, "LinkedIn would not describe this token.",
                      "If posting fails, reconnect.")

    if data.get("status") != "active" or not data.get("active", True):
        return Result(BAD, "The token is no longer active.", "Press Reconnect.")

    granted = str(data.get("scope", ""))
    if POST_SCOPE not in granted:
        return Result(BAD, "Signed in, but the token may not publish posts.",
                      "Products tab - add 'Share on LinkedIn', then Reconnect.")

    return Result(OK, f"Active, and allowed to post. Scopes: {granted}.", "")
