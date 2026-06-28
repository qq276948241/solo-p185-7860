from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_admin
from app.models.user import User
from app.models.course import Course
from app.models.coach import Coach
from app.models.booking import Booking, BookingStatus
from app.models.check_in import CheckIn
from app.models.membership_card import MembershipCard, CardType, CardStatus
from app.schemas.check_in import CheckInCreate, CheckInResponse

router = APIRouter(prefix="/check-ins", tags=["签到管理"])


@router.post("", response_model=CheckInResponse, summary="签到")
def create_check_in(
    check_in_in: CheckInCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    booking = db.query(Booking).filter(
        Booking.id == check_in_in.booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预约不存在"
        )

    if booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权为他人签到"
        )

    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该预约已取消"
        )

    if booking.status == BookingStatus.CHECKED_IN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已签到，无需重复签到"
        )

    course = db.query(Course).filter(Course.id == booking.course_id).first()
    class_datetime = datetime.combine(booking.class_date, course.start_time)
    now = datetime.now()

    if now < class_datetime - timedelta(minutes=30):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="签到时间未到，课前30分钟可签到"
        )

    if now > class_datetime + timedelta(minutes=30):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已超过签到时间（开课后30分钟）"
        )

    card = db.query(MembershipCard).filter(
        MembershipCard.id == booking.membership_card_id
    ).first()

    if not card:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="关联的会员卡不存在"
        )

    if card.status != CardStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"会员卡状态异常: {card.status}"
        )

    deducted_count = 0
    if card.card_type == CardType.COUNT:
        if card.remaining_count <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="次卡次数已用完"
            )
        card.remaining_count -= 1
        deducted_count = 1

        if card.remaining_count <= 0:
            card.status = CardStatus.USED_UP

    check_in = CheckIn(
        user_id=booking.user_id,
        booking_id=booking.id,
        course_id=booking.course_id,
        check_in_time=datetime.now(),
        deducted_count=deducted_count,
    )
    db.add(check_in)

    booking.status = BookingStatus.CHECKED_IN

    db.commit()
    db.refresh(check_in)
    db.refresh(card)

    coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
    user = db.query(User).filter(User.id == booking.user_id).first()

    result = CheckInResponse.model_validate(check_in)
    result.user_name = user.name if user else None
    result.course_name = course.name
    result.coach_name = coach.name if coach else None
    result.remaining_count = card.remaining_count if card.card_type == CardType.COUNT else None

    return result


@router.get("/my", response_model=List[CheckInResponse], summary="查询我的签到记录")
def get_my_check_ins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    check_ins = db.query(CheckIn).filter(
        CheckIn.user_id == current_user.id
    ).order_by(CheckIn.check_in_time.desc()).all()

    result = []
    for ci in check_ins:
        course = db.query(Course).filter(Course.id == ci.course_id).first()
        coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
        user = db.query(User).filter(User.id == ci.user_id).first()
        ci_resp = CheckInResponse.model_validate(ci)
        ci_resp.user_name = user.name if user else None
        ci_resp.course_name = course.name
        ci_resp.coach_name = coach.name if coach else None
        result.append(ci_resp)

    return result


@router.get("", response_model=List[CheckInResponse], summary="查询所有签到记录(管理员)")
def get_all_check_ins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    check_ins = db.query(CheckIn).order_by(
        CheckIn.check_in_time.desc()
    ).all()

    result = []
    for ci in check_ins:
        course = db.query(Course).filter(Course.id == ci.course_id).first()
        coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
        user = db.query(User).filter(User.id == ci.user_id).first()
        ci_resp = CheckInResponse.model_validate(ci)
        ci_resp.user_name = user.name if user else None
        ci_resp.course_name = course.name
        ci_resp.coach_name = coach.name if coach else None
        result.append(ci_resp)

    return result
