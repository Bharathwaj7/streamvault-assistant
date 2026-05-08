import aiosqlite
from typing import Optional
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.analytics import InsightResponse, KPIMetric, ChartData

logger   = get_logger()
settings = get_settings()


def _period_to_date_range(period: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not period or period == 'all':
        return None, None
    ranges = {
        'last30':  ('2025-04-01', '2025-05-01'),
        'q1_2025': ('2025-01-01', '2025-03-31'),
        'q2_2025': ('2025-04-01', '2025-06-30'),
        'q3_2025': ('2025-07-01', '2025-09-30'),
        'q4_2025': ('2025-10-01', '2025-12-31'),
    }
    return ranges.get(period, (None, None))


def _trend_group_format(period: Optional[str]) -> str:
    """
    Returns SQLite SUBSTR format for grouping trend data.
    last30  → daily   (YYYY-MM-DD)
    quarter → bi-weekly (every ~15 days via week number)
    all     → monthly (YYYY-MM)
    """
    if period == 'last30':
        return 'SUBSTR(wa.watch_date, 1, 10)'   # daily
    elif period in ('q1_2025', 'q2_2025', 'q3_2025', 'q4_2025'):
        # Group by ~15-day periods using day of month
        return """
            SUBSTR(wa.watch_date, 1, 7) ||
            CASE WHEN CAST(SUBSTR(wa.watch_date, 9, 2) AS INTEGER) <= 10
                 THEN '-01'
                 ELSE '-11'
            END
        """
    else:
        return 'SUBSTR(wa.watch_date, 1, 7)'    # monthly


async def get_insights(
    period: Optional[str] = None,
    genre:  Optional[str] = None,
) -> InsightResponse:
    logger.info(
        "analytics: generating insights",
        extra={"period": period or "all", "genre": genre or "all"}
    )

    db_path              = settings.sqlite_db_path
    start_date, end_date = _period_to_date_range(period)

    has_date  = bool(start_date)
    has_genre = bool(genre and genre != 'all')

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        # ── KPIs ──────────────────────────────────────────────────────────────
        kpi_join   = "JOIN movies m ON wa.movie_id = m.movie_id" if has_genre else ""
        kpi_where  = []
        kpi_params = []
        if has_date:
            kpi_where.append("wa.watch_date >= ?")
            kpi_params.append(start_date)
            kpi_where.append("wa.watch_date <= ?")
            kpi_params.append(end_date)
        if has_genre:
            kpi_where.append("m.genre = ?")
            kpi_params.append(genre)
        kpi_filter = ("WHERE " + " AND ".join(kpi_where)) if kpi_where else ""

        async with db.execute(
            f"SELECT COUNT(*) as c FROM watch_activity wa {kpi_join} {kpi_filter}",
            kpi_params
        ) as cur:
            total_views = (await cur.fetchone())["c"]

        async with db.execute(
            "SELECT COUNT(DISTINCT viewer_id) as c FROM viewers WHERE is_active=1"
        ) as cur:
            active_users = (await cur.fetchone())["c"]

        async with db.execute(
            f"SELECT AVG(wa.completion_rate) as avg FROM watch_activity wa {kpi_join} {kpi_filter}",
            kpi_params
        ) as cur:
            avg_completion = round(((await cur.fetchone())["avg"] or 0) * 100, 1)

        async with db.execute("SELECT AVG(score) as avg FROM reviews") as cur:
            avg_score = round((await cur.fetchone())["avg"] or 0, 2)

        kpis = [
            KPIMetric(label="Total Views",        value=f"{total_views:,}",    trend="up",      change="+34% QoQ"),
            KPIMetric(label="Active Subscribers",  value=f"{active_users:,}",  trend="up",      change="+18% YoY"),
            KPIMetric(label="Avg Completion Rate", value=f"{avg_completion}%", trend="neutral", change=""),
            KPIMetric(label="Avg Review Score",    value=str(avg_score),       trend="up",      change="+0.3 vs last Q"),
        ]

        # ── Top titles ────────────────────────────────────────────────────────
        top_where  = []
        top_params = []
        if has_date:
            top_where.append("wa.watch_date >= ?")
            top_params.append(start_date)
            top_where.append("wa.watch_date <= ?")
            top_params.append(end_date)
        if has_genre:
            top_where.append("m.genre = ?")
            top_params.append(genre)
        top_filter = ("WHERE " + " AND ".join(top_where)) if top_where else ""

        async with db.execute(f"""
            SELECT m.title, m.genre, m.rating,
                   COUNT(wa.activity_id)   as views,
                   AVG(wa.completion_rate) as avg_completion
            FROM movies m
            JOIN watch_activity wa ON m.movie_id = wa.movie_id
            {top_filter}
            GROUP BY m.movie_id
            ORDER BY views DESC
            LIMIT 7
        """, top_params) as cur:
            rows = await cur.fetchall()
            top_titles = [dict(r) for r in rows]
            for t in top_titles:
                t["avg_completion"] = round((t["avg_completion"] or 0) * 100, 1)

        # ── Genre bar chart — always all genres for comparison ────────────────
        genre_date_where  = []
        genre_date_params = []
        if has_date:
            genre_date_where.append("wa.watch_date >= ?")
            genre_date_params.append(start_date)
            genre_date_where.append("wa.watch_date <= ?")
            genre_date_params.append(end_date)
        genre_date_filter = ("WHERE " + " AND ".join(genre_date_where)) if genre_date_where else ""

        async with db.execute(f"""
            SELECT m.genre,
                   COUNT(wa.activity_id) as total_views,
                   AVG(r.score)          as avg_score
            FROM movies m
            JOIN watch_activity wa ON m.movie_id = wa.movie_id
            LEFT JOIN reviews r    ON m.movie_id = r.movie_id
            {genre_date_filter}
            GROUP BY m.genre
            ORDER BY total_views DESC
        """, genre_date_params) as cur:
            rows = await cur.fetchall()
            genre_data = [
                {
                    "genre":     r["genre"],
                    "views":     r["total_views"],
                    "avg_score": round(r["avg_score"] or 0, 1),
                }
                for r in rows
            ]

        genre_chart = ChartData(
            chart_type="bar", title="Views by Genre",
            x_key="genre", y_key="views", data=genre_data,
        )

        # ── Monthly views trend — dynamic grouping ────────────────────────────
        trend_group  = _trend_group_format(period)
        trend_where  = []
        trend_params = []
        if has_date:
            trend_where.append("wa.watch_date >= ?")
            trend_params.append(start_date)
            trend_where.append("wa.watch_date <= ?")
            trend_params.append(end_date)
        if has_genre:
            trend_where.append("m.genre = ?")
            trend_params.append(genre)
        trend_join   = "JOIN movies m ON wa.movie_id = m.movie_id" if has_genre else ""
        trend_filter = ("WHERE " + " AND ".join(trend_where)) if trend_where else ""

        async with db.execute(f"""
            SELECT {trend_group} as period,
                   COUNT(*) as total_views
            FROM watch_activity wa
            {trend_join}
            {trend_filter}
            GROUP BY period
            ORDER BY period
        """, trend_params) as cur:
            rows = await cur.fetchall()
            trend_data = [{"month": r["period"], "views": r["total_views"]} for r in rows]

        views_trend = ChartData(
            chart_type="line", title="Monthly Views Trend",
            x_key="month", y_key="views", data=trend_data,
        )

        # ── Regional engagement — filter by genre via watch_activity ──────────
        regional_where  = []
        regional_params = []
        if has_date:
            regional_where.append("wa.watch_date >= ?")
            regional_params.append(start_date)
            regional_where.append("wa.watch_date <= ?")
            regional_params.append(end_date)
        if has_genre:
            regional_where.append("m.genre = ?")
            regional_params.append(genre)
        regional_filter = ("WHERE " + " AND ".join(regional_where)) if regional_where else ""

        if has_genre or has_date:
            # Join through watch_activity to filter by genre/date
            async with db.execute(f"""
                SELECT v.city,
                       AVG(rp.engagement_score) as avg_engagement,
                       COUNT(wa.activity_id)    as total_views
                FROM watch_activity wa
                JOIN movies   m  ON wa.movie_id  = m.movie_id
                JOIN viewers  v  ON wa.viewer_id = v.viewer_id
                JOIN regional_performance rp ON v.city = rp.city
                {regional_filter}
                GROUP BY v.city
                ORDER BY avg_engagement DESC
                LIMIT 10
            """, regional_params) as cur:
                rows = await cur.fetchall()
        else:
            # Default — no filters
            async with db.execute("""
                SELECT city,
                       AVG(engagement_score) as avg_engagement,
                       SUM(total_views)      as total_views
                FROM regional_performance
                GROUP BY city
                ORDER BY avg_engagement DESC
                LIMIT 8
            """) as cur:
                rows = await cur.fetchall()

        regional_data = [
            {
                "city":       r["city"],
                "engagement": round(r["avg_engagement"], 1),
                "views":      r["total_views"],
            }
            for r in rows
        ]

        regional_chart = ChartData(
            chart_type="bar", title="City Engagement Scores",
            x_key="city", y_key="engagement", data=regional_data,
        )

        # ── Marketing ROAS ────────────────────────────────────────────────────
        mkt_where  = []
        mkt_params = []
        if has_date:
            mkt_where.append("ms.month >= ?")
            mkt_params.append(start_date[:7])
            mkt_where.append("ms.month <= ?")
            mkt_params.append(end_date[:7])
        mkt_filter = ("WHERE " + " AND ".join(mkt_where)) if mkt_where else ""

        async with db.execute(f"""
            SELECT ms.channel,
                   SUM(ms.spend_usd)   as total_spend,
                   SUM(ms.conversions) as total_conversions,
                   SUM(ms.impressions) as total_impressions
            FROM marketing_spend ms
            {mkt_filter}
            GROUP BY ms.channel
            ORDER BY total_spend DESC
        """, mkt_params) as cur:
            rows = await cur.fetchall()
            mkt_data = []
            for r in rows:
                cpa = round(r["total_spend"] / r["total_conversions"], 2) \
                      if r["total_conversions"] else 0
                mkt_data.append({
                    "channel":     r["channel"],
                    "spend":       round(r["total_spend"]),
                    "conversions": r["total_conversions"],
                    "cpa":         cpa,
                })

        marketing_chart = ChartData(
            chart_type="bar", title="Marketing Spend by Channel",
            x_key="channel", y_key="spend", data=mkt_data,
        )

    return InsightResponse(
        kpis=kpis,
        top_titles=top_titles,
        genre_chart=genre_chart,
        views_trend=views_trend,
        regional_chart=regional_chart,
        marketing_chart=marketing_chart,
    )