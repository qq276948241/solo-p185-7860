from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.models.coach import Coach
from app.schemas.coach import CoachCreate, CoachUpdate, CoachResponse

router = APIRouter(prefix="/coaches", tags=["教练管理"])


@router.post("", response_model=CoachResponse, summary="添加教练(管理员)")
def create_coach(
    coach_in: CoachCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if coach_in.phone:
        existing = db.query(Coach).filter(Coach.phone == coach_in.phone).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该手机号已被使用"
            )

    coach = Coach(**coach_in.model_dump())
    db.add(coach)
    db.commit()
    db.refresh(coach)

    return coach


@router.get("", response_model=List[CoachResponse], summary="查询教练列表")
def get_coaches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    coaches = db.query(Coach).order_by(Coach.created_at.desc()).all()
    return coaches


@router.get("/{coach_id}", response_model=CoachResponse, summary="查询教练详情")
def get_coach(
    coach_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="教练不存在"
        )
    return coach


@router.put("/{coach_id}", response_model=CoachResponse, summary="更新教练信息(管理员)")
def update_coach(
    coach_id: int,
    coach_in: CoachUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="教练不存在"
        )

    if coach_in.phone and coach_in.phone != coach.phone:
        existing = db.query(Coach).filter(Coach.phone == coach_in.phone).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该手机号已被使用"
            )

    update_data = coach_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(coach, field, value)

    db.commit()
    db.refresh(coach)

    return coach
