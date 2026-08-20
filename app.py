import os
import binascii
from flask import Flask
from database.db_core import init_db
from ai.rag import init_vector_db
from routes.api import api_bp

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'balance_nutrition.db')
EXCEL_PATH = os.path.join(BASE_DIR, 'data', 'mon_an.xlsx')

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = os.getenv("SECRET_KEY", binascii.hexlify(os.urandom(24)).decode())

os.makedirs(os.path.join(BASE_DIR, 'data'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'templates'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'ai_models'), exist_ok=True)

init_db(DB_PATH, EXCEL_PATH)
try:
    init_vector_db(DB_PATH)
except Exception as e:
    print(f"[WARN] Vector DB: {e}")

app.register_blueprint(api_bp)

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    print(f"🥑 BalanceNutrition AI → http://127.0.0.1:{port}")
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)
