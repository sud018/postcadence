"""Start the local UI:  python -m web

The port can be changed without editing this file:
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
CANDIDATE_PORTS = (8787, 8123, 5177, 7420, 0)


def free_port(host: str, ports: tuple[int, ...]) -> int:
    """First port we can actually bind. 0 asks the OS for any free one."""
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((host, port))
                return probe.getsockname()[1]
            except OSError:
                continue
    raise SystemExit("No free port found. Set POSTCADENCE_PORT to one you can use.")


def main() -> None:
    chosen = os.environ.get("POSTCADENCE_PORT")
    port = int(chosen) if chosen else free_port(HOST, CANDIDATE_PORTS)
    url = f"http://{HOST}:{port}"

    print(f"PostCadence is running at {url}  (Ctrl+C to stop)")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        uvicorn.run("web.app:app", host=HOST, port=port, log_level="warning")
    except OSError as exc:
        sys.exit(f"Could not start on port {port}: {exc}")


if __name__ == "__main__":
    main()
