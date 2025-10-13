from sqlalchemy import Column, Integer, String, Boolean, DateTime, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    # is_active = Column(Boolean, default=True)