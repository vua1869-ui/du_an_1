from datetime import date, timedelta
from database.db_core import get_db_connection

def init_default_achievements():
    conn = get_db_connection()
    c = conn.cursor()
    defaults = [
        # Khởi đầu
        ('FIRST_BLOOD', 'Khởi Đầu Mới', 'Hoàn thành hồ sơ và đăng nhập lần đầu', '🌟'),
        ('PROFILE_PRO', 'Hồ Sơ Hoàn Hảo', 'Điền đầy đủ thông tin onboarding', '📋'),
        # Nước
        ('WATER_MASTER', 'Vua Nước Lọc', 'Uống đủ 2000ml nước trong một ngày', '🌊'),
        ('WATER_STREAK_3', 'Hydration Hero', 'Uống đủ nước 3 ngày liên tiếp', '💧'),
        ('WATER_STREAK_7', 'Aqua Legend', 'Uống đủ nước 7 ngày liên tiếp', '🏆'),
        # Ăn uống
        ('DIET_PRO', 'Người Chơi Hệ Healthy', 'Thêm món ăn đầu tiên vào nhật ký', '🥗'),
        ('MEAL_5', 'Nhật Ký 5 Món', 'Ghi nhận 5 món ăn trong nhật ký', '🍽️'),
        ('MEAL_20', 'Food Logger', 'Ghi nhận 20 món ăn trong nhật ký', '📓'),
        ('CALORIE_HIT', 'Cân Bằng Calo', 'Nạp đủ 90–110% calo mục tiêu trong ngày', '🎯'),
        ('PROTEIN_KING', 'Vua Protein', 'Đạt ≥90% mục tiêu protein trong ngày', '💪'),
        # Cân nặng
        ('WEIGHT_LOSER', 'Kẻ Hủy Diệt Mỡ', 'Ghi nhận cân nặng lần đầu tiên', '🔥'),
        ('WEIGHT_3', 'Theo Dõi Chuyên Nghiệp', 'Ghi nhận cân nặng 3 lần', '⚖️'),
        # Streak & engagement
        ('STREAK_3', 'Chuỗi 3 Ngày', 'Ghi nhật ký ăn uống 3 ngày liên tiếp', '🔥'),
        ('STREAK_7', 'Tuần Không Nghỉ', 'Ghi nhật ký ăn uống 7 ngày liên tiếp', '📅'),
        ('SCAN_FIRST', 'AI Vision Starter', 'Quét món ăn bằng ảnh lần đầu', '📸'),
        ('CHAT_FIRST', 'Trò Chuyện Với AI', 'Chat với trợ lý dinh dưỡng lần đầu', '💬'),
        # Special
        ('PERFECT_DAY', 'Ngày Hoàn Hảo', 'Đủ nước + đạt 90–110% calo + log ≥3 món', '✨'),
        ('EARLY_BIRD', 'Early Bird', 'Log bữa sáng trước 9h sáng', '🌅'),
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

    c.execute('SELECT a.code FROM user_achievements ua JOIN achievements a ON ua.achievement_id = a.id WHERE ua.user_id = ?', (user_id,))
    unlocked_codes = [row[0] for row in c.fetchall()]

    def unlock(code):
        if code not in unlocked_codes:
            c.execute('SELECT id, name, description, icon FROM achievements WHERE code = ?', (code,))
            ach = c.fetchone()
            if ach:
                c.execute('INSERT INTO user_achievements (user_id, achievement_id, unlocked_at) VALUES (?, ?, ?)', (user_id, ach[0], today))
                newly_unlocked.append({"name": ach[1], "description": ach[2], "icon": ach[3]})
                unlocked_codes.append(code)

    # 1. Đăng nhập / hồ sơ
    unlock('FIRST_BLOOD')
    c.execute('SELECT target_calories, height, weight FROM users WHERE id=?', (user_id,))
    user_row = c.fetchone()
    if user_row and user_row[0] and user_row[1] and user_row[2]:
        unlock('PROFILE_PRO')

    # 2. Nước hôm nay
    c.execute('SELECT SUM(amount_ml) FROM water_logs WHERE user_id=? AND date=?', (user_id, today))
    water_today = c.fetchone()[0] or 0
    if water_today >= 2000:
        unlock('WATER_MASTER')

    # Water streak
    water_streak = 0
    for i in range(14):
        d = (date.today() - timedelta(days=i)).isoformat()
        c.execute('SELECT SUM(amount_ml) FROM water_logs WHERE user_id=? AND date=?', (user_id, d))
        if (c.fetchone()[0] or 0) >= 2000:
            water_streak += 1
        else:
            break
    if water_streak >= 3:
        unlock('WATER_STREAK_3')
    if water_streak >= 7:
        unlock('WATER_STREAK_7')

    # 3. Món ăn
    c.execute('SELECT COUNT(id) FROM daily_logs WHERE user_id=?', (user_id,))
    meal_count = c.fetchone()[0] or 0
    if meal_count >= 1:
        unlock('DIET_PRO')
    if meal_count >= 5:
        unlock('MEAL_5')
    if meal_count >= 20:
        unlock('MEAL_20')

    # Calo & protein hôm nay
    target_cals = 2000
    if user_row and user_row[0]:
        target_cals = float(user_row[0])
    c.execute('SELECT COALESCE(SUM(calories),0), COALESCE(SUM(protein),0), COUNT(id) FROM daily_logs WHERE user_id=? AND date=?', (user_id, today))
    cal_sum, pro_sum, today_meals = c.fetchone()
    if target_cals > 0 and 0.9 * target_cals <= cal_sum <= 1.1 * target_cals:
        unlock('CALORIE_HIT')
    max_p = max(1, round((target_cals * 0.3) / 4))
    if pro_sum >= 0.9 * max_p:
        unlock('PROTEIN_KING')

    # Perfect day
    if water_today >= 2000 and today_meals >= 3 and target_cals > 0 and 0.9 * target_cals <= cal_sum <= 1.1 * target_cals:
        unlock('PERFECT_DAY')

    # Early bird (breakfast before 9 — approximate by having breakfast meal type today; time not stored, so skip strict check)
    c.execute("SELECT COUNT(id) FROM daily_logs WHERE user_id=? AND date=? AND meal_type='breakfast'", (user_id, today))
    if (c.fetchone()[0] or 0) >= 1:
        unlock('EARLY_BIRD')

    # 4. Cân nặng
    c.execute('SELECT COUNT(id) FROM weight_logs WHERE user_id=?', (user_id,))
    w_count = c.fetchone()[0] or 0
    if w_count >= 1:
        unlock('WEIGHT_LOSER')
    if w_count >= 3:
        unlock('WEIGHT_3')

    # 5. Eating streak
    eat_streak = 0
    for i in range(30):
        d = (date.today() - timedelta(days=i)).isoformat()
        c.execute('SELECT COUNT(id) FROM daily_logs WHERE user_id=? AND date=?', (user_id, d))
        if (c.fetchone()[0] or 0) >= 1:
            eat_streak += 1
        else:
            break
    if eat_streak >= 3:
        unlock('STREAK_3')
    if eat_streak >= 7:
        unlock('STREAK_7')

    conn.commit()
    conn.close()
    return {"status": "success", "new_achievements": newly_unlocked, "streak": eat_streak, "water_streak": water_streak}

def get_user_achievements(user_id):
    init_default_achievements()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT a.name, a.description, a.icon, ua.unlocked_at, a.code
        FROM achievements a
        LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_id = ?
        ORDER BY CASE WHEN ua.unlocked_at IS NOT NULL THEN 0 ELSE 1 END, a.id
    ''', (user_id,))
    data = [{"name": r[0], "desc": r[1], "icon": r[2], "unlocked": bool(r[3]), "date": r[3], "code": r[4]} for r in c.fetchall()]
    unlocked_count = sum(1 for d in data if d["unlocked"])
    conn.close()
    return {"status": "success", "achievements": data, "unlocked_count": unlocked_count, "total": len(data)}
