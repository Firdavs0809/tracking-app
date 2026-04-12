from sqlalchemy import Column, DateTime
from async_database import Base
from datetime import datetime

class BaseModel(Base):
    __abstract__ = True
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,nullable=False)
