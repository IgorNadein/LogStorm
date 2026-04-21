"""HTTP API authentication dependencies."""

from typing import Optional

from fastapi import Header, HTTPException, Request, status


def require_token(
    request: Request,
    authorization: Optional[str] = Header(default=None),
) -> None:
    token = request.app.state.api_token
    if not token:
        return
    expected = f"Bearer {token}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid LogStorm API token",
        )
