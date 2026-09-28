"""Start the local UI:  python -m web

The port is fixed on purpose. LinkedIn only sends you back to a redirect URL
that matches *exactly*, so a port that changes between runs would break the
"Connect LinkedIn" step.

To use a different port, change PORT below, then add the new callback URL on
LinkedIn's developer website (linkedin.com/developers/apps -> your app -> Auth
tab -> Authorized redirect URLs for your app). One run can also use a different
port without editing this file:
    $env:POSTCADENCE_PORT = "9123"; python -m web
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import webbrowser

import uvicorn

HOST = "127.0.0.1"
# 8080 is often inside a Windows reserved range (Hyper-V, WSL, Docker), so avoid it.
PORT = 8787


def chosen_port() -> int:
    """PORT, unless POSTCADENCE_PORT overrides it for this run."""
    override = os.environ.get("POSTCADENCE_PORT", "").strip()
    if not override:
        return PORT
    if not override.isdigit():
        raise SystemExit(f"POSTCADENCE_PORT must be a number, not {override!r}.")
    return int(override)


def is_free(host: str, port: int) -> bool:
    """True when nothing else is holding the port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((host, port))
            return True
        except OSError:
            return False


def main() -> None:
    port = chosen_port()
    url = f"http://{HOST}:{port}"

    if not is_free(HOST, port):
        sys.exit(
            f"Port {port} is already in use.\n"
            f"  - Another PostCadence window may still be running: close it and try again.\n"
            f"  - Or pick a free port: change PORT in web/__main__.py, then add\n"
            f"    http://{HOST}:<new port>/setup/linkedin/callback\n"
            f"    on LinkedIn's developer website: linkedin.com/developers/apps\n"
            f"    -> your app -> Auth tab -> Authorized redirect URLs for your app."
        )

    print(f"PostCadence is running at {url}  (Ctrl+C to stop)")
    print("Redirect URL to paste at linkedin.com/developers/apps (Auth tab):")
    print(f"    {url}/setup/linkedin/callback")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        uvicorn.run("web.app:app", host=HOST, port=port, log_level="warning")
    except OSError as exc:
        sys.exit(f"Could not start on port {port}: {exc}")


if __name__ == "__main__":
    main()
