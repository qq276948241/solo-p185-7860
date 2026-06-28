from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    MEMBER = "member"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(50), nullable=True)
    gender = Column(String(10), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.MEMBER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    membership_cards = relationship("MembershipCard", back_populates="user")
    bookings = relationship("Booking", back_populates="user")
    check_ins = relationship("CheckIn", back_populates="user")
