from sqlalchemy import select
from sqlalchemy.orm import Session

from datetime import date, datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo

from app.activities.schemas import ActivityInput
from app.activities.models import Activity

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
    db: Session, request: ActivityInput
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
    db: Session, activity_id: int, request: ActivityInput
) -> Activity | None:

    activity = db.get(Activity, activity_id)
    
    if activity is None:
        return None
    
    for field, value in request.model_dump(mode="json").items():
        setattr(activity, field, value)
    
    db.commit()
    db.refresh(activity)
    return activity
    