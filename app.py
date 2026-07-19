from flask import Flask, render_template, request, jsonify
from ai_logic import predict_image
from database import init_db, get_diet_plan, log_food, get_today_logs
from rag_chatbot import get_chatbot_response, init_vector_db
import os

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

init_db()
init_vector_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files: 
        return jsonify({'error': 'No image provided'}), 400
    try:
        img_bytes = request.files['image'].read()
        result = predict_image(img_bytes)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Lỗi server: {str(e)}'}), 500

@app.route('/api/diet', methods=['POST'])
def diet():
    tdee = request.json.get('tdee', 2150)
    return jsonify(get_diet_plan(tdee))

@app.route('/api/chat', methods=['POST'])
def chat():
    message = request.json.get('message', '')
    if not message: 
        return jsonify({'response': 'Vui lòng nhập câu hỏi.'}), 400
    ai_response = get_chatbot_response(message)
    return jsonify({'response': ai_response})

# ROUTE MỚI: Thêm thức ăn vào nhật ký
@app.route('/api/log_food', methods=['POST'])
def add_food_log():
    data = request.json
    result = log_food(data)
    return jsonify(result)

# ROUTE MỚI: Lấy danh sách thức ăn đã ăn hôm nay
@app.route('/api/today_logs', methods=['GET'])
def today_logs():
    result = get_today_logs()
    return jsonify(result)
# ROUTE MỚI: Lấy dữ liệu thống kê 7 ngày
@app.route('/api/weekly_stats', methods=['GET'])
def weekly_stats():
    from database import get_weekly_stats
    result = get_weekly_stats()
    return jsonify(result)
if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    app.run(debug=True, port=5000, use_reloader=False)