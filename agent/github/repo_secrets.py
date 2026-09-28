"""Put secrets into GitHub Actions without GitHub ever seeing them in the clear.

GitHub publishes a public key for each repository. We lock the value with that
key here, on your machine, and send only the locked box. GitHub can store it,
and the Actions runner can open it - but the value never travels as plain text,
not even over HTTPS.

That is a "sealed box": encrypt with someone's public key, and only their
private key opens it. The same idea as a padlock anyone can click shut and only
the owner can unlock.
"""
from __future__ import annotations

from base64 import b64encode

from nacl import encoding, public

from agent.github.api import call

# Secrets the app is allowed to push, and where each one comes from locally.
PUSHABLE = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "LINKEDIN_ACCESS_TOKEN")


def seal(public_key_b64: str, value: str) -> str:
    """Lock one value with the repository's public key."""
    key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    box = public.SealedBox(key)
    return b64encode(box.encrypt(value.encode("utf-8"))).decode("utf-8")


def public_key(repo: str, token: str) -> tuple[str, str]:
    """(key, key_id) - GitHub needs the id back so it knows which key was used."""
    data = call("GET", f"/repos/{repo}/actions/secrets/public-key", token)
    return data["key"], data["key_id"]


def put_secret(repo: str, name: str, value: str, token: str,
               key: str = "", key_id: str = "") -> None:
    """Create or replace one repository secret."""
    if not key or not key_id:
        key, key_id = public_key(repo, token)

    call("PUT", f"/repos/{repo}/actions/secrets/{name}", token,
         json={"encrypted_value": seal(key, value), "key_id": key_id})


def existing_secrets(repo: str, token: str) -> list[str]:
    """Names only - GitHub never gives a secret's value back, not even to you."""
    data = call("GET", f"/repos/{repo}/actions/secrets?per_page=100", token)
    return [s["name"] for s in data.get("secrets", [])]
