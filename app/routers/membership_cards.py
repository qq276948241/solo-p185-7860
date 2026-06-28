from datetime import date
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_admin
from app.models.user import User
from app.models.membership_card import MembershipCard, CardType, CardStatus
from app.schemas.membership_card import (
    MembershipCardCreate,
    MembershipCardResponse,
)

router = APIRouter(prefix="/membership-cards", tags=["会员卡"])


@router.post("", response_model=MembershipCardResponse, summary="办卡(管理员)")
def create_membership_card(
    card_in: MembershipCardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == card_in.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    if card_in.start_date > card_in.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="开始日期不能晚于结束日期"
        )

    if card_in.card_type == CardType.COUNT and card_in.total_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="次卡必须设置有效次数"
        )

    remaining_count = card_in.total_count if card_in.card_type == CardType.COUNT else 0

    card = MembershipCard(
        user_id=card_in.user_id,
        card_type=card_in.card_type,
        name=card_in.name,
        total_count=card_in.total_count,
        remaining_count=remaining_count,
        start_date=card_in.start_date,
        end_date=card_in.end_date,
        price=card_in.price,
        status=CardStatus.ACTIVE,
    )
    db.add(card)
    db.commit()
    db.refresh(card)

    return card


@router.get("", response_model=List[MembershipCardResponse], summary="查询我的会员卡")
def get_my_membership_cards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    cards = db.query(MembershipCard).filter(
        MembershipCard.user_id == current_user.id
    ).order_by(MembershipCard.created_at.desc()).all()

    for card in cards:
        if card.status == CardStatus.ACTIVE:
            today = date.today()
            if card.end_date < today:
                card.status = CardStatus.EXPIRED
            elif card.card_type == CardType.COUNT and card.remaining_count <= 0:
                card.status = CardStatus.USED_UP
    db.commit()

    return cards


@router.get("/{card_id}", response_model=MembershipCardResponse, summary="查询单张会员卡详情")
def get_membership_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    card = db.query(MembershipCard).filter(MembershipCard.id == card_id).first()
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会员卡不存在"
        )

    if card.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看该会员卡"
        )

    if card.status == CardStatus.ACTIVE:
        today = date.today()
        if card.end_date < today:
            card.status = CardStatus.EXPIRED
        elif card.card_type == CardType.COUNT and card.remaining_count <= 0:
            card.status = CardStatus.USED_UP
        db.commit()

    return card


@router.get("/balance/summary", summary="查询会员卡剩余次数汇总")
def get_card_balance_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    today = date.today()
    active_cards = db.query(MembershipCard).filter(
        MembershipCard.user_id == current_user.id,
        MembershipCard.status == CardStatus.ACTIVE,
        MembershipCard.start_date <= today,
        MembershipCard.end_date >= today,
    ).all()

    count_cards = []
    monthly_cards = []

    for card in active_cards:
        if card.card_type == CardType.COUNT and card.remaining_count > 0:
            count_cards.append({
                "id": card.id,
                "name": card.name,
                "remaining_count": card.remaining_count,
                "total_count": card.total_count,
                "end_date": card.end_date.isoformat(),
            })
        elif card.card_type == CardType.MONTHLY:
            monthly_cards.append({
                "id": card.id,
                "name": card.name,
                "end_date": card.end_date.isoformat(),
            })

    total_remaining = sum(c["remaining_count"] for c in count_cards)

    return {
        "total_remaining_count": total_remaining,
        "active_count_cards": count_cards,
        "active_monthly_cards": monthly_cards,
    }
