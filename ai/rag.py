from google import genai
import sqlite3
import os
import re
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import chromadb
from services.diet_service import get_diet_plan

load_dotenv(override=True)
api_key = os.getenv("GEMINI_API_KEY")

client = None

def get_client():
    global client
    load_dotenv(override=True)
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key and key != 'your_api_key_here':
        if not client or getattr(client, '_api_key', None) != key:
            try:
                client = genai.Client(api_key=key)
                client._api_key = key
            except Exception as e:
                print(f"Lỗi khởi tạo Gemini Client: {e}")
                client = None
    return client

# Khởi tạo lần đầu nếu đã có key
get_client()

# 2. Khởi tạo Model Embedding
print("Đang tải model Embedding...")
embed_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# 3. Khởi tạo ChromaDB
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="food_database")

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
    db_path = os.path.join('data', 'balance_nutrition.db')
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
    if collection.count() == 0:
        # Đường dẫn dự phòng nếu chưa có data
        db_path = os.path.join('data', 'balance_nutrition.db')
        init_vector_db(db_path)

    results = collection.query(
        query_texts=[user_message],
        n_results=3
    )

    context = ""
    for i in range(len(results['documents'][0])):
        meta = results['metadatas'][0][i]
        context += f"- {meta['name']} | Calo: {meta['calories']} | Protein: {meta['protein']}g | Carbs: {meta['carbs']}g | Fat: {meta['fat']}g\n"

    return context

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

def get_chatbot_response(user_message, current_tdee=2000, profile=None):
    current_client = get_client()
    if not current_client:
        return {
            "response": "Lỗi: Chưa cấu hình hoặc chưa lưu GEMINI_API_KEY trong file .env (Hãy mở file .env, điền key và nhấn Cmd+S / Ctrl+S để lưu).",
            "type": "chat",
            "tdee": None,
            "goal": None,
            "diet": None,
        }

    # if is_diet_request(user_message):
    #     if not profile or not profile.get('weight') or not profile.get('height'):
    #         return {
    #             "response": "Để lập thực đơn chính xác, mình cần biết thêm vài thông tin về bạn trước đã 👇",
    #             "type": "clarify",
    #             "tdee": None, "goal": None, "diet": None,
    #         }
    #     tdee = extract_tdee(user_message, default=current_tdee or 2000)
    #     goal = extract_goal(user_message)
    #     diet = get_diet_plan(tdee, goal)
    # 
    #     if diet.get("error"):
    #         return {
    #             "response": f"Xin lỗi, không lập được thực đơn: {diet['error']}",
    #             "type": "chat",
    #             "tdee": tdee,
    #             "goal": goal,
    #             "diet": None,
    #         }
    # 
    #     explanation = build_diet_summary(diet, goal)
    #     try:
    #         prompt = f"""
    #         Bạn là chuyên gia dinh dưỡng. Người dùng vừa hỏi: "{user_message}"
    #         Hệ thống đã lập thực đơn với TDEE={tdee} kcal, mục tiêu={goal}.
    #         Tổng calo: {diet.get('total_calories')}.
    #         Sáng: {diet['meals']['breakfast']['name']} ({diet['meals']['breakfast']['cals']} kcal)
    #         Trưa: {diet['meals']['lunch']['name']} ({diet['meals']['lunch']['cals']} kcal)
    #         Tối: {diet['meals']['dinner']['name']} ({diet['meals']['dinner']['cals']} kcal)
    # 
    #         Hãy viết 2-3 câu thân thiện:
    #         1) Xác nhận đã hiểu mục tiêu của họ
    #         2) Giải thích ngắn vì sao mức calo/mục tiêu này hợp lý
    #         3) Khuyến khích xem thực đơn bên dưới
    #         Không liệt kê lại chi tiết món (đã có sẵn trong UI). Trả lời tiếng Việt.
    #         """
    #         ai_text = client.models.generate_content(
    #             model="gemini-3.6-flash",
    #             contents=prompt,
    #         ).text
    #         explanation = (ai_text or "").strip() + "\n\n" + build_diet_summary(diet, goal)
    #     except Exception:
    #         pass
    # 
    #     return {
    #         "response": explanation,
    #         "type": "diet",
    #         "tdee": tdee,
    #         "goal": goal,
    #         "diet": diet,
    #     }

    retrieved_context = retrieve_nutrition_data_vector(user_message)

    prompt = f"""
    Bạn là một chuyên gia dinh dưỡng thông minh và thân thiện.
    Nhiệm vụ của bạn là tư vấn dinh dưỡng dựa trên câu hỏi của người dùng.

    Dưới đây là dữ liệu thức ăn được truy xuất từ Cơ sở dữ liệu Vector (RAG) (nếu có):
    {retrieved_context if retrieved_context else "(Không tìm thấy dữ liệu liên quan trong DB, hãy dùng kiến thức chung của bạn)"}

    Yêu cầu:
    1. Nếu có dữ liệu DB, hãy ưu tiên sử dụng chính xác số liệu đó để trả lời.
    2. Trả lời ngắn gọn, súc tích và dễ hiểu.
    3. Nếu người dùng hỏi "lập thực đơn", BẮT BUỘC trả lời yêu cầu họ cung cấp các nguyên liệu họ đang có hôm nay để bạn có thể lập thực đơn. TUYỆT ĐỐI KHÔNG bắt người dùng nhập thông tin chiều cao, cân nặng, mục tiêu (vì hệ thống đã lưu lúc đăng nhập).
    4. Nếu họ đã cung cấp nguyên liệu, hãy lập một thực đơn 1 ngày chi tiết (Sáng, Trưa, Tối) dựa trên những nguyên liệu đó.

    Câu hỏi của người dùng: "{user_message}"
    """

    import time
    for attempt in range(3):
        try:
            response = current_client.models.generate_content(
                model="gemini-3.6-flash",
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