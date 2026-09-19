"""Publish a text post to LinkedIn."""

from __future__ import annotations
import requests
from agent.linkedin.errors import LinkedInAuthError, LinkedInError

POSTS_URL = "https://api.linkedin.com/rest/posts"
LINKEDIN_VERSION = "202608"
MAX_LENGTH = 3000

def post_text(text: str, access_token: str, member_id: str) -> str:
    """Publish `text`. Returns the post's URN."""
    
    text = text.strip()
    if not text:
        raise LinkedInError("Refusing to post empty text.")
    if len(text) > MAX_LENGTH:
        raise LinkedInError(f"Post is {len(text)} characters; LinkedIn allows {MAX_LENGTH}.")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    
    body = {
        "author": f"urn:li:person:{member_id}",
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    
    response = requests.post(POSTS_URL, headers=headers, json=body, timeout=30)

    if response.status_code == 401:
        raise LinkedInAuthError("LinkedIn rejected the token. Run: python -m agent linkedin connect")
    if response.status_code not in (200, 201):
        raise LinkedInError(f"Post failed ({response.status_code}): {response.text[:300]}")

    return response.headers.get("x-restli-id", "")
