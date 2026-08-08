# File: services/weight_service.py
from database.db_core import get_db_connection
from datetime import date, datetime, timedelta

def add_or_update_weight(user_id, weight_val, record_date):
    conn = get_db_connection()
    c = conn.cursor()
    # Nếu cùng 1 ngày đã nhập rồi thì cập nhật (Chỉnh sửa), chưa có thì thêm mới
    c.execute('SELECT id FROM weight_history WHERE user_id=? AND date=?', (user_id, record_date))
    row = c.fetchone()
    if row:
        c.execute('UPDATE weight_history SET weight=? WHERE id=?', (weight_val, row[0]))
    else:
        c.execute('INSERT INTO weight_history (user_id, weight, date) VALUES (?, ?, ?)', (user_id, weight_val, record_date))
    
    # Đồng bộ cân nặng mới nhất vào hồ sơ User
    c.execute('UPDATE users SET weight=? WHERE id=?', (weight_val, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

def delete_weight(record_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM weight_history WHERE id=?', (record_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

def get_weight_data(user_id, period='30', target_weight=None):
    conn = get_db_connection()
    c = conn.cursor()
    
    if period == 'all':
        c.execute('SELECT id, weight, date FROM weight_history WHERE user_id=? ORDER BY date ASC', (user_id,))
    else:
        days = int(period)
        start_date = (date.today() - timedelta(days=days)).isoformat()
        c.execute('SELECT id, weight, date FROM weight_history WHERE user_id=? AND date >= ? ORDER BY date ASC', (user_id, start_date))
    
    records = c.fetchall()
    conn.close()

    if not records:
        return {"status": "success", "records": [], "stats": None}

    # AI TÍNH TOÁN CÁC CHỈ SỐ
    first_weight = records[0][1]
    last_weight = records[-1][1]
    weight_diff = last_weight - first_weight
    
    start_date = datetime.strptime(records[0][2], '%Y-%m-%d')
    end_date = datetime.strptime(records[-1][2], '%Y-%m-%d')
    days_diff = (end_date - start_date).days
    
    speed = 0
    prediction = "Cần thêm thời gian"
    
    if days_diff > 0:
        speed = abs(weight_diff) / (days_diff / 7.0) # Tính tốc độ kg/tuần
        
        if target_weight and speed > 0:
            target = float(target_weight)
            # Chỉ dự đoán nếu đang đi đúng hướng (Đang giảm & Mục tiêu thấp hơn HT, hoặc ngược lại)
            if (weight_diff < 0 and target < last_weight) or (weight_diff > 0 and target > last_weight):
                remaining_kg = abs(last_weight - target)
                weeks_needed = remaining_kg / speed
                predicted_date = date.today() + timedelta(days=int(weeks_needed * 7))
                prediction = predicted_date.strftime('%d/%m/%Y')
            elif target == last_weight:
                prediction = "Đã đạt mục tiêu! 🎉"
            else:
                prediction = "Đang đi ngược hướng ⚠️"

    stats = {
        "weight_diff": round(weight_diff, 2),
        "speed": round(speed, 2),
        "prediction": prediction
    }
    
    return {
        "status": "success", 
        "records": [{"id": r[0], "weight": r[1], "date": r[2]} for r in records],
        "stats": stats
    }