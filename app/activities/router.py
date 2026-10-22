from fastapi import APIRouter
from fastapi import HTTPException, Depends

from sqlalchemy.orm import Session
from datetime import date

from app.database import get_session
from app.activities.models import Activity
from app.activities.schemas import ActivityResponse, ActivityInput
from app.activities import service
from app.activities.options import ActivityType, EaseRating, EASE_LABELS, EASE_RATING_ACTIVITY_TYPES


router = APIRouter(prefix="/activities", tags=["Activities"])


@router.get("", response_model=list[ActivityResponse])
def get_activities(
    day: date | None = None, db: Session = Depends(get_session)
):
    return service.get_activities(db, day)


@router.get("/{activity_id:int}", response_model=ActivityResponse)
def get_activity_by_id(activity_id: int, db: Session = Depends(get_session)):
    activity = service.get_activity_by_id(db, activity_id)

    if activity is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return activity


@router.post("/start", response_model=ActivityResponse, status_code=201)
def start_activity(
    request: ActivityInput,
    db: Session = Depends(get_session)
):
    return service.start_activity(db, request)


@router.post("/stop",response_model=ActivityResponse)
def stop_activity(
    db: Session = Depends(get_session)
):
    activity = service.stop_activity(db)

    if activity is None:
        raise HTTPException(status_code=409,detail="No active activity")
    
    return activity


@router.put("/{activity_id:int}" ,response_model=ActivityResponse)
def update_activity(activity_id, request: ActivityInput,
    db: Session = Depends(get_session)
):
    activity = service.update_activity(db, activity_id, request)

    if activity is None:
       raise HTTPException(status_code=404, detail="Activity not found")
        
    return activity


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