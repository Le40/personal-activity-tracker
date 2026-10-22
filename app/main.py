
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.options import ActivityType, EaseRating, EASE_LABELS, EASE_RATING_ACTIVITY_TYPES
from app.routers import activities


app = FastAPI()

app.include_router(activities.router)

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

