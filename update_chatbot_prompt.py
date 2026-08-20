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
# ============================================================
# ADDITIONAL SAFE TEST CODE
# ============================================================

def safe_test_51():
    value = "AI"
    return value


def safe_test_52():
    value = "Python"
    return value


def safe_test_53():
    value = "Flask"
    return value


def safe_test_54():
    numbers = [1, 2, 3, 4, 5]
    return numbers


def safe_test_55():
    numbers = [10, 20, 30, 40, 50]
    return sum(numbers)


def safe_test_56():
    data = {
        "id": 1,
        "status": "OK",
        "enabled": True
    }
    return data


def safe_test_57():
    items = ["AI", "ML", "Python", "Flask"]
    return len(items)


def safe_test_58():
    text = "chatbot testing"
    return text.upper()


def safe_test_59():
    text = "application development"
    return text.title()


def safe_test_60():
    number = 60

    if number > 0:
        return True

    return False


def safe_test_61():
    result = []

    for number in range(5):
        result.append(number)

    return result


def safe_test_62():
    result = []

    for number in range(1, 6):
        result.append(number * number)

    return result


def safe_test_63():
    words = [
        "Python",
        "Flask",
        "AI",
        "Database"
    ]

    return [word.lower() for word in words]


def safe_test_64():
    user = {
        "name": "Test User",
        "role": "Developer"
    }

    return user.get("name")


def safe_test_65():
    values = [5, 10, 15, 20]

    return {
        "minimum": min(values),
        "maximum": max(values),
        "total": sum(values)
    }


def safe_test_66():
    message = "System is ready"

    return {
        "message": message,
        "success": True
    }


def safe_test_67():
    counter = 0

    for _ in range(10):
        counter += 1

    return counter


def safe_test_68():
    numbers = [2, 4, 6, 8, 10]

    return [
        number
        for number in numbers
        if number % 2 == 0
    ]


def safe_test_69():
    text = "   test message   "

    return text.strip()


def safe_test_70():
    text = "Hello Python"

    return text.replace("Python", "World")


# ============================================================
# SAFE DATA OBJECTS
# ============================================================

safe_data_01 = {
    "name": "Demo",
    "type": "test"
}

safe_data_02 = {
    "project": "DU_AN_1",
    "language": "Python"
}

safe_data_03 = {
    "framework": "Flask",
    "status": "development"
}

safe_data_04 = {
    "feature": "Chatbot",
    "enabled": True
}

safe_data_05 = {
    "version": "1.0",
    "testing": True
}


# ============================================================
# SAFE LIST DATA
# ============================================================

safe_list_01 = [
    "Python",
    "Flask",
    "AI"
]

safe_list_02 = [
    "Database",
    "API",
    "Chatbot"
]

safe_list_03 = [
    10,
    20,
    30,
    40,
    50
]

safe_list_04 = [
    True,
    False,
    True,
    True
]


# ============================================================
# SAFE STRING DATA
# ============================================================

safe_string_01 = "Python Programming"
safe_string_02 = "Artificial Intelligence"
safe_string_03 = "Machine Learning"
safe_string_04 = "Flask Application"
safe_string_05 = "Chatbot Project"
safe_string_06 = "Database System"
safe_string_07 = "Software Development"
safe_string_08 = "Application Testing"
safe_string_09 = "Git Repository"
safe_string_10 = "Main Branch"


# ============================================================
# SAFE NUMERIC DATA
# ============================================================

safe_number_01 = 100
safe_number_02 = 200
safe_number_03 = 300
safe_number_04 = 400
safe_number_05 = 500
safe_number_06 = 600
safe_number_07 = 700
safe_number_08 = 800
safe_number_09 = 900
safe_number_10 = 1000


# ============================================================
# END ADDITIONAL SAFE TEST CODE
# ============================================================\
# ============================================================
# MORE SAFE TEST FUNCTIONS
# ============================================================

def safe_test_71():
    return {
        "test": 71,
        "result": "success"
    }


def safe_test_72():
    values = [1, 3, 5, 7, 9]
    return [value * 2 for value in values]


def safe_test_73():
    values = [10, 20, 30, 40]
    return [value / 10 for value in values]


def safe_test_74():
    names = ["Alice", "Bob", "Charlie"]
    return ", ".join(names)


def safe_test_75():
    text = "Python Flask Application"
    words = text.split()
    return words


def safe_test_76():
    data = {
        "python": True,
        "flask": True,
        "database": True,
        "chatbot": True
    }

    return all(data.values())


def safe_test_77():
    data = {
        "python": True,
        "flask": False,
        "database": True
    }

    return any(data.values())


def safe_test_78():
    numbers = [11, 22, 33, 44, 55]

    result = {}

    for index, number in enumerate(numbers):
        result[index] = number

    return result


def safe_test_79():
    first = ["A", "B", "C"]
    second = [1, 2, 3]

    return list(zip(first, second))


def safe_test_80():
    numbers = [1, 2, 3, 4, 5, 6]

    even_numbers = [
        number
        for number in numbers
        if number % 2 == 0
    ]

    return even_numbers


def safe_test_81():
    numbers = [1, 2, 3, 4, 5, 6]

    odd_numbers = [
        number
        for number in numbers
        if number % 2 != 0
    ]

    return odd_numbers


def safe_test_82():
    data = ["python", "flask", "ai"]

    return sorted(data)


def safe_test_83():
    data = [5, 2, 9, 1, 7]

    return sorted(data)


def safe_test_84():
    data = [5, 2, 9, 1, 7]

    return sorted(data, reverse=True)


def safe_test_85():
    text = "testing"

    return {
        "length": len(text),
        "upper": text.upper(),
        "lower": text.lower()
    }


def safe_test_86():
    numbers = [10, 20, 30]

    average = sum(numbers) / len(numbers)

    return average


def safe_test_87():
    products = [
        {"name": "A", "price": 100},
        {"name": "B", "price": 200},
        {"name": "C", "price": 300}
    ]

    return products


def safe_test_88():
    active_users = [
        {"name": "User 1", "active": True},
        {"name": "User 2", "active": False},
        {"name": "User 3", "active": True}
    ]

    return [
        user
        for user in active_users
        if user["active"]
    ]


def safe_test_89():
    values = [100, 200, 300]

    result = {
        "count": len(values),
        "sum": sum(values),
        "max": max(values),
        "min": min(values)
    }

    return result


def safe_test_90():
    return {
        "application": "DU_AN_1",
        "language": "Python",
        "framework": "Flask",
        "branch": "main",
        "status": "OK"
    }


# ============================================================
# EXTRA SAMPLE DATA
# ============================================================

sample_data_01 = {
    "id": 1,
    "name": "Demo User",
    "email": "demo@example.com"
}

sample_data_02 = {
    "id": 2,
    "name": "Test User",
    "email": "test@example.com"
}

sample_data_03 = {
    "id": 3,
    "name": "Sample User",
    "email": "sample@example.com"
}

sample_data_04 = {
    "id": 4,
    "name": "Developer",
    "email": "developer@example.com"
}

sample_data_05 = {
    "id": 5,
    "name": "Administrator",
    "email": "admin@example.com"
}


# ============================================================
# EXTRA APPLICATION INFORMATION
# ============================================================

project_name = "DU_AN_1"
project_language = "Python"
project_framework = "Flask"
project_status = "Development"
project_version = "1.0"
project_branch = "main"

feature_python = True
feature_flask = True
feature_database = True
feature_chatbot = True
feature_testing = True


# ============================================================
# EXTRA CONFIGURATION DATA
# ============================================================

test_config = {
    "debug": False,
    "testing": True,
    "version": "1.0",
    "environment": "development",
    "application": "DU_AN_1"
}


# ============================================================
# EXTRA STATUS DATA
# ============================================================

status_ready = True
status_testing = True
status_database = True
status_chatbot = True
status_application = True


# ============================================================
# END MORE SAFE TEST CODE
# ============================================================