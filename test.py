# # from google import genai
# # import os
# # from dotenv import load_dotenv

# # load_dotenv()
# # api_key = os.getenv("GEMINI_API_KEY")

# # client = genai.Client(api_key=api_key)

# # print("Đang lấy danh sách model mà API Key của bạn có thể truy cập...")
# # for model in client.models.list():
# #     if 'generateContent' in str(model.supported_actions):
# #         print(model.name)
# # print("test thử xem như nào")
# # 1. Import và kết nối (Code em copy từ Roboflow)
# from inference_sdk import InferenceHTTPClient

# client = InferenceHTTPClient(
#     api_url="https://detect.roboflow.com", # Hoặc serverless URL của em
#     api_key="API_KEY_CUA_EM"
# )

# # 2. Gọi API nhận diện ảnh
# # Thay "duong_dan_anh.jpg" bằng file ảnh tải lên từ máy hoặc URL ảnh
# result = client.infer("duong_dan_anh.jpg", model_id="vietnamese-food-yolo-es0vg/1")

# # ==========================================
# # 3. ĐOẠN CODE LẤY TÊN MÓN ĂN
# # ==========================================
# predictions = result.get("predictions", []) # Lấy danh sách kết quả

# danh_sach_mon_an = []

# if len(predictions) > 0:
#     print("AI Vision đã nhận diện được:")
#     for pred in predictions:
#         ten_mon = pred["class"]               # <--- TÊN MÓN ĂN NẰM Ở ĐÂY
#         do_tin_cay = pred["confidence"]       # Tỷ lệ % chắc chắn của AI
        
#         # Chỉ lấy những dự đoán có độ tin cậy > 0.5 (50%) theo đúng kiến trúc của em
#         if do_tin_cay > 0.5:
#             danh_sach_mon_an.append(ten_mon)
#             print(f"- {ten_mon} (Độ tin cậy: {do_tin_cay*100:.1f}%)")
    
#     # Bước tiếp theo của Backend: 
#     # Em dùng biến 'danh_sach_mon_an' (VD: ['Pho', 'Nem chua']) 
#     # để query vào database SQL lấy thông số Calo, Protein, Carbs...
    
# else:
#     print("YOLO không nhận diện được món nào.")
#     # CODE LOGIC CỦA EM Ở ĐÂY: Nếu rỗng, kích hoạt cơ chế Fallback gọi Google Gemini API!
from modulefinder import test


print:"Đang test thử xem như nào" 
print:"test lần 1" 
print:"test lần 2" 
print:"test lần 3"
print:"test lần 4"
print:"test lần 5"
print:"test lần 6"
print:"test lần 7"
print:"test lần 8"
print:"test lần 9"
print:"tlần 10"
