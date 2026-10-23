from sqlalchemy import create_engine
from sqlalchemy.orm import Session

engine = create_engine("sqlite:///./activity_tracker.db", echo=True)

def get_session():
    with Session(engine) as session:
        yield session