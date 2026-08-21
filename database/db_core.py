import sqlite3
import pandas as pd
import os
from datetime import date
from utils.helpers import safe_int, guess_meal_type


def get_db_connection():
    db_path = os.path.join('data', 'balance_nutrition.db')
    conn = sqlite3.connect(db_path, timeout=15, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(cursor, table, column):
    cursor.execute(f'PRAGMA table_info({table})')
    return any(row[1] == column for row in cursor.fetchall())


def _migrate_schema(c):
    """Bổ sung cột / bảng mới mà không phá dữ liệu cũ."""
    # --- users ---
    if not _column_exists(c, 'users', 'is_active'):
        c.execute('ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1')
        c.execute('UPDATE users SET is_active=1 WHERE is_active IS NULL')
    if not _column_exists(c, 'users', 'google_id'):
        c.execute('ALTER TABLE users ADD COLUMN google_id TEXT')
    if not _column_exists(c, 'users', 'avatar_url'):
        c.execute('ALTER TABLE users ADD COLUMN avatar_url TEXT')
    try:
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL')
    except Exception:
        pass

    # --- password reset tokens ---
    c.execute('''CREATE TABLE IF NOT EXISTS password_resets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        email TEXT NOT NULL,
        token TEXT NOT NULL UNIQUE,
        expires_at TEXT NOT NULL,
        used INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )''')
    try:
        c.execute('CREATE INDEX IF NOT EXISTS idx_password_resets_token ON password_resets(token)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_password_resets_user ON password_resets(user_id)')
    except Exception:
        pass

    # --- foods ---
    for col, typedef in [
        ('fiber', 'REAL DEFAULT 0'),
        ('unit', "TEXT DEFAULT 'phần'"),
        ('description', "TEXT DEFAULT ''"),
    ]:
        if not _column_exists(c, 'foods', col):
            c.execute(f'ALTER TABLE foods ADD COLUMN {col} {typedef}')

    # --- ingredients ---
    c.execute('''CREATE TABLE IF NOT EXISTS ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        calories REAL DEFAULT 0,
        protein REAL DEFAULT 0,
        carbs REAL DEFAULT 0,
        fat REAL DEFAULT 0,
        fiber REAL DEFAULT 0,
        unit TEXT DEFAULT 'g',
        created_at TEXT
    )''')

    # --- meal plans (thực đơn mẫu do admin quản lý) ---
    c.execute('''CREATE TABLE IF NOT EXISTS meal_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        goal TEXT DEFAULT 'duy_tri',
        target_calories INTEGER DEFAULT 2000,
        description TEXT DEFAULT '',
        created_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS meal_plan_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        food_id INTEGER,
        meal_slot TEXT DEFAULT 'lunch',
        quantity REAL DEFAULT 1,
        FOREIGN KEY (plan_id) REFERENCES meal_plans(id) ON DELETE CASCADE,
        FOREIGN KEY (food_id) REFERENCES foods(id)
    )''')

    # --- Articles (bài viết dinh dưỡng) ---
    c.execute('''CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT DEFAULT '',
        cover_image TEXT DEFAULT '',
        category TEXT DEFAULT 'general',
        status TEXT DEFAULT 'draft',
        author_id INTEGER,
        created_at TEXT,
        updated_at TEXT
    )''')

    # --- FAQ ---
    c.execute('''CREATE TABLE IF NOT EXISTS faqs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT,
        updated_at TEXT
    )''')

    # --- Chat sessions (kiểu ChatGPT) ---
    c.execute('''CREATE TABLE IF NOT EXISTS chat_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT DEFAULT 'Đoạn chat mới',
        created_at TEXT,
        updated_at TEXT
    )''')
    try:
        c.execute('CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated ON chat_sessions(updated_at)')
    except Exception:
        pass

    # --- Chatbot logs ---
    c.execute('''CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        question TEXT,
        answer TEXT,
        response_type TEXT DEFAULT 'chat',
        is_error INTEGER DEFAULT 0,
        created_at TEXT
    )''')
    if not _column_exists(c, 'chat_logs', 'session_id'):
        try:
            c.execute('ALTER TABLE chat_logs ADD COLUMN session_id INTEGER')
        except Exception:
            pass
    try:
        c.execute('CREATE INDEX IF NOT EXISTS idx_chat_logs_session ON chat_logs(session_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_chat_logs_user ON chat_logs(user_id)')
    except Exception:
        pass

    # --- Image analysis logs ---
    c.execute('''CREATE TABLE IF NOT EXISTS analysis_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        dish_name TEXT,
        calories REAL DEFAULT 0,
        success INTEGER DEFAULT 1,
        source TEXT DEFAULT 'unknown',
        error_message TEXT DEFAULT '',
        duration_ms INTEGER DEFAULT 0,
        created_at TEXT
    )''')

    # --- Knowledge base docs for RAG ---
    c.execute('''CREATE TABLE IF NOT EXISTS knowledge_docs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        source TEXT DEFAULT 'manual',
        is_indexed INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    )''')

    # --- Audit logs ---
    c.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        admin_email TEXT,
        action TEXT NOT NULL,
        resource TEXT,
        resource_id TEXT,
        status TEXT DEFAULT 'success',
        error_message TEXT DEFAULT '',
        ip_address TEXT DEFAULT '',
        detail TEXT DEFAULT '',
        created_at TEXT
    )""")

    # --- System / app logs ---
    c.execute("""CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        severity TEXT DEFAULT 'error',
        module TEXT,
        endpoint TEXT,
        status_code INTEGER,
        message TEXT,
        detail TEXT DEFAULT '',
        created_at TEXT
    )""")

    # --- App settings (safe configs only) ---
    c.execute("""CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TEXT,
        updated_by INTEGER
    )""")

    # --- Admin notifications ---
    c.execute("""CREATE TABLE IF NOT EXISTS admin_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        message TEXT,
        severity TEXT DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created_at TEXT
    )""")

    # --- Backup metadata ---
    c.execute("""CREATE TABLE IF NOT EXISTS backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        size_bytes INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TEXT,
        note TEXT DEFAULT ''
    )""")

    # Indexes
    try:
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_foods_name ON foods(name)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_foods_meal ON foods(meal_type)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_daily_logs_user_date ON daily_logs(user_id, date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_chat_logs_created ON chat_logs(created_at)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_analysis_logs_created ON analysis_logs(created_at)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_audit_logs_admin ON audit_logs(admin_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_system_logs_severity ON system_logs(severity)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status)')
    except Exception:
        pass



def init_db(db_path, file_path):
    conn = sqlite3.connect(db_path, timeout=15)
    conn.execute('PRAGMA journal_mode=WAL;')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS foods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meal_type TEXT,
        name TEXT,
        calories INTEGER,
        protein INTEGER,
        carbs INTEGER,
        fat INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, date TEXT, meal_type TEXT, name TEXT,
        calories INTEGER, protein INTEGER, carbs INTEGER, fat INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT, email TEXT UNIQUE, password TEXT,
        role TEXT DEFAULT 'user', nickname TEXT, gender TEXT,
        birth_year INTEGER, height REAL, weight REAL, goal TEXT,
        activity_level TEXT, weekly_goal REAL, bmr REAL, tdee REAL,
        target_calories REAL, created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS weight_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, weight REAL, date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS water_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount_ml INTEGER, date TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, name TEXT, description TEXT, icon TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, achievement_id INTEGER,
        unlocked_at TEXT, UNIQUE(user_id, achievement_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS weight_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, weight REAL, date TEXT
    )''')

    # Migration an toàn
    _migrate_schema(c)

    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        today = date.today().isoformat()
        from services.auth_service import hash_password
        users_data = [
            ('Quản trị viên', 'admin@gmail.com', hash_password('admin123'), 'admin', today),
            ('Lê Văn Quý', 'quy@gmail.com', hash_password('123'), 'user', today),
            ('Vũ Tiến Anh', 'anh@gmail.com', hash_password('456'), 'user', today),
            ('Hoàng Xuân Đức', 'duc@gmail.com', hash_password('789'), 'user', today),
        ]
        c.executemany(
            'INSERT INTO users (fullname, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)',
            users_data,
        )

    c.execute('SELECT COUNT(*) FROM foods')
    if c.fetchone()[0] == 0:
        if os.path.exists(file_path):
            try:
                df = pd.read_excel(file_path)
                meal_map = {'Sáng': 'breakfast', 'Trưa': 'lunch', 'Tối': 'dinner', 'Ăn nhẹ': 'snack'}
                for index, row in df.iterrows():
                    name = str(row.get('ten_mon', f'Món ăn {index}')).strip()
                    loai_bua_vn = str(row.get('loai_bua', 'Ăn nhẹ')).strip()
                    meal_type = meal_map.get(loai_bua_vn, 'snack')
                    c.execute(
                        'INSERT INTO foods (meal_type, name, calories, protein, carbs, fat) VALUES (?,?,?,?,?,?)',
                        (
                            meal_type, name,
                            safe_int(row.get('calo', 0)),
                            safe_int(row.get('protein', 0)),
                            safe_int(row.get('carbs', 0)),
                            safe_int(row.get('fat', 0)),
                        ),
                    )
            except Exception as e:
                print(f"Lỗi khi import dữ liệu Excel: {e}")
        else:
            sample_data = [
                ('breakfast', 'Trứng ốp la + Bánh mì', 350, 15, 30, 10),
                ('lunch', 'Cơm gà xối mỡ', 700, 40, 60, 20),
                ('dinner', 'Salad ức gà', 400, 35, 10, 15),
            ]
            c.executemany(
                'INSERT INTO foods (meal_type, name, calories, protein, carbs, fat) VALUES (?,?,?,?,?,?)',
                sample_data,
            )

    # Seed nguyên liệu mẫu nếu trống
    c.execute('SELECT COUNT(*) FROM ingredients')
    if c.fetchone()[0] == 0:
        today = date.today().isoformat()
        samples = [
            ('Gạo trắng', 130, 2.7, 28, 0.3, 0.4, '100g', today),
            ('Ức gà', 165, 31, 0, 3.6, 0, '100g', today),
            ('Trứng gà', 155, 13, 1.1, 11, 0, '100g', today),
            ('Rau cải', 25, 2.5, 4, 0.3, 2.5, '100g', today),
            ('Dầu oliu', 884, 0, 0, 100, 0, '100g', today),
            ('Khoai tây', 77, 2, 17, 0.1, 2.2, '100g', today),
            ('Cá basa', 90, 15, 0, 3, 0, '100g', today),
            ('Đậu hũ', 76, 8, 1.9, 4.8, 0.4, '100g', today),
        ]
        c.executemany(
            'INSERT INTO ingredients (name, calories, protein, carbs, fat, fiber, unit, created_at) VALUES (?,?,?,?,?,?,?,?)',
            samples,
        )

    conn.commit()
    conn.close()
