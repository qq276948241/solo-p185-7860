import urllib.request
import json

print("=== 健身工作室 API 测试 ===\n")

# 测试管理员登录
login_data = json.dumps({
    "phone": "13800138000",
    "password": "admin123456"
}).encode("utf-8")

req = urllib.request.Request(
    "http://localhost:8000/api/auth/login",
    data=login_data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("1. 管理员登录成功！")
        token = data["access_token"]
        user = data["user"]
        print(f"   用户: {user['name']} ({user['role']})")
        print(f"   Token: {token[:50]}...")
    
    print("\n2. 获取当前用户信息...")
    req2 = urllib.request.Request(
        "http://localhost:8000/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )
    with urllib.request.urlopen(req2) as response:
        data = json.loads(response.read().decode())
        print(f"   成功: {data['name']}")
    
    print("\n3. 管理员看板...")
    req3 = urllib.request.Request(
        "http://localhost:8000/api/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )
    with urllib.request.urlopen(req3) as response:
        data = json.loads(response.read().decode())
        print(f"   成功: {json.dumps(data, ensure_ascii=False, indent=6)}")
    
    print("\n4. 测试会员注册...")
    reg_data = json.dumps({
        "phone": "13810000001",
        "password": "123456",
        "name": "测试会员",
        "gender": "男"
    }).encode("utf-8")
    
    req4 = urllib.request.Request(
        "http://localhost:8000/api/auth/register",
        data=reg_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req4) as response:
            data = json.loads(response.read().decode())
            print(f"   注册成功: {data['user']['name']}")
            member_token = data["access_token"]
    except urllib.error.HTTPError as e:
        if e.code == 400:
            err = json.loads(e.read().decode())
            if "已注册" in err.get("detail", ""):
                print("   会员已存在，尝试登录...")
                login_data2 = json.dumps({
                    "phone": "13810000001",
                    "password": "123456"
                }).encode("utf-8")
                req5 = urllib.request.Request(
                    "http://localhost:8000/api/auth/login",
                    data=login_data2,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req5) as response:
                    data = json.loads(response.read().decode())
                    print(f"   登录成功: {data['user']['name']}")
                    member_token = data["access_token"]
            else:
                raise
    
    print("\n5. 会员查询自己的会员卡...")
    req6 = urllib.request.Request(
        "http://localhost:8000/api/membership-cards/balance/summary",
        headers={"Authorization": f"Bearer {member_token}"},
        method="GET"
    )
    with urllib.request.urlopen(req6) as response:
        data = json.loads(response.read().decode())
        print(f"   成功: {json.dumps(data, ensure_ascii=False, indent=6)}")
    
    print("\n6. 查询本周课表...")
    req7 = urllib.request.Request(
        "http://localhost:8000/api/courses/weekly",
        headers={"Authorization": f"Bearer {member_token}"},
        method="GET"
    )
    with urllib.request.urlopen(req7) as response:
        data = json.loads(response.read().decode())
        print(f"   本周共 {len(data)} 门课程")
        if data:
            print(f"   示例课程: {data[0]['name']} - {data[0]['date']} {data[0]['start_time']}")
    
    print("\n" + "="*50)
    print("✓ 所有核心 API 测试通过！")
    print(f"📖 接口文档: http://localhost:8000/docs")
    print(f"🔑 管理员账号: 13800138000 / admin123456")
    print(f"👤 测试会员账号: 13810000001 / 123456")
    print("="*50)

except Exception as e:
    print(f"\n✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()
