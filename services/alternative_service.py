import json
from ai.rag import get_client

def generate_alternatives(food_data):
    client = get_client()
    if not client:
        return {"status": "error", "message": "Chưa kết nối Gemini AI"}

    name = food_data.get('name', 'Món ăn')
    cals = food_data.get('calories', 0)
    pro = food_data.get('protein', 0)

    prompt = f"""
    Người dùng đang định ăn món: "{name}" (lượng calo: {cals} kcal, {pro}g protein).
    Hãy đóng vai chuyên gia dinh dưỡng, đề xuất 3 món ăn THAY THẾ lành mạnh hơn (ưu tiên các món dễ tìm hoặc món Việt Nam).
    Mỗi món thay thế phải giải thích cực kỳ NGẮN GỌN (dưới 10 chữ): giảm bao nhiêu kcal, tăng bao nhiêu protein so với món gốc.
    
    Trả về ĐÚNG định dạng JSON mảng sau (không giải thích thêm, không dùng markdown block):
    [
      {{
        "name": "Salad Ức Gà",
        "calories": 250,
        "protein": 30,
        "carbs": 10,
        "fat": 5,
        "reason": "Giảm 100 kcal, tăng 15g protein"
      }}
    ]
    """
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
        raw_text = response.text.strip()
        if raw_text.startswith("```json"): raw_text = raw_text[7:-3]
        elif raw_text.startswith("```"): raw_text = raw_text[3:-3]
        
        alts = json.loads(raw_text.strip())
        return {"status": "success", "alternatives": alts}
    except Exception as e:
        return {"status": "error", "message": str(e)}