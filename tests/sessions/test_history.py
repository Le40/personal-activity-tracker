import pytest

from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import Base, ActivitySession