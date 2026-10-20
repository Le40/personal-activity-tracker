from app.database import engine
from app.models import Base, running_session_index

Base.metadata.create_all(bind=engine)

running_session_index.create(bind=engine, checkfirst=True)