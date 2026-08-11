from database.db_core import get_db_connection
from datetime import date, timedelta

def log_food(food_data):
    conn = get_db_connection()
    c = conn.cursor()

    cals = food_data.get('calories')
    if cals is None:
        cals = food_data.get('cals', 0)
        
    c.execute('''INSERT INTO daily_logs (user_id, date, meal_type, name, calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (1, date.today().isoformat(), food_data.get('meal_type', 'snack'), food_data.get('name', 'Món ăn'), cals, food_data.get('protein', 0), food_data.get('carbs', 0), food_data.get('fat', 0)))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã thêm vào nhật ký!"}

def get_today_logs():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, meal_type, name, calories, protein, carbs, fat FROM daily_logs WHERE user_id=1 AND date=?', (date.today().isoformat(),))
    logs = c.fetchall()
    conn.close()
    return {"foods": [{"id": l[0], "meal_type": l[1], "name": l[2], "calories": l[3], "protein": l[4], "carbs": l[5], "fat": l[6]} for l in logs], "totals": {"calories": sum(l[3] for l in logs), "protein": sum(l[4] for l in logs), "carbs": sum(l[5] for l in logs), "fat": sum(l[6] for l in logs)}}

def get_weekly_stats():
    conn = get_db_connection()
    c = conn.cursor()
    today, dates, calories = date.today(), [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        dates.append(day.strftime('%d/%m')) 
        c.execute('SELECT calories FROM daily_logs WHERE user_id=1 AND date=?', (day.isoformat(),))
        calories.append(sum(log[0] for log in c.fetchall()))
    conn.close()
    return {"dates": dates, "calories": calories}

def delete_log(log_id):
    conn = get_db_connection()
    c = conn.cursor()
    # Xóa bản ghi dựa trên ID (tạm thời để user_id=1 theo cấu trúc hiện tại của bạn)
    c.execute('DELETE FROM daily_logs WHERE id=? AND user_id=1', (log_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã xóa món ăn khỏi nhật ký!"}