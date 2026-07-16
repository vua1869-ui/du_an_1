import google.generativeai as genai
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if api_key and api_key != 'your_api_key_here':
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

def retrieve_nutrition_data(query_keywords):
    conn = sqlite3.connect('balance_nutrition.db')
    c = conn.cursor()
    search_query = f"%{query_keywords}%"
    c.execute('SELECT name, calories, protein, carbs, fat FROM foods WHERE name LIKE ? LIMIT 5', (search_query,))
    results = c.fetchall()
    conn.close()
    
    context = ""
    for r in results:
        context += f"- {r[0]} | Calo: {r[1]} | Protein: {r[2]}g\n"
    return context

def get_chatbot_response(user_message):
    if not model:
        return "Lỗi: Chưa cấu hình GEMINI_API_KEY trong file .env."

    keywords = user_message.split()[0]
    retrieved_context = retrieve_nutrition_data(keywords)
    
    prompt = f"""
    Bạn là chuyên gia dinh dưỡng. Hãy trả lời câu hỏi của người dùng.
    Nếu người dùng hỏi về món ăn, hãy ưu tiên dùng dữ liệu thực tế sau từ CSDL:
    {retrieved_context if retrieved_context else "Không tìm thấy trong DB, hãy dùng kiến thức chung."}
    
    Người dùng: {user_message}
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Lỗi AI: {str(e)}"