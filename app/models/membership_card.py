from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey, Date
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


class CardType(str, enum.Enum):
    COUNT = "count"
    MONTHLY = "monthly"


class CardStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    USED_UP = "used_up"


class MembershipCard(Base):
    __tablename__ = "membership_cards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    card_type = Column(Enum(CardType), nullable=False)
    name = Column(String(50), nullable=False)
    total_count = Column(Integer, default=0)
    remaining_count = Column(Integer, default=0)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(Enum(CardStatus), default=CardStatus.ACTIVE)
    price = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="membership_cards")
