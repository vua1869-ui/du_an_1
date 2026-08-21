"""Admin business logic — quản lý users, foods, ingredients, meal plans, dashboard."""
from database.db_core import get_db_connection
from utils.helpers import safe_int
from datetime import date
from flask import session


def _safe_float(val, default=0.0):
    try:
        v = float(val)
        return max(0.0, v)
    except (TypeError, ValueError):
        return default


def _validate_nutrition(data, require_name=True):
    """Validate tên + dinh dưỡng không âm."""
    errors = []
    name = (data.get('name') or '').strip()
    if require_name and not name:
        errors.append('Tên không được để trống')
    if len(name) > 200:
        errors.append('Tên quá dài (tối đa 200 ký tự)')

    for field in ('calories', 'protein', 'carbs', 'fat', 'fiber'):
        raw = data.get(field, 0)
        try:
            v = float(raw)
            if v < 0:
                errors.append(f'{field} không được âm')
            if v > 10000:
                errors.append(f'{field} quá lớn')
        except (TypeError, ValueError):
            errors.append(f'{field} phải là số')

    return errors, name


# ═══════════════════════════════════════════
# DASHBOARD STATS
# ═══════════════════════════════════════════

def get_dashboard_stats():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    total_admins = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM users WHERE COALESCE(is_active,1)=1')
    active_users = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM users WHERE COALESCE(is_active,1)=0')
    locked_users = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM foods')
    total_foods = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM ingredients')
    total_ingredients = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM meal_plans')
    total_plans = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM daily_logs')
    total_logs = c.fetchone()[0]

    # Đăng ký 7 ngày gần nhất
    c.execute('''
        SELECT created_at, COUNT(*) FROM users
        WHERE created_at IS NOT NULL
        GROUP BY created_at ORDER BY created_at DESC LIMIT 14
    ''')
    reg_rows = c.fetchall()
    registrations = [{'date': r[0], 'count': r[1]} for r in reversed(reg_rows)]

    # Phân bố meal_type
    c.execute('SELECT meal_type, COUNT(*) FROM foods GROUP BY meal_type')
    meal_dist = {r[0] or 'other': r[1] for r in c.fetchall()}

    # Phân bố goal của user
    c.execute("SELECT COALESCE(goal,'chua_set'), COUNT(*) FROM users GROUP BY goal")
    goal_dist = {r[0]: r[1] for r in c.fetchall()}

    conn.close()
    return {
        'status': 'success',
        'total_users': total_users,
        'total_admins': total_admins,
        'active_users': active_users,
        'locked_users': locked_users,
        'total_foods': total_foods,
        'total_ingredients': total_ingredients,
        'total_plans': total_plans,
        'total_logs': total_logs,
        'registrations': registrations,
        'meal_distribution': meal_dist,
        'goal_distribution': goal_dist,
    }


# ═══════════════════════════════════════════
# USERS
# ═══════════════════════════════════════════

def _users_where(q=None, status=None, role=None):
    """Build WHERE clause + params for user listing."""
    sql = ' WHERE 1=1'
    params = []
    if q:
        sql += ' AND (LOWER(fullname) LIKE ? OR LOWER(email) LIKE ? OR LOWER(COALESCE(nickname,"")) LIKE ?)'
        like = f'%{q.lower()}%'
        params.extend([like, like, like])
    if status == 'active':
        sql += ' AND COALESCE(is_active,1)=1'
    elif status == 'locked':
        sql += ' AND COALESCE(is_active,1)=0'
    if role in ('admin', 'user'):
        sql += ' AND role=?'
        params.append(role)
    return sql, params


def get_all_users(q=None, status=None, role=None, page=1, per_page=20):
    """
    Lấy danh sách user có phân trang.
    Trả về dict: { items, total, page, per_page, total_pages }
    """
    try:
        page = max(1, int(page or 1))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = min(100, max(5, int(per_page or 20)))
    except (TypeError, ValueError):
        per_page = 20

    conn = get_db_connection()
    c = conn.cursor()
    where_sql, params = _users_where(q, status, role)

    c.execute('SELECT COUNT(*) FROM users' + where_sql, params)
    total = c.fetchone()[0] or 0

    offset = (page - 1) * per_page
    sql = '''SELECT id, fullname, email, role, created_at,
                    COALESCE(is_active,1) as is_active,
                    nickname, gender, birth_year, height, weight, goal,
                    activity_level, weekly_goal, bmr, tdee, target_calories,
                    avatar_url, google_id,
                    CASE WHEN password IS NULL OR password = '' THEN 0 ELSE 1 END as has_password
             FROM users''' + where_sql + ' ORDER BY id DESC LIMIT ? OFFSET ?'
    c.execute(sql, params + [per_page, offset])
    rows = c.fetchall()
    conn.close()

    items = [
        {
            'id': r[0], 'fullname': r[1], 'email': r[2], 'role': r[3],
            'created_at': r[4], 'is_active': bool(r[5]),
            'nickname': r[6], 'gender': r[7], 'birth_year': r[8],
            'height': r[9], 'weight': r[10], 'goal': r[11],
            'activity_level': r[12], 'weekly_goal': r[13],
            'bmr': r[14], 'tdee': r[15], 'target_calories': r[16],
            'avatar_url': r[17],
            'google_linked': bool(r[18]),
            'has_password': bool(r[19]),
            'status': 'active' if r[5] else 'locked',
        }
        for r in rows
    ]
    total_pages = max(1, (total + per_page - 1) // per_page) if total else 1
    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
    }


def export_users_csv(q=None, status=None, role=None):
    """Xuất toàn bộ user (theo filter) ra CSV string."""
    import csv
    import io
    data = get_all_users(q=q, status=status, role=role, page=1, per_page=10000)
    users = data.get('items') or []
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        'ID', 'Họ tên', 'Email', 'Nickname', 'Role', 'Trạng thái',
        'Giới tính', 'Năm sinh', 'Chiều cao', 'Cân nặng', 'Mục tiêu',
        'Hoạt động', 'BMR', 'TDEE', 'Calo mục tiêu',
        'Google', 'Có MK', 'Ngày tạo',
    ])
    goal_map = {
        'giam_can': 'Giảm cân', 'tang_can': 'Tăng cân',
        'duy_tri': 'Duy trì', 'tang_co': 'Tăng cơ',
    }
    for u in users:
        writer.writerow([
            u.get('id'),
            u.get('fullname') or '',
            u.get('email') or '',
            u.get('nickname') or '',
            u.get('role') or '',
            'Hoạt động' if u.get('is_active') else 'Đã khóa',
            u.get('gender') or '',
            u.get('birth_year') or '',
            u.get('height') or '',
            u.get('weight') or '',
            goal_map.get(u.get('goal'), u.get('goal') or ''),
            u.get('activity_level') or '',
            u.get('bmr') or '',
            u.get('tdee') or '',
            u.get('target_calories') or '',
            'Có' if u.get('google_linked') else 'Không',
            'Có' if u.get('has_password') else 'Không',
            u.get('created_at') or '',
        ])
    return buf.getvalue()


def get_user_detail(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT id, fullname, email, role, created_at,
                        COALESCE(is_active,1), nickname, gender, birth_year,
                        height, weight, goal, activity_level, weekly_goal,
                        bmr, tdee, target_calories, avatar_url, google_id,
                        CASE WHEN password IS NULL OR password = '' THEN 0 ELSE 1 END
                 FROM users WHERE id=?''', (user_id,))
    u = c.fetchone()
    if not u:
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy người dùng'}

    c.execute('SELECT COUNT(*) FROM daily_logs WHERE user_id=?', (user_id,))
    log_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM water_logs WHERE user_id=?', (user_id,))
    water_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM weight_logs WHERE user_id=?', (user_id,))
    weight_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM user_achievements WHERE user_id=?', (user_id,))
    try:
        ach_count = c.fetchone()[0]
    except Exception:
        ach_count = 0
    # Recent weight
    c.execute('SELECT weight, date FROM weight_logs WHERE user_id=? ORDER BY date DESC LIMIT 1', (user_id,))
    last_w = c.fetchone()
    # Chat & analysis usage
    chat_count = 0
    analysis_count = 0
    try:
        c.execute('SELECT COUNT(*) FROM chat_logs WHERE user_id=?', (user_id,))
        chat_count = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM analysis_logs WHERE user_id=?', (user_id,))
        analysis_count = c.fetchone()[0]
    except Exception:
        pass
    conn.close()

    age = None
    if u[8]:
        try:
            from datetime import date as _date
            age = _date.today().year - int(u[8])
        except Exception:
            age = None

    return {
        'status': 'success',
        'user': {
            'id': u[0], 'fullname': u[1], 'email': u[2], 'role': u[3],
            'created_at': u[4], 'is_active': bool(u[5]),
            'status': 'active' if u[5] else 'locked',
            'nickname': u[6], 'gender': u[7], 'birth_year': u[8],
            'height': u[9], 'weight': u[10], 'goal': u[11],
            'activity_level': u[12], 'weekly_goal': u[13],
            'bmr': u[14], 'tdee': u[15], 'target_calories': u[16],
            'avatar_url': u[17],
            'google_linked': bool(u[18]),
            'has_password': bool(u[19]),
            'age': age,
            'stats': {
                'food_logs': log_count,
                'water_logs': water_count,
                'weight_logs': weight_count,
                'achievements': ach_count,
                'chat_messages': chat_count,
                'image_analyses': analysis_count,
            },
            'last_weight': {'weight': last_w[0], 'date': last_w[1]} if last_w else None,
        },
    }


def update_user(user_id, data, admin_id=None):
    """Admin cập nhật toàn bộ thông tin hồ sơ người dùng."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, email, role FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy người dùng'}

    fullname = (data.get('fullname') or '').strip()
    if not fullname:
        conn.close()
        return {'status': 'error', 'message': 'Họ tên không được để trống'}
    if len(fullname) > 120:
        conn.close()
        return {'status': 'error', 'message': 'Họ tên quá dài'}

    email = (data.get('email') or '').strip().lower()
    if email and email != (row[1] or '').lower():
        try:
            from email_validator import validate_email, EmailNotValidError
            validate_email(email)
        except Exception:
            conn.close()
            return {'status': 'error', 'message': 'Email không hợp lệ'}
        c.execute('SELECT id FROM users WHERE LOWER(email)=? AND id!=?', (email, user_id))
        if c.fetchone():
            conn.close()
            return {'status': 'error', 'message': 'Email đã được sử dụng bởi tài khoản khác'}
    else:
        email = row[1]

    nickname = (data.get('nickname') or '').strip()[:60] or None
    gender = data.get('gender')
    if gender not in ('male', 'female', 'other', None, ''):
        gender = None
    if gender == '':
        gender = None

    def _num(key, lo=None, hi=None):
        v = data.get(key)
        if v is None or v == '':
            return None
        try:
            n = float(v)
            if lo is not None and n < lo:
                return None
            if hi is not None and n > hi:
                return None
            return n
        except (TypeError, ValueError):
            return None

    birth_year = data.get('birth_year')
    try:
        birth_year = int(birth_year) if birth_year not in (None, '') else None
        if birth_year is not None and (birth_year < 1920 or birth_year > 2020):
            birth_year = None
    except (TypeError, ValueError):
        birth_year = None

    height = _num('height', 50, 250)
    weight = _num('weight', 20, 300)
    weekly_goal = _num('weekly_goal', -5, 5)
    bmr = _num('bmr', 500, 5000)
    tdee = _num('tdee', 500, 8000)
    target_calories = _num('target_calories', 500, 8000)

    goal = data.get('goal')
    if goal not in ('giam_can', 'tang_can', 'duy_tri', 'tang_co', None, ''):
        goal = None
    if goal == '':
        goal = None

    activity = data.get('activity_level')
    if activity not in ('sedentary', 'light', 'moderate', 'active', 'very_active', None, ''):
        activity = None
    if activity == '':
        activity = None

    c.execute(
        '''UPDATE users SET fullname=?, email=?, nickname=?, gender=?, birth_year=?,
           height=?, weight=?, goal=?, activity_level=?, weekly_goal=?,
           bmr=?, tdee=?, target_calories=?
           WHERE id=?''',
        (
            fullname, email, nickname, gender, birth_year,
            height, weight, goal, activity, weekly_goal,
            bmr, tdee, target_calories, user_id,
        ),
    )
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã cập nhật thông tin người dùng'}


def admin_reset_password(user_id, new_password, admin_id=None):
    """Admin đặt lại mật khẩu cho user."""
    pwd = (new_password or '').strip()
    if len(pwd) < 6:
        return {'status': 'error', 'message': 'Mật khẩu mới tối thiểu 6 ký tự'}
    if len(pwd) > 128:
        return {'status': 'error', 'message': 'Mật khẩu quá dài'}

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE id=?', (user_id,))
    if not c.fetchone():
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy người dùng'}

    from services.auth_service import hash_password
    hashed = hash_password(pwd)
    c.execute('UPDATE users SET password=? WHERE id=?', (hashed, user_id))
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã đặt lại mật khẩu thành công'}


def toggle_user_lock(user_id, admin_id):
    """Khóa / mở khóa. Không cho admin tự khóa chính mình."""
    if int(user_id) == int(admin_id):
        return {'status': 'error', 'message': 'Không thể khóa tài khoản của chính bạn'}

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT role, COALESCE(is_active,1) FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy người dùng'}

    # Không cho khóa admin cuối cùng
    if row[0] == 'admin' and row[1] == 1:
        c.execute("SELECT COUNT(*) FROM users WHERE role IN ('admin','super_admin') AND COALESCE(is_active,1)=1")
        if c.fetchone()[0] <= 1:
            conn.close()
            return {'status': 'error', 'message': 'Không thể khóa admin duy nhất còn hoạt động'}

    new_status = 0 if row[1] else 1
    c.execute('UPDATE users SET is_active=? WHERE id=?', (new_status, user_id))
    conn.commit()
    conn.close()
    return {
        'status': 'success',
        'message': 'Đã khóa tài khoản' if new_status == 0 else 'Đã mở khóa tài khoản',
        'is_active': bool(new_status),
    }


def set_user_role(user_id, new_role, admin_id):
    if new_role not in ('admin', 'user'):
        return {'status': 'error', 'message': 'Role chỉ chấp nhận admin hoặc user'}
    if int(user_id) == int(admin_id) and new_role != 'admin':
        return {'status': 'error', 'message': 'Không thể tự hạ quyền admin của chính bạn'}

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT role FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy người dùng'}

    if row[0] == 'admin' and new_role == 'user':
        c.execute("SELECT COUNT(*) FROM users WHERE role IN ('admin','super_admin') AND COALESCE(is_active,1)=1")
        if c.fetchone()[0] <= 1:
            conn.close()
            return {'status': 'error', 'message': 'Không thể hạ quyền admin duy nhất'}

    c.execute('UPDATE users SET role=? WHERE id=?', (new_role, user_id))
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': f'Đã đổi role thành {new_role}'}


def delete_user(user_id, admin_id=None):
    """Xóa user. Không cho xóa chính mình / admin cuối."""
    if admin_id is not None and int(user_id) == int(admin_id):
        return {'status': 'error', 'message': 'Không thể xóa tài khoản của chính bạn'}

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT role FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy người dùng'}

    if row[0] == 'admin':
        c.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
        if c.fetchone()[0] <= 1:
            conn.close()
            return {'status': 'error', 'message': 'Không thể xóa admin duy nhất'}

    for table in ('daily_logs', 'water_logs', 'weight_logs', 'weight_history', 'user_achievements'):
        try:
            c.execute(f'DELETE FROM {table} WHERE user_id=?', (user_id,))
        except Exception:
            pass
    c.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã xóa tài khoản'}


# ═══════════════════════════════════════════
# FOODS
# ═══════════════════════════════════════════

def get_all_foods(q=None, meal_type=None, page=1, per_page=50):
    conn = get_db_connection()
    c = conn.cursor()
    sql = '''SELECT id, meal_type, name, calories, protein, carbs, fat,
                    COALESCE(fiber,0), COALESCE(unit,'phần'), COALESCE(description,'')
             FROM foods WHERE 1=1'''
    params = []
    if q:
        sql += ' AND LOWER(name) LIKE ?'
        params.append(f'%{q.lower()}%')
    if meal_type and meal_type != 'all':
        sql += ' AND meal_type=?'
        params.append(meal_type)

    # count
    count_sql = 'SELECT COUNT(*) FROM foods WHERE 1=1'
    count_params = []
    if q:
        count_sql += ' AND LOWER(name) LIKE ?'
        count_params.append(f'%{q.lower()}%')
    if meal_type and meal_type != 'all':
        count_sql += ' AND meal_type=?'
        count_params.append(meal_type)
    c.execute(count_sql, count_params)
    total = c.fetchone()[0]

    sql += ' ORDER BY id DESC LIMIT ? OFFSET ?'
    page = max(1, int(page or 1))
    per_page = min(200, max(1, int(per_page or 50)))
    params.extend([per_page, (page - 1) * per_page])
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()

    foods = [
        {
            'id': r[0], 'meal_type': r[1], 'name': r[2],
            'calories': r[3], 'protein': r[4], 'carbs': r[5], 'fat': r[6],
            'fiber': r[7], 'unit': r[8], 'description': r[9],
        }
        for r in rows
    ]
    return {
        'status': 'success',
        'foods': foods,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': max(1, (total + per_page - 1) // per_page),
    }


def add_new_food(data):
    errors, name = _validate_nutrition(data)
    if errors:
        return {'status': 'error', 'message': '; '.join(errors)}

    meal_type = data.get('meal_type', 'snack')
    if meal_type not in ('breakfast', 'lunch', 'dinner', 'snack'):
        meal_type = 'snack'

    cal = _safe_float(data.get('calories'))
    pro = _safe_float(data.get('protein'))
    carbs = _safe_float(data.get('carbs'))
    fat = _safe_float(data.get('fat'))
    fiber = _safe_float(data.get('fiber'))
    unit = (data.get('unit') or 'phần').strip()[:30]
    desc = (data.get('description') or '').strip()[:500]

    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            '''INSERT INTO foods (meal_type, name, calories, protein, carbs, fat, fiber, unit, description)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            (meal_type, name, cal, pro, carbs, fat, fiber, unit, desc),
        )
        new_id = c.lastrowid
        conn.commit()
        conn.close()

        try:
            from ai.rag import collection
            if collection is not None:
                doc = f"{name} chứa {cal} calo, {pro}g protein, {carbs}g carbs, {fat}g fat."
                collection.add(
                    documents=[doc],
                    metadatas=[{'name': name, 'calories': cal, 'protein': pro, 'carbs': carbs, 'fat': fat}],
                    ids=[f'food_{new_id}'],
                )
        except Exception:
            pass

        return {'status': 'success', 'message': 'Đã thêm món ăn thành công!', 'id': new_id}
    except Exception as e:
        return {'status': 'error', 'message': f'Lỗi: {str(e)}'}


def update_food(food_id, data):
    errors, name = _validate_nutrition(data)
    if errors:
        return {'status': 'error', 'message': '; '.join(errors)}

    meal_type = data.get('meal_type', 'snack')
    if meal_type not in ('breakfast', 'lunch', 'dinner', 'snack'):
        meal_type = 'snack'

    cal = _safe_float(data.get('calories'))
    pro = _safe_float(data.get('protein'))
    carbs = _safe_float(data.get('carbs'))
    fat = _safe_float(data.get('fat'))
    fiber = _safe_float(data.get('fiber'))
    unit = (data.get('unit') or 'phần').strip()[:30]
    desc = (data.get('description') or '').strip()[:500]

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM foods WHERE id=?', (food_id,))
    if not c.fetchone():
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy món ăn'}

    c.execute(
        '''UPDATE foods SET meal_type=?, name=?, calories=?, protein=?, carbs=?, fat=?,
           fiber=?, unit=?, description=? WHERE id=?''',
        (meal_type, name, cal, pro, carbs, fat, fiber, unit, desc, food_id),
    )
    conn.commit()
    conn.close()

    try:
        from ai.rag import collection
        if collection is not None:
            collection.delete(ids=[f'food_{food_id}'])
            doc = f"{name} chứa {cal} calo, {pro}g protein, {carbs}g carbs, {fat}g fat."
            collection.add(
                documents=[doc],
                metadatas=[{'name': name, 'calories': cal, 'protein': pro, 'carbs': carbs, 'fat': fat}],
                ids=[f'food_{food_id}'],
            )
    except Exception:
        pass

    return {'status': 'success', 'message': 'Đã cập nhật món ăn!'}


def delete_food(food_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM foods WHERE id=?', (food_id,))
    # Gỡ khỏi meal_plan_items nếu có
    try:
        c.execute('DELETE FROM meal_plan_items WHERE food_id=?', (food_id,))
    except Exception:
        pass
    conn.commit()
    conn.close()
    try:
        from ai.rag import collection
        if collection is not None:
            collection.delete(ids=[f'food_{food_id}'])
    except Exception:
        pass
    return {'status': 'success', 'message': 'Đã xóa món ăn!'}


# ═══════════════════════════════════════════
# INGREDIENTS
# ═══════════════════════════════════════════

def get_ingredients(q=None, page=1, per_page=30):
    conn = get_db_connection()
    c = conn.cursor()
    sql = 'SELECT id, name, calories, protein, carbs, fat, fiber, unit, created_at FROM ingredients WHERE 1=1'
    params = []
    if q:
        sql += ' AND LOWER(name) LIKE ?'
        params.append(f'%{q.lower()}%')

    count_sql = 'SELECT COUNT(*) FROM ingredients WHERE 1=1'
    count_params = list(params)
    c.execute(count_sql if not q else count_sql + ' AND LOWER(name) LIKE ?', count_params)
    total = c.fetchone()[0]

    page = max(1, int(page or 1))
    per_page = min(100, max(1, int(per_page or 30)))
    sql += ' ORDER BY name ASC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()

    return {
        'status': 'success',
        'ingredients': [
            {
                'id': r[0], 'name': r[1], 'calories': r[2], 'protein': r[3],
                'carbs': r[4], 'fat': r[5], 'fiber': r[6], 'unit': r[7],
                'created_at': r[8],
            }
            for r in rows
        ],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': max(1, (total + per_page - 1) // per_page),
    }


def add_ingredient(data):
    errors, name = _validate_nutrition(data)
    if errors:
        return {'status': 'error', 'message': '; '.join(errors)}
    unit = (data.get('unit') or 'g').strip()[:30]
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO ingredients (name, calories, protein, carbs, fat, fiber, unit, created_at)
           VALUES (?,?,?,?,?,?,?,?)''',
        (
            name,
            _safe_float(data.get('calories')),
            _safe_float(data.get('protein')),
            _safe_float(data.get('carbs')),
            _safe_float(data.get('fat')),
            _safe_float(data.get('fiber')),
            unit,
            date.today().isoformat(),
        ),
    )
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã thêm nguyên liệu!', 'id': new_id}


def update_ingredient(ing_id, data):
    errors, name = _validate_nutrition(data)
    if errors:
        return {'status': 'error', 'message': '; '.join(errors)}
    unit = (data.get('unit') or 'g').strip()[:30]
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM ingredients WHERE id=?', (ing_id,))
    if not c.fetchone():
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy nguyên liệu'}
    c.execute(
        '''UPDATE ingredients SET name=?, calories=?, protein=?, carbs=?, fat=?, fiber=?, unit=?
           WHERE id=?''',
        (
            name,
            _safe_float(data.get('calories')),
            _safe_float(data.get('protein')),
            _safe_float(data.get('carbs')),
            _safe_float(data.get('fat')),
            _safe_float(data.get('fiber')),
            unit,
            ing_id,
        ),
    )
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã cập nhật nguyên liệu!'}


def delete_ingredient(ing_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM ingredients WHERE id=?', (ing_id,))
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã xóa nguyên liệu!'}


# ═══════════════════════════════════════════
# MEAL PLANS
# ═══════════════════════════════════════════

VALID_GOALS = ('giam_can', 'tang_can', 'duy_tri', 'tang_co')


def _plan_totals(c, plan_id):
    c.execute('''
        SELECT COALESCE(SUM(f.calories * mpi.quantity),0),
               COALESCE(SUM(f.protein * mpi.quantity),0),
               COALESCE(SUM(f.carbs * mpi.quantity),0),
               COALESCE(SUM(f.fat * mpi.quantity),0)
        FROM meal_plan_items mpi
        LEFT JOIN foods f ON f.id = mpi.food_id
        WHERE mpi.plan_id=?
    ''', (plan_id,))
    row = c.fetchone()
    return {
        'total_calories': round(row[0] or 0, 1),
        'total_protein': round(row[1] or 0, 1),
        'total_carbs': round(row[2] or 0, 1),
        'total_fat': round(row[3] or 0, 1),
    }


def get_meal_plans(q=None, goal=None):
    conn = get_db_connection()
    c = conn.cursor()
    sql = 'SELECT id, name, goal, target_calories, description, created_at FROM meal_plans WHERE 1=1'
    params = []
    if q:
        sql += ' AND LOWER(name) LIKE ?'
        params.append(f'%{q.lower()}%')
    if goal and goal in VALID_GOALS:
        sql += ' AND goal=?'
        params.append(goal)
    sql += ' ORDER BY id DESC'
    c.execute(sql, params)
    rows = c.fetchall()
    plans = []
    for r in rows:
        totals = _plan_totals(c, r[0])
        plans.append({
            'id': r[0], 'name': r[1], 'goal': r[2],
            'target_calories': r[3], 'description': r[4], 'created_at': r[5],
            **totals,
        })
    conn.close()
    return {'status': 'success', 'plans': plans}


def get_meal_plan_detail(plan_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        'SELECT id, name, goal, target_calories, description, created_at FROM meal_plans WHERE id=?',
        (plan_id,),
    )
    r = c.fetchone()
    if not r:
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy thực đơn'}

    c.execute('''
        SELECT mpi.id, mpi.food_id, mpi.meal_slot, mpi.quantity,
               f.name, f.calories, f.protein, f.carbs, f.fat, f.meal_type
        FROM meal_plan_items mpi
        LEFT JOIN foods f ON f.id = mpi.food_id
        WHERE mpi.plan_id=?
        ORDER BY CASE mpi.meal_slot
            WHEN 'breakfast' THEN 1 WHEN 'lunch' THEN 2
            WHEN 'dinner' THEN 3 ELSE 4 END, mpi.id
    ''', (plan_id,))
    items = [
        {
            'id': i[0], 'food_id': i[1], 'meal_slot': i[2], 'quantity': i[3],
            'food_name': i[4], 'calories': i[5], 'protein': i[6],
            'carbs': i[7], 'fat': i[8], 'food_meal_type': i[9],
        }
        for i in c.fetchall()
    ]
    totals = _plan_totals(c, plan_id)
    conn.close()
    return {
        'status': 'success',
        'plan': {
            'id': r[0], 'name': r[1], 'goal': r[2],
            'target_calories': r[3], 'description': r[4], 'created_at': r[5],
            'items': items, **totals,
        },
    }


def create_meal_plan(data):
    name = (data.get('name') or '').strip()
    if not name:
        return {'status': 'error', 'message': 'Tên thực đơn không được trống'}
    goal = data.get('goal', 'duy_tri')
    if goal not in VALID_GOALS:
        goal = 'duy_tri'
    target = safe_int(data.get('target_calories', 2000))
    if target < 800 or target > 6000:
        return {'status': 'error', 'message': 'Calories mục tiêu phải trong khoảng 800–6000'}
    desc = (data.get('description') or '').strip()[:500]

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        'INSERT INTO meal_plans (name, goal, target_calories, description, created_at) VALUES (?,?,?,?,?)',
        (name, goal, target, desc, date.today().isoformat()),
    )
    plan_id = c.lastrowid

    # Gắn món nếu có
    items = data.get('items') or []
    for it in items:
        fid = it.get('food_id')
        if not fid:
            continue
        slot = it.get('meal_slot', 'lunch')
        if slot not in ('breakfast', 'lunch', 'dinner', 'snack'):
            slot = 'lunch'
        qty = max(0.1, _safe_float(it.get('quantity', 1), 1))
        c.execute(
            'INSERT INTO meal_plan_items (plan_id, food_id, meal_slot, quantity) VALUES (?,?,?,?)',
            (plan_id, fid, slot, qty),
        )

    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã tạo thực đơn!', 'id': plan_id}


def update_meal_plan(plan_id, data):
    name = (data.get('name') or '').strip()
    if not name:
        return {'status': 'error', 'message': 'Tên thực đơn không được trống'}
    goal = data.get('goal', 'duy_tri')
    if goal not in VALID_GOALS:
        goal = 'duy_tri'
    target = safe_int(data.get('target_calories', 2000))
    if target < 800 or target > 6000:
        return {'status': 'error', 'message': 'Calories mục tiêu phải trong khoảng 800–6000'}
    desc = (data.get('description') or '').strip()[:500]

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM meal_plans WHERE id=?', (plan_id,))
    if not c.fetchone():
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy thực đơn'}

    c.execute(
        'UPDATE meal_plans SET name=?, goal=?, target_calories=?, description=? WHERE id=?',
        (name, goal, target, desc, plan_id),
    )

    # Nếu client gửi items → thay toàn bộ
    if 'items' in data:
        c.execute('DELETE FROM meal_plan_items WHERE plan_id=?', (plan_id,))
        for it in (data.get('items') or []):
            fid = it.get('food_id')
            if not fid:
                continue
            slot = it.get('meal_slot', 'lunch')
            if slot not in ('breakfast', 'lunch', 'dinner', 'snack'):
                slot = 'lunch'
            qty = max(0.1, _safe_float(it.get('quantity', 1), 1))
            c.execute(
                'INSERT INTO meal_plan_items (plan_id, food_id, meal_slot, quantity) VALUES (?,?,?,?)',
                (plan_id, fid, slot, qty),
            )

    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã cập nhật thực đơn!'}


def delete_meal_plan(plan_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM meal_plan_items WHERE plan_id=?', (plan_id,))
    c.execute('DELETE FROM meal_plans WHERE id=?', (plan_id,))
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã xóa thực đơn!'}


def add_food_to_plan(plan_id, food_id, meal_slot='lunch', quantity=1):
    if meal_slot not in ('breakfast', 'lunch', 'dinner', 'snack'):
        meal_slot = 'lunch'
    quantity = max(0.1, _safe_float(quantity, 1))
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM meal_plans WHERE id=?', (plan_id,))
    if not c.fetchone():
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy thực đơn'}
    c.execute('SELECT id FROM foods WHERE id=?', (food_id,))
    if not c.fetchone():
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy món ăn'}
    c.execute(
        'INSERT INTO meal_plan_items (plan_id, food_id, meal_slot, quantity) VALUES (?,?,?,?)',
        (plan_id, food_id, meal_slot, quantity),
    )
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã thêm món vào thực đơn'}


def remove_food_from_plan(item_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM meal_plan_items WHERE id=?', (item_id,))
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã gỡ món khỏi thực đơn'}
