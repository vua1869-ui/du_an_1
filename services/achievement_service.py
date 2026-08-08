from datetime import date
from database.db_core import get_db_connection

def init_default_achievements():
    conn = get_db_connection()
    c = conn.cursor()
    defaults = [
        ('FIRST_BLOOD', 'Khởi Đầu Mới', 'Hoàn thành hồ sơ và đăng nhập lần đầu', '🌟'),
        ('WATER_MASTER', 'Vua Nước Lọc', 'Uống đủ 2000ml nước trong một ngày', '🌊'),
        ('DIET_PRO', 'Người Chơi Hệ Healthy', 'Thêm món ăn đầu tiên vào nhật ký', '🥗'),
        ('WEIGHT_LOSER', 'Kẻ Hủy Diệt Mỡ', 'Ghi nhận cân nặng lần đầu tiên', '🔥')
    ]
    for ach in defaults:
        c.execute('INSERT OR IGNORE INTO achievements (code, name, description, icon) VALUES (?, ?, ?, ?)', ach)
    conn.commit()
    conn.close()

def check_and_unlock(user_id):
    init_default_achievements()
    conn = get_db_connection()
    c = conn.cursor()
    today = date.today().isoformat()
    newly_unlocked = []

    # Lấy danh sách đã mở khóa
    c.execute('SELECT a.code FROM user_achievements ua JOIN achievements a ON ua.achievement_id = a.id WHERE ua.user_id = ?', (user_id,))
    unlocked_codes = [row[0] for row in c.fetchall()]

    def unlock(code):
        if code not in unlocked_codes:
            c.execute('SELECT id, name, description, icon FROM achievements WHERE code = ?', (code,))
            ach = c.fetchone()
            if ach:
                c.execute('INSERT INTO user_achievements (user_id, achievement_id, unlocked_at) VALUES (?, ?, ?)', (user_id, ach[0], today))
                newly_unlocked.append({"name": ach[1], "description": ach[2], "icon": ach[3]})

    # 1. Điều kiện: Đăng nhập
    unlock('FIRST_BLOOD')

    # 2. Điều kiện: Uống đủ nước
    c.execute('SELECT SUM(amount_ml) FROM water_logs WHERE user_id=? AND date=?', (user_id, today))
    if (c.fetchone()[0] or 0) >= 2000:
        unlock('WATER_MASTER')

    # 3. Điều kiện: Thêm món ăn
    c.execute('SELECT COUNT(id) FROM daily_logs WHERE user_id=?', (user_id,))
    if (c.fetchone()[0] or 0) >= 1:
        unlock('DIET_PRO')
        
    # 4. Điều kiện: Khai báo cân nặng
    c.execute('SELECT COUNT(id) FROM weight_logs WHERE user_id=?', (user_id,))
    if (c.fetchone()[0] or 0) >= 1:
        unlock('WEIGHT_LOSER')

    conn.commit()
    conn.close()
    return {"status": "success", "new_achievements": newly_unlocked}

def get_user_achievements(user_id):
    init_default_achievements()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT a.name, a.description, a.icon, ua.unlocked_at
        FROM achievements a
        LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_id = ?
    ''', (user_id,))
    data = [{"name": r[0], "desc": r[1], "icon": r[2], "unlocked": bool(r[3]), "date": r[3]} for r in c.fetchall()]
    conn.close()
    return {"status": "success", "achievements": data}