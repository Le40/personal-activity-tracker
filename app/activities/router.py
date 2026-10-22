from fastapi import APIRouter
from fastapi import HTTPException, Depends

from sqlalchemy.orm import Session
from datetime import date

from app.database import get_session
from app.activities import service, schemas
from app.activities.options import (
    ActivityType, EaseRating, EASE_LABELS, EASE_RATING_ACTIVITY_TYPES
)


router = APIRouter(prefix="/activities", tags=["Activities"])


@router.get("", response_model=list[schemas.ActivityResponse])
def get_activities(
    day: date | None = None, db: Session = Depends(get_session)
):
    return service.get_activities(db, day)

# Create a completed activity with manually specified timestamps
@router.post("" ,response_model=schemas.ActivityResponse, status_code=201)
def add_completed_activity(
    request: schemas.CompletedActivityInput, db: Session = Depends(get_session)
):
    try:
        activity = service.add_completed_activity(db, request)
    except service.ActivityConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    
    return activity


@router.get("/{activity_id:int}", response_model=schemas.ActivityResponse)
def get_activity_by_id(
    activity_id: int, db: Session = Depends(get_session)
):
    activity = service.get_activity_by_id(db, activity_id)

    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    return activity

# STARTS ACTIVITY & STOPS PREVIOUSLY RUNNING ONE
@router.post("/start", response_model=schemas.ActivityResponse, status_code=201)
def start_activity(
    request: schemas.ActivityInput, db: Session = Depends(get_session)
):
    return service.start_activity(db, request)

# STOPS CURRENTLY RUNNNING ACTIVITY
@router.post("/stop",response_model=schemas.ActivityResponse)
def stop_activity(
    db: Session = Depends(get_session)
):
    activity = service.stop_activity(db)

    if activity is None:
        raise HTTPException(status_code=409,detail="No active activity")
    
    return activity

# UPDATES CURRENTLY RUNNING ACTIVITY
@router.put("/{activity_id:int}" ,response_model=schemas.ActivityResponse)
def update_activity(
    activity_id, request: schemas.ActivityUpdate, db: Session = Depends(get_session)
):
    try:
        activity = service.update_activity(db, activity_id, request)
    except service.ActivityConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    
    if activity is None:
       raise HTTPException(status_code=404, detail="Activity not found")
        
    return activity

# DELETES COMPLETED ACTIVITY
@router.delete("/{activity_id:int}",  status_code=204)
def delete_activity(
    activity_id, db: Session = Depends(get_session)
):
    deleted = service.delete_activity(db, activity_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Activity not found")



@router.get("/options")
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