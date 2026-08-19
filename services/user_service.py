from database.db_core import get_db_connection
from datetime import date, timedelta

def log_food(user_id, food_data):
    conn = get_db_connection()
    c = conn.cursor()

    cals = food_data.get('calories')
    if cals is None:
        cals = food_data.get('cals', 0)
        
    c.execute('''INSERT INTO daily_logs (user_id, date, meal_type, name, calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
              (user_id, date.today().isoformat(), food_data.get('meal_type', 'snack'), food_data.get('name', 'Món ăn'), cals, food_data.get('protein', 0), food_data.get('carbs', 0), food_data.get('fat', 0)))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã thêm vào nhật ký!"}

def get_today_logs(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, meal_type, name, calories, protein, carbs, fat FROM daily_logs WHERE user_id=? AND date=?', 
              (user_id, date.today().isoformat()))
    logs = c.fetchall()
    conn.close()
    
    if not logs:
        return {"foods": [], "totals": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}}
        
    return {
        "foods": [{"id": l[0], "meal_type": l[1], "name": l[2], "calories": l[3], "protein": l[4], "carbs": l[5], "fat": l[6]} for l in logs], 
        "totals": {"calories": sum(l[3] for l in logs), "protein": sum(l[4] for l in logs), "carbs": sum(l[5] for l in logs), "fat": sum(l[6] for l in logs)}
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
