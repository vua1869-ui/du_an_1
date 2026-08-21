import os
from flask import Blueprint, request, jsonify, render_template
from ai.vision import predict_image
from ai.rag import get_chatbot_response, client
from services.auth_service import (
    verify_login, register_user, save_user_onboarding, change_password,
    delete_account, export_user_data, get_security_info, login_or_register_google,
    request_password_reset, reset_password_with_token,
)
from services.diet_service import get_diet_plan
from services.user_service import (
    log_food, get_today_logs, get_logs_by_date, get_weekly_stats, delete_log,
    update_log, copy_day_logs, apply_meal_plan, get_daily_checklist,
    search_foods, get_recent_foods, get_day_comparison,
)
from services.admin_service import (
    get_all_foods, add_new_food, update_food, delete_food,
    get_all_users, get_user_detail, toggle_user_lock, set_user_role, delete_user,
    update_user, admin_reset_password, export_users_csv,
    get_ingredients, add_ingredient, update_ingredient, delete_ingredient,
    get_meal_plans, get_meal_plan_detail, create_meal_plan, update_meal_plan,
    delete_meal_plan, add_food_to_plan, remove_food_from_plan,
    get_dashboard_stats,
)
from services.admin_content_service import (
    get_articles, get_article, create_article, update_article, delete_article,
    get_published_articles, get_faqs, create_faq, update_faq, delete_faq, reorder_faqs,
    log_chat, get_chatbot_stats, get_chat_logs, get_user_chat_history,
    create_chat_session, list_chat_sessions, get_session_messages,
    rename_chat_session, delete_chat_session, ensure_chat_session,
    get_knowledge_docs, create_knowledge_doc, update_knowledge_doc, delete_knowledge_doc,
    reindex_knowledge, log_analysis, get_ai_monitoring_stats,
    import_foods_from_file, get_advanced_stats,
)
import time
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
from utils.decorators import admin_required, login_required

api_bp = Blueprint('api', __name__)

@api_bp.route('/')
def index():
    return render_template('index.html')

@api_bp.route('/api/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    t0 = time.time()
    user_id = session.get('user_id') or request.form.get('user_id')
    try:
        img_bytes = request.files['image'].read()
        result = predict_image(img_bytes)
        duration_ms = int((time.time() - t0) * 1000)

        # PROACTIVE ADVICE (Idea 2)
        if "error" not in result and "analysis" in result:
            tdee = int(request.form.get('tdee', 2000))
            if user_id:
                from services.user_service import get_today_logs
                logs = get_today_logs(user_id)
                current_cal = logs.get('totals', {}).get('calories', 0)
                item_cal = result['analysis'].get('calories', 0)

                advice = ""
                if item_cal > tdee * 0.4:
                    advice = f"\n\n💡 Cố vấn AI: Món này chiếm hơn 40% lượng calo mỗi ngày của bạn ({item_cal} kcal). Hãy ăn bữa tiếp theo thật nhẹ nhàng nhé!"
                elif current_cal + item_cal > tdee:
                    advice = f"\n\n💡 Cố vấn AI: Cảnh báo! Ăn xong món này bạn sẽ nạp tổng cộng {current_cal + item_cal} kcal, vượt quá mức TDEE ({tdee} kcal). Cân nhắc chỉ ăn một nửa nhé!"
                elif result['analysis'].get('carbs', 0) > 60:
                    advice = f"\n\n💡 Cố vấn AI: Món này chứa khá nhiều tinh bột ({result['analysis'].get('carbs')}g). Buổi chiều nên vận động nhẹ để tiêu hao năng lượng."
                elif item_cal < 200 and item_cal > 0:
                    advice = f"\n\n💡 Cố vấn AI: Món này rất nhẹ bụng. Có thể dùng làm bữa phụ hoặc kết hợp thêm đạm thực vật."

                if advice:
                    result['analysis']['description'] = result['analysis'].get('description', '') + advice

            # Log success
            analysis = result.get('analysis') or {}
            source = 'yolo' if result.get('detections') else 'gemini'
            log_analysis(
                user_id, analysis.get('dish_name', ''),
                analysis.get('calories', 0), True, source, '', duration_ms,
            )
        else:
            err = result.get('error') or result.get('message') or 'unknown'
            log_analysis(user_id, '', 0, False, 'unknown', str(err)[:300], duration_ms)

        return jsonify(result)
    except Exception as e:
        duration_ms = int((time.time() - t0) * 1000)
        log_analysis(user_id, '', 0, False, 'server', str(e)[:300], duration_ms)
        return jsonify({'error': f'Lỗi server: {str(e)}'}), 500

@api_bp.route('/api/diet', methods=['POST'])
def diet():
    data = request.json
    return jsonify(get_diet_plan(data.get('tdee', 2000), data.get('goal', 'duy_tri')))

@api_bp.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    message = data.get('message', '')
    if not message:
        return jsonify({'response': 'Vui lòng nhập câu hỏi.', 'type': 'chat'}), 400

    current_tdee = data.get('tdee') or 2000
    try:
        current_tdee = int(current_tdee)
    except Exception:
        current_tdee = 2000

    user_id = session.get('user_id') or data.get('user_id')
    session_id = data.get('session_id')
    try:
        session_id = int(session_id) if session_id not in (None, '', 0, '0') else None
    except (TypeError, ValueError):
        session_id = None

    today_logs_data = None
    if user_id:
        from services.user_service import get_today_logs
        today_logs_data = get_today_logs(user_id)

    result = get_chatbot_response(
        message, current_tdee=current_tdee,
        profile=data.get('profile'), today_logs=today_logs_data,
    )
    answer = result.get('response', '') if isinstance(result, dict) else str(result)
    is_err = any(k in (answer or '') for k in ('Lỗi', 'quá tải', 'chưa cấu hình', 'error'))
    # Lưu bản sạch (không kèm ghi chú hệ thống) vào lịch sử
    log_question = (data.get('display_message') or message or '').strip()
    marker = '(Lưu ý hệ thống:'
    if marker in log_question:
        log_question = log_question.split(marker)[0].strip()
    new_sid = log_chat(
        user_id, log_question, answer,
        result.get('type', 'chat') if isinstance(result, dict) else 'chat',
        is_err,
        session_id=session_id,
    )
    if isinstance(result, dict):
        result['session_id'] = new_sid
    else:
        result = {'response': str(result), 'type': 'chat', 'session_id': new_sid}
    return jsonify(result)


@api_bp.route('/api/chat/history', methods=['GET'])
def chat_history():
    """Lịch sử chat phẳng (fallback)."""
    user_id = session.get('user_id') or request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Chưa đăng nhập', 'logs': []}), 401
    limit = request.args.get('limit', 50, type=int)
    return jsonify(get_user_chat_history(user_id, limit=limit))


def _resolve_user_id():
    """Lấy user_id từ Flask session hoặc query/body (app dùng localStorage)."""
    uid = session.get('user_id')
    if uid:
        return uid
    uid = request.args.get('user_id', type=int)
    if uid:
        return uid
    data = request.get_json(silent=True) or {}
    try:
        return int(data['user_id']) if data.get('user_id') not in (None, '', 0, '0') else None
    except (TypeError, ValueError):
        return None


@api_bp.route('/api/chat/sessions', methods=['GET'])
def chat_sessions_list():
    user_id = _resolve_user_id()
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Chưa đăng nhập', 'sessions': []}), 401
    limit = request.args.get('limit', 40, type=int)
    try:
        return jsonify(list_chat_sessions(user_id, limit=limit))
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'sessions': []}), 500


@api_bp.route('/api/chat/sessions', methods=['POST'])
def chat_sessions_create():
    user_id = _resolve_user_id()
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Chưa đăng nhập'}), 401
    title = (request.json or {}).get('title')
    return jsonify(create_chat_session(user_id, title=title))


@api_bp.route('/api/chat/sessions/<int:session_id>', methods=['GET'])
def chat_session_detail(session_id):
    user_id = _resolve_user_id()
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Chưa đăng nhập', 'logs': []}), 401
    limit = request.args.get('limit', 100, type=int)
    try:
        return jsonify(get_session_messages(user_id, session_id, limit=limit))
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'logs': []}), 500


@api_bp.route('/api/chat/sessions/<int:session_id>', methods=['PATCH'])
def chat_session_rename(session_id):
    user_id = _resolve_user_id()
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Chưa đăng nhập'}), 401
    title = (request.json or {}).get('title', '')
    result = rename_chat_session(user_id, session_id, title)
    return jsonify(result), 200 if result.get('status') == 'success' else 400


@api_bp.route('/api/chat/sessions/<int:session_id>', methods=['DELETE'])
def chat_session_delete(session_id):
    user_id = _resolve_user_id()
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Chưa đăng nhập'}), 401
    result = delete_chat_session(user_id, session_id)
    return jsonify(result), 200 if result.get('status') == 'success' else 400

@api_bp.route('/api/log_food', methods=['POST'])
def add_food_log():
    data = request.json or {}
    user_id = session.get('user_id') or data.get('user_id')
    try:
        user_id = int(user_id) if user_id not in (None, '', 0, '0') else None
    except (TypeError, ValueError):
        user_id = None
    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    return jsonify(log_food(user_id, data))


@api_bp.route('/api/log_food/<int:log_id>', methods=['PUT'])
def edit_food_log(log_id):
    data = request.json or {}
    user_id = session.get('user_id') or data.get('user_id')
    try:
        user_id = int(user_id) if user_id not in (None, '', 0, '0') else None
    except (TypeError, ValueError):
        user_id = None
    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    result = update_log(user_id, log_id, data)
    return jsonify(result), 200 if result.get('status') == 'success' else 400


@api_bp.route('/api/today_logs', methods=['GET'])
def today_logs():
    user_id = session.get('user_id') or request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"foods": [], "totals": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}})
    date_str = request.args.get('date')
    if date_str:
        return jsonify(get_logs_by_date(user_id, date_str))
    return jsonify(get_today_logs(user_id))


@api_bp.route('/api/logs/copy-yesterday', methods=['POST'])
def api_copy_yesterday():
    data = request.json or {}
    user_id = session.get('user_id') or data.get('user_id')
    try:
        user_id = int(user_id) if user_id not in (None, '', 0, '0') else None
    except (TypeError, ValueError):
        user_id = None
    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    result = copy_day_logs(user_id, data.get('from_date'), data.get('to_date'))
    return jsonify(result), 200 if result.get('status') == 'success' else 400


@api_bp.route('/api/checklist', methods=['GET'])
def api_checklist():
    user_id = session.get('user_id') or request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    return jsonify(get_daily_checklist(user_id))


@api_bp.route('/api/weekly_stats', methods=['GET'])
def weekly_stats():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"dates": [], "calories": []})
    return jsonify(get_weekly_stats(user_id))

# ═══════════════════════════════════════════════════════════
# ADMIN APIs — tất cả bắt buộc role=admin (server-side)
# ═══════════════════════════════════════════════════════════

@api_bp.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    return jsonify(get_dashboard_stats())


# --- Users ---
@api_bp.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_get_users():
    q = request.args.get('q')
    status = request.args.get('status')
    role = request.args.get('role')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    result = get_all_users(q=q, status=status, role=role, page=page, per_page=per_page)
    return jsonify(result)


@api_bp.route('/api/admin/users/export', methods=['GET'])
@admin_required
def admin_export_users():
    from flask import Response
    q = request.args.get('q')
    status = request.args.get('status')
    role = request.args.get('role')
    csv_data = export_users_csv(q=q, status=status, role=role)
    filename = 'users_export.csv'
    return Response(
        '\ufeff' + csv_data,  # BOM for Excel UTF-8
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@api_bp.route('/api/admin/users/<int:user_id>', methods=['GET'])
@admin_required
def admin_user_detail(user_id):
    return jsonify(get_user_detail(user_id))


@api_bp.route('/api/admin/users/<int:user_id>/lock', methods=['POST'])
@admin_required
def admin_lock_user(user_id):
    admin_id = session.get('user_id')
    result = toggle_user_lock(user_id, admin_id)
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


@api_bp.route('/api/admin/users/<int:user_id>/role', methods=['POST'])
@admin_required
def admin_set_role(user_id):
    data = request.json or {}
    admin_id = session.get('user_id')
    result = set_user_role(user_id, data.get('role', 'user'), admin_id)
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


@api_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    admin_id = session.get('user_id')
    result = delete_user(user_id, admin_id)
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


@api_bp.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def admin_update_user(user_id):
    data = request.json or {}
    admin_id = session.get('user_id')
    result = update_user(user_id, data, admin_id)
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


@api_bp.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def admin_user_reset_password(user_id):
    data = request.json or {}
    admin_id = session.get('user_id')
    result = admin_reset_password(user_id, data.get('new_password', ''), admin_id)
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


# --- Foods ---

@api_bp.route('/api/admin/foods', methods=['GET'])
@admin_required
def admin_get_foods():
    q = request.args.get('q')
    meal_type = request.args.get('meal_type')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    result = get_all_foods(q=q, meal_type=meal_type, page=page, per_page=per_page)
    # Backward compatible: frontend cũ expect array; mới expect {foods, total}
    return jsonify(result)


@api_bp.route('/api/admin/foods', methods=['POST'])
@admin_required
def admin_add_food():
    result = add_new_food(request.json or {})
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


@api_bp.route('/api/admin/foods/<int:food_id>', methods=['PUT'])
@admin_required
def admin_update_food(food_id):
    result = update_food(food_id, request.json or {})
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


@api_bp.route('/api/admin/foods/<int:food_id>', methods=['DELETE'])
@admin_required
def admin_delete_food(food_id):
    return jsonify(delete_food(food_id))


# --- Ingredients ---
@api_bp.route('/api/admin/ingredients', methods=['GET'])
@admin_required
def admin_get_ingredients():
    return jsonify(get_ingredients(
        q=request.args.get('q'),
        page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 30, type=int),
    ))


@api_bp.route('/api/admin/ingredients', methods=['POST'])
@admin_required
def admin_add_ingredient():
    result = add_ingredient(request.json or {})
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


@api_bp.route('/api/admin/ingredients/<int:ing_id>', methods=['PUT'])
@admin_required
def admin_update_ingredient(ing_id):
    result = update_ingredient(ing_id, request.json or {})
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


@api_bp.route('/api/admin/ingredients/<int:ing_id>', methods=['DELETE'])
@admin_required
def admin_delete_ingredient(ing_id):
    return jsonify(delete_ingredient(ing_id))


# --- Meal Plans ---
@api_bp.route('/api/admin/meal-plans', methods=['GET'])
@admin_required
def admin_get_plans():
    return jsonify(get_meal_plans(q=request.args.get('q'), goal=request.args.get('goal')))


@api_bp.route('/api/admin/meal-plans/<int:plan_id>', methods=['GET'])
@admin_required
def admin_plan_detail(plan_id):
    return jsonify(get_meal_plan_detail(plan_id))


@api_bp.route('/api/admin/meal-plans', methods=['POST'])
@admin_required
def admin_create_plan():
    result = create_meal_plan(request.json or {})
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


@api_bp.route('/api/admin/meal-plans/<int:plan_id>', methods=['PUT'])
@admin_required
def admin_update_plan(plan_id):
    result = update_meal_plan(plan_id, request.json or {})
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


@api_bp.route('/api/admin/meal-plans/<int:plan_id>', methods=['DELETE'])
@admin_required
def admin_delete_plan(plan_id):
    return jsonify(delete_meal_plan(plan_id))


@api_bp.route('/api/admin/meal-plans/<int:plan_id>/items', methods=['POST'])
@admin_required
def admin_add_plan_item(plan_id):
    data = request.json or {}
    result = add_food_to_plan(
        plan_id,
        data.get('food_id'),
        data.get('meal_slot', 'lunch'),
        data.get('quantity', 1),
    )
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


@api_bp.route('/api/admin/meal-plans/items/<int:item_id>', methods=['DELETE'])
@admin_required
def admin_remove_plan_item(item_id):
    return jsonify(remove_food_from_plan(item_id))


# --- Articles ---
@api_bp.route('/api/admin/articles', methods=['GET'])
@admin_required
def admin_list_articles():
    return jsonify(get_articles(
        q=request.args.get('q'), category=request.args.get('category'),
        status=request.args.get('status'), page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 20, type=int),
    ))


@api_bp.route('/api/admin/articles/<int:aid>', methods=['GET'])
@admin_required
def admin_get_article(aid):
    return jsonify(get_article(aid))


@api_bp.route('/api/admin/articles', methods=['POST'])
@admin_required
def admin_create_article():
    result = create_article(request.json or {}, session.get('user_id'))
    return jsonify(result), 200 if result.get('status') == 'success' else 400


@api_bp.route('/api/admin/articles/<int:aid>', methods=['PUT'])
@admin_required
def admin_update_article(aid):
    result = update_article(aid, request.json or {})
    return jsonify(result), 200 if result.get('status') == 'success' else 400


@api_bp.route('/api/admin/articles/<int:aid>', methods=['DELETE'])
@admin_required
def admin_delete_article(aid):
    return jsonify(delete_article(aid))


# --- FAQ ---
@api_bp.route('/api/admin/faqs', methods=['GET'])
@admin_required
def admin_list_faqs():
    return jsonify(get_faqs(active_only=False))


@api_bp.route('/api/admin/faqs', methods=['POST'])
@admin_required
def admin_create_faq():
    result = create_faq(request.json or {})
    return jsonify(result), 200 if result.get('status') == 'success' else 400


@api_bp.route('/api/admin/faqs/<int:fid>', methods=['PUT'])
@admin_required
def admin_update_faq(fid):
    result = update_faq(fid, request.json or {})
    return jsonify(result), 200 if result.get('status') == 'success' else 400


@api_bp.route('/api/admin/faqs/<int:fid>', methods=['DELETE'])
@admin_required
def admin_delete_faq(fid):
    return jsonify(delete_faq(fid))


@api_bp.route('/api/admin/faqs/reorder', methods=['POST'])
@admin_required
def admin_reorder_faqs():
    result = reorder_faqs((request.json or {}).get('ids', []))
    return jsonify(result), 200 if result.get('status') == 'success' else 400


# --- Chatbot / RAG ---
@api_bp.route('/api/admin/chatbot/stats', methods=['GET'])
@admin_required
def admin_chatbot_stats():
    return jsonify(get_chatbot_stats())


@api_bp.route('/api/admin/chatbot/logs', methods=['GET'])
@admin_required
def admin_chatbot_logs():
    return jsonify(get_chat_logs(
        page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 30, type=int),
        only_errors=request.args.get('errors') == '1',
    ))


@api_bp.route('/api/admin/knowledge', methods=['GET'])
@admin_required
def admin_list_knowledge():
    return jsonify(get_knowledge_docs())


@api_bp.route('/api/admin/knowledge', methods=['POST'])
@admin_required
def admin_create_knowledge():
    result = create_knowledge_doc(request.json or {})
    return jsonify(result), 200 if result.get('status') == 'success' else 400


@api_bp.route('/api/admin/knowledge/<int:kid>', methods=['PUT'])
@admin_required
def admin_update_knowledge(kid):
    result = update_knowledge_doc(kid, request.json or {})
    return jsonify(result), 200 if result.get('status') == 'success' else 400


@api_bp.route('/api/admin/knowledge/<int:kid>', methods=['DELETE'])
@admin_required
def admin_delete_knowledge(kid):
    return jsonify(delete_knowledge_doc(kid))


@api_bp.route('/api/admin/knowledge/reindex', methods=['POST'])
@admin_required
def admin_reindex_knowledge():
    return jsonify(reindex_knowledge())


# --- AI Monitoring ---
@api_bp.route('/api/admin/ai-monitor', methods=['GET'])
@admin_required
def admin_ai_monitor():
    return jsonify(get_ai_monitoring_stats())


# --- Import foods ---
@api_bp.route('/api/admin/foods/import', methods=['POST'])
@admin_required
def admin_import_foods():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'Thiếu file upload'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'status': 'error', 'message': 'File rỗng'}), 400
    result = import_foods_from_file(f)
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


# --- Advanced stats ---
@api_bp.route('/api/admin/stats/advanced', methods=['GET'])
@admin_required
def admin_advanced_stats():
    return jsonify(get_advanced_stats())


# Public content (user-facing)
@api_bp.route('/api/articles', methods=['GET'])
def public_articles():
    return jsonify(get_published_articles(limit=request.args.get('limit', 20, type=int)))


@api_bp.route('/api/articles/<int:aid>', methods=['GET'])
def public_article_detail(aid):
    result = get_article(aid)
    if result.get('status') != 'success':
        return jsonify(result), 404
    art = result.get('article') or {}
    if art.get('status') != 'published':
        return jsonify({'status': 'error', 'message': 'Bài viết chưa được xuất bản'}), 404
    return jsonify(result)


@api_bp.route('/api/faqs', methods=['GET'])
def public_faqs():
    return jsonify(get_faqs(active_only=True))


@api_bp.route('/api/meal-plans', methods=['GET'])
def public_meal_plans():
    goal = request.args.get('goal')
    return jsonify(get_meal_plans(q=request.args.get('q'), goal=goal))


@api_bp.route('/api/meal-plans/<int:plan_id>', methods=['GET'])
def public_meal_plan_detail(plan_id):
    return jsonify(get_meal_plan_detail(plan_id))


@api_bp.route('/api/meal-plans/<int:plan_id>/apply', methods=['POST'])
def api_apply_meal_plan(plan_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    data = request.json or {}
    result = apply_meal_plan(user_id, plan_id, data.get('date'))
    return jsonify(result), 200 if result.get('status') == 'success' else 400


@api_bp.route('/api/profile', methods=['PUT'])
def api_update_profile():
    """User tự cập nhật hồ sơ → tính lại BMR/TDEE."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    data = request.json or {}
    result = save_user_onboarding(user_id, data)
    return jsonify(result)



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
    user_id = request.args.get('user_id', type=int) or session.get('user_id') or 1
    tdee = request.args.get('tdee', 2000, type=int)
    goal = request.args.get('goal', 'duy_tri')
    slot = request.args.get('slot')  # breakfast | lunch | dinner — chỉ làm mới 1 ô
    exclude = request.args.get('exclude', '')  # tên món loại trừ, phân tách bằng |
    exclude_names = [x.strip() for x in exclude.split('|') if x.strip()] if exclude else None
    only_slots = [slot] if slot in ('breakfast', 'lunch', 'dinner') else None
    result = get_personalized_recommendations(
        user_id, tdee, goal,
        exclude_names=exclude_names,
        only_slots=only_slots,
    )
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
    data = request.json or {}
    email = data.get('email', '').strip()
    password = data.get('password', '')
    fullname = data.get('fullname', '').strip()
    nickname = (data.get('nickname') or '').strip() or None

    if not email or not password or not fullname:
        return jsonify({"status": "error", "message": "Vui lòng nhập đầy đủ thông tin"}), 400

    result = register_user(fullname, email, password, nickname=nickname)

    if result["status"] == "success":
        # Tự động đăng nhập luôn sau khi đăng ký
        session['user_id'] = result["user"]["id"]
        session['role'] = result["user"]["role"]
        session['email'] = result["user"].get("email") or email

    return jsonify(result), 200 if result["status"] == "success" else 400

@api_bp.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"status": "error", "message": "Thiếu email hoặc mật khẩu"}), 400

    result = verify_login(email, password)

    if result["status"] == "success":
        session['user_id'] = result["user"]["id"]
        session['role'] = result["user"]["role"]
        session['email'] = result["user"].get("email") or email

    return jsonify(result), 200 if result["status"] == "success" else 401


@api_bp.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json or {}
    email = (data.get('email') or '').strip()
    result = request_password_reset(email)
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


@api_bp.route('/api/reset-password', methods=['POST'])
def reset_password_api():
    data = request.json or {}
    token = (data.get('token') or '').strip()
    new_password = data.get('new_password') or data.get('password') or ''
    result = reset_password_with_token(token, new_password)
    code = 200 if result.get('status') == 'success' else 400
    return jsonify(result), code


@api_bp.route('/api/auth/google/status', methods=['GET'])
def google_auth_status():
    """Frontend kiểm tra Google OAuth đã cấu hình chưa."""
    cid = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    return jsonify({
        "status": "success",
        "enabled": bool(cid and os.getenv('GOOGLE_CLIENT_SECRET', '').strip()),
    })


@api_bp.route('/api/auth/google', methods=['GET'])
def google_login_start():
    """Redirect user sang Google consent screen."""
    client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
    if not client_id or not client_secret:
        return jsonify({
            "status": "error",
            "message": "Chưa cấu hình GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET trong file .env",
        }), 503

    from authlib.integrations.requests_client import OAuth2Session
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI') or request.url_root.rstrip('/') + '/api/auth/google/callback'
    oauth = OAuth2Session(
        client_id,
        client_secret,
        scope='openid email profile',
        redirect_uri=redirect_uri,
    )
    uri, state = oauth.create_authorization_url(
        'https://accounts.google.com/o/oauth2/v2/auth',
        access_type='online',
        prompt='select_account',
    )
    session['google_oauth_state'] = state
    session['google_oauth_redirect'] = redirect_uri
    from flask import redirect
    return redirect(uri)


@api_bp.route('/api/auth/google/callback', methods=['GET'])
def google_login_callback():
    """Google redirect về đây sau khi user đồng ý."""
    from flask import redirect as flask_redirect, current_app
    client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
    if not client_id or not client_secret:
        return flask_redirect('/?google_error=not_configured')

    error = request.args.get('error')
    if error:
        return flask_redirect(f'/?google_error={error}')

    state = request.args.get('state')
    if not state or state != session.get('google_oauth_state'):
        return flask_redirect('/?google_error=invalid_state')

    code = request.args.get('code')
    if not code:
        return flask_redirect('/?google_error=no_code')

    try:
        from authlib.integrations.requests_client import OAuth2Session
        redirect_uri = session.get('google_oauth_redirect') or (
            request.url_root.rstrip('/') + '/api/auth/google/callback'
        )
        oauth = OAuth2Session(client_id, client_secret, redirect_uri=redirect_uri)
        token = oauth.fetch_token(
            'https://oauth2.googleapis.com/token',
            code=code,
            grant_type='authorization_code',
        )
        resp = oauth.get('https://www.googleapis.com/oauth2/v3/userinfo')
        info = resp.json()
        google_id = info.get('sub')
        email = info.get('email')
        fullname = info.get('name') or info.get('given_name') or ''
        avatar = info.get('picture')
        if not info.get('email_verified', True):
            return flask_redirect('/?google_error=email_not_verified')

        result = login_or_register_google(google_id, email, fullname, avatar)
        if result.get('status') != 'success':
            msg = result.get('message', 'login_failed')
            return flask_redirect(f'/?google_error={msg}')

        user = result['user']
        session['user_id'] = user['id']
        session['role'] = user.get('role', 'user')
        session['email'] = user.get('email') or email
        session.pop('google_oauth_state', None)

        # Truyền user qua query (frontend đọc rồi lưu localStorage) — encode an toàn
        import json, base64
        payload = base64.urlsafe_b64encode(json.dumps(user, ensure_ascii=False).encode('utf-8')).decode('ascii')
        needs = '1' if user.get('needs_onboarding') else '0'
        return flask_redirect(f'/?google_login=1&u={payload}&onboarding={needs}')
    except Exception as e:
        print(f'[Google OAuth] {e}')
        return flask_redirect('/?google_error=oauth_failed')


@api_bp.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "success", "message": "Đã đăng xuất"})

@api_bp.route('/api/log_food/<int:log_id>', methods=['DELETE'])
def remove_food_log(log_id):
    user_id = session.get('user_id') or request.args.get('user_id', type=int)
    if not user_id:
        data = request.get_json(silent=True) or {}
        try:
            user_id = int(data['user_id']) if data.get('user_id') not in (None, '', 0, '0') else None
        except (TypeError, ValueError, KeyError):
            user_id = None
    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    return jsonify(delete_log(user_id, log_id))

# ========== SETTINGS & SECURITY ==========
@api_bp.route('/api/change_password', methods=['POST'])
def api_change_password():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    data = request.json or {}
    result = change_password(user_id, data.get('current_password', ''), data.get('new_password', ''))
    return jsonify(result), 200 if result["status"] == "success" else 400

@api_bp.route('/api/delete_account', methods=['POST'])
def api_delete_account():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    data = request.json or {}
    result = delete_account(user_id, data.get('password', ''))
    if result["status"] == "success":
        session.clear()
    return jsonify(result), 200 if result["status"] == "success" else 400

@api_bp.route('/api/export_data', methods=['GET'])
def api_export_data():
    user_id = session.get('user_id')
    if not user_id:
        user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    return jsonify(export_user_data(user_id))

@api_bp.route('/api/security_info', methods=['GET'])
def api_security_info():
    user_id = session.get('user_id')
    if not user_id:
        user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    return jsonify(get_security_info(user_id))

@api_bp.route('/api/search_foods', methods=['GET'])
def api_search_foods():
    q = request.args.get('q', '')
    return jsonify(search_foods(q))

@api_bp.route('/api/recent_foods', methods=['GET'])
def api_recent_foods():
    user_id = session.get('user_id') or request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    return jsonify(get_recent_foods(user_id))

@api_bp.route('/api/day_compare', methods=['GET'])
def api_day_compare():
    user_id = session.get('user_id') or request.args.get('user_id', type=int)
    target = request.args.get('target', 2000, type=int)
    if not user_id:
        return jsonify({"status": "error", "message": "Chưa đăng nhập"}), 401
    return jsonify(get_day_comparison(user_id, target))
