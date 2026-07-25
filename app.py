from flask import Flask, render_template, request, jsonify
from ai_logic import predict_image
from database import init_db, get_diet_plan, log_food, get_today_logs
from rag_chatbot import get_chatbot_response, init_vector_db
import os
from database import get_all_foods, add_new_food, delete_food

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
    data = request.json
    tdee = data.get('tdee', 2000)
    goal = data.get('goal', 'duy_tri')   # mặc định duy trì nếu không gửi lên
    result = get_diet_plan(tdee, goal)
    return jsonify(result)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    message = data.get('message', '')
    if not message:
        return jsonify({'response': 'Vui lòng nhập câu hỏi.', 'type': 'chat'}), 400

    # current_tdee: dùng giá trị đang có trên dashboard nếu user không nêu số
    current_tdee = data.get('tdee') or 2000
    try:
        current_tdee = int(current_tdee)
    except (TypeError, ValueError):
        current_tdee = 2000

    result = get_chatbot_response(message, current_tdee=current_tdee)
    # result là dict: response, type, tdee, goal, diet
    return jsonify(result)

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

# ================= ADMIN ROUTES =================
@app.route('/api/admin/foods', methods=['GET'])
def admin_get_foods():
    from database import get_all_foods
    return jsonify(get_all_foods())

@app.route('/api/admin/foods', methods=['POST'])
def admin_add_food():
    from database import add_new_food
    data = request.json
    result = add_new_food(data)
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)

@app.route('/api/admin/foods/<int:food_id>', methods=['DELETE'])
def admin_delete_food(food_id):
    from database import delete_food
    result = delete_food(food_id)
    return jsonify(result)

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    app.run(debug=True, port=5000, use_reloader=False)