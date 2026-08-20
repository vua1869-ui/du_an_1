import json
from ai.rag import client

def get_food_health_score(name, calories, protein, carbs, fat):
    if not client:
        return {"score": 50, "explanation": "Chưa kết nối Gemini AI để đánh giá."}
    
    prompt = f"""
    Đánh giá độ lành mạnh (Healthy Score) của món ăn: {name} 
    Chỉ số hiện tại: {calories} kcal, {protein}g Protein, {carbs}g Carbs, {fat}g Fat.
    Hãy ước lượng thêm lượng Đường (Sugar), Chất xơ (Fiber) và Muối (Sodium) của món này để chấm điểm từ 0 đến 100.
    - 0-39: Kém lành mạnh (Đỏ)
    - 40-69: Bình thường (Vàng)
    - 70-100: Rất lành mạnh (Xanh)
    
    Trả về ĐÚNG định dạng JSON sau (không giải thích ngoài JSON):
    {{
        "score": 75,
        "explanation": "Giải thích ngắn gọn (2-3 câu) vì sao được số điểm này dựa trên Calories, Protein, Fat, Carbs, Sugar, Fiber, Sodium."
    }}
    """
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest", 
            contents=prompt
        )
        raw_text = response.text.strip()
        if raw_text.startswith("```json"): raw_text = raw_text[7:-3]
        elif raw_text.startswith("```"): raw_text = raw_text[3:-3]
        return json.loads(raw_text.strip())
    except Exception as e:
        return {"score": 50, "explanation": "Không thể phân tích điểm lành mạnh lúc này."}