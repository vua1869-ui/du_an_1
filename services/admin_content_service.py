"""Admin nâng cao: articles, FAQ, chatbot logs, AI monitoring, knowledge base, import foods."""
from database.db_core import get_db_connection
from utils.helpers import safe_int
from datetime import date, datetime, timedelta
import os
import io


def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _today():
    return date.today().isoformat()


# ═══════════════════════════════════════════
# ARTICLES
# ═══════════════════════════════════════════

VALID_ARTICLE_STATUS = ('draft', 'published')
VALID_CATEGORIES = ('general', 'nutrition', 'weight_loss', 'muscle', 'recipe', 'tips')


def get_articles(q=None, category=None, status=None, page=1, per_page=20):
    conn = get_db_connection()
    c = conn.cursor()
    sql = '''SELECT a.id, a.title, a.content, a.cover_image, a.category, a.status,
                    a.author_id, a.created_at, a.updated_at, u.fullname
             FROM articles a LEFT JOIN users u ON u.id = a.author_id WHERE 1=1'''
    params = []
    if q:
        sql += ' AND (LOWER(a.title) LIKE ? OR LOWER(a.content) LIKE ?)'
        like = f'%{q.lower()}%'
        params.extend([like, like])
    if category and category != 'all':
        sql += ' AND a.category=?'
        params.append(category)
    if status and status in VALID_ARTICLE_STATUS:
        sql += ' AND a.status=?'
        params.append(status)

    count_sql = 'SELECT COUNT(*) FROM articles a WHERE 1=1'
    count_params = []
    if q:
        count_sql += ' AND (LOWER(a.title) LIKE ? OR LOWER(a.content) LIKE ?)'
        like = f'%{q.lower()}%'
        count_params.extend([like, like])
    if category and category != 'all':
        count_sql += ' AND a.category=?'
        count_params.append(category)
    if status and status in VALID_ARTICLE_STATUS:
        count_sql += ' AND a.status=?'
        count_params.append(status)
    c.execute(count_sql, count_params)
    total = c.fetchone()[0]

    page = max(1, int(page or 1))
    per_page = min(50, max(1, int(per_page or 20)))
    sql += ' ORDER BY a.id DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    return {
        'status': 'success',
        'articles': [
            {
                'id': r[0], 'title': r[1],
                'content': r[2][:200] + ('...' if r[2] and len(r[2]) > 200 else ''),
                'full_content': r[2],
                'cover_image': r[3] or '',
                'category': r[4], 'status': r[5],
                'author_id': r[6], 'created_at': r[7], 'updated_at': r[8],
                'author_name': r[9] or 'Admin',
            }
            for r in rows
        ],
        'total': total, 'page': page, 'per_page': per_page,
        'pages': max(1, (total + per_page - 1) // per_page),
    }


def get_article(article_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT a.id, a.title, a.content, a.cover_image, a.category, a.status,
                        a.author_id, a.created_at, a.updated_at, u.fullname
                 FROM articles a LEFT JOIN users u ON u.id = a.author_id WHERE a.id=?''', (article_id,))
    r = c.fetchone()
    conn.close()
    if not r:
        return {'status': 'error', 'message': 'Không tìm thấy bài viết'}
    return {
        'status': 'success',
        'article': {
            'id': r[0], 'title': r[1], 'content': r[2], 'cover_image': r[3] or '',
            'category': r[4], 'status': r[5], 'author_id': r[6],
            'created_at': r[7], 'updated_at': r[8], 'author_name': r[9] or 'Admin',
        },
    }


def create_article(data, author_id):
    title = (data.get('title') or '').strip()
    if not title:
        return {'status': 'error', 'message': 'Tiêu đề không được trống'}
    content = (data.get('content') or '').strip()
    category = data.get('category', 'general')
    if category not in VALID_CATEGORIES:
        category = 'general'
    status = data.get('status', 'draft')
    if status not in VALID_ARTICLE_STATUS:
        status = 'draft'
    cover = (data.get('cover_image') or '').strip()[:500]
    now = _now()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO articles (title, content, cover_image, category, status, author_id, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?)''',
        (title, content, cover, category, status, author_id, now, now),
    )
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã tạo bài viết!', 'id': new_id}


def update_article(article_id, data):
    title = (data.get('title') or '').strip()
    if not title:
        return {'status': 'error', 'message': 'Tiêu đề không được trống'}
    content = (data.get('content') or '').strip()
    category = data.get('category', 'general')
    if category not in VALID_CATEGORIES:
        category = 'general'
    status = data.get('status', 'draft')
    if status not in VALID_ARTICLE_STATUS:
        status = 'draft'
    cover = (data.get('cover_image') or '').strip()[:500]
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM articles WHERE id=?', (article_id,))
    if not c.fetchone():
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy bài viết'}
    c.execute(
        '''UPDATE articles SET title=?, content=?, cover_image=?, category=?, status=?, updated_at=?
           WHERE id=?''',
        (title, content, cover, category, status, _now(), article_id),
    )
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã cập nhật bài viết!'}


def delete_article(article_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM articles WHERE id=?', (article_id,))
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã xóa bài viết!'}


def get_published_articles(limit=10):
    """Public API cho user — chỉ bài published."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        '''SELECT id, title, content, cover_image, category, created_at
           FROM articles WHERE status='published' ORDER BY id DESC LIMIT ?''',
        (limit,),
    )
    rows = c.fetchall()
    conn.close()
    return {
        'status': 'success',
        'articles': [
            {
                'id': r[0], 'title': r[1],
                'excerpt': (r[2] or '')[:160] + '...',
                'cover_image': r[3] or '', 'category': r[4], 'created_at': r[5],
            }
            for r in rows
        ],
    }


# ═══════════════════════════════════════════
# FAQ
# ═══════════════════════════════════════════

def get_faqs(active_only=False):
    conn = get_db_connection()
    c = conn.cursor()
    if active_only:
        c.execute(
            'SELECT id, question, answer, sort_order, is_active, created_at, updated_at FROM faqs WHERE is_active=1 ORDER BY sort_order ASC, id ASC'
        )
    else:
        c.execute(
            'SELECT id, question, answer, sort_order, is_active, created_at, updated_at FROM faqs ORDER BY sort_order ASC, id ASC'
        )
    rows = c.fetchall()
    conn.close()
    return {
        'status': 'success',
        'faqs': [
            {
                'id': r[0], 'question': r[1], 'answer': r[2],
                'sort_order': r[3], 'is_active': bool(r[4]),
                'created_at': r[5], 'updated_at': r[6],
            }
            for r in rows
        ],
    }


def create_faq(data):
    q = (data.get('question') or '').strip()
    a = (data.get('answer') or '').strip()
    if not q or not a:
        return {'status': 'error', 'message': 'Câu hỏi và câu trả lời không được trống'}
    sort_order = safe_int(data.get('sort_order', 0))
    is_active = 1 if data.get('is_active', True) else 0
    now = _now()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        'INSERT INTO faqs (question, answer, sort_order, is_active, created_at, updated_at) VALUES (?,?,?,?,?,?)',
        (q, a, sort_order, is_active, now, now),
    )
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã thêm FAQ!', 'id': new_id}


def update_faq(faq_id, data):
    q = (data.get('question') or '').strip()
    a = (data.get('answer') or '').strip()
    if not q or not a:
        return {'status': 'error', 'message': 'Câu hỏi và câu trả lời không được trống'}
    sort_order = safe_int(data.get('sort_order', 0))
    is_active = 1 if data.get('is_active', True) else 0
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM faqs WHERE id=?', (faq_id,))
    if not c.fetchone():
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy FAQ'}
    c.execute(
        'UPDATE faqs SET question=?, answer=?, sort_order=?, is_active=?, updated_at=? WHERE id=?',
        (q, a, sort_order, is_active, _now(), faq_id),
    )
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã cập nhật FAQ!'}


def delete_faq(faq_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM faqs WHERE id=?', (faq_id,))
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã xóa FAQ!'}


def reorder_faqs(ordered_ids):
    """ordered_ids: list of faq ids theo thứ tự mong muốn."""
    if not isinstance(ordered_ids, list):
        return {'status': 'error', 'message': 'Dữ liệu không hợp lệ'}
    conn = get_db_connection()
    c = conn.cursor()
    for idx, fid in enumerate(ordered_ids):
        c.execute('UPDATE faqs SET sort_order=?, updated_at=? WHERE id=?', (idx, _now(), int(fid)))
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã sắp xếp lại FAQ'}


# ═══════════════════════════════════════════
# CHAT LOGS + KNOWLEDGE BASE
# ═══════════════════════════════════════════

def log_chat(user_id, question, answer, response_type='chat', is_error=False):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            'INSERT INTO chat_logs (user_id, question, answer, response_type, is_error, created_at) VALUES (?,?,?,?,?,?)',
            (user_id, (question or '')[:1000], (answer or '')[:2000], response_type, 1 if is_error else 0, _now()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f'[WARN] log_chat: {e}')


def get_chatbot_stats():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM chat_logs')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM chat_logs WHERE is_error=1')
    errors = c.fetchone()[0]
    c.execute('''SELECT DATE(created_at) as d, COUNT(*) FROM chat_logs
                 WHERE created_at >= date('now', '-14 days')
                 GROUP BY d ORDER BY d''')
    daily = [{'date': r[0], 'count': r[1]} for r in c.fetchall()]
    # Top questions (normalize lowercase, group)
    c.execute('''SELECT LOWER(question), COUNT(*) as cnt FROM chat_logs
                 WHERE question IS NOT NULL AND question != ''
                 GROUP BY LOWER(question) ORDER BY cnt DESC LIMIT 15''')
    top_q = [{'question': r[0], 'count': r[1]} for r in c.fetchall()]
    # Recent errors / poor answers
    c.execute('''SELECT id, question, answer, created_at FROM chat_logs
                 WHERE is_error=1 OR answer LIKE '%quá tải%' OR answer LIKE '%Lỗi%' OR answer LIKE '%chưa cấu hình%'
                 ORDER BY id DESC LIMIT 20''')
    poor = [
        {'id': r[0], 'question': r[1], 'answer': (r[2] or '')[:200], 'created_at': r[3]}
        for r in c.fetchall()
    ]
    conn.close()

    # Vector DB status
    chroma_status = {'available': False, 'count': 0, 'message': 'ChromaDB không khả dụng'}
    try:
        from ai.rag import collection
        if collection is not None:
            chroma_status = {
                'available': True,
                'count': collection.count(),
                'message': f'ChromaDB OK · {collection.count()} vectors',
            }
    except Exception as e:
        chroma_status['message'] = str(e)[:120]

    return {
        'status': 'success',
        'total_chats': total,
        'error_chats': errors,
        'success_rate': round((1 - errors / total) * 100, 1) if total else 100,
        'daily': daily,
        'top_questions': top_q,
        'poor_answers': poor,
        'vector_db': chroma_status,
    }


def get_chat_logs(page=1, per_page=30, only_errors=False):
    conn = get_db_connection()
    c = conn.cursor()
    where = 'WHERE is_error=1' if only_errors else ''
    c.execute(f'SELECT COUNT(*) FROM chat_logs {where}')
    total = c.fetchone()[0]
    page = max(1, int(page or 1))
    per_page = min(100, max(1, int(per_page or 30)))
    c.execute(
        f'''SELECT id, user_id, question, answer, response_type, is_error, created_at
            FROM chat_logs {where} ORDER BY id DESC LIMIT ? OFFSET ?''',
        (per_page, (page - 1) * per_page),
    )
    rows = c.fetchall()
    conn.close()
    return {
        'status': 'success',
        'logs': [
            {
                'id': r[0], 'user_id': r[1], 'question': r[2],
                'answer': (r[3] or '')[:300], 'response_type': r[4],
                'is_error': bool(r[5]), 'created_at': r[6],
            }
            for r in rows
        ],
        'total': total, 'page': page, 'pages': max(1, (total + per_page - 1) // per_page),
    }


def get_knowledge_docs():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        'SELECT id, title, content, source, is_indexed, created_at, updated_at FROM knowledge_docs ORDER BY id DESC'
    )
    rows = c.fetchall()
    conn.close()
    return {
        'status': 'success',
        'docs': [
            {
                'id': r[0], 'title': r[1],
                'content': r[2][:300] + ('...' if len(r[2] or '') > 300 else ''),
                'full_content': r[2],
                'source': r[3], 'is_indexed': bool(r[4]),
                'created_at': r[5], 'updated_at': r[6],
            }
            for r in rows
        ],
    }


def create_knowledge_doc(data):
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    if not title or not content:
        return {'status': 'error', 'message': 'Tiêu đề và nội dung không được trống'}
    now = _now()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        'INSERT INTO knowledge_docs (title, content, source, is_indexed, created_at, updated_at) VALUES (?,?,?,?,?,?)',
        (title, content, data.get('source', 'manual'), 0, now, now),
    )
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    # Try index
    indexed = _index_doc(new_id, title, content)
    return {
        'status': 'success',
        'message': 'Đã thêm tài liệu!' + (' (đã index)' if indexed else ' (chưa index — ChromaDB offline)'),
        'id': new_id,
        'indexed': indexed,
    }


def update_knowledge_doc(doc_id, data):
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    if not title or not content:
        return {'status': 'error', 'message': 'Tiêu đề và nội dung không được trống'}
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM knowledge_docs WHERE id=?', (doc_id,))
    if not c.fetchone():
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy tài liệu'}
    c.execute(
        'UPDATE knowledge_docs SET title=?, content=?, is_indexed=0, updated_at=? WHERE id=?',
        (title, content, _now(), doc_id),
    )
    conn.commit()
    conn.close()
    indexed = _index_doc(doc_id, title, content)
    return {'status': 'success', 'message': 'Đã cập nhật tài liệu!', 'indexed': indexed}


def delete_knowledge_doc(doc_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM knowledge_docs WHERE id=?', (doc_id,))
    conn.commit()
    conn.close()
    try:
        from ai.rag import collection
        if collection is not None:
            collection.delete(ids=[f'kb_{doc_id}'])
    except Exception:
        pass
    return {'status': 'success', 'message': 'Đã xóa tài liệu!'}


def _index_doc(doc_id, title, content):
    try:
        from ai.rag import collection
        if collection is None:
            return False
        try:
            collection.delete(ids=[f'kb_{doc_id}'])
        except Exception:
            pass
        doc_text = f"{title}. {content}"[:2000]
        collection.add(
            documents=[doc_text],
            metadatas=[{'name': title, 'type': 'knowledge', 'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0}],
            ids=[f'kb_{doc_id}'],
        )
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('UPDATE knowledge_docs SET is_indexed=1 WHERE id=?', (doc_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'[WARN] index doc: {e}')
        return False


def reindex_knowledge():
    """Re-index toàn bộ knowledge_docs + foods vào Chroma."""
    try:
        from ai.rag import collection, init_vector_db
        if collection is None:
            return {'status': 'error', 'message': 'ChromaDB không khả dụng'}
        # Re-init foods
        init_vector_db(os.path.join('data', 'balance_nutrition.db'))
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT id, title, content FROM knowledge_docs')
        docs = c.fetchall()
        ok, fail = 0, 0
        for d in docs:
            if _index_doc(d[0], d[1], d[2]):
                ok += 1
            else:
                fail += 1
        conn.close()
        count = collection.count()
        return {
            'status': 'success',
            'message': f'Re-index xong: {ok} docs OK, {fail} lỗi · Vector DB: {count} items',
            'indexed': ok, 'failed': fail, 'vector_count': count,
        }
    except Exception as e:
        return {'status': 'error', 'message': f'Re-index thất bại: {str(e)[:200]}'}


# ═══════════════════════════════════════════
# AI IMAGE ANALYSIS MONITORING
# ═══════════════════════════════════════════

def log_analysis(user_id, dish_name, calories, success, source='unknown', error_message='', duration_ms=0):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            '''INSERT INTO analysis_logs
               (user_id, dish_name, calories, success, source, error_message, duration_ms, created_at)
               VALUES (?,?,?,?,?,?,?,?)''',
            (
                user_id, (dish_name or '')[:200], calories or 0,
                1 if success else 0, source, (error_message or '')[:500],
                int(duration_ms or 0), _now(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f'[WARN] log_analysis: {e}')


def get_ai_monitoring_stats():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM analysis_logs')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM analysis_logs WHERE success=1')
    success = c.fetchone()[0]
    failed = total - success
    c.execute('SELECT AVG(duration_ms) FROM analysis_logs WHERE duration_ms > 0')
    avg_ms = c.fetchone()[0] or 0
    c.execute('''SELECT dish_name, COUNT(*) as cnt FROM analysis_logs
                 WHERE success=1 AND dish_name IS NOT NULL AND dish_name != ''
                 AND dish_name NOT LIKE 'Chưa%' AND dish_name NOT LIKE 'Không%'
                 GROUP BY dish_name ORDER BY cnt DESC LIMIT 15''')
    top_dishes = [{'name': r[0], 'count': r[1]} for r in c.fetchall()]
    c.execute('''SELECT DATE(created_at) as d, COUNT(*),
                        SUM(CASE WHEN success=1 THEN 1 ELSE 0 END)
                 FROM analysis_logs WHERE created_at >= date('now', '-14 days')
                 GROUP BY d ORDER BY d''')
    daily = [{'date': r[0], 'total': r[1], 'success': r[2], 'failed': r[1] - r[2]} for r in c.fetchall()]
    c.execute('''SELECT id, dish_name, source, error_message, duration_ms, created_at, success
                 FROM analysis_logs ORDER BY id DESC LIMIT 30''')
    recent = [
        {
            'id': r[0], 'dish_name': r[1], 'source': r[2],
            'error_message': r[3], 'duration_ms': r[4],
            'created_at': r[5], 'success': bool(r[6]),
        }
        for r in c.fetchall()
    ]
    c.execute('''SELECT source, COUNT(*) FROM analysis_logs GROUP BY source''')
    by_source = {r[0] or 'unknown': r[1] for r in c.fetchall()}
    conn.close()
    return {
        'status': 'success',
        'total': total,
        'success': success,
        'failed': failed,
        'success_rate': round(success / total * 100, 1) if total else 0,
        'avg_duration_ms': round(avg_ms),
        'top_dishes': top_dishes,
        'daily': daily,
        'recent': recent,
        'by_source': by_source,
    }


# ═══════════════════════════════════════════
# IMPORT FOODS FROM CSV/XLSX
# ═══════════════════════════════════════════

def import_foods_from_file(file_storage):
    """Validate & import từ CSV/XLSX. Không ghi dòng lỗi."""
    import pandas as pd

    filename = (file_storage.filename or '').lower()
    try:
        raw = file_storage.read()
        if filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(raw))
        elif filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(raw))
        else:
            return {'status': 'error', 'message': 'Chỉ hỗ trợ .csv, .xlsx, .xls'}
    except Exception as e:
        return {'status': 'error', 'message': f'Không đọc được file: {str(e)[:150]}'}

    if df.empty:
        return {'status': 'error', 'message': 'File trống'}

    # Normalize column names
    col_map = {}
    for col in df.columns:
        cl = str(col).strip().lower()
        if cl in ('ten_mon', 'name', 'tên món', 'ten mon', 'mon_an'):
            col_map[col] = 'name'
        elif cl in ('calo', 'calories', 'calorie', 'kcal'):
            col_map[col] = 'calories'
        elif cl in ('protein', 'đạm', 'dam'):
            col_map[col] = 'protein'
        elif cl in ('carbs', 'carb', 'carbohydrate', 'tinh bột', 'tinh_bot'):
            col_map[col] = 'carbs'
        elif cl in ('fat', 'béo', 'beo', 'chat_beo'):
            col_map[col] = 'fat'
        elif cl in ('fiber', 'chat_xo', 'chất xơ'):
            col_map[col] = 'fiber'
        elif cl in ('loai_bua', 'meal_type', 'bữa', 'bua'):
            col_map[col] = 'meal_type'
        elif cl in ('unit', 'don_vi', 'đơn vị'):
            col_map[col] = 'unit'
        elif cl in ('description', 'mo_ta', 'mô tả'):
            col_map[col] = 'description'

    df = df.rename(columns=col_map)
    if 'name' not in df.columns:
        return {'status': 'error', 'message': 'Thiếu cột tên món (name / ten_mon)'}

    meal_map = {
        'sáng': 'breakfast', 'sang': 'breakfast', 'breakfast': 'breakfast',
        'trưa': 'lunch', 'trua': 'lunch', 'lunch': 'lunch',
        'tối': 'dinner', 'toi': 'dinner', 'dinner': 'dinner',
        'ăn nhẹ': 'snack', 'an nhe': 'snack', 'snack': 'snack',
    }

    conn = get_db_connection()
    c = conn.cursor()
    # Existing names for duplicate detection
    c.execute('SELECT LOWER(name) FROM foods')
    existing = {r[0] for r in c.fetchall() if r[0]}

    success_rows, fail_rows, skip_dup = [], [], []
    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # excel-like
        name = str(row.get('name', '')).strip()
        if not name or name.lower() == 'nan':
            fail_rows.append({'row': row_num, 'reason': 'Tên trống'})
            continue
        try:
            cal = float(row.get('calories', 0) or 0)
            pro = float(row.get('protein', 0) or 0)
            carbs = float(row.get('carbs', 0) or 0)
            fat = float(row.get('fat', 0) or 0)
            fiber = float(row.get('fiber', 0) or 0)
        except (TypeError, ValueError):
            fail_rows.append({'row': row_num, 'name': name, 'reason': 'Số liệu không hợp lệ'})
            continue
        if cal < 0 or pro < 0 or carbs < 0 or fat < 0 or fiber < 0:
            fail_rows.append({'row': row_num, 'name': name, 'reason': 'Giá trị dinh dưỡng âm'})
            continue
        if cal > 10000:
            fail_rows.append({'row': row_num, 'name': name, 'reason': 'Calories quá lớn'})
            continue
        if name.lower() in existing:
            skip_dup.append({'row': row_num, 'name': name, 'reason': 'Trùng tên'})
            continue

        mt_raw = str(row.get('meal_type', 'snack')).strip().lower()
        meal_type = meal_map.get(mt_raw, 'snack')
        unit = str(row.get('unit', 'phần') or 'phần').strip()[:30]
        desc = str(row.get('description', '') or '').strip()[:500]
        if desc.lower() == 'nan':
            desc = ''

        c.execute(
            '''INSERT INTO foods (meal_type, name, calories, protein, carbs, fat, fiber, unit, description)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            (meal_type, name, cal, pro, carbs, fat, fiber, unit, desc),
        )
        existing.add(name.lower())
        success_rows.append({'row': row_num, 'name': name, 'calories': cal})

    conn.commit()
    conn.close()
    return {
        'status': 'success',
        'message': f'Import xong: {len(success_rows)} OK, {len(fail_rows)} lỗi, {len(skip_dup)} trùng',
        'success_count': len(success_rows),
        'fail_count': len(fail_rows),
        'duplicate_count': len(skip_dup),
        'successes': success_rows[:50],
        'failures': fail_rows[:50],
        'duplicates': skip_dup[:50],
    }


# ═══════════════════════════════════════════
# ADVANCED DASHBOARD STATS
# ═══════════════════════════════════════════

def get_advanced_stats():
    conn = get_db_connection()
    c = conn.cursor()

    # Registrations last 30 days
    c.execute('''SELECT DATE(created_at) as d, COUNT(*) FROM users
                 WHERE created_at IS NOT NULL AND created_at >= date('now', '-30 days')
                 GROUP BY d ORDER BY d''')
    registrations = [{'date': r[0], 'count': r[1]} for r in c.fetchall()]

    # Analysis per day
    c.execute('''SELECT DATE(created_at), COUNT(*), SUM(success)
                 FROM analysis_logs WHERE created_at >= date('now', '-14 days')
                 GROUP BY DATE(created_at) ORDER BY 1''')
    analysis_daily = [{'date': r[0], 'total': r[1], 'success': r[2] or 0} for r in c.fetchall()]

    # Chat per day
    c.execute('''SELECT DATE(created_at), COUNT(*) FROM chat_logs
                 WHERE created_at >= date('now', '-14 days')
                 GROUP BY DATE(created_at) ORDER BY 1''')
    chat_daily = [{'date': r[0], 'count': r[1]} for r in c.fetchall()]

    # Popular foods from daily_logs
    c.execute('''SELECT name, COUNT(*) as cnt, AVG(calories) FROM daily_logs
                 WHERE name IS NOT NULL GROUP BY name ORDER BY cnt DESC LIMIT 10''')
    popular_foods = [{'name': r[0], 'count': r[1], 'avg_calories': round(r[2] or 0)} for r in c.fetchall()]

    # Popular meal plans
    c.execute('SELECT name, goal, target_calories FROM meal_plans ORDER BY id DESC LIMIT 10')
    popular_plans = [{'name': r[0], 'goal': r[1], 'target_calories': r[2]} for r in c.fetchall()]

    # Top AI dishes
    c.execute('''SELECT dish_name, COUNT(*) FROM analysis_logs
                 WHERE success=1 AND dish_name IS NOT NULL AND dish_name != ''
                 GROUP BY dish_name ORDER BY 2 DESC LIMIT 10''')
    top_ai = [{'name': r[0], 'count': r[1]} for r in c.fetchall()]

    # AI success rate
    c.execute('SELECT COUNT(*), SUM(success) FROM analysis_logs')
    row = c.fetchone()
    ai_total, ai_ok = row[0] or 0, row[1] or 0

    # Content counts
    c.execute('SELECT COUNT(*) FROM articles')
    articles_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM faqs')
    faqs_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM knowledge_docs')
    kb_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM chat_logs')
    chat_count = c.fetchone()[0]

    conn.close()
    return {
        'status': 'success',
        'registrations': registrations,
        'analysis_daily': analysis_daily,
        'chat_daily': chat_daily,
        'popular_foods': popular_foods,
        'popular_plans': popular_plans,
        'top_ai_dishes': top_ai,
        'ai_total': ai_total,
        'ai_success': ai_ok,
        'ai_success_rate': round(ai_ok / ai_total * 100, 1) if ai_total else 0,
        'articles_count': articles_count,
        'faqs_count': faqs_count,
        'kb_count': kb_count,
        'chat_count': chat_count,
    }
