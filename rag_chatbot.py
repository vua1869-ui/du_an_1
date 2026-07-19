from google import genai
import sqlite3
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import chromadb

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# 1. Khởi tạo Gemini Client (Dùng để sinh câu trả lời)
if api_key and api_key != 'your_api_key_here':
    client = genai.Client(api_key=api_key)
else:
    client = None

# 2. Khởi tạo Model Embedding (Chuyển chữ thành Vector)
# Dùng model multilingual để hiểu tiếng Việt
print("Đang tải model Embedding...")
embed_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# 3. Khởi tạo ChromaDB (Vector Database lưu trữ)
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="food_database")

def init_vector_db():
    """Hàm này dùng để nạp dữ liệu từ SQLite vào ChromaDB (Chỉ chạy 1 lần khi cần)"""
    conn = sqlite3.connect('balance_nutrition.db')
    c = conn.cursor()
    c.execute('SELECT name, calories, protein, carbs, fat FROM foods')
    foods = c.fetchall()
    conn.close()
    
    # Nếu DB đã có dữ liệu thì không cần thêm lại
    if collection.count() == 0 and len(foods) > 0:
        print("Đang tạo Vector Database cho đồ ăn...")
        documents = []
        metadatas = []
        ids = []
        
        for i, food in enumerate(foods):
            name, cals, pro, carbs, fat = food
            # Tạo 1 câu mô tả để AI dễ hiểu ngữ nghĩa
            doc_text = f"{name} chứa {cals} calo, {pro}g protein, {carbs}g carbs, {fat}g chất béo."
            documents.append(doc_text)
            metadatas.append({"name": name, "calories": cals, "protein": pro, "carbs": carbs, "fat": fat})
            ids.append(f"food_{i}")
            
        # Thêm vào ChromaDB
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Đã nạp {len(foods)} món ăn vào Vector DB.")

def retrieve_nutrition_data_vector(user_message):
    """Hàm tìm kiếm bằng Vector (Semantic Search)"""
    if collection.count() == 0:
        init_vector_db()
        
    # Query ChromaDB (Tìm top 3 món ăn có ngữ nghĩa gần nhất)
    results = collection.query(
        query_texts=[user_message],
        n_results=3
    )
    
    context = ""
    for i in range(len(results['documents'][0])):
        meta = results['metadatas'][0][i]
        context += f"- {meta['name']} | Calo: {meta['calories']} | Protein: {meta['protein']}g | Carbs: {meta['carbs']}g | Fat: {meta['fat']}g\n"
    
    return context

def get_chatbot_response(user_message):
    if not client:
        return "Lỗi: Chưa cấu hình GEMINI_API_KEY trong file .env."

    # Gọi hàm tìm kiếm Vector
    retrieved_context = retrieve_nutrition_data_vector(user_message)
    
    prompt = f"""
    Bạn là một chuyên gia dinh dưỡng thông minh và thân thiện.
    Nhiệm vụ của bạn là tư vấn dinh dưỡng dựa trên câu hỏi của người dùng.

    Dưới đây là dữ liệu thức ăn được truy xuất từ Cơ sở dữ liệu Vector (RAG) (nếu có):
    {retrieved_context if retrieved_context else "(Không tìm thấy dữ liệu liên quan trong DB, hãy dùng kiến thức chung của bạn)"}

    Yêu cầu:
    1. Nếu có dữ liệu DB, hãy ưu tiên sử dụng chính xác số liệu đó để trả lời.
    2. Trả lời ngắn gọn, súc tích và dễ hiểu.
    3. Nếu người dùng hỏi về lượng calo hoặc dinh dưỡng, hãy liệt kê rõ ràng các chỉ số (Protein, Carbs, Fat).
    
    Câu hỏi của người dùng: "{user_message}"
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest", 
            contents=prompt
        )                
        return response.text
    except Exception as e:
        return f"Lỗi AI: {str(e)}"