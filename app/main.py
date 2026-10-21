from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_, select
from datetime import date, datetime, time, timezone, timedelta
from app.database import get_session
from app.models import ActivitySession
from app.schemas import ActivitySessionResponse, ActivitySessionInput
from app.options import ActivityType, EaseRating, EASE_LABELS, EASE_RATING_ACTIVITY_TYPES

from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static"
)

@app.get("/")
def index():
    return FileResponse(
        Path(__file__).resolve().parent / "static" / "index.html"
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/sessions", response_model=list[ActivitySessionResponse])
def get_sessions(day: date | None = None, session: Session = Depends(get_session)):
    statement = select(ActivitySession)

    if day is not None:
        local_tz = ZoneInfo("Europe/Bratislava")

        local_start = datetime.combine(day, time(5), tzinfo=local_tz)
        local_end = datetime.combine(day + timedelta(days=1), time(5), tzinfo=local_tz)

        day_start = local_start.astimezone(timezone.utc).replace(tzinfo=None)
        day_end = local_end.astimezone(timezone.utc).replace(tzinfo=None)

        statement = statement.where(
            ActivitySession.ended_at > day_start,
            ActivitySession.ended_at <= day_end    
        )

    return session.scalars(statement).all()


@app.get("/sessions/{session_id}", response_model=ActivitySessionResponse)
def get_session_by_id(session_id: int, session: Session = Depends(get_session)):
    activity = session.get(ActivitySession, session_id)

    if activity is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return activity


@app.post("/sessions/start",response_model=ActivitySessionResponse,status_code=201)
def start_session(
    request: ActivitySessionInput,
    session: Session = Depends(get_session)
):
    current_datetime = datetime.now(timezone.utc)

    old_session = session.scalars(
        select(ActivitySession).where(ActivitySession.ended_at.is_(None))
    ).first()
        
    if old_session is not None:
        old_session.ended_at = current_datetime

    new_session = ActivitySession(
        **request.model_dump(mode="json"),
        started_at=current_datetime
    ) 

    session.add(new_session)
    session.commit()
    session.refresh(new_session)

    return new_session


@app.post("/sessions/stop",response_model=ActivitySessionResponse)
def stop_session(
    session: Session = Depends(get_session)
):

    current_session = session.scalars(
        select(ActivitySession).where(ActivitySession.ended_at.is_(None))
    ).first()

    if current_session is None:
        raise HTTPException(status_code=409,detail="No active session")

    current_session.ended_at = datetime.now(timezone.utc)

    session.commit()
    session.refresh(current_session)

    return current_session


@app.put("/sessions/{session_id}")
def update_session(session_id, request: ActivitySessionInput,
    session: Session = Depends(get_session)
):
    activity = session.get(ActivitySession, session_id)

    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    for field, value in request.model_dump(mode="json").items():
        setattr(activity, field, value)

    session.commit()
    session.refresh(activity)
    return activity


@app.get("/options")
def get_options():
    return {
        "activity_types": [
            {
                "value": activity.value,
                "label": activity.value.capitalize(),
                "supports_ease_rating": activity in EASE_RATING_ACTIVITY_TYPES
            }
            for activity in ActivityType
        ],
        "ease_ratings": [
            {
                "value": rating.value,
                "label": EASE_LABELS[rating]
            }
            for rating in EaseRating
        ]
    }

