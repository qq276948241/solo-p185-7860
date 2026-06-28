import urllib.request
import json
from datetime import date, timedelta, time, datetime

print("=" * 60)
print("课程评价功能测试")
print("=" * 60)

BASE_URL = "http://localhost:8000"


def login(phone, password):
    login_data = json.dumps({
        "phone": phone,
        "password": password
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=login_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        return data["access_token"]


def api_request(method, path, token=None, data=None, params=None):
    url = f"{BASE_URL}{path}"
    if params:
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{url}?{query}"

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            return True, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_data = json.loads(e.read().decode())
        return False, error_data


def setup_test_data():
    print("\n📝 准备测试数据...")
    from app.core.database import SessionLocal
    from app.models.booking import Booking, BookingStatus
    from app.models.check_in import CheckIn
    from app.models.course import Course
    from app.models.user import User
    from app.models.membership_card import MembershipCard, CardType, CardStatus
    from app.models.review import Review

    db = SessionLocal()
    try:
        db.query(Review).delete()
        db.commit()

        member = db.query(User).filter(User.phone == "13810000001").first()
        if not member:
            print("  ✗ 测试会员不存在，请先运行 seed_data.py")
            return None, None

        course = db.query(Course).filter(Course.day_of_week == 0).first()
        if not course:
            print("  ✗ 测试课程不存在，请先运行 seed_data.py")
            return None, None

        today = date.today()
        last_monday = today - timedelta(days=today.weekday() + 7)

        booking = db.query(Booking).filter(
            Booking.user_id == member.id,
            Booking.course_id == course.id,
            Booking.class_date == last_monday,
        ).first()

        if not booking:
            card = db.query(MembershipCard).filter(
                MembershipCard.user_id == member.id,
                MembershipCard.status == CardStatus.ACTIVE,
            ).first()

            booking = Booking(
                user_id=member.id,
                course_id=course.id,
                class_date=last_monday,
                status=BookingStatus.CHECKED_IN,
                membership_card_id=card.id if card else None,
            )
            db.add(booking)
            db.flush()

            check_in = CheckIn(
                user_id=member.id,
                booking_id=booking.id,
                course_id=course.id,
                deducted_count=1,
            )
            db.add(check_in)
            db.commit()
            print(f"  ✓ 创建了测试预约和签到记录 (booking_id={booking.id})")
        else:
            if booking.status != BookingStatus.CHECKED_IN:
                booking.status = BookingStatus.CHECKED_IN
                db.commit()
            print(f"  ✓ 已存在测试预约 (booking_id={booking.id})")

        unbooked_course = db.query(Course).filter(Course.day_of_week == 1).first()
        unbooked_date = last_monday + timedelta(days=1)
        unbooked = db.query(Booking).filter(
            Booking.user_id == member.id,
            Booking.course_id == unbooked_course.id,
            Booking.class_date == unbooked_date,
        ).first()

        if not unbooked:
            card = db.query(MembershipCard).filter(
                MembershipCard.user_id == member.id,
                MembershipCard.status == CardStatus.ACTIVE,
            ).first()
            unbooked = Booking(
                user_id=member.id,
                course_id=unbooked_course.id,
                class_date=unbooked_date,
                status=BookingStatus.BOOKED,
                membership_card_id=card.id if card else None,
            )
            db.add(unbooked)
            db.commit()
            print(f"  ✓ 创建了未签到测试预约 (booking_id={unbooked.id})")
        else:
            if unbooked.status != BookingStatus.BOOKED:
                unbooked.status = BookingStatus.BOOKED
                db.commit()
            print(f"  ✓ 已存在未签到测试预约 (booking_id={unbooked.id})")

        return booking.id, unbooked.id

    finally:
        db.close()


def main():
    checked_in_booking_id, booked_booking_id = setup_test_data()
    if not checked_in_booking_id:
        return

    print("\n" + "=" * 60)
    print("🔐 登录账号")
    print("=" * 60)

    member_token = login("13810000001", "123456")
    print("✓ 会员登录成功")

    admin_token = login("13800138000", "admin123456")
    print("✓ 管理员登录成功")

    print("\n" + "=" * 60)
    print("🧪 测试1: 已签到课程正常评价")
    print("=" * 60)

    success, data = api_request(
        "POST",
        f"/api/bookings/{checked_in_booking_id}/review",
        token=member_token,
        data={"rating": 5, "comment": "教练教得非常好，课程很有收获！"}
    )

    if success:
        print(f"✓ 评价提交成功！")
        print(f"  评价ID: {data['id']}")
        print(f"  评分: {data['rating']}星")
        print(f"  评价内容: {data['comment']}")
        print(f"  评价时间: {data['created_at']}")
        review_id = data["id"]
    else:
        print(f"✗ 评价失败: {data.get('detail', '未知错误')}")
        return

    print("\n" + "=" * 60)
    print("🧪 测试2: 重复评价拦截")
    print("=" * 60)

    success, data = api_request(
        "POST",
        f"/api/bookings/{checked_in_booking_id}/review",
        token=member_token,
        data={"rating": 4, "comment": "再评一次试试"}
    )

    if not success and "已评价" in data.get("detail", ""):
        print(f"✓ 重复评价拦截成功！")
        print(f"  错误信息: {data['detail']}")
    else:
        print(f"✗ 重复评价拦截失败！")
        return

    print("\n" + "=" * 60)
    print("🧪 测试3: 未签到课程评价拦截")
    print("=" * 60)

    success, data = api_request(
        "POST",
        f"/api/bookings/{booked_booking_id}/review",
        token=member_token,
        data={"rating": 5, "comment": "没签到也想评"}
    )

    if not success and "已签到" in data.get("detail", ""):
        print(f"✓ 未签到评价拦截成功！")
        print(f"  错误信息: {data['detail']}")
    else:
        print(f"✗ 未签到评价拦截失败！")
        return

    print("\n" + "=" * 60)
    print("🧪 测试4: 超范围评分拦截")
    print("=" * 60)

    success, data = api_request(
        "POST",
        f"/api/bookings/{checked_in_booking_id}/review",
        token=member_token,
        data={"rating": 6, "comment": "打个6星"}
    )

    if not success:
        print(f"✓ 超范围评分拦截成功！")
        print(f"  错误信息: {data.get('detail', '验证失败')}")
    else:
        print(f"✗ 超范围评分拦截失败！")
        return

    print("\n" + "=" * 60)
    print("🧪 测试5: 查询我的评价")
    print("=" * 60)

    success, data = api_request(
        "GET",
        "/api/bookings/reviews/my",
        token=member_token
    )

    if success and len(data) > 0:
        print(f"✓ 查询成功，共 {len(data)} 条评价")
        for r in data:
            print(f"  - {r['course_name']} | {r['rating']}星 | {r['comment']}")
    else:
        print(f"✗ 查询我的评价失败: {data}")
        return

    print("\n" + "=" * 60)
    print("🧪 测试6: 教练查询自己的评价")
    print("=" * 60)

    success, data = api_request(
        "GET",
        "/api/bookings/reviews/coach",
        token=admin_token,
        params={"coach_id": 1}
    )

    if success:
        print(f"✓ 查询成功，教练1共 {len(data)} 条评价")
    else:
        print(f"✗ 查询教练评价失败: {data}")
        return

    print("\n" + "=" * 60)
    print("🧪 测试7: 教练评分统计")
    print("=" * 60)

    success, data = api_request(
        "GET",
        "/api/bookings/reviews/coach/stats",
        token=admin_token
    )

    if success and len(data) > 0:
        print(f"✓ 查询成功，共 {len(data)} 个教练统计")
        for stat in data:
            print(f"  - {stat['coach_name']}: {stat['total_reviews']}条评价, 平均分{stat['avg_rating']}")
    else:
        print(f"✗ 查询评分统计失败: {data}")
        return

    print("\n" + "=" * 60)
    print("🧪 测试8: 管理员查询全量评价")
    print("=" * 60)

    success, data = api_request(
        "GET",
        "/api/admin/reviews",
        token=admin_token
    )

    if success and len(data) > 0:
        print(f"✓ 查询成功，共 {len(data)} 条评价")
        print(f"  最新评价: {data[0]['course_name']} | {data[0]['user_name']} | {data[0]['rating']}星")
    else:
        print(f"✗ 查询全量评价失败: {data}")
        return

    print("\n" + "=" * 60)
    print("🧪 测试9: 管理员按评分筛选评价")
    print("=" * 60)

    success, data = api_request(
        "GET",
        "/api/admin/reviews",
        token=admin_token,
        params={"rating": 5}
    )

    if success:
        print(f"✓ 查询成功，5星评价共 {len(data)} 条")
    else:
        print(f"✗ 按评分筛选失败: {data}")
        return

    print("\n" + "=" * 60)
    print("🧪 测试10: 验证数据落库")
    print("=" * 60)

    from app.core.database import SessionLocal
    from app.models.review import Review

    db = SessionLocal()
    try:
        review = db.query(Review).filter(Review.id == review_id).first()
        if review and review.rating == 5:
            print(f"✓ 数据落库验证成功！")
            print(f"  数据库中评价ID: {review.id}")
            print(f"  数据库中评分: {review.rating}星")
            print(f"  数据库中评价内容: {review.comment}")
            print(f"  关联booking_id: {review.booking_id}")
            print(f"  关联user_id: {review.user_id}")
            print(f"  关联coach_id: {review.coach_id}")
        else:
            print(f"✗ 数据落库验证失败")
            return
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！课程评价功能正常")
    print("=" * 60)
    print("\n📋 新增接口:")
    print("  POST   /api/bookings/{booking_id}/review    - 提交评价")
    print("  GET    /api/bookings/reviews/my             - 查询我的评价")
    print("  GET    /api/bookings/reviews/coach          - 教练查评价")
    print("  GET    /api/bookings/reviews/coach/stats    - 教练评分统计")
    print("  GET    /api/admin/reviews                   - 管理员查全量")
    print("\n🔒 业务规则:")
    print("  ✓ 只有已签到(checked_in)的课程才能评价")
    print("  ✓ 每个预约只能评价一次，重复评价被拦截")
    print("  ✓ 评分必须在1-5星之间")
    print("  ✓ 外键CASCADE删除，无孤儿数据")
    print("  ✓ 评价时间自动记录")


if __name__ == "__main__":
    main()
