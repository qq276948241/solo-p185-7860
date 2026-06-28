from datetime import datetime
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.course import Course
from app.models.coach import Coach
from app.models.user import User
from app.models.review import Review
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewStats


def validate_review_creation(
    db: Session,
    booking_id: int,
    current_user: User
) -> Tuple[Booking, Course]:
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
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )

    return booking, course


def create_review(
    db: Session,
    booking: Booking,
    course: Course,
    review_in: ReviewCreate
) -> Review:
    review = Review(
        booking_id=booking.id,
        user_id=booking.user_id,
        course_id=booking.course_id,
        coach_id=course.coach_id,
        rating=review_in.rating,
        comment=review_in.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def build_review_response(db: Session, review: Review) -> ReviewResponse:
    course = db.query(Course).filter(Course.id == review.course_id).first()
    coach = db.query(Coach).filter(Coach.id == review.coach_id).first()
    user = db.query(User).filter(User.id == review.user_id).first()
    booking = db.query(Booking).filter(Booking.id == review.booking_id).first()

    result = ReviewResponse.model_validate(review)
    result.user_name = user.name if user else None
    result.course_name = course.name if course else None
    result.coach_name = coach.name if coach else None
    result.class_date = booking.class_date.isoformat() if booking else None
    result.start_time = course.start_time.strftime("%H:%M") if course else None
    return result


def get_coach_id_for_user(db: Session, current_user: User) -> Optional[int]:
    coach = db.query(Coach).filter(Coach.phone == current_user.phone).first()
    return coach.id if coach else None


def validate_coach_access(
    db: Session,
    coach_id: int,
    current_user: User
) -> None:
    if current_user.role == "admin":
        return

    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if coach and coach.phone != current_user.phone:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看其他教练的评价"
        )


def get_reviews_by_filter(
    db: Session,
    coach_id: Optional[int] = None,
    user_id: Optional[int] = None,
    rating: Optional[int] = None
) -> List[Review]:
    query = db.query(Review)

    if coach_id:
        query = query.filter(Review.coach_id == coach_id)
    if user_id:
        query = query.filter(Review.user_id == user_id)
    if rating:
        query = query.filter(Review.rating == rating)

    return query.order_by(Review.created_at.desc()).all()


def get_review_responses(
    db: Session,
    coach_id: Optional[int] = None,
    user_id: Optional[int] = None,
    rating: Optional[int] = None
) -> List[ReviewResponse]:
    reviews = get_reviews_by_filter(db, coach_id, user_id, rating)
    return [build_review_response(db, r) for r in reviews]


def get_coach_review_stats(db: Session) -> List[ReviewStats]:
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
