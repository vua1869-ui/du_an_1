# import google.generativeai as genai
# import os
# from dotenv import load_dotenv

# load_dotenv()
# api_key = os.getenv("GEMINI_API_KEY")

# genai.configure(api_key=api_key)

# print("Đang lấy danh sách model mà API Key của bạn có thể truy cập...")
# for m in genai.list_models():
#     # Chỉ in ra các model hỗ trợ generateContent (sinh văn bản)
#     if 'generateContent' in m.name:
#         print(m.name)