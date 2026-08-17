import sqlite3
import pandas as pd
import os
from datetime import date
from utils.helpers import safe_int, guess_meal_type

def get_db_connection():
    db_path = os.path.join('data', 'balance_nutrition.db')
    conn = sqlite3.connect(db_path, timeout=15, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

def init_db(db_path, file_path):
    conn = sqlite3.connect(db_path, timeout=15)
    conn.execute('PRAGMA journal_mode=WAL;')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS foods (id INTEGER PRIMARY KEY AUTOINCREMENT, meal_type TEXT, name TEXT, calories INTEGER, protein INTEGER, carbs INTEGER, fat INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT, meal_type TEXT, name TEXT, calories INTEGER, protein INTEGER, carbs INTEGER, fat INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, fullname TEXT, email TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'user', nickname TEXT, gender TEXT, birth_year INTEGER, height REAL, weight REAL, goal TEXT, activity_level TEXT, weekly_goal REAL, bmr REAL, tdee REAL, target_calories REAL, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS weight_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, weight REAL, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS water_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount_ml INTEGER, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS achievements (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, name TEXT, description TEXT, icon TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_achievements (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, achievement_id INTEGER, unlocked_at TEXT, UNIQUE(user_id, achievement_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS weight_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, weight REAL, date TEXT)''')

    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        today = date.today().isoformat()
        
        # Import cục bộ để tránh lỗi vòng lặp (Circular Import)
        from services.auth_service import hash_password
        
        # Phải băm mật khẩu (hash_password) trước khi đưa vào Database
        users_data = [
            ('Quản trị viên', 'admin@gmail.com', hash_password('admin123'), 'admin', today),
            ('Lê Văn Quý', 'quy@gmail.com', hash_password('123'), 'user', today),
            ('Vũ Tiến Anh', 'anh@gmail.com', hash_password('456'), 'user', today),
            ('Hoàng Xuân Đức', 'duc@gmail.com', hash_password('789'), 'user', today)
        ]
        c.executemany('INSERT INTO users (fullname, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)', users_data)
    
    c.execute('SELECT COUNT(*) FROM foods')
    if c.fetchone()[0] == 0:
        if os.path.exists(file_path):
            try:
                df = pd.read_excel(file_path)
                
                # 2. Tạo bộ từ điển ánh xạ loại bữa ăn sang tiếng Anh để khớp logic hệ thống
                meal_map = {
                    'Sáng': 'breakfast',
                    'Trưa': 'lunch',
                    'Tối': 'dinner',
                    'Ăn nhẹ': 'snack'
                }

                for index, row in df.iterrows():
                    # 3. Đọc dữ liệu theo tên cột mới trong file Excel
                    name = str(row.get('ten_mon', f'Món ăn {index}')).strip()
                    loai_bua_vn = str(row.get('loai_bua', 'Ăn nhẹ')).strip()
                    
                    meal_type = meal_map.get(loai_bua_vn, 'snack') 
                    
                    c.execute('INSERT INTO foods (meal_type, name, calories, protein, carbs, fat) VALUES (?,?,?,?,?,?)', 
                              (meal_type, name, safe_int(row.get('calo', 0)), safe_int(row.get('protein', 0)), safe_int(row.get('carbs', 0)), safe_int(row.get('fat', 0))))
            except Exception as e:
                print(f"Lỗi khi import dữ liệu Excel: {e}")
        else:
            # Dữ liệu mẫu dự phòng
            sample_data = [
                ('breakfast', 'Trứng ốp la + Bánh mì', 350, 15, 30, 10),
                ('lunch', 'Cơm gà xối mỡ', 700, 40, 60, 20),
                ('dinner', 'Salad ức gà', 400, 35, 10, 15)
            ]
            c.executemany('INSERT INTO foods (meal_type, name, calories, protein, carbs, fat) VALUES (?,?,?,?,?,?)', sample_data)
    conn.commit()
    conn.close()