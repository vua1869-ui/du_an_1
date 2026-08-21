"""Articles, FAQ, chat/analysis logs, knowledge docs, AI stats, food import."""
from database.db_core import get_db_connection
from datetime import datetime
import csv
import io


def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# ═══════════════════════════════════════════
# ARTICLES
# ═══════════════════════════════════════════

def get_articles(q=None, status=None, category=None, page=1, per_page=30):
    conn = get_db_connection()
    c = conn.cursor()
    sql = '''SELECT id, title, content, cover_image, category, status, author_id, created_at, updated_at
             FROM articles WHERE 1=1'''
    params = []
    if q:
        sql += ' AND (LOWER(title) LIKE ? OR LOWER(content) LIKE ?)'
        like = f'%{q.lower()}%'
        params.extend([like, like])
    if status in ('draft', 'published'):
        sql += ' AND status=?'
        params.append(status)
    if category:
        sql += ' AND category=?'
        params.append(category)

    count_sql = 'SELECT COUNT(*) FROM articles WHERE 1=1'
    cp = []
    if q:
        count_sql += ' AND (LOWER(title) LIKE ? OR LOWER(content) LIKE ?)'
        like = f'%{q.lower()}%'
        cp.extend([like, like])
    if status in ('draft', 'published'):
        count_sql += ' AND status=?'
        cp.append(status)
    if category:
        count_sql += ' AND category=?'
        cp.append(category)
    c.execute(count_sql, cp)
    total = c.fetchone()[0]

    page = max(1, int(page or 1))
    per_page = min(100, max(1, int(per_page or 30)))
    sql += ' ORDER BY id DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    articles = []
    for r in rows:
        articles.append({
            'id': r[0], 'title': r[1],
            'content': (r[2] or '')[:200],
            'full_content': r[2] or '',
            'cover_image': r[3] or '',
            'category': r[4] or 'general',
            'status': r[5] or 'draft',
            'author_id': r[6],
            'created_at': r[7], 'updated_at': r[8],
        })
    return {
        'status': 'success',
        'articles': articles,
        'total': total,
        'page': page,
        'pages': max(1, (total + per_page - 1) // per_page),
    }


def get_article(aid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        'SELECT id, title, content, cover_image, category, status, author_id, created_at, updated_at FROM articles WHERE id=?',
        (aid,),
    )
    r = c.fetchone()
    conn.close()
    if not r:
        return {'status': 'error', 'message': 'Không tìm thấy bài viết'}
    return {
        'status': 'success',
        'article': {
            'id': r[0], 'title': r[1], 'content': r[2] or '',
            'cover_image': r[3] or '', 'category': r[4] or 'general',
            'status': r[5] or 'draft', 'author_id': r[6],
            'created_at': r[7], 'updated_at': r[8],
        },
    }


def create_article(data, author_id=None):
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    if not title:
        return {'status': 'error', 'message': 'Tiêu đề không được trống'}
    status = data.get('status') if data.get('status') in ('draft', 'published') else 'draft'
    category = (data.get('category') or 'general')[:50]
    cover = (data.get('cover_image') or '')[:500]
    now = _now()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO articles (title, content, cover_image, category, status, author_id, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?)''',
        (title, content, cover, category, status, author_id, now, now),
    )
    aid = c.lastrowid
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã tạo bài viết', 'id': aid}


def update_article(aid, data):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM articles WHERE id=?', (aid,))
    if not c.fetchone():
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy bài viết'}
    fields = []
    params = []
    if 'title' in data:
        t = (data.get('title') or '').strip()
        if not t:
            conn.close()
            return {'status': 'error', 'message': 'Tiêu đề không được trống'}
        fields.append('title=?')
        params.append(t)
    if 'content' in data:
        fields.append('content=?')
        params.append(data.get('content') or '')
    if 'cover_image' in data:
        fields.append('cover_image=?')
        params.append((data.get('cover_image') or '')[:500])
    if 'category' in data:
        fields.append('category=?')
        params.append((data.get('category') or 'general')[:50])
    if 'status' in data and data['status'] in ('draft', 'published'):
        fields.append('status=?')
        params.append(data['status'])
    if not fields:
        conn.close()
        return {'status': 'error', 'message': 'Không có dữ liệu cập nhật'}
    fields.append('updated_at=?')
    params.append(_now())
    params.append(aid)
    c.execute(f"UPDATE articles SET {', '.join(fields)} WHERE id=?", params)
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã cập nhật bài viết'}


def delete_article(aid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM articles WHERE id=?', (aid,))
    conn.commit()
    n = c.rowcount
    conn.close()
    if n == 0:
        return {'status': 'error', 'message': 'Không tìm thấy bài viết'}
    return {'status': 'success', 'message': 'Đã xóa bài viết'}


def get_published_articles(limit=20):
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
                'content': (r[2] or '')[:300],
                'cover_image': r[3] or '',
                'category': r[4] or '',
                'created_at': r[5],
            }
            for r in rows
        ],
    }


# ═══════════════════════════════════════════
# FAQ
# ═══════════════════════════════════════════

def get_faqs(active_only=True):
    conn = get_db_connection()
    c = conn.cursor()
    if active_only:
        c.execute(
            'SELECT id, question, answer, sort_order, is_active, created_at FROM faqs WHERE is_active=1 ORDER BY sort_order, id'
        )
    else:
        c.execute(
            'SELECT id, question, answer, sort_order, is_active, created_at FROM faqs ORDER BY sort_order, id'
        )
    rows = c.fetchall()
    conn.close()
    return {
        'status': 'success',
        'faqs': [
            {
                'id': r[0], 'question': r[1], 'answer': r[2],
                'sort_order': r[3], 'is_active': bool(r[4]), 'created_at': r[5],
            }
            for r in rows
        ],
    }


def create_faq(data):
    q = (data.get('question') or '').strip()
    a = (data.get('answer') or '').strip()
    if not q or not a:
        return {'status': 'error', 'message': 'Câu hỏi và trả lời không được trống'}
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COALESCE(MAX(sort_order),0)+1 FROM faqs')
    order = c.fetchone()[0]
    now = _now()
    c.execute(
        'INSERT INTO faqs (question, answer, sort_order, is_active, created_at, updated_at) VALUES (?,?,?,?,?,?)',
        (q, a, order, 1 if data.get('is_active', True) else 0, now, now),
    )
    fid = c.lastrowid
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã thêm FAQ', 'id': fid}


def update_faq(fid, data):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM faqs WHERE id=?', (fid,))
    if not c.fetchone():
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy FAQ'}
    fields, params = [], []
    if 'question' in data:
        fields.append('question=?')
        params.append((data.get('question') or '').strip())
    if 'answer' in data:
        fields.append('answer=?')
        params.append((data.get('answer') or '').strip())
    if 'is_active' in data:
        fields.append('is_active=?')
        params.append(1 if data.get('is_active') else 0)
    if 'sort_order' in data:
        fields.append('sort_order=?')
        params.append(int(data.get('sort_order') or 0))
    fields.append('updated_at=?')
    params.append(_now())
    params.append(fid)
    c.execute(f"UPDATE faqs SET {', '.join(fields)} WHERE id=?", params)
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã cập nhật FAQ'}


def delete_faq(fid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM faqs WHERE id=?', (fid,))
    conn.commit()
    n = c.rowcount
    conn.close()
    return {'status': 'success', 'message': 'Đã xóa FAQ'} if n else {'status': 'error', 'message': 'Không tìm thấy'}


def reorder_faqs(order_list):
    """order_list: [{id, sort_order}, ...]"""
    if not isinstance(order_list, list):
        return {'status': 'error', 'message': 'Dữ liệu không hợp lệ'}
    conn = get_db_connection()
    c = conn.cursor()
    for item in order_list:
        try:
            c.execute(
                'UPDATE faqs SET sort_order=?, updated_at=? WHERE id=?',
                (int(item.get('sort_order', 0)), _now(), int(item['id'])),
            )
        except Exception:
            pass
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã sắp xếp FAQ'}


# ═══════════════════════════════════════════
# CHAT LOGS + SESSIONS (kiểu ChatGPT)
# ═══════════════════════════════════════════

def _make_title_from_question(question, max_len=48):
    q = (question or '').strip().replace('\n', ' ')
    if not q:
        return 'Đoạn chat mới'
    if len(q) <= max_len:
        return q
    return q[: max_len - 1].rstrip() + '…'


def create_chat_session(user_id, title=None):
    if not user_id:
        return {'status': 'error', 'message': 'Chưa đăng nhập'}
    now = _now()
    title = (title or 'Đoạn chat mới').strip()[:120] or 'Đoạn chat mới'
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO chat_sessions (user_id, title, created_at, updated_at) VALUES (?,?,?,?)''',
        (user_id, title, now, now),
    )
    sid = c.lastrowid
    conn.commit()
    conn.close()
    return {
        'status': 'success',
        'session': {
            'id': sid,
            'title': title,
            'created_at': now,
            'updated_at': now,
            'preview': '',
        },
    }


def list_chat_sessions(user_id, limit=40):
    if not user_id:
        return {'status': 'success', 'sessions': []}
    try:
        limit = min(100, max(1, int(limit or 40)))
    except (TypeError, ValueError):
        limit = 40
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        '''SELECT s.id, s.title, s.created_at, s.updated_at,
                  (SELECT question FROM chat_logs WHERE session_id=s.id ORDER BY id ASC LIMIT 1) as first_q
           FROM chat_sessions s
           WHERE s.user_id=?
           ORDER BY s.updated_at DESC, s.id DESC
           LIMIT ?''',
        (user_id, limit),
    )
    rows = c.fetchall()
    conn.close()
    sessions = []
    for r in rows:
        title = r[1] or 'Đoạn chat mới'
        if title == 'Đoạn chat mới' and r[4]:
            title = _make_title_from_question(r[4])
        sessions.append({
            'id': r[0],
            'title': title,
            'created_at': r[2],
            'updated_at': r[3],
            'preview': (r[4] or '')[:80],
        })
    return {'status': 'success', 'sessions': sessions}


def get_session_messages(user_id, session_id, limit=100):
    if not user_id or not session_id:
        return {'status': 'error', 'message': 'Thiếu thông tin', 'logs': []}
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, title FROM chat_sessions WHERE id=? AND user_id=?', (session_id, user_id))
    sess = c.fetchone()
    if not sess:
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy đoạn chat', 'logs': []}
    try:
        limit = min(200, max(1, int(limit or 100)))
    except (TypeError, ValueError):
        limit = 100
    c.execute(
        '''SELECT id, question, answer, response_type, is_error, created_at
           FROM chat_logs WHERE session_id=? AND user_id=?
           ORDER BY id ASC LIMIT ?''',
        (session_id, user_id, limit),
    )
    rows = c.fetchall()
    conn.close()
    return {
        'status': 'success',
        'session': {'id': sess[0], 'title': sess[1] or 'Đoạn chat mới'},
        'logs': [
            {
                'id': r[0],
                'question': r[1],
                'answer': r[2],
                'response_type': r[3],
                'is_error': bool(r[4]),
                'created_at': r[5],
            }
            for r in rows
        ],
    }


def rename_chat_session(user_id, session_id, title):
    title = (title or '').strip()[:120]
    if not title:
        return {'status': 'error', 'message': 'Tiêu đề trống'}
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        'UPDATE chat_sessions SET title=?, updated_at=? WHERE id=? AND user_id=?',
        (title, _now(), session_id, user_id),
    )
    ok = c.rowcount > 0
    conn.commit()
    conn.close()
    if not ok:
        return {'status': 'error', 'message': 'Không tìm thấy đoạn chat'}
    return {'status': 'success', 'message': 'Đã đổi tên', 'title': title}


def delete_chat_session(user_id, session_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM chat_sessions WHERE id=? AND user_id=?', (session_id, user_id))
    if not c.fetchone():
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy đoạn chat'}
    c.execute('DELETE FROM chat_logs WHERE session_id=? AND user_id=?', (session_id, user_id))
    c.execute('DELETE FROM chat_sessions WHERE id=? AND user_id=?', (session_id, user_id))
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã xóa đoạn chat'}


def ensure_chat_session(user_id, session_id=None, first_question=None):
    """Lấy session hiện có hoặc tạo mới. Trả về session_id."""
    if not user_id:
        return None
    conn = get_db_connection()
    c = conn.cursor()
    if session_id:
        c.execute('SELECT id FROM chat_sessions WHERE id=? AND user_id=?', (session_id, user_id))
        if c.fetchone():
            conn.close()
            return int(session_id)
    now = _now()
    title = _make_title_from_question(first_question) if first_question else 'Đoạn chat mới'
    c.execute(
        '''INSERT INTO chat_sessions (user_id, title, created_at, updated_at) VALUES (?,?,?,?)''',
        (user_id, title, now, now),
    )
    sid = c.lastrowid
    conn.commit()
    conn.close()
    return sid


def log_chat(user_id, question, answer, response_type='chat', is_error=False, session_id=None):
    try:
        now = _now()
        # Tự tạo session nếu chưa có
        if user_id and not session_id:
            session_id = ensure_chat_session(user_id, None, question)
        elif user_id and session_id:
            # verify ownership; create if invalid
            session_id = ensure_chat_session(user_id, session_id, question)

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            '''INSERT INTO chat_logs (user_id, question, answer, response_type, is_error, created_at, session_id)
               VALUES (?,?,?,?,?,?,?)''',
            (user_id, (question or '')[:1000], (answer or '')[:2000], response_type or 'chat',
             1 if is_error else 0, now, session_id),
        )
        if session_id and user_id:
            # Cập nhật thời gian + auto title nếu vẫn là mặc định
            c.execute('SELECT title FROM chat_sessions WHERE id=? AND user_id=?', (session_id, user_id))
            row = c.fetchone()
            if row:
                title = row[0] or 'Đoạn chat mới'
                if title in ('Đoạn chat mới', 'New chat', '') and question:
                    title = _make_title_from_question(question)
                    c.execute(
                        'UPDATE chat_sessions SET title=?, updated_at=? WHERE id=?',
                        (title, now, session_id),
                    )
                else:
                    c.execute('UPDATE chat_sessions SET updated_at=? WHERE id=?', (now, session_id))
        conn.commit()
        conn.close()
        return session_id
    except Exception as e:
        print(f'[WARN] log_chat: {e}')
        return session_id


def get_chatbot_stats():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM chat_logs')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM chat_logs WHERE is_error=1')
    errors = c.fetchone()[0]
    c.execute(
        '''SELECT question, COUNT(*) as cnt FROM chat_logs
           GROUP BY question ORDER BY cnt DESC LIMIT 10'''
    )
    popular = [{'question': r[0], 'count': r[1]} for r in c.fetchall()]
    conn.close()
    return {
        'status': 'success',
        'total': total,
        'errors': errors,
        'success': total - errors,
        'popular': popular,
    }


def get_chat_logs(page=1, per_page=30, q=None):
    conn = get_db_connection()
    c = conn.cursor()
    sql = 'SELECT id, user_id, question, answer, response_type, is_error, created_at FROM chat_logs WHERE 1=1'
    params = []
    if q:
        sql += ' AND LOWER(question) LIKE ?'
        params.append(f'%{q.lower()}%')
    c.execute(sql.replace(
        'SELECT id, user_id, question, answer, response_type, is_error, created_at',
        'SELECT COUNT(*)',
    ), params)
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
                'id': r[0], 'user_id': r[1], 'question': r[2], 'answer': r[3],
                'response_type': r[4], 'is_error': bool(r[5]), 'created_at': r[6],
            }
            for r in rows
        ],
        'total': total, 'page': page,
        'pages': max(1, (total + per_page - 1) // per_page),
    }


def get_user_chat_history(user_id, limit=50):
    """Lịch sử chat của một user (mới nhất trước)."""
    if not user_id:
        return {'status': 'success', 'logs': []}
    try:
        limit = min(100, max(1, int(limit or 50)))
    except (TypeError, ValueError):
        limit = 50
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        '''SELECT id, question, answer, response_type, is_error, created_at
           FROM chat_logs WHERE user_id=? ORDER BY id DESC LIMIT ?''',
        (user_id, limit),
    )
    rows = c.fetchall()
    conn.close()
    return {
        'status': 'success',
        'logs': [
            {
                'id': r[0],
                'question': r[1],
                'answer': r[2],
                'response_type': r[3],
                'is_error': bool(r[4]),
                'created_at': r[5],
            }
            for r in rows
        ],
    }


# ═══════════════════════════════════════════
# KNOWLEDGE / RAG DOCS
# ═══════════════════════════════════════════

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
                'content': (r[2] or '')[:200],
                'full_content': r[2] or '',
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
        '''INSERT INTO knowledge_docs (title, content, source, is_indexed, created_at, updated_at)
           VALUES (?,?,?,?,?,?)''',
        (title, content, data.get('source') or 'manual', 0, now, now),
    )
    kid = c.lastrowid
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã thêm tài liệu', 'id': kid}


def update_knowledge_doc(kid, data):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM knowledge_docs WHERE id=?', (kid,))
    if not c.fetchone():
        conn.close()
        return {'status': 'error', 'message': 'Không tìm thấy'}
    fields, params = [], []
    if 'title' in data:
        fields.append('title=?')
        params.append((data.get('title') or '').strip())
    if 'content' in data:
        fields.append('content=?')
        params.append(data.get('content') or '')
        fields.append('is_indexed=?')
        params.append(0)
    fields.append('updated_at=?')
    params.append(_now())
    params.append(kid)
    c.execute(f"UPDATE knowledge_docs SET {', '.join(fields)} WHERE id=?", params)
    conn.commit()
    conn.close()
    return {'status': 'success', 'message': 'Đã cập nhật tài liệu'}


def delete_knowledge_doc(kid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM knowledge_docs WHERE id=?', (kid,))
    conn.commit()
    n = c.rowcount
    conn.close()
    return {'status': 'success', 'message': 'Đã xóa'} if n else {'status': 'error', 'message': 'Không tìm thấy'}


def reindex_knowledge():
    """Đánh dấu re-index; vector DB thực tế phụ thuộc chromadb optional."""
    try:
        from ai.rag import collection, embed_model
        if collection is None:
            return {'status': 'error', 'message': 'ChromaDB không khả dụng'}
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT id, title, content FROM knowledge_docs')
        docs = c.fetchall()
        for d in docs:
            doc_id = f'knowledge_{d[0]}'
            text = f"{d[1]}\n{d[2]}"
            try:
                collection.upsert(documents=[text], ids=[doc_id], metadatas=[{'title': d[1], 'source': 'knowledge'}])
                c.execute('UPDATE knowledge_docs SET is_indexed=1, updated_at=? WHERE id=?', (_now(), d[0]))
            except Exception as e:
                print(f'[WARN] index doc {d[0]}: {e}')
        conn.commit()
        conn.close()
        return {'status': 'success', 'message': f'Đã index {len(docs)} tài liệu', 'count': len(docs)}
    except Exception as e:
        return {'status': 'error', 'message': str(e)[:200]}


# ═══════════════════════════════════════════
# AI ANALYSIS LOGS
# ═══════════════════════════════════════════

def log_analysis(user_id, dish_name, calories=0, success=True, source='', error_message='', duration_ms=0):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            '''INSERT INTO analysis_logs
               (user_id, dish_name, calories, success, source, error_message, duration_ms, created_at)
               VALUES (?,?,?,?,?,?,?,?)''',
            (user_id, (dish_name or '')[:200], float(calories or 0),
             1 if success else 0, (source or '')[:50],
             (error_message or '')[:500], int(duration_ms or 0), _now()),
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
    c.execute(
        '''SELECT dish_name, COUNT(*) as cnt FROM analysis_logs
           WHERE success=1 AND dish_name IS NOT NULL AND dish_name != ''
           GROUP BY dish_name ORDER BY cnt DESC LIMIT 10'''
    )
    top_foods = [{'name': r[0], 'count': r[1]} for r in c.fetchall()]
    c.execute('SELECT AVG(duration_ms) FROM analysis_logs WHERE duration_ms > 0')
    avg_ms = c.fetchone()[0] or 0
    conn.close()
    return {
        'status': 'success',
        'total': total,
        'success': success,
        'failed': failed,
        'top_foods': top_foods,
        'avg_duration_ms': round(avg_ms, 1),
    }


# ═══════════════════════════════════════════
# FOOD IMPORT
# ═══════════════════════════════════════════

def import_foods_from_file(file_storage):
    """Import foods from CSV or XLSX upload."""
    filename = (file_storage.filename or '').lower()
    try:
        if filename.endswith('.csv'):
            raw = file_storage.read()
            try:
                text = raw.decode('utf-8-sig')
            except Exception:
                text = raw.decode('latin-1')
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
        elif filename.endswith(('.xlsx', '.xls')):
            import pandas as pd
            df = pd.read_excel(file_storage)
            rows = df.to_dict(orient='records')
        else:
            return {'status': 'error', 'message': 'Chỉ hỗ trợ CSV hoặc XLSX'}
    except Exception as e:
        return {'status': 'error', 'message': f'Đọc file thất bại: {str(e)[:150]}'}

    if not rows:
        return {'status': 'error', 'message': 'File trống'}

    def _num(v, default=0):
        try:
            if v is None or (isinstance(v, float) and str(v) == 'nan'):
                return default
            n = float(v)
            return n if n >= 0 else default
        except Exception:
            return default

    def _str(v, default=''):
        if v is None:
            return default
        s = str(v).strip()
        return s if s and s.lower() != 'nan' else default

    conn = get_db_connection()
    c = conn.cursor()
    ok, fail = 0, 0
    errors = []
    for i, row in enumerate(rows, start=2):
        # Flexible column names
        name = _str(row.get('name') or row.get('ten') or row.get('tên') or row.get('Name'))
        if not name:
            fail += 1
            errors.append(f'Dòng {i}: thiếu tên món')
            continue
        meal = _str(row.get('meal_type') or row.get('loai') or row.get('bua') or 'snack', 'snack').lower()
        if meal not in ('breakfast', 'lunch', 'dinner', 'snack'):
            meal = 'snack'
        cal = _num(row.get('calories') or row.get('calo') or row.get('Calories'))
        pro = _num(row.get('protein') or row.get('Protein'))
        carb = _num(row.get('carbs') or row.get('carbohydrate') or row.get('carb'))
        fat = _num(row.get('fat') or row.get('Fat'))
        fiber = _num(row.get('fiber') or row.get('chat_xo') or 0)
        unit = _str(row.get('unit') or row.get('don_vi') or 'phần', 'phần')
        desc = _str(row.get('description') or row.get('mo_ta') or '')
        try:
            c.execute(
                '''INSERT INTO foods (meal_type, name, calories, protein, carbs, fat, fiber, unit, description)
                   VALUES (?,?,?,?,?,?,?,?,?)''',
                (meal, name, cal, pro, carb, fat, fiber, unit, desc),
            )
            ok += 1
        except Exception as e:
            fail += 1
            errors.append(f'Dòng {i}: {str(e)[:80]}')
    conn.commit()
    conn.close()
    return {
        'status': 'success' if ok > 0 else 'error',
        'message': f'Import xong: {ok} thành công, {fail} lỗi',
        'ok_count': ok,
        'fail_count': fail,
        'errors': errors[:20],
    }


# ═══════════════════════════════════════════
# ADVANCED STATS (basic, real data only)
# ═══════════════════════════════════════════

def get_advanced_stats():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM foods')
    total_foods = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM meal_plans')
    total_plans = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM articles')
    total_articles = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM chat_logs')
    total_chats = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM analysis_logs')
    total_analysis = c.fetchone()[0]
    conn.close()
    return {
        'status': 'success',
        'total_users': total_users,
        'total_foods': total_foods,
        'total_plans': total_plans,
        'total_articles': total_articles,
        'total_chats': total_chats,
        'total_analysis': total_analysis,
    }
