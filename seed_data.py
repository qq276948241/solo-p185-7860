from datetime import date, timedelta, time
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.coach import Coach
from app.models.course import Course
from app.models.membership_card import MembershipCard, CardType, CardStatus
from app.models.booking import Booking, BookingStatus
from app.models.check_in import CheckIn


def seed_data():
    db = SessionLocal()
    try:
        print("开始插入示例数据...")

        coaches_data = [
            {"name": "张教练", "phone": "13900139001", "specialty": "瑜伽、普拉提"},
            {"name": "李教练", "phone": "13900139002", "specialty": "力量训练、HIIT"},
            {"name": "王教练", "phone": "13900139003", "specialty": "动感单车、有氧操"},
        ]

        coaches = []
        for data in coaches_data:
            coach = db.query(Coach).filter(Coach.phone == data["phone"]).first()
            if not coach:
                coach = Coach(**data)
                db.add(coach)
                db.flush()
            coaches.append(coach)
        db.commit()
        print(f"已创建 {len(coaches)} 个教练")

        today = date.today()
        courses_data = [
            {"name": "晨间瑜伽", "description": "舒缓身心，开启美好一天", "coach_id": coaches[0].id,
             "day_of_week": 0, "start_time": time(7, 0, 0), "end_time": time(8, 0, 0), "capacity": 15},
            {"name": "力量训练", "description": "增肌塑形，提升基础代谢", "coach_id": coaches[1].id,
             "day_of_week": 0, "start_time": time(18, 0, 0), "end_time": time(19, 0, 0), "capacity": 10},
            {"name": "动感单车", "description": "燃脂塑形，释放激情", "coach_id": coaches[2].id,
             "day_of_week": 1, "start_time": time(19, 0, 0), "end_time": time(19, 45, 0), "capacity": 20},
            {"name": "普拉提", "description": "核心训练，改善体态", "coach_id": coaches[0].id,
             "day_of_week": 2, "start_time": time(9, 0, 0), "end_time": time(10, 0, 0), "capacity": 12},
            {"name": "HIIT燃脂", "description": "高强度间歇训练", "coach_id": coaches[1].id,
             "day_of_week": 2, "start_time": time(19, 0, 0), "end_time": time(20, 0, 0), "capacity": 15},
            {"name": "有氧操", "description": "快乐运动，轻松燃脂", "coach_id": coaches[2].id,
             "day_of_week": 3, "start_time": time(18, 30, 0), "end_time": time(19, 30, 0), "capacity": 25},
            {"name": "塑形瑜伽", "description": "精准塑形，优雅蜕变", "coach_id": coaches[0].id,
             "day_of_week": 4, "start_time": time(18, 0, 0), "end_time": time(19, 0, 0), "capacity": 15},
            {"name": "核心训练", "description": "强化核心，提升运动表现", "coach_id": coaches[1].id,
             "day_of_week": 5, "start_time": time(10, 0, 0), "end_time": time(11, 0, 0), "capacity": 10},
            {"name": "周末动感单车", "description": "周末狂欢，燃烧卡路里", "coach_id": coaches[2].id,
             "day_of_week": 6, "start_time": time(15, 0, 0), "end_time": time(15, 45, 0), "capacity": 20},
        ]

        courses = []
        for data in courses_data:
            course = Course(**data)
            db.add(course)
            courses.append(course)
        db.commit()
        print(f"已创建 {len(courses)} 门课程")

        members_data = []
        for i in range(1, 21):
            phone = f"138{10000000 + i}"
            members_data.append({
                "phone": phone,
                "password": "123456",
                "name": f"会员{i:02d}",
                "gender": "男" if i % 2 == 1 else "女",
            })

        members = []
        for data in members_data:
            member = db.query(User).filter(User.phone == data["phone"]).first()
            if not member:
                member = User(
                    phone=data["phone"],
                    password_hash=get_password_hash(data["password"]),
                    name=data["name"],
                    gender=data["gender"],
                    role=UserRole.MEMBER,
                    is_active=True,
                )
                db.add(member)
                db.flush()
            members.append(member)
        db.commit()
        print(f"已创建 {len(members)} 个会员")

        cards_data = []
        for i, member in enumerate(members):
            if i % 2 == 0:
                cards_data.append({
                    "user_id": member.id,
                    "card_type": CardType.COUNT,
                    "name": "30次卡",
                    "total_count": 30,
                    "remaining_count": 30 - (i % 10),
                    "start_date": today,
                    "end_date": today + timedelta(days=365),
                    "price": 3000,
                })
            else:
                cards_data.append({
                    "user_id": member.id,
                    "card_type": CardType.MONTHLY,
                    "name": "月卡",
                    "total_count": 0,
                    "remaining_count": 0,
                    "start_date": today,
                    "end_date": today + timedelta(days=30),
                    "price": 299,
                })

        for i in range(3):
            cards_data.append({
                "user_id": members[i].id,
                "card_type": CardType.COUNT,
                "name": "10次卡(快到期)",
                "total_count": 10,
                "remaining_count": 5,
                "start_date": today - timedelta(days=30),
                "end_date": today + timedelta(days=5 + i),
                "price": 1000,
            })

        for data in cards_data:
            card = MembershipCard(**data)
            db.add(card)
        db.commit()
        print(f"已创建 {len(cards_data)} 张会员卡")

        print("\n示例数据插入完成！")
        print(f"默认管理员账号: 13800138000 / admin123456")
        print(f"示例会员账号: 13810000001 ~ 13810000020，密码统一为 123456")

    except Exception as e:
        print(f"插入示例数据时出错: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
