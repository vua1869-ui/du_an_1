import random
from database.db_core import get_db_connection
from ai.diet_optimizer import optimize_diet_plan # Import thuật toán tối ưu

def score_food(food, goal):
    cals, protein, fat = food[3], food[4], food[6]
    if cals <= 0: return -999
    protein_ratio = (protein * 4) / cals
    fat_ratio = (fat * 9) / cals
    if goal == "giam_can": return protein_ratio * 2 - fat_ratio - (cals / 500)
    elif goal == "tang_can": return (cals / 300) + protein_ratio
    else: return protein_ratio

def get_diet_plan(tdee, goal="duy_tri"):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM foods WHERE meal_type="breakfast"')
    breakfasts = c.fetchall()
    c.execute('SELECT * FROM foods WHERE meal_type IN ("lunch", "dinner")')
    main_meals = c.fetchall()
    conn.close()

    if not breakfasts or len(main_meals) < 2: 
        return {"error": "Thiếu dữ liệu DB."}
    
    # Lọc ra top 50 món tốt nhất cho mục tiêu hiện tại để giảm bớt không gian duyệt thuật toán
    breakfasts = sorted(breakfasts, key=lambda f: score_food(f, goal), reverse=True)[:50]
    lunches = sorted(main_meals, key=lambda f: score_food(f, goal), reverse=True)[:50]
    dinners = lunches.copy() # Dùng chung data bữa chính cho trưa và tối

    # GỌI THUẬT TOÁN TỐI ƯU (KNAPSACK-LIKE) thay vì random scale
    best_plan = optimize_diet_plan(breakfasts, lunches, dinners, tdee)
    
    return best_plan