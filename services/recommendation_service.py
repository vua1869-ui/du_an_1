from collections import Counter
from database.db_core import get_db_connection
from services.diet_service import score_food

def analyze_user_preferences(user_id, days=30):
    """Trích xuất từ khóa món ăn yêu thích từ lịch sử 30 ngày qua"""
    conn = get_db_connection()
    c = conn.cursor()
    # Lấy lịch sử món ăn
    c.execute('''
        SELECT name FROM daily_logs 
        WHERE user_id=? AND date >= date('now', ?)
    ''', (user_id, f'-{days} days'))
    logs = c.fetchall()
    conn.close()

    if not logs:
        return {}

    # Tách từ khóa (Simple Tokenization)
    words = []
    # Loại bỏ các từ nối không mang ý nghĩa món ăn
    stop_words = ['và', 'với', 'có', 'thêm', 'không', 'món', 'bát', 'tô', 'đĩa', 'ly', 'cốc']
    for log in logs:
        food_name = log[0].lower()
        tokens = food_name.split()
        words.extend([w for w in tokens if len(w) > 2 and w not in stop_words])
    
    # Đếm tần suất xuất hiện để tạo User Profile Vector
    keyword_counts = Counter(words)
    # Trả về top 15 từ khóa hay ăn nhất
    return dict(keyword_counts.most_common(15))

def get_personalized_recommendations(user_id, tdee, goal):
    """Chấm điểm và đề xuất món ăn kết hợp Mục tiêu + Sở thích"""
    prefs = analyze_user_preferences(user_id)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM foods')
    all_foods = c.fetchall()
    conn.close()

    if not all_foods:
        return {"error": "Không có dữ liệu món ăn"}

    scored_foods = []
    for food in all_foods:
        # 1. Điểm cốt lõi: Phù hợp mục tiêu giảm/tăng cân (hàm cũ tái sử dụng)
        base_score = score_food(food, goal) 
        
        # Bỏ qua các món quá sai mục tiêu
        if base_score < -100:
            continue

        # 2. Điểm sở thích: Content-Based Filtering
        food_name_lower = food[2].lower()
        pref_score = 0
        for kw, count in prefs.items():
            if kw in food_name_lower:
                pref_score += (count * 0.2) # Cộng điểm nếu món này chứa từ khóa User thích

        total_score = base_score + pref_score
        scored_foods.append((total_score, food))

    # Sắp xếp món ăn từ điểm cao xuống thấp
    scored_foods.sort(key=lambda x: x[0], reverse=True)
    
    # Phân loại và lấy món ngon nhất cho từng bữa
    breakfasts = [f for s, f in scored_foods if f[1] == 'breakfast']
    mains = [f for s, f in scored_foods if f[1] in ('lunch', 'dinner')]
    
    # Chia tỷ lệ Calo mục tiêu cho từng bữa
    targets = {'bf': tdee * 0.25, 'main': tdee * 0.35}
    
    def scale_macro(item, target_cals):
        if not item: return None
        cals_per_100g = item[3] if item[3] > 0 else 1
        grams = round((target_cals / cals_per_100g) * 100)
        factor = grams / 100
        return {
            'id': item[0], 'meal_type': item[1], 'name': item[2], 'grams': grams,
            'cals': round(item[3]*factor), 'protein': round(item[4]*factor),
            'carbs': round(item[5]*factor), 'fat': round(item[6]*factor)
        }

    recommended = {}
    if breakfasts: 
        recommended['breakfast'] = scale_macro(breakfasts[0], targets['bf'])
    if mains:
        recommended['lunch'] = scale_macro(mains[0], targets['main'])
        if len(mains) > 1:
            recommended['dinner'] = scale_macro(mains[1], targets['main'])

    return {
        "status": "success", 
        "recommendations": recommended, 
        "keywords_learned": list(prefs.keys())
    }