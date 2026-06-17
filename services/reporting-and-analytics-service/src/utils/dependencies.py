from typing import Any, Dict, Optional

from fastapi import Header, HTTPException, status


def _parse_user_id(x_user_id: Optional[str]) -> int:
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header",
        )
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-User-Id header: must be numeric",
        )


async def get_current_trainer(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> Dict[str, Any]:
    user_id = _parse_user_id(x_user_id)
    if (x_user_role or "").upper() != "TRAINER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trainer role required",
        )
    return {"id": user_id, "role": x_user_role}


async def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> Dict[str, Any]:
    user_id = _parse_user_id(x_user_id)
    return {"id": user_id, "role": x_user_role}
