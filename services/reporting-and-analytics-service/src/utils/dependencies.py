from fastapi import Header, HTTPException, status


async def require_trainer(
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_user_email: str | None = Header(None, alias="X-User-Email"),
    x_user_role: str | None = Header(None, alias="X-User-Role"),
) -> dict:
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth headers")
    if (x_user_role or "").upper() != "TRAINER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Trainer role required")
    return {"user_id": x_user_id, "email": x_user_email, "role": x_user_role}


async def get_current_user(
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_user_email: str | None = Header(None, alias="X-User-Email"),
    x_user_role: str | None = Header(None, alias="X-User-Role"),
) -> dict:
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth headers")
    return {"user_id": x_user_id, "email": x_user_email, "role": x_user_role}
