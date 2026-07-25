import sqlite3
import pandas as pd
import os
import random
from datetime import date
from datetime import date, timedelta
from diet_optimizer import optimize_diet_plan
# Hàm ép kiểu an toàn
def safe_int(val):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0

# Hàm đoán bữa ăn
def guess_meal_type(name):
    name = str(name).lower()
    breakfast_kw = ['bánh mì', 'phở', 'bún', 'cháo', 'yến mạch', 'trứng', 'sáng', 'bún bò', 'miến']
    lunch_kw = ['cơm', 'gà', 'bò', 'heo', 'cá', 'trưa', 'sườn', 'thịt']
    dinner_kw = ['salad', 'súp', 'chay', 'tối', 'nấm', 'rau', 'đậu hũ']
    
    if any(kw in name for kw in breakfast_kw): return 'breakfast'
    if any(kw in name for kw in lunch_kw): return 'lunch'
    if any(kw in name for kw in dinner_kw): return 'dinner'
    return 'snack'

def init_db():
    conn = sqlite3.connect('balance_nutrition.db')
    c = conn.cursor()
    
    # Bảng thức ăn gốc
    c.execute('''
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meal_type TEXT, name TEXT, calories INTEGER, 
            protein INTEGER, carbs INTEGER, fat INTEGER
        )
    ''')
    
    # BẢNG MỚI: Lưu nhật ký ăn uống hàng ngày
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            meal_type TEXT,
            name TEXT,
            calories INTEGER,
            protein INTEGER,
            carbs INTEGER,
            fat INTEGER
        )
    ''')

    # TẠO BẢNG USERS
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'user',
            created_at TEXT
        )
    ''')
    
    # Tạo tài khoản mẫu nếu chưa có
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        today = date.today().isoformat()
        c.execute('INSERT INTO users (fullname, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)', 
                  ('Quản trị viên', 'admin@gmail.com', 'admin123', 'admin', today))
        c.execute('INSERT INTO users (fullname, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)', 
                  ('Lê Văn Quý', 'quy@gmail.com', '123', 'user', today))
        c.execute('INSERT INTO users (fullname, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)', 
                ('Vũ Tiến Anh', 'anh@gmail.com', '456', 'user', today))
        c.execute('INSERT INTO users (fullname, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)', 
                ('Hoàng Xuân Đức', 'duc@gmail.com', '789', 'user', today))
    
    c.execute('SELECT COUNT(*) FROM foods')
    if c.fetchone()[0] == 0:
        csv_path = 'data/vi-food-nutrition_vi.csv'
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                for index, row in df.iterrows():
                    name = str(row.get('Name', f'Món ăn {index}'))
                    cals = safe_int(row.get('Calories Kcal', 0))
                    pro = safe_int(row.get('Protein G', 0))
                    carbs = safe_int(row.get('Carbohydrates G', 0))
                    fat = safe_int(row.get('Fat G', 0))
                    meal = guess_meal_type(name)
                    c.execute('INSERT INTO foods (meal_type, name, calories, protein, carbs, fat) VALUES (?,?,?,?,?,?)', 
                              (meal, name, cals, pro, carbs, fat))
                print(f"Đã nạp {len(df)} món từ CSV vào Database.")
            except Exception as e:
                print(f"Lỗi đọc CSV: {e}")
        else:
            sample_data = [
                ('breakfast', 'Trứng ốp la + Bánh mì', 350, 15, 30, 10),
                ('lunch', 'Cơm gà xối mỡ', 700, 40, 60, 20),
                ('dinner', 'Salad ức gà', 400, 35, 10, 15)
            ]
            c.executemany('INSERT INTO foods (meal_type, name, calories, protein, carbs, fat) VALUES (?,?,?,?,?,?)', sample_data)
    conn.commit()
    conn.close()
    
def score_food(food, goal):
    # food = (id, meal_type, name, calories, protein, carbs, fat)
    cals, protein, fat = food[3], food[4], food[6]
    if cals <= 0:
        return -999
    protein_ratio = (protein * 4) / cals
    fat_ratio = (fat * 9) / cals
    density = cals

    if goal == "giam_can":
        return protein_ratio * 2 - fat_ratio - (density / 500)
    elif goal == "tang_can":
        return (density / 300) + protein_ratio
    else:
        return protein_ratio

def get_diet_plan(tdee, goal="duy_tri"):
    conn = sqlite3.connect('balance_nutrition.db')
    c = conn.cursor()
    c.execute('SELECT * FROM foods WHERE meal_type="breakfast"')
    breakfasts = c.fetchall()
    c.execute('SELECT * FROM foods WHERE meal_type IN ("lunch", "dinner")')
    main_meals = c.fetchall()
    conn.close()

    if not breakfasts or len(main_meals) < 2:
        return {"error": "Thiếu dữ liệu DB."}

    breakfasts = sorted(breakfasts, key=lambda f: score_food(f, goal), reverse=True)[:15]
    main_meals = sorted(main_meals, key=lambda f: score_food(f, goal), reverse=True)[:15]

    bf = random.choice(breakfasts)
    lu, dn = random.sample(main_meals, 2)

    targets = {'bf': tdee * 0.25, 'lu': tdee * 0.40, 'dn': tdee * 0.35}

    def scale(item, target_cals):
        cals_per_100g = item[3] if item[3] > 0 else 1
        grams = round((target_cals / cals_per_100g) * 100)
        factor = grams / 100
        return {
            'name': item[2], 'grams': grams,
            'cals': round(item[3]*factor), 'protein': round(item[4]*factor),
            'carbs': round(item[5]*factor), 'fat': round(item[6]*factor)
        }

    m_bf, m_lu, m_dn = scale(bf, targets['bf']), scale(lu, targets['lu']), scale(dn, targets['dn'])
    total_cals = m_bf['cals'] + m_lu['cals'] + m_dn['cals']

    return {
        'target_tdee': tdee, 'total_calories': total_cals,
        'total_protein': m_bf['protein']+m_lu['protein']+m_dn['protein'],
        'total_carbs': m_bf['carbs']+m_lu['carbs']+m_dn['carbs'],
        'total_fat': m_bf['fat']+m_lu['fat']+m_dn['fat'],
        'meals': {'breakfast': m_bf, 'lunch': m_lu, 'dinner': m_dn}
    }
# HÀM MỚI: Lưu món ăn vào nhật ký
def log_food(food_data):
    conn = sqlite3.connect('balance_nutrition.db')
    c = conn.cursor()
    today = date.today().isoformat()
    c.execute('''
        INSERT INTO daily_logs (user_id, date, meal_type, name, calories, protein, carbs, fat)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        1, # Tạm thời hardcode user_id=1 (sau này có login thì sửa)
        today,
        food_data.get('meal_type', 'snack'),
        food_data.get('name', 'Món ăn'),
        food_data.get('calories', 0),
        food_data.get('protein', 0),
        food_data.get('carbs', 0),
        food_data.get('fat', 0)
    ))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã thêm vào nhật ký!"}

# HÀM MỚI: Lấy nhật ký ăn uống hôm nay
def get_today_logs():
    conn = sqlite3.connect('balance_nutrition.db')
    c = conn.cursor()
    today = date.today().isoformat()
    c.execute('SELECT id, meal_type, name, calories, protein, carbs, fat FROM daily_logs WHERE user_id=1 AND date=?', (today,))
    logs = c.fetchall()
    conn.close()
    
    total_cals = sum(log[3] for log in logs)
    total_p = sum(log[4] for log in logs)
    total_c = sum(log[5] for log in logs)
    total_f = sum(log[6] for log in logs)
        
    return {
        "foods": [{"id": log[0], "meal_type": log[1], "name": log[2], "calories": log[3], "protein": log[4], "carbs": log[5], "fat": log[6]} for log in logs],
        "totals": {
            "calories": total_cals,
            "protein": total_p,
            "carbs": total_c,
            "fat": total_f
        }
    }
# HÀM MỚI: Lấy lượng calo của 7 ngày gần nhất
def get_weekly_stats():
    conn = sqlite3.connect('balance_nutrition.db')
    c = conn.cursor()
    today = date.today()
    
    dates = []
    calories = []
    
    # Lặp qua 7 ngày gần nhất
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        dates.append(day.strftime('%d/%m')) # Định dạng ngày cho đẹp
        
        c.execute('SELECT calories FROM daily_logs WHERE user_id=1 AND date=?', (day_str,))
        logs = c.fetchall()
        total_cals = sum(log[0] for log in logs)
        calories.append(total_cals)
        
    conn.close()
    return {"dates": dates, "calories": calories}

# ================= ADMIN FUNCTIONS =================

def get_all_foods():
    """Lấy danh sách toàn bộ món ăn cho Admin"""
    import sqlite3
    conn = sqlite3.connect('balance_nutrition.db')
    c = conn.cursor()
    c.execute('SELECT id, meal_type, name, calories, protein, carbs, fat FROM foods ORDER BY id DESC')
    foods = c.fetchall()
    conn.close()
    return [{"id": f[0], "meal_type": f[1], "name": f[2], "calories": f[3], "protein": f[4], "carbs": f[5], "fat": f[6]} for f in foods]

def add_new_food(data):
    """Admin thêm món ăn mới vào DB và cập nhật Vector DB"""
    import sqlite3
    try:
        conn = sqlite3.connect('balance_nutrition.db')
        c = conn.cursor()
        
        # 1. Thêm vào SQLite
        c.execute('''
            INSERT INTO foods (meal_type, name, calories, protein, carbs, fat)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data.get('meal_type', 'snack'),
            data.get('name'),
            safe_int(data.get('calories', 0)),
            safe_int(data.get('protein', 0)),
            safe_int(data.get('carbs', 0)),
            safe_int(data.get('fat', 0))
        ))
        
        new_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # 2. Cập nhật trực tiếp vào ChromaDB (RAG)
        try:
            from rag_chatbot import collection
            doc_text = f"{data.get('name')} chứa {data.get('calories', 0)} calo, {data.get('protein', 0)}g protein, {data.get('carbs', 0)}g carbs, {data.get('fat', 0)}g chất béo."
            meta = {
                "name": data.get('name'), 
                "calories": safe_int(data.get('calories', 0)), 
                "protein": safe_int(data.get('protein', 0)), 
                "carbs": safe_int(data.get('carbs', 0)), 
                "fat": safe_int(data.get('fat', 0))
            }
            collection.add(
                documents=[doc_text],
                metadatas=[meta],
                ids=[f"food_new_{new_id}"]
            )
        except Exception as vec_err:
            print("Lỗi update Vector DB:", vec_err)
            
        return {"status": "success", "message": "Đã thêm món ăn mới thành công!"}
        
    except Exception as e:
        print("Lỗi Database:", e)
        return {"error": f"Có lỗi xảy ra: {str(e)}"}

def delete_food(food_id):
    """Admin xóa món ăn"""
    import sqlite3
    conn = sqlite3.connect('balance_nutrition.db')
    c = conn.cursor()
    c.execute('DELETE FROM foods WHERE id=?', (food_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã xóa món ăn!"}

def get_all_users():
    """Lấy danh sách người dùng cho Admin"""
    conn = sqlite3.connect('balance_nutrition.db')
    c = conn.cursor()
    c.execute('SELECT id, fullname, email, role, created_at FROM users ORDER BY id DESC')
    users = c.fetchall()
    conn.close()
    return [{"id": u[0], "fullname": u[1], "email": u[2], "role": u[3], "created_at": u[4]} for u in users]

def delete_user(user_id):
    """Xóa/Khóa tài khoản người dùng"""
    conn = sqlite3.connect('balance_nutrition.db')
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã xóa tài khoản!"}

# ================= AUTH FUNCTIONS =================
def verify_login(email, password):
    """Kiểm tra đăng nhập"""
    import sqlite3
    conn = sqlite3.connect('balance_nutrition.db')
    c = conn.cursor()
    c.execute('SELECT id, fullname, role FROM users WHERE email=? AND password=?', (email, password))
    user = c.fetchone()
    conn.close()
    
    if user:
        return {"status": "success", "user": {"id": user[0], "fullname": user[1], "role": user[2]}}
    return {"status": "error", "message": "Email hoặc mật khẩu không đúng!"}

def register_user(fullname, email, password):
    """Đăng ký tài khoản mới"""
    import sqlite3
    from datetime import date
    try:
        conn = sqlite3.connect('balance_nutrition.db')
        c = conn.cursor()
        today = date.today().isoformat()
        c.execute('INSERT INTO users (fullname, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)', 
                  (fullname, email, password, 'user', today))
        new_id = c.lastrowid
        conn.commit()
        conn.close()
        return {"status": "success", "user": {"id": new_id, "fullname": fullname, "role": "user"}}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Email này đã được đăng ký!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}