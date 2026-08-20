from google import genai
import sqlite3
import os
import re
from dotenv import load_dotenv
from services.diet_service import get_diet_plan

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# 1. Khởi tạo Gemini Client
if api_key and api_key != 'your_api_key_here':
    client = genai.Client(api_key=api_key)
else:
    client = None


def get_client():
    return client

# 2. Embedding model (optional — không bắt buộc để chạy app)
embed_model = None
try:
    from sentence_transformers import SentenceTransformer
    print("Đang tải model Embedding...")
    embed_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
except Exception as e:
    print(f"[WARN] sentence_transformers không khả dụng: {e}")

# 3. ChromaDB (optional)
collection = None
try:
    import chromadb
    chroma_client = chromadb.Client()
    collection = chroma_client.get_or_create_collection(name="food_database")
except Exception as e:
    print(f"[WARN] ChromaDB không khả dụng: {e}")

DIET_KEYWORDS = [
    "tdee", "thực đơn", "thuc don", "lập thực đơn", "lap thuc don",
    "gợi ý món", "goi y mon", "kế hoạch ăn", "ke hoach an",
    "giảm cân", "giam can", "tăng cân", "tang can", "duy trì", "duy tri",
    "calo mục tiêu", "mục tiêu calo", "ăn bao nhiêu", "an bao nhieu",
    "menu", "meal plan", "diet plan", "lượng calo cần", "nhu cầu calo",
    "tính calo", "tinh calo", "lượng calo trong ngày", "lập menu",
]

def init_vector_db(db_path):
    """Hàm này dùng để nạp dữ liệu từ SQLite vào ChromaDB"""
    if collection is None:
        return
    db_path = os.path.join('data', 'balance_nutrition.db')
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # THÊM id VÀO CÂU TRUY VẤN
    c.execute('SELECT id, name, calories, protein, carbs, fat FROM foods')
    foods = c.fetchall()
    conn.close()

    if collection.count() == 0 and len(foods) > 0:
        print("Đang tạo Vector Database cho đồ ăn...")
        documents = []
        metadatas = []
        ids = []

        for food in foods:
            fid, name, cals, pro, carbs, fat = food # Đọc id (fid)
            doc_text = f"{name} chứa {cals} calo, {pro}g protein, {carbs}g carbs, {fat}g chất béo."
            documents.append(doc_text)
            metadatas.append({"name": name, "calories": cals, "protein": pro, "carbs": carbs, "fat": fat})
            ids.append(f"food_{fid}") # ĐẶT ID ĐỒNG BỘ VỚI SQLITE

        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Đã nạp {len(foods)} món ăn vào Vector DB.")

def retrieve_nutrition_data_vector(user_message):
    if collection is None:
        return ""
    try:
        if collection.count() == 0:
            db_path = os.path.join('data', 'balance_nutrition.db')
            init_vector_db(db_path)
        if collection.count() == 0:
            return ""
        results = collection.query(query_texts=[user_message], n_results=3)
        context = ""
        for i in range(len(results['documents'][0])):
            meta = results['metadatas'][0][i]
            context += f"- {meta['name']} | Calo: {meta['calories']} | Protein: {meta['protein']}g | Carbs: {meta['carbs']}g | Fat: {meta['fat']}g\n"
        return context
    except Exception as e:
        print(f"[WARN] RAG query lỗi: {e}")
        return ""

def is_diet_request(user_message: str) -> bool:
    msg = user_message.lower()
    return any(kw in msg for kw in DIET_KEYWORDS)

def extract_goal(user_message: str) -> str:
    msg = user_message.lower()
    if any(k in msg for k in ["giảm cân", "giam can", "giảm mỡ", "giam mo", "cut", "lose weight"]):
        return "giam_can"
    if any(k in msg for k in ["tăng cân", "tang can", "bulk", "tăng cơ", "tang co", "gain weight"]):
        return "tang_can"
    return "duy_tri"

def extract_tdee(user_message: str, default: int = 2000) -> int:
    msg = user_message.lower()
    patterns = [
        r"tdee\s*[:=]?\s*(\d{3,5})",
        r"(\d{3,5})\s*(?:kcal|calo|calories?)",
        r"(?:mục tiêu|muc tieu|cần|can|khoảng|khoang)\s*(\d{3,5})",
        r"(\d{3,5})",
    ]
    for pattern in patterns:
        match = re.search(pattern, msg)
        if match:
            value = int(match.group(1))
            if 800 <= value <= 6000:
                return value
    return default

def build_diet_summary(diet: dict, goal: str) -> str:
    goal_labels = {
        "giam_can": "Giảm cân",
        "tang_can": "Tăng cân",
        "duy_tri": "Duy trì / Tăng cơ",
    }
    meals = diet.get("meals", {})
    icons = {"breakfast": "🌅 Sáng", "lunch": "☀️ Trưa", "dinner": "🌙 Tối"}

    lines = [
        f"Đã lập thực đơn theo TDEE **{diet.get('target_tdee')} kcal** — mục tiêu: **{goal_labels.get(goal, goal)}**.",
        f"Tổng calo gợi ý: **{diet.get('total_calories')} kcal** "
        f"(P: {diet.get('total_protein')}g · C: {diet.get('total_carbs')}g · F: {diet.get('total_fat')}g).",
        "",
        "Thực đơn đề xuất:",
    ]
    for key in ("breakfast", "lunch", "dinner"):
        meal = meals.get(key)
        if meal:
            lines.append(
                f"- {icons.get(key, key)}: {meal['name']} — {meal['cals']} kcal "
                f"({meal.get('grams', '?')}g)"
            )
    lines.append("")
    lines.append("Bạn có thể bấm **+ Thêm** trên từng món để đưa vào nhật ký, hoặc hỏi mình để chỉnh lại TDEE/mục tiêu.")
    return "\n".join(lines)

def get_chatbot_response(user_message, current_tdee=2000, profile=None, today_logs=None):
    if not client:
        return {
            "response": "Lỗi: Chưa cấu hình GEMINI_API_KEY trong file .env.",
            "type": "chat",
            "tdee": None,
            "goal": None,
            "diet": None,
        }

    retrieved_context = retrieve_nutrition_data_vector(user_message)
    
    # Chuẩn bị dữ liệu lịch sử ăn uống hôm nay (Idea 1)
    logs_context = ""
    if today_logs and today_logs.get('foods'):
        foods = today_logs['foods']
        totals = today_logs.get('totals', {})
        food_list = ", ".join([f"{f['name']} ({f['calories']} kcal)" for f in foods])
        logs_context = f"\n\nLỊCH SỬ ĂN UỐNG HÔM NAY CỦA USER:\n- Các món đã ăn (quét ảnh hoặc tự nhập): {food_list}\n- Tổng calo đã nạp: {totals.get('calories', 0)} kcal (P: {totals.get('protein', 0)}g, C: {totals.get('carbs', 0)}g, F: {totals.get('fat', 0)}g)\n- Mức TDEE: {current_tdee} kcal\n=> Dựa vào lịch sử này, hãy đưa ra lời khuyên thực tế. Ví dụ: Nếu họ hỏi tối nay ăn gì, hãy nhìn xem sáng/trưa họ đã ăn gì và nạp bao nhiêu calo để bù trừ cho hợp lý."

    prompt = f"""
    Bạn là một chuyên gia dinh dưỡng cực kỳ chi tiết và thông minh (NutriBot).
    Nhiệm vụ của bạn là tư vấn dinh dưỡng dựa trên câu hỏi của người dùng.

    Dưới đây là dữ liệu thức ăn được truy xuất từ Cơ sở dữ liệu Vector (RAG) (nếu có):
    {retrieved_context if retrieved_context else "(Không tìm thấy dữ liệu liên quan trong DB, hãy dùng kiến thức chung của bạn)"}
    {logs_context}

    **KỸ THUẬT PHÂN TÍCH (CHAIN OF THOUGHT) BẮT BUỘC KHI NGƯỜI DÙNG KỂ VỀ BỮA ĂN:**
    Nếu người dùng mô tả một bữa ăn (ví dụ: "Tối nay tôi ăn 2 con cá chiên và 1 chén cơm"), bạn PHẢI bóc tách cặn kẽ theo các bước sau trong suy nghĩ và thể hiện ra câu trả lời:
    1. **Đếm số lượng & Định lượng:** (Ví dụ: 2 con cá, 1 chén cơm).
    2. **Xác định phương pháp chế biến:** (Chiên, hấp, luộc, xào). Bắt buộc phải nói rõ phương pháp này ảnh hưởng thế nào đến calo (Ví dụ: cá chiên cộng thêm 150-200 calo từ dầu mỡ so với cá hấp).
    3. **Bóc tách từng món:** Phải gạch đầu dòng rõ ràng từng món, mỗi món bao nhiêu calo, bao nhiêu protein/carbs/fat nếu có thể.
    4. **Tổng kết & Đánh giá:** Cộng tổng calo của bữa ăn, so sánh với TDEE của họ và đưa ra lời khuyên.

    **YÊU CẦU CHUNG:**
    1. Nếu có dữ liệu DB, hãy ưu tiên sử dụng chính xác số liệu đó để trả lời.
    2. Nếu người dùng hỏi "lập thực đơn", BẮT BUỘC trả lời yêu cầu họ cung cấp các nguyên liệu họ đang có hôm nay. TUYỆT ĐỐI KHÔNG bắt người dùng nhập thông tin chiều cao, cân nặng, mục tiêu (vì hệ thống đã lưu).
    3. Nếu họ đã cung cấp nguyên liệu, hãy lập một thực đơn 1 ngày chi tiết (Sáng, Trưa, Tối) dựa trên những nguyên liệu đó.

    Câu hỏi của người dùng: "{user_message}"
    """

    import time
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            return {
                "response": response.text,
                "type": "chat",
                "tdee": None,
                "goal": None,
                "diet": None,
            }
        except Exception as e:
            if attempt == 2:
                return {
                    "response": f"Hệ thống AI đang quá tải (Lỗi 503), vui lòng chờ chút rồi thử lại nhé! Chi tiết: {str(e)}",
                    "type": "chat",
                    "tdee": None,
                    "goal": None,
                    "diet": None,
                }
            time.sleep(2)