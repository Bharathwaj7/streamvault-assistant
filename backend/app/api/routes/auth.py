from fastapi import APIRouter, HTTPException, status
from app.schemas.auth import TokenRequest, TokenResponse
from app.core.security import authenticate_user, create_access_token
from app.core.logging import get_logger

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger()


@router.post("/token", response_model=TokenResponse)
async def login(request: TokenRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        logger.warning("auth: failed login", extra={"username": request.username})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    logger.info("auth: successful login", extra={"username": request.username})
    return TokenResponse(
        access_token=token,
        username=user["username"],
        role=user["role"],
    )
