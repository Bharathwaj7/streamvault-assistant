from pydantic import BaseModel
from typing import Any


class ChartDataPoint(BaseModel):
    label: str
    value: float
    extra: dict[str, Any] = {}


class ChartData(BaseModel):
    chart_type: str          # bar | line | pie
    title:      str
    x_key:      str
    y_key:      str
    data:       list[dict[str, Any]]


class KPIMetric(BaseModel):
    label:  str
    value:  str
    change: str = ""
    trend:  str = "neutral"   # up | down | neutral


class InsightResponse(BaseModel):
    kpis:          list[KPIMetric]
    top_titles:    list[dict[str, Any]]
    genre_chart:   ChartData
    views_trend:   ChartData
    regional_chart: ChartData
    marketing_chart: ChartData
