from app.database import engine
from app.activities.models import Base

Base.metadata.create_all(bind=engine)