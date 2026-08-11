import json
import os
import unicodedata
from inference_sdk import InferenceHTTPClient
from google import genai
from google.genai import types
from dotenv import load_dotenv
import re
 
 
def safe_json_parse(text):
    text = text.strip()
    # Bỏ dấu markdown code fence nếu Gemini lỡ thêm vào
    text = re.sub(r'^```json\s*|\s*```$', '', text.strip(), flags=re.MULTILINE)
    # Chỉ lấy đúng khối {...} đầu tiên, bỏ qua mọi ký tự thừa trước/sau
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)
 
 
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
roboflow_key = os.getenv("ROBOFLOW_API_KEY")
 
# Client Gemini (dự phòng / phân tích chi tiết)
gemini_client = genai.Client(api_key=gemini_key) if gemini_key and gemini_key != 'your_api_key_here' else None
 
# Client Roboflow (model YOLO tự train)
roboflow_client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=roboflow_key
) if roboflow_key else None
 
MODEL_ID = "vietnamese-food-flf5p/1"   # đổi đúng theo project của em nếu khác
CONFIDENCE_THRESHOLD = 0.5   # dưới ngưỡng này thì chuyển sang hỏi Gemini
 
# Bảng tra dinh dưỡng ước lượng cho 35 món model YOLO đã học (calo/protein/carb/fat cho 1 phần ăn)
NUTRITION_LOOKUP = {
    "sup cua": {"calories": 200, "protein": 15, "carbs": 20, "fat": 5},
    "bun ngan": {"calories": 450, "protein": 25, "carbs": 50, "fat": 15},
    "banh flan": {"calories": 150, "protein": 5, "carbs": 20, "fat": 5},
    "com chien": {"calories": 550, "protein": 15, "carbs": 70, "fat": 20},
    "cha gio": {"calories": 100, "protein": 4, "carbs": 10, "fat": 6},
    "bun dau mam tom": {"calories": 650, "protein": 30, "carbs": 60, "fat": 30},
    "xoi xeo": {"calories": 450, "protein": 12, "carbs": 60, "fat": 15},
    "banh can": {"calories": 200, "protein": 8, "carbs": 25, "fat": 5},
    "ca kho": {"calories": 300, "protein": 25, "carbs": 10, "fat": 18},
    "cao lau": {"calories": 400, "protein": 20, "carbs": 55, "fat": 10},
    "banh duc": {"calories": 150, "protein": 5, "carbs": 25, "fat": 3},
    "bun mam": {"calories": 500, "protein": 25, "carbs": 60, "fat": 15},
    "banh pia": {"calories": 300, "protein": 6, "carbs": 40, "fat": 12},
    "banh bot loc": {"calories": 180, "protein": 8, "carbs": 25, "fat": 5},
    "banh gio": {"calories": 250, "protein": 10, "carbs": 25, "fat": 12},
    "banh canh": {"calories": 400, "protein": 15, "carbs": 55, "fat": 10},
    "pho": {"calories": 450, "protein": 25, "carbs": 60, "fat": 10},
    "nem chua": {"calories": 50, "protein": 4, "carbs": 2, "fat": 2},
    "mi quang": {"calories": 480, "protein": 20, "carbs": 60, "fat": 14},
    "banh chung": {"calories": 600, "protein": 20, "carbs": 65, "fat": 25},
    "banh tet": {"calories": 600, "protein": 20, "carbs": 65, "fat": 25},
    "hu tieu": {"calories": 420, "protein": 18, "carbs": 55, "fat": 12},
    "banh trang nuong": {"calories": 250, "protein": 10, "carbs": 20, "fat": 15},
    "goi cuon": {"calories": 200, "protein": 12, "carbs": 25, "fat": 4},
    "banh khot": {"calories": 250, "protein": 10, "carbs": 30, "fat": 10},
    "canh chua": {"calories": 150, "protein": 10, "carbs": 15, "fat": 5},
    "banh mi": {"calories": 400, "protein": 15, "carbs": 50, "fat": 15},
    "com tam": {"calories": 650, "protein": 30, "carbs": 80, "fat": 20},
    "bun rieu": {"calories": 400, "protein": 20, "carbs": 50, "fat": 12},
    "bun thit nuong": {"calories": 550, "protein": 25, "carbs": 65, "fat": 22},
    "banh xeo": {"calories": 450, "protein": 12, "carbs": 40, "fat": 25},
    "chao long": {"calories": 450, "protein": 20, "carbs": 40, "fat": 20},
    "bun bo hue": {"calories": 500, "protein": 22, "carbs": 65, "fat": 15},
    "banh uot": {"calories": 350, "protein": 10, "carbs": 45, "fat": 10},
    "banh beo": {"calories": 250, "protein": 8, "carbs": 40, "fat": 5},
}
 
 
def bo_dau(text):
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.lower().replace('-', ' ').replace('_', ' ').strip()
 
 
def _num(value, default=0):
    """Ép số an toàn (int/float) từ JSON AI."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
 
 
def normalize_analysis(raw):
    """
    Chuẩn hóa kết quả phân tích ảnh về 1 cấu trúc thống nhất:
    {
      dish_name, calories, protein, carbs, fat, description,
      items: [{ name, quantity, unit, cooking_method, portion_note,
                calories_per_unit, calories, protein, carbs, fat }]
    }
    """
    if not isinstance(raw, dict):
        return {
            "dish_name": "Không xác định",
            "calories": 0, "protein": 0, "carbs": 0, "fat": 0,
            "description": "Không đọc được kết quả phân tích.",
            "items": []
        }
 
    items_raw = raw.get("items") or raw.get("dishes") or raw.get("foods") or []
    items = []
    for it in items_raw:
        if not isinstance(it, dict):
            continue
        qty = max(1, int(_num(it.get("quantity"), 1) or 1))
        cal = _num(it.get("calories"))
        cal_per = _num(it.get("calories_per_unit"))
        if cal_per <= 0 and qty > 0 and cal > 0:
            cal_per = round(cal / qty, 1)
        if cal <= 0 and cal_per > 0:
            cal = round(cal_per * qty, 1)
 
        name = (it.get("name") or it.get("dish_name") or "Món ăn").strip()
        cooking = (it.get("cooking_method") or it.get("method") or "").strip()
        # Gộp tên + cách chế biến nếu name chưa có (vd: "Cá" + "kho" -> hiển thị rõ)
        display_name = name
        if cooking and cooking.lower() not in name.lower():
            display_name = f"{name} ({cooking})"
 
        items.append({
            "name": display_name,
            "base_name": name,
            "quantity": qty,
            "unit": (it.get("unit") or "phần").strip() or "phần",
            "cooking_method": cooking,
            "portion_note": (it.get("portion_note") or it.get("note") or "").strip(),
            "calories_per_unit": round(cal_per, 1),
            "calories": round(cal, 1),
            "protein": round(_num(it.get("protein")), 1),
            "carbs": round(_num(it.get("carbs")), 1),
            "fat": round(_num(it.get("fat")), 1),
        })
 
    # Tổng từ items nếu có; nếu không thì lấy từ root
    if items:
        total_cal = round(sum(i["calories"] for i in items), 1)
        total_p = round(sum(i["protein"] for i in items), 1)
        total_c = round(sum(i["carbs"] for i in items), 1)
        total_f = round(sum(i["fat"] for i in items), 1)
        dish_name = (raw.get("dish_name") or "").strip()
        if not dish_name or dish_name == "Tên món ăn":
            dish_name = ", ".join(i["name"] for i in items[:5])
            if len(items) > 5:
                dish_name += f" (+{len(items) - 5} món)"
    else:
        total_cal = round(_num(raw.get("calories")), 1)
        total_p = round(_num(raw.get("protein")), 1)
        total_c = round(_num(raw.get("carbs")), 1)
        total_f = round(_num(raw.get("fat")), 1)
        dish_name = (raw.get("dish_name") or "Không xác định").strip()
        # Tạo 1 item tổng nếu không có breakdown
        if dish_name and dish_name != "Không phải thức ăn" and total_cal > 0:
            items = [{
                "name": dish_name,
                "base_name": dish_name,
                "quantity": 1,
                "unit": "phần",
                "cooking_method": "",
                "portion_note": "",
                "calories_per_unit": total_cal,
                "calories": total_cal,
                "protein": total_p,
                "carbs": total_c,
                "fat": total_f,
            }]
 
    # Ưu tiên tổng root nếu AI đã tính (và items rỗng đã xử lý ở trên)
    if not items:
        total_cal = round(_num(raw.get("calories")), 1)
        total_p = round(_num(raw.get("protein")), 1)
        total_c = round(_num(raw.get("carbs")), 1)
        total_f = round(_num(raw.get("fat")), 1)
 
    return {
        "dish_name": dish_name or "Không xác định",
        "calories": total_cal if items else round(_num(raw.get("calories")), 1),
        "protein": total_p if items else round(_num(raw.get("protein")), 1),
        "carbs": total_c if items else round(_num(raw.get("carbs")), 1),
        "fat": total_f if items else round(_num(raw.get("fat")), 1),
        "description": (raw.get("description") or "").strip(),
        "items": items,
    }
 
 
def predict_with_yolo(image_bytes):
    temp_path = "temp_upload.jpg"
    with open(temp_path, "wb") as f:
        f.write(image_bytes)
    try:
        # Cập nhật dùng API run_workflow mới
        result = roboflow_client.run_workflow(
            workspace_name="tien-anh-vu-5dm0q",
            workflow_id="vietnamese-food-yolo-vvietnamese-food-yolo-es0vg-1-yolo11n-t1-logic",
            images={
                "image": temp_path
            },
            use_cache=True
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
 
    # Phân tích kết quả từ Workflow (cấu trúc có thể nằm lồng bên trong dict trả về)
    raw_predictions = []
    if isinstance(result, list) and len(result) > 0:
        result = result[0]
        
    if isinstance(result, dict):
        if "predictions" in result:
            raw_predictions = result["predictions"]
        else:
            # Tìm key chứa predictions trong workflow output
            for k, v in result.items():
                if isinstance(v, dict) and "predictions" in v:
                    raw_predictions.extend(v["predictions"])
                elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and "confidence" in v[0]:
                    raw_predictions.extend(v)

    predictions = [p for p in raw_predictions if p.get("confidence", 0) >= CONFIDENCE_THRESHOLD]
    if not predictions:
        return None   # không món nào đủ tin cậy -> rơi xuống Gemini
 
    # Gộp theo class: nếu detect 2 bánh mì thì quantity=2
    grouped = {}
    for p in predictions:
        key = p["class"]
        if key not in grouped:
            grouped[key] = {"count": 0, "conf_sum": 0.0}
        grouped[key]["count"] += 1
        grouped[key]["conf_sum"] += p["confidence"]
 
    items = []
    total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    for class_name, info in grouped.items():
        qty = info["count"]
        n = NUTRITION_LOOKUP.get(bo_dau(class_name), {"calories": 0, "protein": 0, "carbs": 0, "fat": 0})
        cal_per = n["calories"]
        items.append({
            "name": class_name,
            "base_name": class_name,
            "quantity": qty,
            "unit": "phần",
            "cooking_method": "",
            "portion_note": f"Độ tin cậy TB: {info['conf_sum'] / qty:.0%}",
            "calories_per_unit": cal_per,
            "calories": cal_per * qty,
            "protein": n["protein"] * qty,
            "carbs": n["carbs"] * qty,
            "fat": n["fat"] * qty,
        })
        total["calories"] += cal_per * qty
        total["protein"] += n["protein"] * qty
        total["carbs"] += n["carbs"] * qty
        total["fat"] += n["fat"] * qty
 
    analysis = {
        "dish_name": ", ".join(
            f"{i['name']}" + (f" x{i['quantity']}" if i["quantity"] > 1 else "")
            for i in items
        ),
        **total,
        "description": f"Nhận diện {sum(i['quantity'] for i in items)} phần bằng YOLOv8 tự train. "
                       f"Chi tiết từng món bên dưới (ước lượng theo phần chuẩn).",
        "items": items,
    }
 
    return {
        "detections": predictions,
        "analysis": analysis,
        "message": "Đã phân tích xong bằng YOLO!"
    }
 
 
DETAILED_FOOD_PROMPT = """
Bạn là chuyên gia dinh dưỡng Việt Nam. Hãy phân tích ẢNH MÓN ĂN một cách CỰC KỲ CHI TIẾT.
 
## Nhiệm vụ bắt buộc
1. Tách TỪNG MÓN / TỪNG THÀNH PHẦN trên mâm/đĩa/khay (không gộp cả mâm thành 1 món).
   Ví dụ mâm có: cơm trắng, canh rau, cá kho, thịt heo luộc → phải liệt kê 4 mục riêng.
 
2. ĐẾM SỐ LƯỢNG rõ ràng:
   - 2 con cá → quantity = 2, unit = "con", calories_per_unit = calo 1 con, calories = tổng 2 con.
   - 3 miếng thịt → quantity = 3, unit = "miếng".
   - 1 chén cơm → quantity = 1, unit = "chén".
   - 1 tô canh → quantity = 1, unit = "tô".
 
3. Xác định CÁCH CHẾ BIẾN (cooking_method) vì calo khác nhau rất nhiều:
   - Cá: kho / chiên / nướng / luộc / hấp / rim / sốt cà...
   - Thịt: kho / luộc / nướng / chiên / xào / rang...
   - Rau: luộc / xào / gỏi / canh...
   - Ghi rõ trong name, ví dụ: "Cá lóc kho tộ", "Thịt heo luộc", "Cá basa chiên".
 
4. Ước lượng khẩu phần thực tế trong ảnh (portion_note): khoảng bao nhiêu gram / phần.
 
5. Ước lượng dinh dưỡng từng mục: calories, protein, carbs, fat (gram).
   - calories_per_unit: calo của 1 đơn vị (1 con cá, 1 miếng thịt...).
   - calories: tổng = calories_per_unit × quantity.
   - Cộng dồn chính xác vào tổng root.
 
6. Nếu ảnh KHÔNG phải thức ăn, trả về đúng JSON:
   {"dish_name":"Không phải thức ăn","calories":0,"protein":0,"carbs":0,"fat":0,"description":"Vui lòng tải ảnh thức ăn.","items":[]}
 
## Format JSON (DUY NHẤT, không markdown, không giải thích ngoài JSON)
{
  "dish_name": "Tóm tắt mâm ăn, ví dụ: Cơm trắng + Canh rau + Cá kho + Thịt luộc",
  "calories": 0,
  "protein": 0,
  "carbs": 0,
  "fat": 0,
  "description": "1-2 câu nhận xét tổng quan (cách chế biến nổi bật, độ dầu mỡ...)",
  "items": [
    {
      "name": "Cá lóc kho tộ",
      "quantity": 2,
      "unit": "con",
      "cooking_method": "kho",
      "portion_note": "mỗi con khoảng 120g (kèm nước kho)",
      "calories_per_unit": 185,
      "calories": 370,
      "protein": 36,
      "carbs": 6,
      "fat": 20
    },
    {
      "name": "Thịt heo luộc",
      "quantity": 3,
      "unit": "miếng",
      "cooking_method": "luộc",
      "portion_note": "mỗi miếng khoảng 40g",
      "calories_per_unit": 95,
      "calories": 285,
      "protein": 24,
      "carbs": 0,
      "fat": 20
    },
    {
      "name": "Cơm trắng",
      "quantity": 1,
      "unit": "chén",
      "cooking_method": "nấu",
      "portion_note": "khoảng 150g",
      "calories_per_unit": 200,
      "calories": 200,
      "protein": 4,
      "carbs": 44,
      "fat": 0.5
    }
  ]
}
 
## Lưu ý quan trọng
- Ưu tiên tên tiếng Việt.
- Phân biệt rõ: cá kho (nhiều calo/mỡ hơn) vs cá luộc/hấp (ít calo hơn); thịt chiên vs thịt luộc.
- Không bỏ sót món phụ: dưa leo, trứng, đậu hũ, nước chấm (nếu rõ lượng), rau sống...
- calories/protein/carbs/fat ở root = TỔNG tất cả items.
- Chỉ trả về JSON hợp lệ.
"""
 
 
def predict_with_gemini(image_bytes):
    if not gemini_client:
        return {"error": "Chưa cấu hình GEMINI_API_KEY trong file .env."}
    import time
    for attempt in range(3):
        try:
            response = gemini_client.models.generate_content(
                model="gemini-flash-latest",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    DETAILED_FOOD_PROMPT,
                ],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            result = safe_json_parse(response.text)
            analysis = normalize_analysis(result)
            return {
                "detections": [],
                "analysis": analysis,
                "message": "Đã phân tích chi tiết từng món bằng Gemini!"
            }
        except Exception as e:
            print(f"Loi Gemini Vision (lan {attempt + 1}): {e}")
            if attempt == 2:
                return {"error": f"Hệ thống AI đang quá tải hoặc hết lượt (Quota). Vui lòng thử lại sau! Chi tiết: {str(e)}"}
            time.sleep(2)
 
 
def predict_image(image_bytes):
    # Ưu tiên model tự train trước (nhanh, 5 class đã học)
    if roboflow_client:
        try:
            yolo_result = predict_with_yolo(image_bytes)
            if yolo_result:
                return yolo_result
        except Exception as e:
            print(f"Loi YOLO, chuyen sang Gemini: {e}")
 
    # Không nhận diện được / lỗi -> dùng Gemini (phân tích chi tiết mâm ăn)
    return predict_with_gemini(image_bytes)