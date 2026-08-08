from database.db_core import get_db_connection
from utils.helpers import safe_int

def get_all_foods():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, meal_type, name, calories, protein, carbs, fat FROM foods ORDER BY id DESC')
    foods = c.fetchall()
    conn.close()
    return [{"id": f[0], "meal_type": f[1], "name": f[2], "calories": f[3], "protein": f[4], "carbs": f[5], "fat": f[6]} for f in foods]

def add_new_food(data):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO foods (meal_type, name, calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?, ?)''', (data.get('meal_type', 'snack'), data.get('name'), safe_int(data.get('calories', 0)), safe_int(data.get('protein', 0)), safe_int(data.get('carbs', 0)), safe_int(data.get('fat', 0))))
        new_id = c.lastrowid
        conn.commit()
        conn.close()
        try:
            from ai.rag import collection
            doc_text = f"{data.get('name')} chứa {data.get('calories', 0)} calo."
            collection.add(documents=[doc_text], metadatas=[{"name": data.get('name'), "calories": safe_int(data.get('calories', 0)), "protein": safe_int(data.get('protein', 0)), "carbs": safe_int(data.get('carbs', 0)), "fat": safe_int(data.get('fat', 0))}], ids=[f"food_new_{new_id}"])
        except: pass
        return {"status": "success", "message": "Đã thêm món ăn mới thành công!"}
    except Exception as e: return {"error": f"Có lỗi: {str(e)}"}

def delete_food(food_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM foods WHERE id=?', (food_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Đã xóa món ăn!"}

def get_all_users():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, fullname, email, role, created_at FROM users ORDER BY id DESC')
    users = c.fetchall()
    conn.close()
    return [{"id": u[0], "fullname": u[1], "email": u[2], "role": u[3], "created_at": u[4]} for u in users]

def delete_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}