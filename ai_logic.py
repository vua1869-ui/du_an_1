import json
import os
import unicodedata
from inference_sdk import InferenceHTTPClient
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
roboflow_key = os.getenv("ROBOFLOW_API_KEY")

# Client Gemini (dự phòng)
gemini_client = genai.Client(api_key=gemini_key) if gemini_key and gemini_key != 'your_api_key_here' else None

# Client Roboflow (model YOLO tự train)
roboflow_client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=roboflow_key
) if roboflow_key else None

MODEL_ID = "vietnamese-food-flf5p/1"   # đổi đúng theo project của em nếu khác

# Bảng tra dinh dưỡng ước lượng cho 5 món model đã học (calo/protein/carb/fat cho 1 phần ăn)
NUTRITION_LOOKUP = {
    "Bánh-Mì": {"calories": 400, "protein": 15, "carbs": 50, "fat": 15},
    "Bột Chiên": {"calories": 350, "protein": 8, "carbs": 40, "fat": 18},
    "Bún": {"calories": 380, "protein": 18, "carbs": 55, "fat": 8},
    "Gỏi-Cuốn": {"calories": 220, "protein": 12, "carbs": 25, "fat": 6},
    "Phở": {"calories": 450, "protein": 25, "carbs": 60, "fat": 10},
}
CONFIDENCE_THRESHOLD = 0.5   # dưới ngưỡng này thì chuyển sang hỏi Gemini

NUTRITION_LOOKUP = {
    "banh mi": {"calories": 400, "protein": 15, "carbs": 50, "fat": 15},
    "bot chien": {"calories": 350, "protein": 8, "carbs": 40, "fat": 18},
    "bun": {"calories": 380, "protein": 18, "carbs": 55, "fat": 8},
    "goi cuon": {"calories": 220, "protein": 12, "carbs": 25, "fat": 6},
    "pho": {"calories": 450, "protein": 25, "carbs": 60, "fat": 10},
}
def predict_with_yolo(image_bytes):
    temp_path = "temp_upload.jpg"
    with open(temp_path, "wb") as f:
        f.write(image_bytes)
    try:
        result = roboflow_client.infer(temp_path, model_id=MODEL_ID)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    predictions = [p for p in result.get("predictions", []) if p["confidence"] >= CONFIDENCE_THRESHOLD]
    if not predictions:
        return None   # không món nào đủ tin cậy -> rơi xuống Gemini

    items = []
    total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    for p in predictions:
        n = NUTRITION_LOOKUP.get(bo_dau(p["class"]), {"calories": 0, "protein": 0, "carbs": 0, "fat": 0})
        items.append({"name": p["class"], "confidence": p["confidence"], **n})
        for k in total: total[k] += n[k]

    return {
        "detections": predictions,
        "analysis": {
            "dish_name": ", ".join(i["name"] for i in items),
            **total,
            "description": f"Nhận diện {len(items)} món bằng YOLOv8 tự train."
        },
        "message": "Đã phân tích xong bằng YOLO!"
    }

def predict_with_gemini(image_bytes):
    if not gemini_client:
        return {"error": "Chưa cấu hình GEMINI_API_KEY trong file .env."}
    try:
        prompt = """
        Bạn là một chuyên gia dinh dưỡng. Hãy phân tích bức ảnh món ăn này.
        1. Xác định tên món ăn (ưu tiên tên tiếng Việt, ví dụ: Phở bò, Cơm tấm, Bún chả).
        2. Ước lượng tổng lượng calo cho 1 phần ăn trong ảnh.
        3. Ước lượng lượng Protein, Carbs, Fat (tính bằng gram).

        Trả về kết quả DUY NHẤT dưới dạng JSON có cấu trúc sau:
        {
          "dish_name": "Tên món ăn",
          "calories": 0,
          "protein": 0,
          "carbs": 0,
          "fat": 0,
          "description": "Mô tả ngắn gọn về món ăn (khoảng 1 câu)"
        }
        Nếu ảnh không phải là thức ăn, trả về: {"dish_name": "Không phải thức ăn", "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "description": "Vui lòng tải ảnh thức ăn."}
        """
        
        response = gemini_client.models.generate_content(
    model="gemini-flash-latest",
    contents=[types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), prompt],
    config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        result = json.loads(response.text)
        return {
            "detections": [],
            "analysis": result,
            "message": "Đã phân tích xong bằng Gemini (dự phòng)!"
        }
    except Exception as e:
        print(f"Lỗi Gemini Vision: {e}")
        return {"error": f"Lỗi khi phân tích ảnh bằng AI: {str(e)}"}

def predict_image(image_bytes):

    # Ưu tiên model tự train trước
    if roboflow_client:
        try:
            yolo_result = predict_with_yolo(image_bytes)
            if yolo_result:
                return yolo_result
        except Exception as e:
            print(f"Lỗi YOLO, chuyển sang Gemini: {e}")

    # Không nhận diện được / lỗi -> dùng Gemini dự phòng
    return predict_with_gemini(image_bytes)

def bo_dau(text):
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.lower().replace('-', ' ').replace('_', ' ').strip()

