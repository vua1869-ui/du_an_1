import json
from datetime import date, timedelta
from database.db_core import get_db_connection
from ai.rag import client

def generate_coach_message(user_id, target_calories):
    if not client:
        return {"status": "error", "message": "Chưa kết nối Gemini AI"}

    conn = get_db_connection()
    c = conn.cursor()
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    
    # 1. Lấy lượng Calo hôm qua
    c.execute('SELECT SUM(calories) FROM daily_logs WHERE user_id=? AND date=?', (user_id, yesterday))
    y_cals = c.fetchone()[0] or 0
    
    # 2. Lấy lượng Calo hôm nay
    c.execute('SELECT SUM(calories) FROM daily_logs WHERE user_id=? AND date=?', (user_id, today))
    t_cals = c.fetchone()[0] or 0
    
    # 3. Lấy lượng Nước hôm nay
    try:
        c.execute('SELECT SUM(amount_ml) FROM water_logs WHERE user_id=? AND date=?', (user_id, today))
        t_water = c.fetchone()[0] or 0
    except:
        t_water = 0 # Đề phòng trường hợp chưa có bảng water_logs
    
    conn.close()

    prompt = f"""
    Đóng vai một huấn luyện viên sức khỏe cá nhân (AI Coach). Dựa vào số liệu sau:
    - Mục tiêu Calo/ngày: {target_calories} kcal
    - Hôm qua đã nạp: {y_cals} kcal
    - Hôm nay đã nạp: {t_cals} kcal
    - Nước hôm nay đã uống: {t_water} ml / 2000 ml
    
    Hãy viết MỘT lời khuyên/nhắc nhở cực kỳ NGẮN GỌN (tối đa 2 câu, khoảng 20-25 chữ) mang tính hành động.
    Ví dụ: "Hôm qua bạn ăn vượt 350 kcal. Hôm nay hãy ăn nhẹ lại và chạy bộ 20 phút nhé!" hoặc "Bạn đang uống quá ít nước hôm nay, hãy bổ sung ngay 1 ly nhé!".
    
    Trả về ĐÚNG định dạng JSON sau:
    {{
        "coach_message": "Lời khuyên của bạn"
    }}
    """
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
        raw_text = response.text.strip()
        if raw_text.startswith("```json"): raw_text = raw_text[7:-3]
        elif raw_text.startswith("```"): raw_text = raw_text[3:-3]
        
        coach_data = json.loads(raw_text.strip())
        return {"status": "success", "message": coach_data.get("coach_message", "Hôm nay hãy cố gắng hoàn thành mục tiêu nhé!")}
    except Exception as e:
        return {"status": "error", "message": str(e)}