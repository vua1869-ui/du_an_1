from database.db_core import get_db_connection

def log_water(user_id, amount_ml, date_str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO water_logs (user_id, amount_ml, date) VALUES (?, ?, ?)', (user_id, amount_ml, date_str))
    conn.commit()
    
    c.execute('SELECT SUM(amount_ml) FROM water_logs WHERE user_id=? AND date=?', (user_id, date_str))
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