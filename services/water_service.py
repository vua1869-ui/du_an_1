from database.db_core import get_db_connection

def log_water(user_id, amount_ml, date_str):
    """Ghi log nước. amount_ml có thể âm (trừ). Tổng không bao giờ < 0."""
    conn = get_db_connection()
    c = conn.cursor()

    # Nếu trừ, kiểm tra tổng hiện tại để không âm
    if amount_ml < 0:
        c.execute('SELECT COALESCE(SUM(amount_ml),0) FROM water_logs WHERE user_id=? AND date=?', (user_id, date_str))
        current = c.fetchone()[0] or 0
        if current + amount_ml < 0:
            amount_ml = -current  # chỉ trừ xuống 0

    if amount_ml != 0:
        c.execute('INSERT INTO water_logs (user_id, amount_ml, date) VALUES (?, ?, ?)', (user_id, amount_ml, date_str))
        conn.commit()

    c.execute('SELECT COALESCE(SUM(amount_ml),0) FROM water_logs WHERE user_id=? AND date=?', (user_id, date_str))
    total = c.fetchone()[0] or 0
    conn.close()

    return {"status": "success", "total_ml": max(0, total)}

def get_water(user_id, date_str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT SUM(amount_ml) FROM water_logs WHERE user_id=? AND date=?', (user_id, date_str))
    total = c.fetchone()[0] or 0
    conn.close()
    
    return {"status": "success", "total_ml": max(0, total)}