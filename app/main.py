from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone
from app.database import get_session
from app.models import ActivitySession
from app.schemas import ActivitySessionResponse, ActivitySessionInput

from pathlib import Path
from fastapi.responses import FileResponse

app = FastAPI()

@app.get("/")
def index():
    return FileResponse(
        Path(__file__).resolve().parent / "static" / "index.html"
    )

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/sessions", response_model=list[ActivitySessionResponse])
def get_sessions(session: Session = Depends(get_session)):
    return session.scalars(select(ActivitySession)).all()

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
        name            = request.name,
        activity_type   = request.activity_type,
        started_at      = current_datetime,
        notes           = request.notes
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
    current_session = session.get(ActivitySession, session_id)

    if current_session is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    current_session.name=request.name
    current_session.activity_type=request.activity_type
    current_session.notes=request.notes

    session.commit()
    session.refresh(current_session)
    return current_session

