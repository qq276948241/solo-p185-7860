from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.membership_card import CardType, CardStatus


class MembershipCardBase(BaseModel):
    card_type: CardType = Field(..., description="卡类型: count=次卡, monthly=月卡")
    name: str = Field(..., max_length=50, description="卡名称")
    total_count: int = Field(0, ge=0, description="总次数(次卡有效)")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    price: int = Field(0, ge=0, description="价格(分)")


class MembershipCardCreate(MembershipCardBase):
    user_id: int = Field(..., description="会员ID")


class MembershipCardUpdate(BaseModel):
    status: Optional[CardStatus] = Field(None, description="卡状态")
    remaining_count: Optional[int] = Field(None, ge=0, description="剩余次数")


class MembershipCardResponse(MembershipCardBase):
    id: int
    user_id: int
    remaining_count: int
    status: CardStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
