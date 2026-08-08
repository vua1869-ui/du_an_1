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