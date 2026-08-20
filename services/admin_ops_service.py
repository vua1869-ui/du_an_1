"""Admin operations: audit, backup, health, system logs, settings, notifications, user analytics."""
from database.db_core import get_db_connection
from datetime import datetime, date, timedelta
from flask import request, session
import os
import shutil
import sys
import platform
import time

APP_VERSION = '1.2.0'
_APP_START = time.time()
BACKUP_DIR = os.path.join('data', 'backups')


def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# ═══════════════════════════════════════════
# AUDIT LOG
# ═══════════════════════════════════════════

def write_audit(action, resource=None, resource_id=None, status='success',
                error_message='', detail='', admin_id=None, admin_email=None):
    try:
        admin_id = admin_id or session.get('user_id')
        admin_email = admin_email or session.get('email') or ''
        ip = ''
        try:
            ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')[:80]
        except Exception:
            pass
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            '''INSERT INTO audit_logs
               (admin_id, admin_email, action, resource, resource_id, status,
                error_message, ip_address, detail, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (admin_id, admin_email, action, resource or '', str(resource_id or ''),
             status, (error_message or '')[:500], ip, (detail or '')[:1000], _now()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f'[WARN] audit: {e}')


def get_audit_logs(q=None, admin_id=None, action=None, status=None,
                   date_from=None, date_to=None, page=1, per_page=30):
    conn = get_db_connection()
    c = conn.cursor()
    sql = 'SELECT id, admin_id, admin_email, action, resource, resource_id, status, error_message, ip_address, detail, created_at FROM audit_logs WHERE 1=1'
    params = []
    if q:
        sql += ' AND (LOWER(action) LIKE ? OR LOWER(resource) LIKE ? OR LOWER(COALESCE(admin_email,"")) LIKE ? OR LOWER(detail) LIKE ?)'
        like = f'%{q.lower()}%'
        params.extend([like, like, like, like])
    if admin_id:
        sql += ' AND admin_id=?'
        params.append(int(admin_id))
    if action:
        sql += ' AND action=?'
        params.append(action)
    if status in ('success', 'failure'):
        sql += ' AND status=?'
        params.append(status)
    if date_from:
        sql += ' AND created_at >= ?'
        params.append(date_from)
    if date_to:
        sql += ' AND created_at <= ?'
        params.append(date_to + ' 23:59:59' if len(date_to) == 10 else date_to)

    count_sql = sql.replace(
        'SELECT id, admin_id, admin_email, action, resource, resource_id, status, error_message, ip_address, detail, created_at',
        'SELECT COUNT(*)',
    )
    c.execute(count_sql, params)
    total = c.fetchone()[0]

    page = max(1, int(page or 1))
    per_page = min(100, max(1, int(per_page or 30)))
    sql += ' ORDER BY id DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    return {
        'status': 'success',
        'logs': [
            {
                'id': r[0], 'admin_id': r[1], 'admin_email': r[2],
                'action': r[3], 'resource': r[4], 'resource_id': r[5],
                'status': r[6], 'error_message': r[7], 'ip_address': r[8],
                'detail': r[9], 'created_at': r[10],
            }
            for r in rows
        ],
        'total': total, 'page': page,
        'pages': max(1, (total + per_page - 1) // per_page),
    }


# ═══════════════════════════════════════════
# SYSTEM LOGS
# ═══════════════════════════════════════════

def write_system_log(severity, message, module=None, endpoint=None,
                     status_code=None, detail=''):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            '''INSERT INTO system_logs
               (severity, module, endpoint, status_code, message, detail, created_at)
               VALUES (?,?,?,?,?,?,?)''',
            (severity, module or '', endpoint or '', status_code,
             (message or '')[:500], (detail or '')[:1000], _now()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f'[WARN] system_log: {e}')


def get_system_logs(q=None, severity=None, page=1, per_page=30):
    conn = get_db_connection()
    c = conn.cursor()
    sql = 'SELECT id, severity, module, endpoint, status_code, message, detail, created_at FROM system_logs WHERE 1=1'
    params = []
    if q:
        sql += ' AND (LOWER(message) LIKE ? OR LOWER(COALESCE(module,"")) LIKE ? OR LOWER(COALESCE(endpoint,"")) LIKE ?)'
        like = f'%{q.lower()}%'
        params.extend([like, like, like])
    if severity in ('error', 'warning', 'info'):
        sql += ' AND severity=?'
        params.append(severity)

    count_sql = sql.replace(
        'SELECT id, severity, module, endpoint, status_code, message, detail, created_at',
        'SELECT COUNT(*)',
    )
    c.execute(count_sql, params)
    total = c.fetchone()[0]
    page = max(1, int(page or 1))
    per_page = min(100, max(1, int(per_page or 30)))
    sql += ' ORDER BY id DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    return {
        'status': 'success',
        'logs': [
            {
                'id': r[0], 'severity': r[1], 'module': r[2], 'endpoint': r[3],
                'status_code': r[4], 'message': r[5], 'detail': r[6], 'created_at': r[7],
            }
            for r in rows
        ],
        'total': total, 'page': page,
        'pages': max(1, (total + per_page - 1) // per_page),
    }


# ═══════════════════════════════════════════
# BACKUP
# ═══════════════════════════════════════════

def create_backup(admin_id=None, note=''):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    db_path = os.path.join('data', 'balance_nutrition.db')
    if not os.path.exists(db_path):
        return {'status': 'error', 'message': 'Không tìm thấy database'}
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'backup_{ts}.db'
    dest = os.path.join(BACKUP_DIR, filename)
    try:
        # Online-safe SQLite backup API
        src = get_db_connection()
        dst = __import__('sqlite3').connect(dest)
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
        size = os.path.getsize(dest)
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            'INSERT INTO backups (filename, size_bytes, created_by, created_at, note) VALUES (?,?,?,?,?)',
            (filename, size, admin_id, _now(), (note or '')[:200]),
        )
        bid = c.lastrowid
        conn.commit()
        conn.close()
        write_audit('backup_create', 'backup', bid, detail=filename)
        push_notification('Backup thành công', f'File {filename} ({size // 1024} KB)', 'info')
        return {
            'status': 'success', 'message': 'Đã tạo backup!',
            'id': bid, 'filename': filename, 'size_bytes': size,
        }
    except Exception as e:
        write_audit('backup_create', 'backup', None, status='failure', error_message=str(e)[:200])
        write_system_log('error', f'Backup failed: {e}', module='backup')
        return {'status': 'error', 'message': f'Backup thất bại: {str(e)[:150]}'}


def list_backups():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, filename, size_bytes, created_by, created_at, note FROM backups ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    items = []
    for r in rows:
        path = os.path.join(BACKUP_DIR, r[1])
        exists = os.path.exists(path)
        items.append({
            'id': r[0], 'filename': r[1], 'size_bytes': r[2],
            'created_by': r[3], 'created_at': r[4], 'note': r[5],
            'exists': exists,
        })
    return {'status': 'success', 'backups': items}


def delete_backup(backup_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT filename FROM backups WHERE id=?', (backup_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy backup'}
    filename = row[0]
    # Path traversal guard
    if '..' in filename or '/' in filename or '\\' in filename:
        conn.close()
        return {'status': 'error', 'message': 'Tên file không hợp lệ'}
    path = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception as e:
            conn.close()
            return {'status': 'error', 'message': str(e)[:100]}
    c.execute('DELETE FROM backups WHERE id=?', (backup_id,))
    conn.commit()
    conn.close()
    write_audit('backup_delete', 'backup', backup_id, detail=filename)
    return {'status': 'success', 'message': 'Đã xóa backup'}


def get_backup_path(backup_id):
    """Return safe absolute path for download, or None."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT filename FROM backups WHERE id=?', (backup_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    filename = row[0]
    if '..' in filename or '/' in filename or '\\' in filename:
        return None
    path = os.path.abspath(os.path.join(BACKUP_DIR, filename))
    # Must stay inside BACKUP_DIR
    if not path.startswith(os.path.abspath(BACKUP_DIR)):
        return None
    if not os.path.exists(path):
        return None
    return path


# ═══════════════════════════════════════════
# SYSTEM HEALTH
# ═══════════════════════════════════════════

def get_system_health():
    checks = {}

    # Database
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users')
        user_count = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM foods')
        food_count = c.fetchone()[0]
        conn.close()
        db_path = os.path.join('data', 'balance_nutrition.db')
        size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        checks['database'] = {
            'status': 'OK',
            'message': f'SQLite OK · {user_count} users · {food_count} foods · {size // 1024} KB',
        }
    except Exception as e:
        checks['database'] = {'status': 'ERROR', 'message': str(e)[:120]}

    # Gemini (presence only — never expose key)
    try:
        from ai.rag import client
        if client:
            checks['gemini_api'] = {'status': 'OK', 'message': 'Gemini client đã khởi tạo'}
        else:
            checks['gemini_api'] = {'status': 'WARNING', 'message': 'GEMINI_API_KEY chưa cấu hình'}
    except Exception as e:
        checks['gemini_api'] = {'status': 'ERROR', 'message': str(e)[:120]}

    # Vector DB / RAG
    try:
        from ai.rag import collection
        if collection is not None:
            checks['vector_db'] = {
                'status': 'OK',
                'message': f'ChromaDB OK · {collection.count()} vectors',
            }
        else:
            checks['vector_db'] = {'status': 'WARNING', 'message': 'ChromaDB không khả dụng (optional)'}
    except Exception as e:
        checks['vector_db'] = {'status': 'WARNING', 'message': str(e)[:120]}

    # Roboflow / YOLO
    try:
        from ai.vision import roboflow_client
        if roboflow_client:
            checks['vision_yolo'] = {'status': 'OK', 'message': 'Roboflow client OK'}
        else:
            checks['vision_yolo'] = {'status': 'WARNING', 'message': 'Roboflow chưa cấu hình (fallback Gemini)'}
    except Exception as e:
        checks['vision_yolo'] = {'status': 'WARNING', 'message': str(e)[:100]}

    # Storage
    try:
        data_dir = 'data'
        free = shutil.disk_usage(data_dir).free if os.path.exists(data_dir) else 0
        checks['storage'] = {
            'status': 'OK' if free > 50 * 1024 * 1024 else 'WARNING',
            'message': f'Còn trống ~{free // (1024 * 1024)} MB trên disk',
        }
    except Exception as e:
        checks['storage'] = {'status': 'WARNING', 'message': str(e)[:100]}

    # Runtime
    uptime_s = int(time.time() - _APP_START)
    checks['runtime'] = {
        'status': 'OK',
        'message': f'Python {platform.python_version()} · {platform.system()} · uptime {uptime_s // 3600}h{(uptime_s % 3600) // 60}m',
    }

    overall = 'OK'
    if any(c['status'] == 'ERROR' for c in checks.values()):
        overall = 'ERROR'
    elif any(c['status'] == 'WARNING' for c in checks.values()):
        overall = 'WARNING'

    return {
        'status': 'success',
        'overall': overall,
        'app_version': APP_VERSION,
        'uptime_seconds': uptime_s,
        'checks': checks,
    }


# ═══════════════════════════════════════════
# SETTINGS (safe keys only)
# ═══════════════════════════════════════════

ALLOWED_SETTINGS = {
    'site_name': 'BalanceNutrition AI',
    'site_description': 'Trợ lý dinh dưỡng thông minh',
    'pagination_size': '30',
    'feature_chatbot': '1',
    'feature_vision': '1',
    'feature_rag': '1',
    'maintenance_mode': '0',
}


def get_settings():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT key, value FROM app_settings')
    rows = {r[0]: r[1] for r in c.fetchall()}
    conn.close()
    result = dict(ALLOWED_SETTINGS)
    for k in ALLOWED_SETTINGS:
        if k in rows:
            result[k] = rows[k]
    return {'status': 'success', 'settings': result}


def update_settings(data, admin_id=None):
    if not isinstance(data, dict):
        return {'status': 'error', 'message': 'Dữ liệu không hợp lệ'}
    conn = get_db_connection()
    c = conn.cursor()
    updated = []
    for k, v in data.items():
        if k not in ALLOWED_SETTINGS:
            continue  # ignore unknown / secret keys
        val = str(v)[:500]
        c.execute(
            '''INSERT INTO app_settings (key, value, updated_at, updated_by) VALUES (?,?,?,?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at, updated_by=excluded.updated_by''',
            (k, val, _now(), admin_id),
        )
        updated.append(k)
    conn.commit()
    conn.close()
    write_audit('settings_update', 'settings', None, detail=','.join(updated))
    return {'status': 'success', 'message': f'Đã cập nhật: {", ".join(updated) or "không có thay đổi"}', 'updated': updated}


# ═══════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════

def push_notification(title, message='', severity='info'):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            'INSERT INTO admin_notifications (title, message, severity, is_read, created_at) VALUES (?,?,?,?,?)',
            (title[:200], (message or '')[:500], severity, 0, _now()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f'[WARN] notification: {e}')


def get_notifications(unread_only=False, limit=50):
    conn = get_db_connection()
    c = conn.cursor()
    if unread_only:
        c.execute(
            'SELECT id, title, message, severity, is_read, created_at FROM admin_notifications WHERE is_read=0 ORDER BY id DESC LIMIT ?',
            (limit,),
        )
    else:
        c.execute(
            'SELECT id, title, message, severity, is_read, created_at FROM admin_notifications ORDER BY id DESC LIMIT ?',
            (limit,),
        )
    rows = c.fetchall()
    c.execute('SELECT COUNT(*) FROM admin_notifications WHERE is_read=0')
    unread = c.fetchone()[0]
    conn.close()
    return {
        'status': 'success',
        'unread_count': unread,
        'notifications': [
            {
                'id': r[0], 'title': r[1], 'message': r[2],
                'severity': r[3], 'is_read': bool(r[4]), 'created_at': r[5],
            }
            for r in rows
        ],
    }


def mark_notification_read(nid=None, all_read=False):
    conn = get_db_connection()
    c = conn.cursor()
    if all_read:
        c.execute('UPDATE admin_notifications SET is_read=1')
    elif nid:
        c.execute('UPDATE admin_notifications SET is_read=1 WHERE id=?', (nid,))
    conn.commit()
    conn.close()
    return {'status': 'success'}


# ═══════════════════════════════════════════
# USER ANALYTICS
# ═══════════════════════════════════════════

def get_user_analytics(period='30', date_from=None, date_to=None):
    """period: today|7|30|90|custom"""
    today = date.today()
    if period == 'today':
        d_from = today.isoformat()
        d_to = today.isoformat()
    elif period == '7':
        d_from = (today - timedelta(days=7)).isoformat()
        d_to = today.isoformat()
    elif period == '90':
        d_from = (today - timedelta(days=90)).isoformat()
        d_to = today.isoformat()
    elif period == 'custom' and date_from and date_to:
        d_from, d_to = date_from, date_to
    else:
        d_from = (today - timedelta(days=30)).isoformat()
        d_to = today.isoformat()

    conn = get_db_connection()
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM users WHERE COALESCE(is_active,1)=1')
    active_users = c.fetchone()[0]
    c.execute(
        'SELECT COUNT(*) FROM users WHERE created_at >= ? AND created_at <= ?',
        (d_from, d_to + ' 23:59:59'),
    )
    new_users = c.fetchone()[0]

    # Users who used image analysis
    c.execute(
        '''SELECT COUNT(DISTINCT user_id) FROM analysis_logs
           WHERE user_id IS NOT NULL AND created_at >= ? AND created_at <= ?''',
        (d_from, d_to + ' 23:59:59'),
    )
    users_vision = c.fetchone()[0]

    # Users who used chatbot
    c.execute(
        '''SELECT COUNT(DISTINCT user_id) FROM chat_logs
           WHERE user_id IS NOT NULL AND created_at >= ? AND created_at <= ?''',
        (d_from, d_to + ' 23:59:59'),
    )
    users_chat = c.fetchone()[0]

    # Users with food logs (proxy for "creating menus"/logging)
    c.execute(
        '''SELECT COUNT(DISTINCT user_id) FROM daily_logs
           WHERE date >= ? AND date <= ?''',
        (d_from, d_to),
    )
    users_logging = c.fetchone()[0]

    # Most active by food logs
    c.execute(
        '''SELECT u.id, u.fullname, u.email, COUNT(d.id) as cnt
           FROM daily_logs d JOIN users u ON u.id = d.user_id
           WHERE d.date >= ? AND d.date <= ?
           GROUP BY u.id ORDER BY cnt DESC LIMIT 10''',
        (d_from, d_to),
    )
    most_active = [
        {'id': r[0], 'fullname': r[1], 'email': r[2], 'log_count': r[3]}
        for r in c.fetchall()
    ]

    # New users by day in range
    c.execute(
        '''SELECT DATE(created_at), COUNT(*) FROM users
           WHERE created_at >= ? AND created_at <= ?
           GROUP BY DATE(created_at) ORDER BY 1''',
        (d_from, d_to + ' 23:59:59'),
    )
    registrations = [{'date': r[0], 'count': r[1]} for r in c.fetchall()]

    conn.close()
    return {
        'status': 'success',
        'period': period,
        'date_from': d_from,
        'date_to': d_to,
        'total_users': total_users,
        'active_users': active_users,
        'new_users': new_users,
        'users_vision': users_vision,
        'users_chat': users_chat,
        'users_logging': users_logging,
        'most_active': most_active,
        'registrations': registrations,
    }
