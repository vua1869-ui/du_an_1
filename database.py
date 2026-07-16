import sqlite3
import pandas as pd
import os
import random

def init_db():
    conn = sqlite3.connect('balance_nutrition.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meal_type TEXT, name TEXT, calories INTEGER, 
            protein INTEGER, carbs INTEGER, fat INTEGER
        )
    ''')
    
    c.execute('SELECT COUNT(*) FROM foods')
    if c.fetchone()[0] == 0:
        # Cập nhật đường dẫn file CSV mới của em tại đây:
        csv_path = 'data/vi-food-nutrition_vi.csv'
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                for index, row in df.iterrows():
                    # Chú ý: Em phải đảm bảo tên các cột (Tên món, Calories, Protein, Carbs, Fat) 
                    # ở dưới đây KHỚP CHÍNH XÁC (viết hoa/thường) với tiêu đề cột trong file CSV của em.
                    name = str(row.get('Tên món', f'Món ăn {index}'))
                    cals = int(row.get('Calories', 0))
                    pro = int(row.get('Protein', 0))
                    carbs = int(row.get('Carbs', 0))
                    fat = int(row.get('Fat', 0))
                    meal = random.choice(['breakfast', 'lunch', 'dinner'])
                    c.execute('INSERT INTO foods (meal_type, name, calories, protein, carbs, fat) VALUES (?,?,?,?,?,?)', 
                              (meal, name, cals, pro, carbs, fat))
                print(f"Đã nạp {len(df)} món từ CSV vào Database.")
            except Exception as e:
                print(f"Lỗi đọc CSV: {e}")
        else:
            # Dữ liệu dự phòng
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
    c.execute('SELECT * FROM foods WHERE meal_type="breakfast" ORDER BY RANDOM() LIMIT 1')
    bf = c.fetchone()
    c.execute('SELECT * FROM foods WHERE meal_type="lunch" ORDER BY RANDOM() LIMIT 1')
    lu = c.fetchone()
    c.execute('SELECT * FROM foods WHERE meal_type="dinner" ORDER BY RANDOM() LIMIT 1')
    dn = c.fetchone()
    conn.close()
    
    if not bf or not lu or not dn: return {"error": "Thiếu dữ liệu DB."}

    return {
        'total_calories': tdee,
        'total_protein': bf[4] + lu[4] + dn[4],
        'total_carbs': bf[5] + lu[5] + dn[5],
        'total_fat': bf[6] + lu[6] + dn[6],
        'meals': {
            'breakfast': {'name': bf[2], 'cals': bf[3]},
            'lunch': {'name': lu[2], 'cals': lu[3]},
            'dinner': {'name': dn[2], 'cals': dn[3]}
        }
    }