from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


class BookingStatus(str, enum.Enum):
    BOOKED = "booked"
    CANCELLED = "cancelled"
    CHECKED_IN = "checked_in"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    class_date = Column(Date, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.BOOKED)
    membership_card_id = Column(Integer, ForeignKey("membership_cards.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "course_id", "class_date", name="uix_user_course_date"),
    )

    user = relationship("User", back_populates="bookings")
    course = relationship("Course", back_populates="bookings")
    check_in = relationship("CheckIn", back_populates="booking", uselist=False)
    review = relationship("Review", back_populates="booking", uselist=False)
