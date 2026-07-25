"""
Production-grade entry point for running the SentinelRAG backend.

Reads PORT and HOST from environment variables, validates the port is
bindable BEFORE handing control to uvicorn, and falls back to a random
available port when the requested port is unavailable.

Usage:
    python run.py
    python run.py --port 8080
    python run.py --host 127.0.0.1 --port 9000
"""

import os
import socket
import sys
from argparse import ArgumentParser


def _find_free_port(preferred: int, host: str = "0.0.0.0") -> int:
    """Try *preferred* first; if that fails return whatever the OS gives us."""
    if preferred == 0:
        candidates = [0]
    else:
        candidates = [preferred, 0]  # 0 = OS-assigned ephemeral port

    last_error = None
    for port in candidates:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                actual = s.getsockname()[1]
                if actual != preferred and preferred != 0:
                    print(
                        f"WARNING: preferred port {preferred} on {host} "
                        f"unavailable ({last_error}). Falling back to port {actual}.",
                        file=sys.stderr,
                    )
                return actual
            except OSError as exc:
                last_error = exc.strerror
    return 0


def main() -> None:
    parser = ArgumentParser(description="SentinelRAG backend server")
    parser.add_argument("--host", default=None, help="Host to bind (default: $HOST or 0.0.0.0)")
    parser.add_argument(
        "--port", type=int, default=None, help="Port to bind (default: $PORT or 8000)"
    )
    args = parser.parse_args()

    requested_host = args.host or os.getenv("HOST", "0.0.0.0")
    requested_port = args.port if args.port is not None else int(os.getenv("PORT", "8000"))

    print(f"Requested binding: {requested_host}:{requested_port}")

    actual_port = _find_free_port(requested_port, requested_host)

    if actual_port != requested_port:
        print(
            f"WARNING: Port {requested_port} is not available on {requested_host}. "
            f"Falling back to port {actual_port}.",
            file=sys.stderr,
        )
    else:
        print(f"Port {requested_port} is available on {requested_host}.")

    print(f"Starting uvicorn on {requested_host}:{actual_port} …")
    os.environ["PORT"] = str(actual_port)

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=requested_host,
        port=actual_port,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
