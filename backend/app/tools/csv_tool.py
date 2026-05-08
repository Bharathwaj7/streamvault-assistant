import pandas as pd
from pathlib import Path
from typing import Any
from app.tools.base import BaseTool
from app.core.config import get_settings
from app.core.logging import get_logger

logger   = get_logger()
settings = get_settings()

# Pre-load CSVs once at startup
_cache: dict[str, pd.DataFrame] = {}

CSV_FILES = [
    "movies", "viewers", "watch_activity",
    "reviews", "marketing_spend", "regional_performance",
]


def load_csvs():
    global _cache
    csv_dir = Path(settings.data_dir) / "csv"
    for name in CSV_FILES:
        path = csv_dir / f"{name}.csv"
        if path.exists():
            _cache[name] = pd.read_csv(path)
            logger.info(f"csv_tool: loaded {name}.csv → {len(_cache[name])} rows")


class CSVTool(BaseTool):
    OPERATIONS = {
        "top_movies_by_views": "Top movies ranked by total watch activity count",
        "genre_performance":   "Average rating and view count grouped by genre",
        "monthly_views_trend": "Total views grouped by month for trend analysis",
        "city_engagement":     "Average engagement score and views grouped by city",
        "marketing_roas":      "Marketing spend vs conversions grouped by channel",
        "completion_by_genre": "Average completion rate grouped by genre",
        "review_sentiment":    "Review sentiment distribution by movie",
        "platform_usage":      "Session count grouped by platform",
        "demographic_views":   "View counts grouped by viewer age group",
        "comedy_analysis":     "Detailed performance breakdown for comedy genre titles",
    }

    @property
    def name(self) -> str:
        return "analyze_csv_data"

    @property
    def description(self) -> str:
        ops = ", ".join(self.OPERATIONS.keys())
        return (
            "Perform analytical operations on StreamVault CSV business data using pandas. "
            "Use this for aggregations, trends, rankings, and statistical summaries. "
            f"Available operations: {ops}. "
            "Optionally filter by movie title, genre, city, or date range."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type":        "string",
                    "enum":        list(self.OPERATIONS.keys()),
                    "description": "The analytical operation to perform.",
                },
                "filters": {
                    "type":        "object",
                    "description": "Optional filters: {genre, title, city, start_date, end_date}",
                    "properties": {
                        "genre":      {"type": "string"},
                        "title":      {"type": "string"},
                        "city":       {"type": "string"},
                        "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                        "end_date":   {"type": "string", "description": "YYYY-MM-DD"},
                    },
                },
                "limit": {
                    "type":        "integer",
                    "description": "Max rows to return (default 10)",
                    "default":     10,
                },
            },
            "required": ["operation"],
        }

    async def run(self, operation: str, filters: dict = None, limit: int = 10) -> Any:
        filters = filters or {}
        limit   = min(int(limit), 50)
        logger.info("csv_tool: running operation",
                    extra={"operation": operation, "filters": filters})

        try:
            handler = getattr(self, f"_op_{operation}", None)
            if not handler:
                return {"error": f"Unknown operation: {operation}"}
            result = handler(filters, limit)
            logger.info("csv_tool: operation complete",
                        extra={"operation": operation, "rows": len(result)})
            return {"data": result, "operation": operation, "count": len(result)}
        except Exception as e:
            logger.error("csv_tool: error", extra={"operation": operation, "exc": str(e)})
            return {"error": str(e)}

    # ── private helpers ────────────────────────────────────────────────────────

    def _movies(self): return _cache.get("movies", pd.DataFrame())
    def _activity(self): return _cache.get("watch_activity", pd.DataFrame())
    def _reviews(self): return _cache.get("reviews", pd.DataFrame())
    def _marketing(self): return _cache.get("marketing_spend", pd.DataFrame())
    def _regional(self): return _cache.get("regional_performance", pd.DataFrame())
    def _viewers(self): return _cache.get("viewers", pd.DataFrame())

    def _apply_date_filter(self, df: pd.DataFrame, col: str, filters: dict):
        if "start_date" in filters:
            df = df[df[col] >= filters["start_date"]]
        if "end_date" in filters:
            df = df[df[col] <= filters["end_date"]]
        return df

    def _op_top_movies_by_views(self, filters, limit):
        act = self._apply_date_filter(self._activity(), "watch_date", filters)
        counts = act.groupby("movie_id").size().reset_index(name="total_views")
        merged = counts.merge(self._movies()[["movie_id","title","genre","rating"]], on="movie_id")
        if "genre" in filters:
            merged = merged[merged["genre"].str.lower() == filters["genre"].lower()]
        return merged.sort_values("total_views", ascending=False).head(limit).to_dict(orient="records")

    def _op_genre_performance(self, filters, limit):
        act    = self._activity()
        counts = act.groupby("movie_id").size().reset_index(name="views")
        merged = counts.merge(self._movies()[["movie_id","genre","rating"]], on="movie_id")
        rev    = self._reviews().groupby("movie_id")["score"].mean().reset_index(name="avg_score")
        merged = merged.merge(rev, on="movie_id", how="left")
        result = merged.groupby("genre").agg(
            total_views=("views", "sum"),
            avg_rating=("rating", "mean"),
            avg_review_score=("avg_score", "mean"),
        ).reset_index().sort_values("total_views", ascending=False)
        return result.head(limit).round(2).to_dict(orient="records")

    def _op_monthly_views_trend(self, filters, limit):
        act = self._apply_date_filter(self._activity(), "watch_date", filters)
        act = act.copy()
        act["month"] = act["watch_date"].str[:7]
        if "title" in filters:
            ids = self._movies()[self._movies()["title"].str.lower()
                                 .str.contains(filters["title"].lower())]["movie_id"]
            act = act[act["movie_id"].isin(ids)]
        result = act.groupby("month").size().reset_index(name="total_views")
        return result.sort_values("month").tail(limit).to_dict(orient="records")

    def _op_city_engagement(self, filters, limit):
        reg = self._regional()
        if "start_date" in filters:
            reg = reg[reg["month"] >= filters["start_date"][:7]]
        if "end_date" in filters:
            reg = reg[reg["month"] <= filters["end_date"][:7]]
        result = reg.groupby("city").agg(
            avg_engagement=("engagement_score", "mean"),
            total_views=("total_views", "sum"),
            avg_revenue=("revenue_usd", "mean"),
        ).reset_index().sort_values("avg_engagement", ascending=False)
        return result.head(limit).round(2).to_dict(orient="records")

    def _op_marketing_roas(self, filters, limit):
        mkt = self._marketing()
        if "title" in filters:
            ids = self._movies()[self._movies()["title"].str.lower()
                                 .str.contains(filters["title"].lower())]["movie_id"]
            mkt = mkt[mkt["movie_id"].isin(ids)]
        result = mkt.groupby("channel").agg(
            total_spend=("spend_usd", "sum"),
            total_impressions=("impressions", "sum"),
            total_clicks=("clicks", "sum"),
            total_conversions=("conversions", "sum"),
        ).reset_index()
        result["cpa"] = (result["total_spend"] / result["total_conversions"]).round(2)
        return result.sort_values("total_conversions", ascending=False).head(limit).to_dict(orient="records")

    def _op_completion_by_genre(self, filters, limit):
        act    = self._activity()
        merged = act.merge(self._movies()[["movie_id","genre"]], on="movie_id")
        result = merged.groupby("genre").agg(
            avg_completion=("completion_rate", "mean"),
            avg_duration=("watch_duration_min", "mean"),
            total_sessions=("activity_id", "count"),
        ).reset_index().sort_values("avg_completion", ascending=False)
        return result.head(limit).round(3).to_dict(orient="records")

    def _op_review_sentiment(self, filters, limit):
        rev    = self._reviews()
        merged = rev.merge(self._movies()[["movie_id","title","genre"]], on="movie_id")
        if "title" in filters:
            merged = merged[merged["title"].str.lower().str.contains(filters["title"].lower())]
        if "genre" in filters:
            merged = merged[merged["genre"].str.lower() == filters["genre"].lower()]
        result = merged.groupby(["title","sentiment"]).size().reset_index(name="count")
        return result.sort_values("count", ascending=False).head(limit).to_dict(orient="records")

    def _op_platform_usage(self, filters, limit):
        act    = self._activity()
        result = act.groupby("platform").agg(
            sessions=("activity_id", "count"),
            avg_duration=("watch_duration_min", "mean"),
            avg_completion=("completion_rate", "mean"),
        ).reset_index().sort_values("sessions", ascending=False)
        return result.head(limit).round(2).to_dict(orient="records")

    def _op_demographic_views(self, filters, limit):
        act     = self._activity()
        viewers = self._viewers()[["viewer_id","age_group","gender","city"]]
        merged  = act.merge(viewers, on="viewer_id")
        if "city" in filters:
            merged = merged[merged["city"].str.lower() == filters["city"].lower()]
        result = merged.groupby("age_group").agg(
            total_views=("activity_id", "count"),
            avg_completion=("completion_rate", "mean"),
        ).reset_index().sort_values("total_views", ascending=False)
        return result.head(limit).round(3).to_dict(orient="records")

    def _op_comedy_analysis(self, filters, limit):
        movies  = self._movies()
        comedy  = movies[movies["genre"] == "Comedy"]
        act     = self._activity()
        rev     = self._reviews()
        merged  = act[act["movie_id"].isin(comedy["movie_id"])].merge(
            comedy[["movie_id","title"]], on="movie_id")
        views   = merged.groupby("title").agg(
            total_views=("activity_id", "count"),
            avg_completion=("completion_rate", "mean"),
        ).reset_index()
        scores  = rev[rev["movie_id"].isin(comedy["movie_id"])].merge(
            comedy[["movie_id","title"]], on="movie_id")
        avg_sc  = scores.groupby("title")["score"].mean().reset_index(name="avg_score")
        result  = views.merge(avg_sc, on="title", how="left")
        return result.sort_values("total_views", ascending=False).head(limit).round(2).to_dict(orient="records")
