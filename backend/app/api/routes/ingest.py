from fastapi import APIRouter, Depends, HTTPException
from app.services.ingestion import run_full_ingestion
from app.api.dependencies import get_current_user
from app.core.logging import get_logger

router = APIRouter(prefix="/ingest", tags=["ingest"])
logger = get_logger()


@router.post("")
async def ingest(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required for ingestion.")
    logger.info("ingest: triggered", extra={"user": current_user["username"]})
    try:
        result = await run_full_ingestion()
        return result
    except Exception as e:
        logger.error("ingest: error", extra={"exc": str(e)})
        raise HTTPException(status_code=500, detail=str(e))
