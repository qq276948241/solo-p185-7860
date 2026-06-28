from fastapi import APIRouter

from app.routers.auth import router as auth_router
from app.routers.membership_cards import router as membership_cards_router
from app.routers.coaches import router as coaches_router
from app.routers.courses import router as courses_router
from app.routers.bookings import router as bookings_router
from app.routers.check_ins import router as check_ins_router
from app.routers.admin import router as admin_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(membership_cards_router)
api_router.include_router(coaches_router)
api_router.include_router(courses_router)
api_router.include_router(bookings_router)
api_router.include_router(check_ins_router)
api_router.include_router(admin_router)

__all__ = ["api_router"]
