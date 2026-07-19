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
    
def get_diet_plan(tdee):
    conn = sqlite3.connect('balance_nutrition.db')
    c = conn.cursor()
    c.execute('SELECT * FROM foods WHERE meal_type="breakfast"')
    breakfasts = c.fetchall()
    c.execute('SELECT * FROM foods WHERE meal_type IN ("lunch", "dinner")')
    main_meals = c.fetchall()
    conn.close()

    if not breakfasts or len(main_meals) < 2:
        return {"error": "Thiếu dữ liệu DB."}

    bf = random.choice(breakfasts)
    # Chọn 2 món chính KHÁC NHAU cho trưa/tối (loại bỏ trùng)
    lu, dn = random.sample(main_meals, 2)

    # Chia TDEE theo tỉ lệ chuẩn: sáng 25% / trưa 40% / tối 35%
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