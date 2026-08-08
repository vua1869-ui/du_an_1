import random
from database.db_core import get_db_connection

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

    if not breakfasts or len(main_meals) < 2: return {"error": "Thiếu dữ liệu DB."}
    breakfasts = sorted(breakfasts, key=lambda f: score_food(f, goal), reverse=True)[:15]
    main_meals = sorted(main_meals, key=lambda f: score_food(f, goal), reverse=True)[:15]
    bf = random.choice(breakfasts)
    lu, dn = random.sample(main_meals, 2)

    targets = {'bf': tdee * 0.25, 'lu': tdee * 0.40, 'dn': tdee * 0.35}
    def scale(item, target_cals):
        factor = (target_cals / (item[3] if item[3]>0 else 1))
        return {'name': item[2], 'grams': round(factor*100), 'cals': round(item[3]*factor), 'protein': round(item[4]*factor), 'carbs': round(item[5]*factor), 'fat': round(item[6]*factor)}

    m_bf, m_lu, m_dn = scale(bf, targets['bf']), scale(lu, targets['lu']), scale(dn, targets['dn'])
    return {'target_tdee': tdee, 'total_calories': m_bf['cals'] + m_lu['cals'] + m_dn['cals'], 'total_protein': m_bf['protein']+m_lu['protein']+m_dn['protein'], 'total_carbs': m_bf['carbs']+m_lu['carbs']+m_dn['carbs'], 'total_fat': m_bf['fat']+m_lu['fat']+m_dn['fat'], 'meals': {'breakfast': m_bf, 'lunch': m_lu, 'dinner': m_dn}}