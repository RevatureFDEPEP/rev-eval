from typing import Any, Dict, Optional

from fastapi import Header, HTTPException, status


async def get_current_trainer(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> Dict[str, Any]:
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header",
        )
    if (x_user_role or "").upper() != "TRAINER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trainer role required",
        )
    return {"id": int(x_user_id), "role": x_user_role}
