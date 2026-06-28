from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import Base, engine, SessionLocal
from app.core.security import get_password_hash
from app.core.config import settings
from app.models.user import User, UserRole
from app.routers import api_router


def init_db():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.phone == settings.ADMIN_PHONE).first()
        if not admin:
            admin = User(
                phone=settings.ADMIN_PHONE,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                name="系统管理员",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print(f"默认管理员账号已创建: {settings.ADMIN_PHONE} / {settings.ADMIN_PASSWORD}")
    except Exception as e:
        print(f"初始化数据库时出错: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="健身工作室管理系统 API",
    description="小型健身工作室后端 API，支持会员管理、会员卡、课程排课、预约签到等功能",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", summary="健康检查")
def health_check():
    return {"status": "ok", "message": "健身工作室 API 运行正常"}


@app.get("/", summary="根路径")
def root():
    return {
        "name": "健身工作室管理系统 API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
