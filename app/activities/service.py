from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from datetime import date, datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo

from app.activities import schemas
from app.activities.models import Activity


class ActivityConflictError(Exception):
    pass

def get_activities(
        db: Session, day: date | None = None
) -> list[Activity]:

    statement = select(Activity)

    if day is not None:
        local_tz = ZoneInfo("Europe/Bratislava")

        local_start = datetime.combine(day, time(5), tzinfo=local_tz)
        local_end = datetime.combine(day + timedelta(days=1), time(5), tzinfo=local_tz)

        day_start = local_start.astimezone(timezone.utc).replace(tzinfo=None)
        day_end = local_end.astimezone(timezone.utc).replace(tzinfo=None)

        statement = statement.where(
            Activity.ended_at > day_start,
            Activity.ended_at <= day_end    
        )

    return db.scalars(statement).all()


def get_activity_by_id(
        db: Session, activity_id: int
) -> Activity | None:
    return db.get(Activity, activity_id)


def start_activity(
    db: Session, request: schemas.ActivityInput
) -> Activity:

    current_datetime = datetime.now(timezone.utc)

    old_activity = db.scalars(
        select(Activity).where(Activity.ended_at.is_(None))
    ).first()
        
    if old_activity is not None:
        old_activity.ended_at = current_datetime

    new_activity = Activity(
        **request.model_dump(mode="json"),
        started_at=current_datetime
    ) 

    db.add(new_activity)
    db.commit()
    db.refresh(new_activity)

    return new_activity

def stop_activity(
    db: Session
) -> Activity | None:

    current_activity = db.scalars(
        select(Activity).where(Activity.ended_at.is_(None))
    ).first()
    
    if current_activity is None:
        return None
    
    current_activity.ended_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(current_activity)
    
    return current_activity

def update_activity(
    db: Session, activity_id: int, request: schemas.ActivityUpdate
) -> Activity | None:

    activity = db.get(Activity, activity_id)
    
    if activity is None:
        return None

    if request.started_at is not None:
        # Running acitivity
        if activity.ended_at is None:
            raise ActivityConflictError(
                "Cannot change timestamps of a running activity"
            )
        # Covert schema timestamps to UTC
        started_at = request.started_at.astimezone(timezone.utc).replace(tzinfo=None)
        ended_at = request.ended_at.astimezone(timezone.utc).replace(tzinfo=None)

        if has_activity_overlap(db, started_at, ended_at, activity_id):
            raise ActivityConflictError("Activity overlaps existing one")

        activity.started_at = started_at
        activity.ended_at = ended_at

    data = request.model_dump(
        mode="json",
        exclude={"started_at", "ended_at"}
    )
    
    for field, value in data.items():
        setattr(activity, field, value)
    
    db.commit()
    db.refresh(activity)
    return activity

def add_completed_activity(
    db: Session, request: schemas.CompletedActivityInput
) -> Activity | None:

    data = request.model_dump()

    data["started_at"] = data["started_at"].astimezone(timezone.utc).replace(tzinfo=None)
    data["ended_at"] = data["ended_at"].astimezone(timezone.utc).replace(tzinfo=None)
    
    activity = Activity(**data)

    if has_activity_overlap(db, activity.started_at, activity.ended_at):
        raise ActivityConflictError("Activity overlaps existing one")

    db.add(activity)
    db.commit()
    db.refresh(activity)

    return activity

def has_activity_overlap(
    db: Session,
    started_at: datetime,
    ended_at: datetime,
    exclude_activity_id: int | None = None
) -> bool:
    
    statement = select(Activity.id).where(
        Activity.started_at < ended_at,
        or_(
            Activity.ended_at > started_at,
            Activity.ended_at.is_(None)
        )
    )

    if exclude_activity_id is not None:
        statement = statement.where(Activity.id != exclude_activity_id)

    return db.scalar(select(statement.exists()))

def delete_activity(
    db: Session, activity_id: int
) -> bool:

    activity = db.get(Activity, activity_id)
    
    if activity is None:
        return False

    db.delete(activity)
    db.commit()
    return True
