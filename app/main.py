
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.activities import router

app = FastAPI()

app.include_router(router.router)

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




