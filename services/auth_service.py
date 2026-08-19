# File: services/auth_service.py
from database.db_core import get_db_connection
from datetime import date
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

def hash_password(password):
    return bcrypt.generate_password_hash(password).decode('utf-8')

def verify_password(stored_password, provided_password):
    return bcrypt.check_password_hash(stored_password, provided_password)

def verify_login(email, password):
    conn = get_db_connection()
    c = conn.cursor()
    # Thêm cột password vào truy vấn (vị trí index 2)
    c.execute('SELECT id, fullname, password, role, nickname, gender, birth_year, height, weight, goal, bmr, tdee, target_calories FROM users WHERE email=?', (email,))
    u = c.fetchone()
    conn.close()
    
    # u[2] là password đã được mã hóa trong database
    if u and verify_password(u[2], password):
        return {
            "status": "success", 
            "user": {
                "id": u[0], 
                "fullname": u[1], 
                "role": u[3], 
                "nickname": u[4], 
                "gender": u[5], 
                "birth_year": u[6], 
                "height": u[7], 
                "weight": u[8], 
                "goal": u[9], 
                "bmr": u[10], 
                "tdee": u[11], 
                "target_calories": u[12]
            }
        }
    return {"status": "error", "message": "Email hoặc mật khẩu không đúng!"}

def register_user(fullname, email, password):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Mã hóa mật khẩu trước khi lưu vào SQLite (Chống lộ password nếu DB bị rò rỉ)
        hashed_password = hash_password(password)
        
        c.execute('INSERT INTO users (fullname, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)', 
                  (fullname, email, hashed_password, 'user', date.today().isoformat()))
        new_id = c.lastrowid
        conn.commit()
        conn.close()
        return {"status": "success", "user": {"id": new_id, "fullname": fullname, "role": "user"}}
    except Exception as e: 
        return {"status": "error", "message": "Email này đã được đăng ký!"}

def _validate_password_strength(password):
    """Quy tắc mật khẩu pro: ≥8 ký tự, có chữ, số và ký tự đặc biệt."""
    if not password or len(password) < 8:
        return "Mật khẩu phải có ít nhất 8 ký tự"
    if not any(c.isalpha() for c in password):
        return "Mật khẩu cần có ít nhất 1 chữ cái"
    if not any(c.isdigit() for c in password):
        return "Mật khẩu cần có ít nhất 1 chữ số"
    specials = set("!@#$%^&*()_+-=[]{}|;:',.<>?/`~\\\"")
    if not any(c in specials for c in password):
        return "Mật khẩu cần có ít nhất 1 ký tự đặc biệt (!@#$%...)"
    return None

def change_password(user_id, current_password, new_password):
    """Đổi mật khẩu — yêu cầu mật khẩu hiện tại đúng + mật khẩu mạnh."""
    err = _validate_password_strength(new_password)
    if err:
        return {"status": "error", "message": err}

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"status": "error", "message": "Không tìm thấy tài khoản"}
    if not verify_password(row[0], current_password):
        conn.close()
        return {"status": "error", "message": "Mật khẩu hiện tại không đúng"}

    hashed = hash_password(new_password)
    c.execute('UPDATE users SET password=? WHERE id=?', (hashed, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã đổi mật khẩu thành công"}

def delete_account(user_id, password):
    """Xóa toàn bộ dữ liệu người dùng (GDPR-style)."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT password, role FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"status": "error", "message": "Không tìm thấy tài khoản"}
    if row[1] == 'admin':
        conn.close()
        return {"status": "error", "message": "Không thể xóa tài khoản Admin"}
    if not verify_password(row[0], password):
        conn.close()
        return {"status": "error", "message": "Mật khẩu không đúng"}

    for table, col in [
        ('daily_logs', 'user_id'),
        ('water_logs', 'user_id'),
        ('weight_logs', 'user_id'),
        ('weight_history', 'user_id'),
        ('user_achievements', 'user_id'),
    ]:
        try:
            c.execute(f'DELETE FROM {table} WHERE {col}=?', (user_id,))
        except Exception:
            pass
    c.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Tài khoản đã được xóa vĩnh viễn"}

def export_user_data(user_id):
    """Xuất toàn bộ dữ liệu cá nhân (JSON) — tính năng pro / quyền riêng tư."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, fullname, email, role, nickname, gender, birth_year, height, weight, goal, activity_level, weekly_goal, bmr, tdee, target_calories, created_at FROM users WHERE id=?', (user_id,))
    u = c.fetchone()
    if not u:
        conn.close()
        return {"status": "error", "message": "Không tìm thấy"}

    profile = {
        "id": u[0], "fullname": u[1], "email": u[2], "role": u[3], "nickname": u[4],
        "gender": u[5], "birth_year": u[6], "height": u[7], "weight": u[8],
        "goal": u[9], "activity_level": u[10], "weekly_goal": u[11],
        "bmr": u[12], "tdee": u[13], "target_calories": u[14], "created_at": u[15]
    }

    c.execute('SELECT date, meal_type, name, calories, protein, carbs, fat FROM daily_logs WHERE user_id=? ORDER BY date DESC', (user_id,))
    foods = [{"date": r[0], "meal_type": r[1], "name": r[2], "calories": r[3], "protein": r[4], "carbs": r[5], "fat": r[6]} for r in c.fetchall()]

    c.execute('SELECT date, amount_ml FROM water_logs WHERE user_id=? ORDER BY date DESC', (user_id,))
    water = [{"date": r[0], "amount_ml": r[1]} for r in c.fetchall()]

    c.execute('SELECT date, weight FROM weight_logs WHERE user_id=? ORDER BY date DESC', (user_id,))
    weights = [{"date": r[0], "weight": r[1]} for r in c.fetchall()]

    c.execute('''SELECT a.code, a.name, ua.unlocked_at FROM user_achievements ua
                 JOIN achievements a ON a.id = ua.achievement_id WHERE ua.user_id=?''', (user_id,))
    badges = [{"code": r[0], "name": r[1], "unlocked_at": r[2]} for r in c.fetchall()]

    conn.close()
    return {
        "status": "success",
        "exported_at": date.today().isoformat(),
        "profile": profile,
        "food_logs": foods,
        "water_logs": water,
        "weight_logs": weights,
        "achievements": badges
    }

def get_security_info(user_id):
    """Thông tin bảo mật hiển thị trên UI."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT email, created_at, role FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return {"status": "error"}
    return {
        "status": "success",
        "email": row[0],
        "created_at": row[1],
        "role": row[2],
        "password_hashed": True,
        "session_based": True,
        "tips": [
            "Mật khẩu được băm Bcrypt — không lưu dạng plain text",
            "Session Flask server-side, tự hết hạn khi đóng trình duyệt (nếu cấu hình)",
            "Nên dùng mật khẩu ≥ 8 ký tự, có chữ và số",
            "Không chia sẻ tài khoản Admin"
        ]
    }

def save_user_onboarding(user_id, profile):
    gender = profile.get('gender', 'male')
    birth_year = int(profile.get('birth_year', 2000))
    height = float(profile.get('height', 170))
    weight = float(profile.get('weight', 65))
    goal = profile.get('goal', 'duy_tri')
    activity = profile.get('activity_level', 'light')
    weekly_goal = float(profile.get('weekly_goal', 0.5))
    nickname = profile.get('nickname', 'Bạn')
    
    current_year = date.today().year
    age = max(10, current_year - birth_year)
    
    if gender == 'male': 
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else: 
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
        
    pal_map = {'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55, 'active': 1.725, 'very_active': 1.9}
    tdee = bmr * pal_map.get(activity, 1.375)
    
    daily_delta = weekly_goal * 1100
    if goal == 'giam_can': 
        target_calories = max(1200, tdee - daily_delta)
    elif goal == 'tang_can': 
        target_calories = tdee + daily_delta
    else: 
        target_calories = tdee
        
    bmr, tdee, target_calories = round(bmr), round(tdee), round(target_calories)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''UPDATE users SET nickname=?, gender=?, birth_year=?, height=?, weight=?, goal=?, activity_level=?, weekly_goal=?, bmr=?, tdee=?, target_calories=? WHERE id=?''', 
              (nickname, gender, birth_year, height, weight, goal, activity, weekly_goal, bmr, tdee, target_calories, user_id))
    conn.commit()
    conn.close()
    
    return {
        "status": "success", 
        "metrics": {
            "nickname": nickname, 
            "age": age, 
            "gender": gender, 
            "height": height, 
            "weight": weight, 
            "goal": goal, 
            "bmr": bmr, 
            "tdee": tdee, 
            "target_calories": target_calories
        }
    }