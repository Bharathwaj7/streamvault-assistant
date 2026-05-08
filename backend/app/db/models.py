from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.database import Base


class Movie(Base):
    __tablename__ = "movies"

    movie_id      = Column(Integer, primary_key=True, index=True)
    title         = Column(String(200), nullable=False, index=True)
    genre         = Column(String(50), nullable=False, index=True)
    release_date  = Column(String(20))
    budget_usd    = Column(Float)
    runtime_min   = Column(Integer)
    language      = Column(String(50))
    rating        = Column(Float)
    director      = Column(String(200))
    cast_lead     = Column(String(200))
    status        = Column(String(50))

    activities    = relationship("WatchActivity", back_populates="movie")
    reviews       = relationship("Review", back_populates="movie")


class Viewer(Base):
    __tablename__ = "viewers"

    viewer_id          = Column(Integer, primary_key=True, index=True)
    age_group          = Column(String(20))
    gender             = Column(String(20))
    city               = Column(String(100), index=True)
    country            = Column(String(100))
    subscription_type  = Column(String(50))
    joined_date        = Column(String(20))
    preferred_genre    = Column(String(50))
    preferred_platform = Column(String(50))
    is_active          = Column(Integer)

    activities = relationship("WatchActivity", back_populates="viewer")
    reviews    = relationship("Review", back_populates="viewer")


class WatchActivity(Base):
    __tablename__ = "watch_activity"

    activity_id        = Column(Integer, primary_key=True, index=True)
    viewer_id          = Column(Integer, ForeignKey("viewers.viewer_id"), index=True)
    movie_id           = Column(Integer, ForeignKey("movies.movie_id"), index=True)
    watch_date         = Column(String(20), index=True)
    platform           = Column(String(50))
    watch_duration_min = Column(Integer)
    completion_rate    = Column(Float)
    rewatched          = Column(Integer)
    device_type        = Column(String(50))

    movie  = relationship("Movie", back_populates="activities")
    viewer = relationship("Viewer", back_populates="activities")


class Review(Base):
    __tablename__ = "reviews"

    review_id     = Column(Integer, primary_key=True, index=True)
    movie_id      = Column(Integer, ForeignKey("movies.movie_id"), index=True)
    viewer_id     = Column(Integer, ForeignKey("viewers.viewer_id"), index=True)
    review_date   = Column(String(20))
    score         = Column(Integer)
    sentiment     = Column(String(20), index=True)
    platform      = Column(String(50))
    helpful_votes = Column(Integer)

    movie  = relationship("Movie", back_populates="reviews")
    viewer = relationship("Viewer", back_populates="reviews")


class MarketingSpend(Base):
    __tablename__ = "marketing_spend"

    spend_id    = Column(Integer, primary_key=True, index=True)
    movie_id    = Column(Integer, ForeignKey("movies.movie_id"), index=True)
    month       = Column(String(10), index=True)
    channel     = Column(String(100))
    spend_usd   = Column(Float)
    impressions = Column(Integer)
    clicks      = Column(Integer)
    conversions = Column(Integer)


class RegionalPerformance(Base):
    __tablename__ = "regional_performance"

    perf_id          = Column(Integer, primary_key=True, index=True)
    movie_id         = Column(Integer, ForeignKey("movies.movie_id"), index=True)
    city             = Column(String(100), index=True)
    month            = Column(String(10), index=True)
    total_views      = Column(Integer)
    unique_viewers   = Column(Integer)
    avg_rating       = Column(Float)
    revenue_usd      = Column(Float)
    engagement_score = Column(Float)
