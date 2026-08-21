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

def get_personalized_recommendations(user_id, tdee, goal, exclude_names=None, only_slots=None):
    """
    Đề xuất món theo mục tiêu + sở thích.
    - exclude_names: bỏ qua tên món (đã log / đang hiện)
    - only_slots: chỉ trả về các slot ['breakfast'|'lunch'|'dinner'] — dùng khi làm mới 1 ô
    Chọn ổn định theo điểm (không random toàn bộ) để tránh đổi cả 3 khi chỉ thêm 1 món.
    """
    prefs = analyze_user_preferences(user_id)
    exclude_set = set()
    if exclude_names:
        exclude_set = {str(n).lower().strip() for n in exclude_names if n}

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM foods')
    all_foods = c.fetchall()
    today_str = date.today().isoformat()
    c.execute('SELECT name FROM daily_logs WHERE user_id=? AND date=?', (user_id, today_str))
    logged_today = {row[0].lower() for row in c.fetchall()}
    conn.close()

    if not all_foods:
        return {"status": "error", "error": "Không có dữ liệu món ăn", "recommendations": {}}

    blocked = logged_today | exclude_set

    scored_foods = []
    for food in all_foods:
        food_name_lower = (food[2] or '').lower()
        if food_name_lower in blocked:
            continue
        base_score = score_food(food, goal)
        if base_score < -100:
            continue
        pref_score = 0
        for kw, count in prefs.items():
            if kw in food_name_lower:
                pref_score += (count * 0.2)
        scored_foods.append((base_score + pref_score, food))

    scored_foods.sort(key=lambda x: x[0], reverse=True)

    top_breakfasts = [f for s, f in scored_foods if f[1] == 'breakfast'][:15]
    top_lunch = [f for s, f in scored_foods if f[1] == 'lunch'][:15]
    top_dinner = [f for s, f in scored_foods if f[1] == 'dinner'][:15]
    # fallback: lunch/dinner pool chung nếu thiếu
    top_mains = [f for s, f in scored_foods if f[1] in ('lunch', 'dinner')][:30]
    if not top_lunch:
        top_lunch = list(top_mains)
    if not top_dinner:
        top_dinner = [f for f in top_mains if f not in top_lunch[:1]] or list(top_mains)

    targets = {
        'breakfast': (tdee or 2000) * 0.25,
        'lunch': (tdee or 2000) * 0.35,
        'dinner': (tdee or 2000) * 0.35,
    }

    def scale_macro(item, target_cals, force_meal=None):
        if not item:
            return None
        cals_per_100g = item[3] if item[3] and item[3] > 0 else 1
        grams = round((target_cals / cals_per_100g) * 100)
        factor = grams / 100.0
        meal = force_meal or item[1] or 'snack'
        return {
            'id': item[0],
            'meal_type': meal,
            'name': item[2],
            'grams': grams,
            'calories': round(item[3] * factor),
            'cals': round(item[3] * factor),
            'protein': round(item[4] * factor),
            'carbs': round(item[5] * factor),
            'fat': round(item[6] * factor),
        }

    def pick_item(pool, seed_offset=0, prefer_top=False):
        """prefer_top=True khi refresh 1 ô → lấy món tốt nhất còn lại (khác món vừa thêm)."""
        if not pool:
            return None
        if prefer_top:
            return pool[0]
        try:
            idx = (int(user_id or 0) + seed_offset + int(date.today().strftime('%j'))) % len(pool)
        except Exception:
            idx = 0
        return pool[idx]

    slots = only_slots or ['breakfast', 'lunch', 'dinner']
    prefer_top = bool(only_slots)
    recommended = {}
    used_names = set()

    for slot in slots:
        if slot == 'breakfast':
            pool = top_breakfasts
            seed = 1
        elif slot == 'lunch':
            pool = top_lunch
            seed = 2
        else:
            pool = top_dinner
            seed = 3
        pool = [f for f in pool if (f[2] or '').lower() not in used_names]
        if not pool and slot in ('lunch', 'dinner'):
            pool = [f for f in top_mains if (f[2] or '').lower() not in used_names]
        item = pick_item(pool, seed_offset=seed, prefer_top=prefer_top)
        if item:
            used_names.add((item[2] or '').lower())
            recommended[slot] = scale_macro(item, targets.get(slot, 500), force_meal=slot)

    return {
        "status": "success",
        "recommendations": recommended,
        "keywords_learned": list(prefs.keys()),
    }