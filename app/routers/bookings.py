from datetime import date, datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_admin
from app.models.user import User
from app.models.course import Course
from app.models.coach import Coach
from app.models.booking import Booking, BookingStatus
from app.models.membership_card import MembershipCard, CardType, CardStatus
from app.models.review import Review
from app.schemas.booking import BookingCreate, BookingResponse
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewStats

router = APIRouter(prefix="/bookings", tags=["预约管理"])


def get_valid_card(db: Session, user_id: int, class_date: date) -> MembershipCard:
    today = date.today()
    cards = db.query(MembershipCard).filter(
        MembershipCard.user_id == user_id,
        MembershipCard.status == CardStatus.ACTIVE,
        MembershipCard.start_date <= class_date,
        MembershipCard.end_date >= class_date,
    ).order_by(MembershipCard.created_at.asc()).all()

    monthly_cards = [c for c in cards if c.card_type == CardType.MONTHLY]
    if monthly_cards:
        return monthly_cards[0]

    count_cards = [c for c in cards if c.card_type == CardType.COUNT and c.remaining_count > 0]
    if count_cards:
        return count_cards[0]

    return None


@router.post("", response_model=BookingResponse, summary="预约课程")
def create_booking(
    booking_in: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    today = date.today()
    if booking_in.class_date < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能预约过去的课程"
        )

    course = db.query(Course).filter(
        Course.id == booking_in.course_id,
        Course.is_active == True,
    ).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )

    if booking_in.class_date.weekday() != course.day_of_week:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该日期与课程星期几不匹配"
        )

    existing = db.query(Booking).filter(
        Booking.user_id == current_user.id,
        Booking.course_id == booking_in.course_id,
        Booking.class_date == booking_in.class_date,
    ).first()

    if existing:
        if existing.status == BookingStatus.CANCELLED:
            existing.status = BookingStatus.BOOKED
            db.commit()
            db.refresh(existing)

            coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
            result = BookingResponse.model_validate(existing)
            result.course_name = course.name
            result.coach_name = coach.name if coach else None
            result.start_time = course.start_time.strftime("%H:%M")
            result.end_time = course.end_time.strftime("%H:%M")
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您已预约该课程"
            )

    booked_count = db.query(Booking).filter(
        Booking.course_id == booking_in.course_id,
        Booking.class_date == booking_in.class_date,
        Booking.status != BookingStatus.CANCELLED,
    ).count()

    if booked_count >= course.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该课程已满员"
        )

    valid_card = get_valid_card(db, current_user.id, booking_in.class_date)
    if not valid_card:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有可用的会员卡，请先办卡或充值"
        )

    booking = Booking(
        user_id=current_user.id,
        course_id=booking_in.course_id,
        class_date=booking_in.class_date,
        status=BookingStatus.BOOKED,
        membership_card_id=valid_card.id,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
    result = BookingResponse.model_validate(booking)
    result.course_name = course.name
    result.coach_name = coach.name if coach else None
    result.start_time = course.start_time.strftime("%H:%M")
    result.end_time = course.end_time.strftime("%H:%M")
    return result


@router.post("/{booking_id}/cancel", response_model=BookingResponse, summary="取消预约")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预约不存在"
        )

    if booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权取消他人预约"
        )

    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该预约已取消"
        )

    if booking.status == BookingStatus.CHECKED_IN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已签到的课程不能取消"
        )

    now = datetime.now()
    class_datetime = datetime.combine(booking.class_date, booking.course.start_time)
    if now >= class_datetime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="课程已开始，不能取消"
        )

    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)

    course = db.query(Course).filter(Course.id == booking.course_id).first()
    coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
    result = BookingResponse.model_validate(booking)
    result.course_name = course.name
    result.coach_name = coach.name if coach else None
    result.start_time = course.start_time.strftime("%H:%M")
    result.end_time = course.end_time.strftime("%H:%M")
    return result


@router.get("/my", response_model=List[BookingResponse], summary="查询我的预约")
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    today = date.today()
    bookings = db.query(Booking).filter(
        Booking.user_id == current_user.id,
        Booking.class_date >= today - timedelta(days=7),
    ).order_by(Booking.class_date.desc(), Booking.id.desc()).all()

    result = []
    for booking in bookings:
        course = db.query(Course).filter(Course.id == booking.course_id).first()
        coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
        booking_resp = BookingResponse.model_validate(booking)
        booking_resp.course_name = course.name
        booking_resp.coach_name = coach.name if coach else None
        booking_resp.start_time = course.start_time.strftime("%H:%M")
        booking_resp.end_time = course.end_time.strftime("%H:%M")
        result.append(booking_resp)

    return result


@router.get("", response_model=List[BookingResponse], summary="查询所有预约(管理员)")
def get_all_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    bookings = db.query(Booking).order_by(
        Booking.class_date.desc(),
        Booking.id.desc(),
    ).all()

    result = []
    for booking in bookings:
        course = db.query(Course).filter(Course.id == booking.course_id).first()
        coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
        booking_resp = BookingResponse.model_validate(booking)
        booking_resp.course_name = course.name
        booking_resp.coach_name = coach.name if coach else None
        booking_resp.start_time = course.start_time.strftime("%H:%M")
        booking_resp.end_time = course.end_time.strftime("%H:%M")
        result.append(booking_resp)

    return result


@router.post("/{booking_id}/review", response_model=ReviewResponse, summary="提交课程评价")
def create_review(
    booking_id: int,
    review_in: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预约不存在"
        )

    if booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权为他人的预约评价"
        )

    if booking.status != BookingStatus.CHECKED_IN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有已签到的课程才能评价"
        )

    existing_review = db.query(Review).filter(Review.booking_id == booking_id).first()
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该课程已评价，不能重复评价"
        )

    course = db.query(Course).filter(Course.id == booking.course_id).first()

    review = Review(
        booking_id=booking_id,
        user_id=booking.user_id,
        course_id=booking.course_id,
        coach_id=course.coach_id,
        rating=review_in.rating,
        comment=review_in.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    coach = db.query(Coach).filter(Coach.id == course.coach_id).first()
    user = db.query(User).filter(User.id == booking.user_id).first()

    result = ReviewResponse.model_validate(review)
    result.user_name = user.name if user else None
    result.course_name = course.name
    result.coach_name = coach.name if coach else None
    result.class_date = booking.class_date.isoformat()
    result.start_time = course.start_time.strftime("%H:%M")
    return result


@router.get("/reviews/my", response_model=List[ReviewResponse], summary="查询我的评价")
def get_my_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    reviews = db.query(Review).filter(
        Review.user_id == current_user.id
    ).order_by(Review.created_at.desc()).all()

    result = []
    for r in reviews:
        course = db.query(Course).filter(Course.id == r.course_id).first()
        coach = db.query(Coach).filter(Coach.id == r.coach_id).first()
        user = db.query(User).filter(User.id == r.user_id).first()
        booking = db.query(Booking).filter(Booking.id == r.booking_id).first()

        r_resp = ReviewResponse.model_validate(r)
        r_resp.user_name = user.name if user else None
        r_resp.course_name = course.name
        r_resp.coach_name = coach.name if coach else None
        r_resp.class_date = booking.class_date.isoformat() if booking else None
        r_resp.start_time = course.start_time.strftime("%H:%M")
        result.append(r_resp)

    return result


@router.get("/reviews/coach", response_model=List[ReviewResponse], summary="查询我带的课的评价(教练)")
def get_coach_reviews(
    coach_id: Optional[int] = Query(None, description="教练ID，管理员可指定，教练默认查自己"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    target_coach_id = coach_id

    if current_user.role != "admin" and not target_coach_id:
        coach = db.query(Coach).filter(Coach.phone == current_user.phone).first()
        if not coach:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到对应的教练信息"
            )
        target_coach_id = coach.id

    if not target_coach_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请指定教练ID"
        )

    if current_user.role != "admin":
        coach = db.query(Coach).filter(Coach.id == target_coach_id).first()
        if coach and coach.phone != current_user.phone:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权查看其他教练的评价"
            )

    reviews = db.query(Review).filter(
        Review.coach_id == target_coach_id
    ).order_by(Review.created_at.desc()).all()

    result = []
    for r in reviews:
        course = db.query(Course).filter(Course.id == r.course_id).first()
        coach = db.query(Coach).filter(Coach.id == r.coach_id).first()
        user = db.query(User).filter(User.id == r.user_id).first()
        booking = db.query(Booking).filter(Booking.id == r.booking_id).first()

        r_resp = ReviewResponse.model_validate(r)
        r_resp.user_name = user.name if user else None
        r_resp.course_name = course.name
        r_resp.coach_name = coach.name if coach else None
        r_resp.class_date = booking.class_date.isoformat() if booking else None
        r_resp.start_time = course.start_time.strftime("%H:%M")
        result.append(r_resp)

    return result


@router.get("/reviews/coach/stats", response_model=List[ReviewStats], summary="教练评分统计")
def get_coach_review_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    coaches = db.query(Coach).filter(Coach.is_active == True).all()

    result = []
    for coach in coaches:
        reviews = db.query(Review).filter(Review.coach_id == coach.id).all()

        if not reviews:
            result.append(ReviewStats(
                coach_id=coach.id,
                coach_name=coach.name,
                total_reviews=0,
                avg_rating=0.0,
                five_star_count=0,
                four_star_count=0,
                three_star_count=0,
                two_star_count=0,
                one_star_count=0,
            ))
            continue

        total = len(reviews)
        avg = sum(r.rating for r in reviews) / total
        five = sum(1 for r in reviews if r.rating == 5)
        four = sum(1 for r in reviews if r.rating == 4)
        three = sum(1 for r in reviews if r.rating == 3)
        two = sum(1 for r in reviews if r.rating == 2)
        one = sum(1 for r in reviews if r.rating == 1)

        result.append(ReviewStats(
            coach_id=coach.id,
            coach_name=coach.name,
            total_reviews=total,
            avg_rating=round(avg, 2),
            five_star_count=five,
            four_star_count=four,
            three_star_count=three,
            two_star_count=two,
            one_star_count=one,
        ))

    return result
