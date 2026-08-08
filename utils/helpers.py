def safe_int(val):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0

def guess_meal_type(name):
    name = str(name).lower()
    breakfast_kw = ['bánh mì', 'phở', 'bún', 'cháo', 'yến mạch', 'trứng', 'sáng', 'bún bò', 'miến']
    lunch_kw = ['cơm', 'gà', 'bò', 'heo', 'cá', 'trưa', 'sườn', 'thịt']
    dinner_kw = ['salad', 'súp', 'chay', 'tối', 'nấm', 'rau', 'đậu hũ']
    
    if any(kw in name for kw in breakfast_kw): return 'breakfast'
    if any(kw in name for kw in lunch_kw): return 'lunch'
    if any(kw in name for kw in dinner_kw): return 'dinner'
    return 'snack'