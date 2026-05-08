import aiosqlite
from app.core.config import get_settings
from app.core.logging import get_logger

logger   = get_logger()
settings = get_settings()

# Views expose only safe columns — sensitive fields excluded
VIEWS = {
    # Excludes: director, cast_lead (PII-adjacent), budget_usd (financial)
    "v_movies": """
        CREATE VIEW IF NOT EXISTS v_movies AS
        SELECT movie_id, title, genre, release_date,
               runtime_min, language, rating, status
        FROM movies
    """,

    # Excludes: viewer_id details kept but no joined_date (temporal PII)
    "v_viewers_summary": """
        CREATE VIEW IF NOT EXISTS v_viewers_summary AS
        SELECT age_group, gender, city, country,
               subscription_type, preferred_genre,
               preferred_platform, is_active
        FROM viewers
    """,

    # Excludes: viewer_id (PII link), device_type
    "v_watch_activity": """
        CREATE VIEW IF NOT EXISTS v_watch_activity AS
        SELECT activity_id, movie_id, watch_date,
               platform, watch_duration_min,
               completion_rate, rewatched
        FROM watch_activity
    """,

    # Excludes: viewer_id (PII link)
    "v_reviews": """
        CREATE VIEW IF NOT EXISTS v_reviews AS
        SELECT review_id, movie_id, review_date,
               score, sentiment, platform, helpful_votes
        FROM reviews
    """,

    # Full marketing spend — no sensitive columns
    "v_marketing_spend": """
        CREATE VIEW IF NOT EXISTS v_marketing_spend AS
        SELECT spend_id, movie_id, month, channel,
               spend_usd, impressions, clicks, conversions
        FROM marketing_spend
    """,

    # Full regional performance — no sensitive columns
    "v_regional_performance": """
        CREATE VIEW IF NOT EXISTS v_regional_performance AS
        SELECT perf_id, movie_id, city, month,
               total_views, unique_viewers,
               avg_rating, revenue_usd, engagement_score
        FROM regional_performance
    """,
}


async def create_views():
    """Create all restricted views at startup."""
    try:
        async with aiosqlite.connect(settings.sqlite_db_path) as db:
            for view_name, sql in VIEWS.items():
                await db.execute(f"DROP VIEW IF EXISTS {view_name}")
                await db.execute(sql)
            await db.commit()
        logger.info("views: all security views created",
                    extra={"count": len(VIEWS)})
    except Exception as e:
        logger.error("views: failed to create views", extra={"exc": str(e)})