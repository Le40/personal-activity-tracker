import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Determine the default database directory.
if getattr(sys, "frozen", False):
    # Running as .exe
    DATABASE_DIR = Path(sys.executable).resolve().parent
else:
    # Running from Python source
    DATABASE_DIR = Path(__file__).resolve().parent.parent


# Allow Docker to override the database location.
DATABASE_PATH = Path(
    os.getenv("PATRICK_DB_PATH", DATABASE_DIR / "activity_tracker.db")
)


engine = create_engine(f"sqlite:///{DATABASE_PATH.as_posix()}")


def get_session():
    with Session(engine) as session:
        yield session