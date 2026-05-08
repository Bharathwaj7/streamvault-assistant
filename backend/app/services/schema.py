import aiosqlite
from app.core.config import get_settings
from app.core.logging import get_logger

logger   = get_logger()
settings = get_settings()

_schema_cache: str = ""


async def get_db_schema() -> str:
    global _schema_cache
    if _schema_cache:
        return _schema_cache

    try:
        async with aiosqlite.connect(settings.sqlite_db_path) as db:
            schema_lines = []

            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ) as cursor:
                tables = [row[0] for row in await cursor.fetchall()]

            for table in tables:
                async with db.execute(f"PRAGMA table_info({table})") as cursor:
                    columns = await cursor.fetchall()

                # ONLY column names — no types, keeps prompt clean for Groq
                col_names = [col[1] for col in columns]
                schema_lines.append(f"   - {table}: {', '.join(col_names)}")

            _schema_cache = "\n".join(schema_lines)
            logger.info("schema: loaded db schema dynamically",
                        extra={"tables": len(tables)})
            return _schema_cache

    except Exception as e:
        logger.error("schema: failed to load", extra={"exc": str(e)})
        return "   - Schema unavailable"


def refresh_schema_cache():
    global _schema_cache
    _schema_cache = ""
    logger.info("schema: cache cleared, will reload on next request")