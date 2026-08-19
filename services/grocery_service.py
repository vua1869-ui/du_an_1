import json
from ai.rag import get_client

def generate_grocery_list(meals_data):
    client = get_client()
    if not client:
        return {"status": "error", "message": "Chưa kết nối Gemini AI"}

    # Chuẩn bị dữ liệu món ăn để AI đọc hiểu
    meal_text = "\n".join([f"- {m['name']} (Khoảng {m.get('grams', 200)}g)" for m in meals_data])

    prompt = f"""
    Dựa vào danh sách các món ăn sau đây của một thực đơn trong ngày:
    {meal_text}

    Hãy bóc tách thành một danh sách nguyên liệu thô (grocery list) cần đi chợ để nấu các món này.
    - Gộp các nguyên liệu trùng nhau (ví dụ: 2 món đều dùng cà chua thì cộng dồn khối lượng).
    - Ước lượng định lượng (g, ml, quả, củ...) tương đối hợp lý dựa trên tổng số gam của món.
    
    Trả về ĐÚNG định dạng JSON sau (không giải thích thêm, không dùng markdown block):
    [
      {{"item": "Ức gà", "qty": "300g"}},
      {{"item": "Gạo tẻ", "qty": "150g"}},
      {{"item": "Cà chua", "qty": "2 quả"}}
    ]
    """
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt
        )
        raw_text = response.text.strip()
        if raw_text.startswith("```json"): raw_text = raw_text[7:-3]
        elif raw_text.startswith("```"): raw_text = raw_text[3:-3]
        
        grocery_list = json.loads(raw_text.strip())
        return {"status": "success", "list": grocery_list}
    except Exception as e:
        return {"status": "error", "message": str(e)}