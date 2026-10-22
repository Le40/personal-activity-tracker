from fastapi import APIRouter
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import date, datetime, time, timezone, timedelta
from app.database import get_session
from app.models import Activity
from app.schemas import ActivityResponse, ActivityInput


router = APIRouter(prefix="/activities", tags=["Activities"])

@router.get("", response_model=list[ActivityResponse])
def get_activities(day: date | None = None, db: Session = Depends(get_session)):
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


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity_by_id(activity_id: int, db: Session = Depends(get_session)):
    activity = db.get(Activity, activity_id)

    if activity is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return activity


@router.post("/start", response_model=ActivityResponse, status_code=201)
def start_activity(
    request: ActivityInput,
    db: Session = Depends(get_session)
):
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


@router.post("/stop",response_model=ActivityResponse)
def stop_activity(
    db: Session = Depends(get_session)
):

    current_activity = db.scalars(
        select(Activity).where(Activity.ended_at.is_(None))
    ).first()

    if current_activity is None:
        raise HTTPException(status_code=409,detail="No active activity")

    current_activity.ended_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(current_activity)

    return current_activity


@router.put("/{activity_id}")
def update_session(activity_id, request: ActivityInput,
    db: Session = Depends(get_session)
):
    activity = db.get(Activity, activity_id)

    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    for field, value in request.model_dump(mode="json").items():
        setattr(activity, field, value)

    db.commit()
    db.refresh(activity)
    return activity
