from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.activities import schemas, service
from app.activities.options import (
    EASE_LABELS,
    EASE_RATING_ACTIVITY_TYPES,
    ActivityType,
    EaseRating,
)
from app.database import get_session

router = APIRouter(prefix="/activities", tags=["Activities"])

DbSession = Annotated[Session, Depends(get_session)]

@router.get("", response_model=list[schemas.ActivityResponse])
def get_activities(
    start_date: date, end_date: date, db: DbSession
):
    if end_date < start_date:
        raise HTTPException(status_code=422,
            detail="End date cannot be before start date")

    if (end_date - start_date).days >= 31:
        raise HTTPException(status_code=422,
            detail="Date range cannot exceed 31 days")

    return service.get_activities(db, start_date, end_date)


@router.get("/{activity_id:int}", response_model=schemas.ActivityResponse)
def get_activity_by_id(
    activity_id: int, db: DbSession
):
    activity = service.get_activity_by_id(db, activity_id)

    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    return activity


@router.get("/current", response_model=schemas.ActivityResponse,
    responses={204: {"description": "No running activity"}})
def get_running_activity(
    db: DbSession
):
    activity = service.get_running_activity(db)

    if activity is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return activity


# STARTS ACTIVITY & STOPS PREVIOUSLY RUNNING ONE
@router.post("/start", response_model=schemas.ActivityResponse, status_code=201)
def start_activity(
    request: schemas.ActivityInput, db: DbSession
):
    return service.start_activity(db, request)


# STOPS CURRENTLY RUNNNING ACTIVITY
@router.post("/stop",response_model=schemas.ActivityResponse)
def stop_activity(
    db: DbSession
):
    activity = service.stop_activity(db)

    if activity is None:
        raise HTTPException(status_code=409,detail="No active activity")
    
    return activity


# UPDATES ACTIVITY
@router.put("/{activity_id:int}" ,response_model=schemas.ActivityResponse)
def update_activity(
    activity_id, request: schemas.ActivityUpdate, db: DbSession
):
    try:
        activity = service.update_activity(db, activity_id, request)
    except service.ActivityConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    
    if activity is None:
       raise HTTPException(status_code=404, detail="Activity not found")
        
    return activity


# Create a completed activity with manually specified timestamps
@router.post("" ,response_model=schemas.ActivityResponse, status_code=201)
def add_completed_activity(
    request: schemas.CompletedActivityInput, db: DbSession
):
    try:
        activity = service.add_completed_activity(db, request)
    except service.ActivityConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    
    return activity


@router.delete("/{activity_id:int}",  status_code=204)
def delete_activity(
    activity_id, db: DbSession
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