import random
from collections import Counter
from datetime import date
from database.db_core import get_db_connection
from services.diet_service import score_food

def analyze_user_preferences(user_id, days=30):
    """Trích xuất từ khóa món ăn yêu thích từ lịch sử 30 ngày qua"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT name FROM daily_logs 
        WHERE user_id=? AND date >= date('now', ?)
    ''', (user_id, f'-{days} days'))
    logs = c.fetchall()
    conn.close()

    if not logs: return {}

    words = []
    stop_words = ['và', 'với', 'có', 'thêm', 'không', 'món', 'bát', 'tô', 'đĩa', 'ly', 'cốc']
    for log in logs:
        food_name = log[0].lower()
        tokens = food_name.split()
        words.extend([w for w in tokens if len(w) > 2 and w not in stop_words])
    
    keyword_counts = Counter(words)
    return dict(keyword_counts.most_common(15))

def get_personalized_recommendations(user_id, tdee, goal):
    """Chấm điểm và đề xuất món ăn kết hợp Mục tiêu + Sở thích + Không trùng lặp"""
    prefs = analyze_user_preferences(user_id)
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Lấy toàn bộ món ăn
    c.execute('SELECT * FROM foods')
    all_foods = c.fetchall()
    
    # Lấy danh sách các món ĐÃ ĂN HÔM NAY
    today_str = date.today().isoformat()
    c.execute('SELECT name FROM daily_logs WHERE user_id=? AND date=?', (user_id, today_str))
    logged_today = [row[0].lower() for row in c.fetchall()] # Chuyển thành chữ thường để so sánh
    
    conn.close()

    if not all_foods:
        return {"error": "Không có dữ liệu món ăn"}

    scored_foods = []
    for food in all_foods:
        food_name_lower = food[2].lower()
        
        # NẾU MÓN NÀY ĐÃ CÓ TRONG NHẬT KÝ HÔM NAY -> BỎ QUA LUÔN
        if food_name_lower in logged_today:
            continue

        base_score = score_food(food, goal) 
        if base_score < -100:
            continue

        pref_score = 0
        for kw, count in prefs.items():
            if kw in food_name_lower:
                pref_score += (count * 0.2)

        total_score = base_score + pref_score
        scored_foods.append((total_score, food))

    # Sắp xếp món ăn từ điểm cao xuống thấp
    scored_foods.sort(key=lambda x: x[0], reverse=True)
    
    # Lấy top 20 món ăn tốt nhất để trộn ngẫu nhiên
    top_breakfasts = [f for s, f in scored_foods if f[1] == 'breakfast'][:20]
    top_mains = [f for s, f in scored_foods if f[1] in ('lunch', 'dinner')][:40]
    
    targets = {'bf': tdee * 0.25, 'main': tdee * 0.35}
    
    def scale_macro(item, target_cals):
        if not item: return None
        cals_per_100g = item[3] if item[3] > 0 else 1
        grams = round((target_cals / cals_per_100g) * 100)
        factor = grams / 100
        return {
            'id': item[0], 'meal_type': item[1], 'name': item[2], 'grams': grams,
            'calories': round(item[3]*factor), # Bổ sung thêm key 'calories' để sửa lỗi 0 calo
            'cals': round(item[3]*factor),
            'protein': round(item[4]*factor),
            'carbs': round(item[5]*factor), 'fat': round(item[6]*factor)
        }

    recommended = {}
    if top_breakfasts:
        bf = random.choice(top_breakfasts)
        recommended['breakfast'] = scale_macro(bf, targets['bf'])
        
    if top_mains:
        selected_mains = random.sample(top_mains, min(2, len(top_mains)))
        recommended['lunch'] = scale_macro(selected_mains[0], targets['main'])
        if len(selected_mains) > 1:
            recommended['dinner'] = scale_macro(selected_mains[1], targets['main'])

    return {
        "status": "success", 
        "recommendations": recommended, 
        "keywords_learned": list(prefs.keys())
    }