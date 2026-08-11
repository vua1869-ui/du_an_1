import json
from datetime import date, timedelta
from database.db_core import get_db_connection
from ai.rag import client

def generate_weekly_report(user_id, tdee, target_calories):
    conn = get_db_connection()
    c = conn.cursor()
    seven_days_ago = (date.today() - timedelta(days=7)).isoformat()
    
    # 1. Lấy lịch sử ăn uống 7 ngày
    c.execute('SELECT date, name, calories, protein, carbs, fat FROM daily_logs WHERE user_id=? AND date >= ?', (user_id, seven_days_ago))
    logs = c.fetchall()
    
    # 2. Lấy lịch sử cân nặng 7 ngày
    c.execute('SELECT date, weight FROM weight_history WHERE user_id=? AND date >= ? ORDER BY date ASC', (user_id, seven_days_ago))
    weights = c.fetchall()
    conn.close()
    
    # 3. Tổng hợp số liệu
    total_cals = sum(l[2] for l in logs)
    total_p = sum(l[3] for l in logs)
    total_c = sum(l[4] for l in logs)
    total_f = sum(l[5] for l in logs)
    meal_count = len(logs)
    
    weight_str = ", ".join([f"{w[0]}: {w[1]}kg" for w in weights]) if weights else "Không có dữ liệu cân nặng."
    
    # 4. Viết Prompt yêu cầu Gemini trả về chuẩn JSON
    prompt = f"""
    Dưới đây là dữ liệu ăn uống 7 ngày qua của người dùng:
    - TDEE: {tdee} kcal/ngày | Mục tiêu Calo: {target_calories} kcal/ngày
    - Tổng bữa ăn ghi nhận: {meal_count} bữa
    - Tổng nạp: {total_cals} kcal | Protein: {total_p}g | Carbs: {total_c}g | Fat: {total_f}g
    - Lịch sử cân nặng: {weight_str}
    
    Hãy đóng vai chuyên gia dinh dưỡng, phân tích dữ liệu trên và trả về ĐÚNG định dạng JSON sau (không giải thích thêm, không dùng markdown format):
    {{
      "pros": ["Điểm tốt 1", "Điểm tốt 2"],
      "cons": ["Điểm chưa tốt 1", "Điểm chưa tốt 2"],
      "advice": ["Khuyên 1", "Khuyên 2", "Khuyên 3"],
      "next_goal": "Mục tiêu hành động ngắn gọn cho tuần sau"
    }}
    """
    
    if not client:
        return {"status": "error", "message": "Gemini API chưa được kết nối."}
        
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
        )
        
        # Làm sạch chuỗi trả về để parse JSON an toàn
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3]
            
        report_data = json.loads(raw_text.strip())
        return {"status": "success", "report": report_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}