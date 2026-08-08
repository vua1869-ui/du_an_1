# 🥑 NutritionAI - Trợ lý Dinh dưỡng Thông minh

NutritionAI là một ứng dụng Web SaaS toàn diện giúp người dùng quản lý sức khỏe, tính toán lượng Calo mục tiêu (BMR/TDEE) và theo dõi nhật ký ăn uống hằng ngày. Hệ thống kết hợp công nghệ Thị giác máy tính (YOLOv8) để bóc tách hình ảnh món ăn và Xử lý ngôn ngữ tự nhiên (Gemini 2.0) để tư vấn dinh dưỡng chuẩn y khoa.

## ✨ Tính năng nổi bật

- **Nhận diện Món ăn qua Ảnh**: Tích hợp YOLOv8 và Gemini Vision để nhận diện món ăn, tự động tính toán Calo và Macro (Đạm, Đường bột, Béo).
- **Onboarding Đa bước**: Thu thập hồ sơ thể chất (Chiều cao, Cân nặng, Cường độ vận động) để sinh lộ trình dinh dưỡng cá nhân hóa.
- **Trợ lý Ảo RAG 24/7**: Chatbot thông minh tự động đọc dữ liệu VectorDB (ChromaDB) để trả lời các câu hỏi về thực đơn và kiến thức sức khỏe.
- **Premium Dashboard**: Bảng điều khiển chuẩn Bento Grid với biểu đồ Chart.js mượt mà, theo dõi Calo, Nước uống và Tiến độ Cân nặng.
- **Gamification & Grocery List**: Tích hợp hệ thống Tủ huy hiệu thành tựu và khả năng bóc tách thực đơn thành danh sách đi siêu thị (xuất PDF).
- **Hệ thống Quản trị (Admin Panel)**: Phân quyền User/Admin, quản lý cơ sở dữ liệu món ăn và kiểm soát người dùng nền tảng.
- **Bảo mật Chuẩn mực**: Băm mật khẩu (Bcrypt), Middleware phân quyền Session, chống SQL Injection và XSS Sanitization.

## 🛠 Tech Stack (Công nghệ sử dụng)

- **Backend**: Python 3.11, Flask, SQLite3.
- **Frontend**: HTML5, Vanilla JS, Tailwind CSS, Chart.js.
- **AI / ML Engine**: 
  - Google Gemini 2.0 Flash (Generative AI & Text-to-text).
  - Roboflow / Ultralytics YOLOv8 (Computer Vision).
  - ChromaDB (Vector Database cho RAG).
- **Bảo mật**: `flask-bcrypt`, `email-validator`, Parameterized Queries.

## 📂 Cấu trúc Dự án

```text
du_an_1/
├── app.py                  # Entry point của ứng dụng (Flask Router)
├── core/                   # Chứa logic AI (YOLO Vision, Gemini RAG Chatbot)
├── database/               # Khởi tạo SQLite và DB Connection
├── services/               # Chứa Business Logic (Auth, Diet, Water, Coach, etc.)
├── data/                   # Chứa Database SQLite và file CSV dữ liệu món ăn
├── templates/              # Chứa giao diện index.html
├── models/                 # Chứa trọng số mô hình yolov8n.pt
├── .env                    # Lưu trữ API Keys (Cần tự tạo)
├── requirements.txt        # Danh sách thư viện Python
└── README.md               # Tài liệu dự án