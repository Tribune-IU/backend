"""
Shim for hosts that invoke `uvicorn main:app` (e.g. Railway/Nixpacks defaults).
The ASGI application is defined in ``app.main``.
"""

from app.main import app

__all__ = ["app"]


def main():
    print("Hello from backend!")


if __name__ == "__main__":
    main()
