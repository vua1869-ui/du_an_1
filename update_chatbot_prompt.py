# -*- coding: utf-8 -*-
import re

with open('ai/rag.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_prompt_str = '''
    prompt = f"""
    Bạn là một chuyên gia dinh dưỡng cực kỳ chi tiết và thông minh (NutriBot).
    Nhiệm vụ của bạn là tư vấn dinh dưỡng dựa trên câu hỏi của người dùng.

    Dưới đây là dữ liệu thức ăn được truy xuất từ Cơ sở dữ liệu Vector (RAG) (nếu có):
    {retrieved_context if retrieved_context else "(Không tìm thấy dữ liệu liên quan trong DB, hãy dùng kiến thức chung của bạn)"}
    {logs_context}

    **KỸ THUẬT PHÂN TÍCH (CHAIN OF THOUGHT) BẮT BUỘC KHI NGƯỜI DÙNG KỂ VỀ BỮA ĂN:**
    Nếu người dùng mô tả một bữa ăn (ví dụ: "Tối nay tôi ăn 2 con cá chiên và 1 chén cơm"), bạn PHẢI bóc tách cặn kẽ theo các bước sau trong suy nghĩ và thể hiện ra câu trả lời:
    1. **Đếm số lượng & Định lượng:** (Ví dụ: 2 con cá, 1 chén cơm).
    2. **Xác định phương pháp chế biến:** (Chiên, hấp, luộc, xào). Bắt buộc phải nói rõ phương pháp này ảnh hưởng thế nào đến calo (Ví dụ: cá chiên cộng thêm 150-200 calo từ dầu mỡ so với cá hấp).
    3. **Bóc tách từng món:** Phải gạch đầu dòng rõ ràng từng món, mỗi món bao nhiêu calo, bao nhiêu protein/carbs/fat nếu có thể.
    4. **Tổng kết & Đánh giá:** Cộng tổng calo của bữa ăn, so sánh với TDEE của họ và đưa ra lời khuyên.

    **YÊU CẦU CHUNG:**
    1. Nếu có dữ liệu DB, hãy ưu tiên sử dụng chính xác số liệu đó để trả lời.
    2. Nếu người dùng hỏi "lập thực đơn", BẮT BUỘC trả lời yêu cầu họ cung cấp các nguyên liệu họ đang có hôm nay. TUYỆT ĐỐI KHÔNG bắt người dùng nhập thông tin chiều cao, cân nặng, mục tiêu (vì hệ thống đã lưu).
    3. Nếu họ đã cung cấp nguyên liệu, hãy lập một thực đơn 1 ngày chi tiết (Sáng, Trưa, Tối) dựa trên những nguyên liệu đó.

    Câu hỏi của người dùng: "{user_message}"
    """'''

# Using a more robust regex that ignores minor differences in the old prompt
pattern = re.compile(r'    prompt = f"""\s*Bạn là một chuyên gia dinh dưỡng thông minh và thân thiện.*?Câu hỏi của người dùng: "\{user_message\}"\s*"""', re.DOTALL)

new_content = pattern.sub(new_prompt_str.strip('\n'), content)

with open('ai/rag.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Updated prompt!")

# ============================================================
# ===================== EXTRA TEST CODE ======================
# ==========  ============
# ============================================================

# Test 01
def extra_test_01():
    message = "Hello World"
    return message


# Test 02
def extra_test_02():
    number = 10
    return number


# Test 03
def extra_test_03():
    a = 5
    b = 10
    return a + b


# Test 04
def extra_test_04():
    name = "Python"
    age = 1
    return name, age


# Test 05
def extra_test_05():
    numbers = [1, 2, 3, 4, 5]
    return numbers


# Test 06
def extra_test_06():
    data = {
        "name": "Test",
        "status": "OK",
        "version": 1
    }
    return data


# Test 07
def extra_test_07():
    text = "Testing application"
    return text.upper()


# Test 08
def extra_test_08():
    text = "python programming"
    return text.capitalize()


# Test 09
def extra_test_09():
    numbers = [10, 20, 30, 40, 50]
    return len(numbers)


# Test 10
def extra_test_10():
    numbers = [1, 2, 3, 4, 5]
    return sum(numbers)


# Test 11
def extra_test_11():
    numbers = [5, 10, 15, 20]
    return max(numbers)


# Test 12
def extra_test_12():
    numbers = [5, 10, 15, 20]
    return min(numbers)


# Test 13
def extra_test_13():
    value = 100
    return value > 0


# Test 14
def extra_test_14():
    username = "test_user"
    return username != ""


# Test 15
def extra_test_15():
    items = ["Python", "Flask", "AI", "Git"]
    return "Python" in items


# Test 16
def extra_test_16():
    numbers = []
    for i in range(5):
        numbers.append(i)
    return numbers


# Test 17
def extra_test_17():
    result = []
    for i in range(1, 11):
        result.append(i * 2)
    return result


# Test 18
def extra_test_18():
    words = ["hello", "python", "test"]
    return [word.upper() for word in words]


# Test 19
def extra_test_19():
    status = True

    if status:
        return "System OK"

    return "System Error"


# Test 20
def extra_test_20():
    try:
        number = 100
        result = number / 2
        return result
    except Exception:
        return None


# Test 21
def extra_test_21():
    test_data = {
        "id": 1,
        "name": "Demo",
        "active": True
    }

    return test_data.get("name")


# Test 22
def extra_test_22():
    numbers = [2, 4, 6, 8, 10]

    result = []

    for number in numbers:
        if number % 2 == 0:
            result.append(number)

    return result


# Test 23
def extra_test_23():
    text = " Flask Application "

    return text.strip()


# Test 24
def extra_test_24():
    text = "hello world"

    return text.replace("world", "Python")


# Test 25
def extra_test_25():
    data = {
        "project": "du_an_1",
        "language": "Python",
        "framework": "Flask",
        "status": "testing"
    }

    return data


# Test 26
def extra_test_26():
    numbers = range(1, 6)

    total = 0

    for number in numbers:
        total += number

    return total


# Test 27
def extra_test_27():
    first_name = "Test"
    last_name = "User"

    full_name = first_name + " " + last_name

    return full_name


# Test 28
def extra_test_28():
    value = 50

    if value >= 50:
        return "PASS"

    return "FAIL"


# Test 29
def extra_test_29():
    data = ["AI", "Python", "Machine Learning"]

    for item in data:
        if item:
            continue

    return True


# Test 30
def extra_test_30():
    counter = 0

    for _ in range(10):
        counter += 1

    return counter


# ============================================================
# ===================== END EXTRA TEST =======================
# ============================================================
# ============================================================
# EXTRA TEST FILE
# Phần này độc lập với code chính của dự án
# ============================================================

def test_01():
    return "Test 01 OK"


def test_02():
    return "Test 02 OK"


def test_03():
    return 10 + 20


def test_04():
    number = 100
    return number


def test_05():
    name = "Python"
    return name


def test_06():
    items = ["AI", "Python", "Flask"]
    return items


def test_07():
    data = {
        "project": "DU_AN_1",
        "status": "testing"
    }
    return data


def test_08():
    numbers = [1, 2, 3, 4, 5]
    return sum(numbers)


def test_09():
    numbers = [10, 20, 30, 40, 50]
    return max(numbers)


def test_10():
    numbers = [10, 20, 30, 40, 50]
    return min(numbers)


def test_11():
    text = "hello world"
    return text.upper()


def test_12():
    text = "python application"
    return text.title()


def test_13():
    text = "   test data   "
    return text.strip()


def test_14():
    text = "Python Flask"
    return "Python" in text


def test_15():
    numbers = []

    for number in range(10):
        numbers.append(number)

    return numbers


def test_16():
    result = []

    for number in range(1, 11):
        result.append(number * 2)

    return result


def test_17():
    numbers = [2, 4, 6, 8, 10]

    result = []

    for number in numbers:
        if number % 2 == 0:
            result.append(number)

    return result


def test_18():
    words = [
        "python",
        "flask",
        "database",
        "chatbot",
        "artificial intelligence"
    ]

    return [word.upper() for word in words]


def test_19():
    user = {
        "id": 1,
        "name": "Test User",
        "active": True
    }

    return user.get("name")


def test_20():
    value = 50

    if value >= 50:
        return "PASS"

    return "FAIL"


def test_21():
    counter = 0

    for _ in range(20):
        counter += 1

    return counter


def test_22():
    first_name = "Test"
    last_name = "User"

    full_name = first_name + " " + last_name

    return full_name


def test_23():
    numbers = range(1, 11)

    total = 0

    for number in numbers:
        total += number

    return total


def test_24():
    try:
        result = 100 / 10
        return result
    except Exception:
        return None


def test_25():
    data = {
        "language": "Python",
        "framework": "Flask",
        "database": "SQLite",
        "type": "Test"
    }

    return len(data)


def test_26():
    items = ["A", "B", "C", "D"]

    return len(items)


def test_27():
    numbers = [1, 2, 3, 4, 5]

    return [number ** 2 for number in numbers]


def test_28():
    numbers = [10, 15, 20, 25, 30]

    return [number for number in numbers if number >= 20]


def test_29():
    status = True

    if status:
        return "System is working"

    return "System is not working"


def test_30():
    message = "Application test completed"

    return message


# ============================================================
# ADDITIONAL TEST FUNCTIONS
# ============================================================

def test_31():
    return "Additional test 31"


def test_32():
    return "Additional test 32"


def test_33():
    return "Additional test 33"


def test_34():
    return "Additional test 34"


def test_35():
    return "Additional test 35"


def test_36():
    return 36


def test_37():
    return 37


def test_38():
    return 38


def test_39():
    return 39


def test_40():
    return 40


def test_41():
    data = ["AI", "ML", "Python"]
    return len(data)


def test_42():
    data = {
        "id": 42,
        "status": "OK"
    }
    return data


def test_43():
    text = "extra testing"
    return text.capitalize()


def test_44():
    numbers = [3, 6, 9, 12]
    return sum(numbers)


def test_45():
    return True


def test_46():
    return False


def test_47():
    value = 100
    return value + 50


def test_48():
    value = 200
    return value - 50


def test_49():
    value = 10
    return value * 5


def test_50():
    value = 100
    return value / 10


# ============================================================
# DATA TESTS
# ============================================================

sample_users = [
    {
        "id": 1,
        "name": "User One",
        "active": True
    },
    {
        "id": 2,
        "name": "User Two",
        "active": True
    },
    {
        "id": 3,
        "name": "User Three",
        "active": False
    }
]


sample_products = [
    {
        "id": 101,
        "name": "Product A",
        "price": 100
    },
    {
        "id": 102,
        "name": "Product B",
        "price": 200
    },
    {
        "id": 103,
        "name": "Product C",
        "price": 300
    }
]


sample_messages = [
    "Hello",
    "Welcome",
    "Testing",
    "Python",
    "Flask",
    "Chatbot"
]


# ============================================================
# STRING TESTS
# ============================================================

test_string_01 = "Python"
test_string_02 = "Flask"
test_string_03 = "Chatbot"
test_string_04 = "Artificial Intelligence"
test_string_05 = "Machine Learning"
test_string_06 = "Database"
test_string_07 = "Application"
test_string_08 = "Testing"
test_string_09 = "Development"
test_string_10 = "Programming"


# ============================================================
# NUMBER TESTS
# ============================================================

test_number_01 = 10
test_number_02 = 20
test_number_03 = 30
test_number_04 = 40
test_number_05 = 50
test_number_06 = 60
test_number_07 = 70
test_number_08 = 80
test_number_09 = 90
test_number_10 = 100


# ============================================================
# BOOLEAN TESTS
# ============================================================

test_status_01 = True
test_status_02 = True
test_status_03 = False
test_status_04 = True
test_status_05 = False


# ============================================================
# END EXTRA TEST FILE
# ============================================================