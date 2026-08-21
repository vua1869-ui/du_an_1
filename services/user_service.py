from database.db_core import get_db_connection
from datetime import date, timedelta


def _safe_num(v, default=0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def log_food(user_id, food_data):
    conn = get_db_connection()
    c = conn.cursor()

    cals = food_data.get('calories')
    if cals is None:
        cals = food_data.get('cals', 0)

    log_date = food_data.get('date') or date.today().isoformat()
    c.execute(
        '''INSERT INTO daily_logs (user_id, date, meal_type, name, calories, protein, carbs, fat)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (
            user_id, log_date, food_data.get('meal_type', 'snack'),
            food_data.get('name', 'Món ăn'), cals,
            food_data.get('protein', 0), food_data.get('carbs', 0), food_data.get('fat', 0),
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã thêm vào nhật ký!"}


def get_logs_by_date(user_id, date_str=None):
    """Lấy nhật ký theo ngày (mặc định hôm nay)."""
    if not date_str:
        date_str = date.today().isoformat()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        'SELECT id, meal_type, name, calories, protein, carbs, fat FROM daily_logs WHERE user_id=? AND date=? ORDER BY id',
        (user_id, date_str),
    )
    logs = c.fetchall()
    conn.close()
    foods = [
        {
            "id": l[0], "meal_type": l[1], "name": l[2],
            "calories": l[3], "protein": l[4], "carbs": l[5], "fat": l[6],
        }
        for l in logs
    ]
    return {
        "status": "success",
        "date": date_str,
        "is_today": date_str == date.today().isoformat(),
        "foods": foods,
        "totals": {
            "calories": sum(f["calories"] or 0 for f in foods),
            "protein": sum(f["protein"] or 0 for f in foods),
            "carbs": sum(f["carbs"] or 0 for f in foods),
            "fat": sum(f["fat"] or 0 for f in foods),
        },
    }


def get_today_logs(user_id):
    return get_logs_by_date(user_id, date.today().isoformat())


def update_log(user_id, log_id, data):
    """Sửa món đã log."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM daily_logs WHERE id=? AND user_id=?', (log_id, user_id))
    if not c.fetchone():
        conn.close()
        return {"status": "error", "message": "Không tìm thấy món trong nhật ký"}

    name = (data.get('name') or '').strip() or 'Món ăn'
    meal_type = data.get('meal_type') or 'snack'
    if meal_type not in ('breakfast', 'lunch', 'dinner', 'snack'):
        meal_type = 'snack'
    cal = _safe_num(data.get('calories'))
    pro = _safe_num(data.get('protein'))
    carbs = _safe_num(data.get('carbs'))
    fat = _safe_num(data.get('fat'))

    c.execute(
        '''UPDATE daily_logs SET meal_type=?, name=?, calories=?, protein=?, carbs=?, fat=?
           WHERE id=? AND user_id=?''',
        (meal_type, name, cal, pro, carbs, fat, log_id, user_id),
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã cập nhật món ăn"}


def copy_day_logs(user_id, from_date=None, to_date=None):
    """Sao chép nhật ký từ ngày A sang ngày B (mặc định: hôm qua → hôm nay)."""
    if not to_date:
        to_date = date.today().isoformat()
    if not from_date:
        from_date = (date.today() - timedelta(days=1)).isoformat()

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        'SELECT meal_type, name, calories, protein, carbs, fat FROM daily_logs WHERE user_id=? AND date=?',
        (user_id, from_date),
    )
    rows = c.fetchall()
    if not rows:
        conn.close()
        return {"status": "error", "message": f"Không có món nào ngày {from_date} để sao chép"}

    for r in rows:
        c.execute(
            '''INSERT INTO daily_logs (user_id, date, meal_type, name, calories, protein, carbs, fat)
               VALUES (?,?,?,?,?,?,?,?)''',
            (user_id, to_date, r[0], r[1], r[2], r[3], r[4], r[5]),
        )
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "message": f"Đã sao chép {len(rows)} món từ {from_date} sang {to_date}",
        "count": len(rows),
    }


def apply_meal_plan(user_id, plan_id, target_date=None):
    """Áp dụng thực đơn mẫu vào nhật ký ngày chỉ định."""
    if not target_date:
        target_date = date.today().isoformat()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, name FROM meal_plans WHERE id=?', (plan_id,))
    plan = c.fetchone()
    if not plan:
        conn.close()
        return {"status": "error", "message": "Không tìm thấy thực đơn"}

    c.execute(
        '''SELECT mpi.meal_slot, mpi.quantity, f.name, f.calories, f.protein, f.carbs, f.fat
           FROM meal_plan_items mpi
           LEFT JOIN foods f ON f.id = mpi.food_id
           WHERE mpi.plan_id=?''',
        (plan_id,),
    )
    items = c.fetchall()
    if not items:
        conn.close()
        return {"status": "error", "message": "Thực đơn chưa có món nào"}

    slot_map = {
        'breakfast': 'breakfast', 'sang': 'breakfast',
        'lunch': 'lunch', 'trua': 'lunch',
        'dinner': 'dinner', 'toi': 'dinner',
        'snack': 'snack', 'phu': 'snack',
    }
    added = 0
    for it in items:
        slot = (it[0] or 'lunch').lower()
        meal_type = slot_map.get(slot, 'snack')
        qty = float(it[1] or 1)
        name = it[2] or 'Món trong thực đơn'
        if qty != 1:
            name = f"{name} (x{qty:g})"
        cal = round((it[3] or 0) * qty)
        pro = round((it[4] or 0) * qty, 1)
        carbs = round((it[5] or 0) * qty, 1)
        fat = round((it[6] or 0) * qty, 1)
        c.execute(
            '''INSERT INTO daily_logs (user_id, date, meal_type, name, calories, protein, carbs, fat)
               VALUES (?,?,?,?,?,?,?,?)''',
            (user_id, target_date, meal_type, name, cal, pro, carbs, fat),
        )
        added += 1
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "message": f"Đã áp dụng thực đơn «{plan[1]}» — {added} món vào nhật ký",
        "count": added,
        "plan_name": plan[1],
    }


def get_daily_checklist(user_id):
    """Checklist ngày đầu / empty-state insights."""
    today = date.today().isoformat()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM daily_logs WHERE user_id=? AND date=?', (user_id, today))
    meals = c.fetchone()[0]
    try:
        c.execute('SELECT COALESCE(SUM(amount_ml),0) FROM water_logs WHERE user_id=? AND date=?', (user_id, today))
        water = c.fetchone()[0] or 0
    except Exception:
        water = 0
    c.execute('SELECT COUNT(*) FROM weight_logs WHERE user_id=? AND date=?', (user_id, today))
    weighed = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM daily_logs WHERE user_id=?', (user_id,))
    total_logs = c.fetchone()[0]
    conn.close()

    items = [
        {"id": "log_meal", "label": "Ghi ít nhất 1 món ăn", "done": meals >= 1, "hint": "Dùng Log nhanh hoặc quét ảnh"},
        {"id": "drink_water", "label": "Uống ít nhất 500ml nước", "done": water >= 500, "hint": "Bấm +250 / +500 trên dashboard"},
        {"id": "weigh", "label": "Cập nhật cân nặng hôm nay", "done": weighed >= 1, "hint": "Nút Cân nặng trên dashboard"},
        {"id": "three_meals", "label": "Log đủ ≥3 món trong ngày", "done": meals >= 3, "hint": "Bữa sáng / trưa / tối"},
    ]
    reminders = []
    hour = __import__('datetime').datetime.now().hour
    if meals == 0 and hour >= 10:
        reminders.append("Bạn chưa log bữa nào hôm nay — thử Log nhanh nhé!")
    if water < 500 and hour >= 12:
        reminders.append(f"Mới uống {water}ml nước. Bổ sung thêm 1–2 ly nhé.")
    if meals > 0 and meals < 3 and hour >= 18:
        reminders.append("Còn thiếu bữa tối trong nhật ký?")

    return {
        "status": "success",
        "is_new_user": total_logs == 0,
        "checklist": items,
        "reminders": reminders,
        "meals_today": meals,
        "water_today": water,
    }

def get_weekly_stats(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    today = date.today()
    dates, calories = [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        dates.append(day.strftime('%d/%m')) 
        c.execute('SELECT SUM(calories) FROM daily_logs WHERE user_id=? AND date=?', (user_id, day.isoformat()))
        total_cal = c.fetchone()[0] or 0
        calories.append(total_cal)
    conn.close()
    return {"dates": dates, "calories": calories}

def delete_log(user_id, log_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM daily_logs WHERE id=? AND user_id=?', (log_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã xóa món ăn khỏi nhật ký!"}

def search_foods(query, limit=20):
    """Tìm món trong CSDL theo tên — hỗ trợ log nhanh không cần quét ảnh."""
    conn = get_db_connection()
    c = conn.cursor()
    q = f"%{(query or '').strip()}%"
    if query and query.strip():
        c.execute("""SELECT id, meal_type, name, calories, protein, carbs, fat FROM foods
                     WHERE name LIKE ? ORDER BY name LIMIT ?""", (q, limit))
    else:
        c.execute("""SELECT id, meal_type, name, calories, protein, carbs, fat FROM foods
                     ORDER BY id DESC LIMIT ?""", (limit,))
    rows = c.fetchall()
    conn.close()
    return {
        "status": "success",
        "foods": [{"id": r[0], "meal_type": r[1], "name": r[2], "calories": r[3],
                   "protein": r[4], "carbs": r[5], "fat": r[6]} for r in rows]
    }

def get_recent_foods(user_id, limit=8):
    """Món gần đây / hay ăn — gợi ý log nhanh."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""SELECT name, meal_type, calories, protein, carbs, fat, COUNT(*) as cnt
                 FROM daily_logs WHERE user_id=?
                 GROUP BY name ORDER BY cnt DESC, MAX(id) DESC LIMIT ?""", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return {
        "status": "success",
        "foods": [{"name": r[0], "meal_type": r[1], "calories": r[2], "protein": r[3],
                   "carbs": r[4], "fat": r[5], "times": r[6]} for r in rows]
    }

def get_day_comparison(user_id, target_calories=2000):
    """So sánh hôm nay vs hôm qua — insight pro."""
    conn = get_db_connection()
    c = conn.cursor()
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    def day_stats(d):
        c.execute("""SELECT COALESCE(SUM(calories),0), COALESCE(SUM(protein),0),
                            COALESCE(SUM(carbs),0), COALESCE(SUM(fat),0), COUNT(id)
                     FROM daily_logs WHERE user_id=? AND date=?""", (user_id, d))
        cal, pro, carb, fat, n = c.fetchone()
        try:
            c.execute("SELECT COALESCE(SUM(amount_ml),0) FROM water_logs WHERE user_id=? AND date=?", (user_id, d))
            water = c.fetchone()[0] or 0
        except Exception:
            water = 0
        return {"calories": cal, "protein": pro, "carbs": carb, "fat": fat, "meals": n, "water": water}

    t = day_stats(today)
    y = day_stats(yesterday)
    conn.close()

    cal_diff = t["calories"] - y["calories"]
    if y["meals"] > 0 or y["calories"] > 0:
        if cal_diff > 150:
            insight = f"Hôm nay bạn đang nạp nhiều hơn hôm qua {abs(cal_diff)} kcal."
        elif cal_diff < -150:
            insight = f"Hôm nay bạn đang nạp ít hơn hôm qua {abs(cal_diff)} kcal — kiểm soát tốt!"
        else:
            insight = "Calo hôm nay tương đương hôm qua — duy trì ổn định."
    else:
        insight = "Chưa có dữ liệu hôm qua để so sánh."

    return {
        "status": "success",
        "today": t,
        "yesterday": y,
        "cal_diff": cal_diff,
        "insight": insight,
        "target": target_calories
    }
