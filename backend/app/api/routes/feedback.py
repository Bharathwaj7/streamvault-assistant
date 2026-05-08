import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import aiosqlite
from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.logging import get_logger

router   = APIRouter(prefix="/feedback", tags=["feedback"])
logger   = get_logger()
settings = get_settings()


class FeedbackRequest(BaseModel):
    query_id:   str
    rating:     str          # "positive" | "negative"
    query_text: Optional[str] = ""
    answer:     Optional[str] = ""
    context: Optional[dict]  = {}


class FeedbackResponse(BaseModel):
    status:      str
    feedback_id: str


async def ensure_feedback_table():
    """Create feedback table if it doesn't exist."""
    async with aiosqlite.connect(settings.sqlite_db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id   TEXT PRIMARY KEY,
                query_id      TEXT NOT NULL,
                username      TEXT NOT NULL,
                rating        TEXT NOT NULL,
                query_text    TEXT,
                answer        TEXT,
                tools_used    TEXT,
                confidence    TEXT,
                model_used    TEXT,
                iterations    INTEGER,
                created_at    TEXT NOT NULL
            )
        """)
        await db.commit()


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request:      FeedbackRequest,
    current_user: dict = Depends(get_current_user),
):
    if request.rating not in ("positive", "negative"):
        raise HTTPException(
            status_code=400,
            detail="Rating must be 'positive' or 'negative'"
        )

    feedback_id = str(uuid.uuid4())
    created_at  = datetime.now(timezone.utc).isoformat()
    context     = request.context or {}

    try:
        await ensure_feedback_table()
        async with aiosqlite.connect(settings.sqlite_db_path) as db:
            await db.execute("""
                INSERT INTO feedback (
                    feedback_id, query_id, username, rating,
                    query_text, answer, tools_used, confidence,
                    model_used, iterations, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback_id,
                request.query_id,
                current_user["username"],
                request.rating,
                request.query_text or "",
                request.answer or "",
                str(context.get("tools_used", [])),
                context.get("confidence", ""),
                context.get("model_used", ""),
                context.get("iterations", 0),
                created_at,
            ))
            await db.commit()

        logger.info(
            "feedback: submitted",
            extra={
                "user":        current_user["username"],
                "rating":      request.rating,
                "feedback_id": feedback_id,
            }
        )
        return FeedbackResponse(status="ok", feedback_id=feedback_id)

    except Exception as e:
        logger.error("feedback: failed to save", extra={"exc": str(e)})
        raise HTTPException(status_code=500, detail="Failed to save feedback")