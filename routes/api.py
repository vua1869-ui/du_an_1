from flask import Blueprint, request, jsonify, render_template
from ai.vision import predict_image
from ai.rag import get_chatbot_response, client
from services.auth_service import verify_login, register_user, save_user_onboarding
from services.diet_service import get_diet_plan
from services.user_service import log_food, get_today_logs, get_weekly_stats, delete_log
from services.admin_service import get_all_foods, add_new_food, delete_food, get_all_users, delete_user
from services.recommendation_service import get_personalized_recommendations
from services.weight_service import add_or_update_weight, delete_weight, get_weight_data
from services.report_service import generate_weekly_report
from services.scoring_service import get_food_health_score
from services.grocery_service import generate_grocery_list
from services.water_service import log_water, get_water
from services.coach_service import generate_coach_message
from services.achievement_service import check_and_unlock, get_user_achievements
from services.alternative_service import generate_alternatives
from flask import session, request, jsonify
from services.auth_service import hash_password, verify_password
from database.db_core import get_db_connection
from email_validator import validate_email, EmailNotValidError

api_bp = Blueprint('api', __name__)

@api_bp.route('/')
def index():
    return render_template('index.html')

@api_bp.route('/api/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files: 
        return jsonify({'error': 'No image provided'}), 400
    try:
        img_bytes = request.files['image'].read()
        return jsonify(predict_image(img_bytes))
    except Exception as e:
        return jsonify({'error': f'Lỗi server: {str(e)}'}), 500

@api_bp.route('/api/diet', methods=['POST'])
def diet():
    data = request.json
    return jsonify(get_diet_plan(data.get('tdee', 2000), data.get('goal', 'duy_tri')))

@api_bp.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    message = data.get('message', '')
    if not message: return jsonify({'response': 'Vui lòng nhập câu hỏi.', 'type': 'chat'}), 400
    
    current_tdee = data.get('tdee') or 2000
    try: current_tdee = int(current_tdee)
    except: current_tdee = 2000
    
    return jsonify(get_chatbot_response(message, current_tdee=current_tdee, profile=data.get('profile')))

@api_bp.route('/api/log_food', methods=['POST'])
def add_food_log():
    return jsonify(log_food(request.json))

@api_bp.route('/api/today_logs', methods=['GET'])
def today_logs():
    return jsonify(get_today_logs())

@api_bp.route('/api/weekly_stats', methods=['GET'])
def weekly_stats():
    return jsonify(get_weekly_stats())

@api_bp.route('/api/admin/foods', methods=['GET'])
def admin_get_foods():
    return jsonify(get_all_foods())

@api_bp.route('/api/admin/foods', methods=['POST'])
def admin_add_food():
    result = add_new_food(request.json)
    return jsonify(result), 500 if "error" in result else 200

@api_bp.route('/api/admin/foods/<int:food_id>', methods=['DELETE'])
def admin_delete_food(food_id):
    return jsonify(delete_food(food_id))

@api_bp.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    return jsonify(get_all_users())

@api_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def admin_delete_user(user_id):
    return jsonify(delete_user(user_id))

@api_bp.route('/api/onboarding', methods=['POST'])
def onboarding_api():
    data = request.json or {}
    res = save_user_onboarding(data.get('user_id', 1), data.get('profile', {}))
    m = res['metrics']
    ai_advice = "Kế hoạch đã sẵn sàng! Hãy duy trì chế độ ăn hợp lý và theo dõi calo mỗi ngày."
    
    if client:
        try:
            prompt = f"Phân tích ngắn gọn (3-4 câu tiếng Việt) hồ sơ: {m['nickname']}, {m['gender']}, {m['age']} tuổi, {m['height']}cm, {m['weight']}kg. BMR: {m['bmr']}, TDEE: {m['tdee']}. Mục tiêu: {m['goal']} ({m['target_calories']} kcal/ngày). Đưa ra 2 lời khuyên dinh dưỡng cốt lõi."
            response = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
            ai_advice = response.text.strip()
        except: pass
    m['ai_advice'] = ai_advice
    return jsonify({"status": "success", "result": m})

@api_bp.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    user_id = request.args.get('user_id', 1, type=int)
    tdee = request.args.get('tdee', 2000, type=int)
    goal = request.args.get('goal', 'duy_tri')
    
    result = get_personalized_recommendations(user_id, tdee, goal)
    return jsonify(result)

@api_bp.route('/api/weight', methods=['GET', 'POST', 'DELETE'])
def handle_weight():
    if request.method == 'POST':
        data = request.json
        return jsonify(add_or_update_weight(data.get('user_id', 1), data.get('weight'), data.get('date')))
    elif request.method == 'DELETE':
        return jsonify(delete_weight(request.json.get('id')))
    else:
        user_id = request.args.get('user_id', 1, type=int)
        period = request.args.get('period', '30')
        target_weight = request.args.get('target_weight')
        return jsonify(get_weight_data(user_id, period, target_weight))

@api_bp.route('/api/weekly_ai_report', methods=['GET'])
def get_weekly_ai_report():
    user_id = request.args.get('user_id', 1, type=int)
    tdee = request.args.get('tdee', 2000, type=int)
    target_calories = request.args.get('target_calories', 2000, type=int)
    
    result = generate_weekly_report(user_id, tdee, target_calories)
    return jsonify(result)

@api_bp.route('/api/score_food', methods=['POST'])
def score_food_api():
    data = request.json or {}
    result = get_food_health_score(
        data.get('name', ''), 
        data.get('calories', 0), 
        data.get('protein', 0), 
        data.get('carbs', 0), 
        data.get('fat', 0)
    )
    return jsonify(result)

@api_bp.route('/api/grocery_list', methods=['POST'])
def grocery_list_api():
    data = request.json
    meals_data = data.get('meals', [])
    result = generate_grocery_list(meals_data)
    return jsonify(result)

@api_bp.route('/api/water', methods=['GET', 'POST'])
def handle_water():
    if request.method == 'POST':
        data = request.json
        return jsonify(log_water(data.get('user_id'), data.get('amount_ml'), data.get('date')))
    else:
        user_id = request.args.get('user_id', type=int)
        date_str = request.args.get('date')
        return jsonify(get_water(user_id, date_str))

@api_bp.route('/api/coach', methods=['GET'])
def get_ai_coach():
    user_id = request.args.get('user_id', type=int)
    target_calories = request.args.get('target_calories', default=2000, type=int)
    return jsonify(generate_coach_message(user_id, target_calories))

@api_bp.route('/api/achievements/check', methods=['POST'])
def check_achievements_api():
    data = request.json
    return jsonify(check_and_unlock(data.get('user_id')))

@api_bp.route('/api/achievements', methods=['GET'])
def get_achievements_api():
    user_id = request.args.get('user_id', type=int)
    return jsonify(get_user_achievements(user_id))

@api_bp.route('/api/alternatives', methods=['POST'])
def get_alternatives_api():
    data = request.json
    return jsonify(generate_alternatives(data))

@api_bp.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '')
    fullname = data.get('fullname', '').strip()

    if not email or not password or not fullname:
        return jsonify({"status": "error", "message": "Vui lòng nhập đầy đủ thông tin"}), 400
    
    if len(password) < 6:
        return jsonify({"status": "error", "message": "Mật khẩu phải có ít nhất 6 ký tự"}), 400

    # Gọi hàm register_user từ services/auth_service.py
    result = register_user(fullname, email, password)
    
    if result["status"] == "success":
        # Tự động đăng nhập luôn sau khi đăng ký
        session['user_id'] = result["user"]["id"]
        session['role'] = result["user"]["role"]
        
    return jsonify(result)

@api_bp.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"status": "error", "message": "Thiếu email hoặc mật khẩu"}), 400

    # Gọi hàm verify_login từ services/auth_service.py
    result = verify_login(email, password)
    
    if result["status"] == "success":
        # Lưu phiên đăng nhập
        session['user_id'] = result["user"]["id"]
        session['role'] = result["user"]["role"]
        
    return jsonify(result), 200 if result["status"] == "success" else 401

@api_bp.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "success", "message": "Đã đăng xuất"})

@api_bp.route('/api/log_food/<int:log_id>', methods=['DELETE'])
def remove_food_log(log_id):
    return jsonify(delete_log(log_id))