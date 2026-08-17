import os
import binascii
from flask import Flask
from database.db_core import init_db
from ai.rag import init_vector_db
from routes.api import api_bp

BASE_DIR = os.path.abspath(os.path.dirname(__name__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'balance_nutrition.db')

# Cập nhật đường dẫn trỏ tới file dữ liệu mới
EXCEL_PATH = os.path.join(BASE_DIR, 'data', 'mon_an.xlsx')

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = os.getenv("SECRET_KEY", binascii.hexlify(os.urandom(24)).decode())

# Khởi tạo Hệ thống với file Excel mới
init_db(DB_PATH, EXCEL_PATH)
init_vector_db(DB_PATH)

# Kết nối toàn bộ API đã viết
app.register_blueprint(api_bp)

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    os.makedirs('ai_models', exist_ok=True)
    app.run(debug=True, port=5000, use_reloader=False)