from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.schemas.analytics import InsightResponse
from app.services.analytics import get_insights
from app.api.dependencies import get_current_user
from app.core.logging import get_logger

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = get_logger()


@router.get("/insights", response_model=InsightResponse)
async def insights(
    current_user: dict = Depends(get_current_user),
    period: Optional[str] = Query(
        default=None,
        description="Time period filter: last30 | q1_2025 | q2_2025 | q3_2025 | q4_2025"
    ),
    genre: Optional[str] = Query(
        default=None,
        description="Genre filter: Sci-Fi | Action | Drama | Comedy | Thriller | Romance"
    ),
):
    logger.info(
        "analytics: insights request",
        extra={
            "user":   current_user["username"],
            "period": period or "all",
            "genre":  genre  or "all",
        }
    )
    try:
        return await get_insights(period=period, genre=genre)
    except Exception as e:
        logger.error("analytics: error", extra={"exc": str(e)})
        raise HTTPException(status_code=500, detail=str(e))