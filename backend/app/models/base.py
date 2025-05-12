from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base class for all models"""
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate __tablename__ automatically"""
        return cls.__name__.lower()

    # Common columns for all models
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False) 