"""Start the local UI:  python -m web"""
from __future__ import annotations

import threading
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8080


def main() -> None:
    threading.Timer(1.0, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()
    uvicorn.run("web.app:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    main()
