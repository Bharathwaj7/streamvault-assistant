import aiosqlite
from typing import Any
from app.tools.base import BaseTool
from app.core.config import get_settings
from app.core.logging import get_logger

logger   = get_logger()
settings = get_settings()

# Tables the AI is allowed to query — security boundary
ALLOWED_TABLES = {
    "movies", "viewers", "watch_activity",
    "reviews", "marketing_spend", "regional_performance",
}


class SQLTool(BaseTool):
    @property
    def name(self) -> str:
        return "query_database"

    @property
    def description(self) -> str:
        return (
            "Query the StreamVault SQLite database for structured business data. "
            "Use this tool for questions about movie performance, viewer counts, "
            "watch activity, reviews, marketing spend, and regional engagement. "
            "Available tables: movies, viewers, watch_activity, reviews, "
            "marketing_spend, regional_performance. "
            "Always write safe, read-only SELECT queries. "
            "Example: SELECT title, rating FROM movies ORDER BY rating DESC LIMIT 5"
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type":        "string",
                    "description": "A valid SQLite SELECT query. Must be read-only.",
                }
            },
            "required": ["query"],
        }

    def _is_safe(self, query: str) -> bool:
        """Block any non-SELECT or multi-statement queries."""
        q = query.strip().upper()
        dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
                     "CREATE", "TRUNCATE", "EXEC", "PRAGMA"]
        if not q.startswith("SELECT"):
            return False
        for kw in dangerous:
            if kw in q:
                return False
        return True

    async def run(self, query: str) -> Any:
        if not self._is_safe(query):
            logger.warning("sql_tool: blocked unsafe query", extra={"query": query})
            return {"error": "Only SELECT queries are permitted."}

        logger.info("sql_tool: executing query", extra={"query": query})
        try:
            async with aiosqlite.connect(settings.sqlite_db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query) as cursor:
                    rows = await cursor.fetchmany(200)   # cap at 200 rows
                    columns = [d[0] for d in cursor.description] if cursor.description else []
                    result = [dict(zip(columns, row)) for row in rows]

            logger.info("sql_tool: returned rows", extra={"count": len(result)})
            return {"columns": columns, "rows": result, "count": len(result)}

        except Exception as e:
            logger.error("sql_tool: query error", extra={"exc": str(e)})
            return {"error": str(e)}
