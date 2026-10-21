from sqlalchemy import String, Index, CheckConstraint
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from datetime import datetime
from sqlalchemy import DateTime

class Base(DeclarativeBase):
    pass

class ActivitySession(Base): 
    __tablename__ = "activity_session"
    __table_args__ = (CheckConstraint(
            "ease_rating BETWEEN 1 AND 5",
            name="ck_ease_rating_range"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    activity_type: Mapped[str] = mapped_column(String(15))

    started_at: Mapped[datetime] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)

    notes: Mapped[str | None] = mapped_column(nullable=True)
    ease_rating: Mapped[int | None] = mapped_column(nullable=True)


running_session_index = Index(
    "uq_one_running_session",
    ActivitySession.ended_at.is_(None),
    unique=True,
    sqlite_where=ActivitySession.ended_at.is_(None),
)