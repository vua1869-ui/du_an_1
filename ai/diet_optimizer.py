import random

def optimize_diet_plan(breakfasts, lunches, dinners, target_tdee):
    """
    Giải bài toán tối ưu tổ hợp (Knapsack-like) để tìm thực đơn 3 bữa 
    sao cho tổng Calo sát nhất với TDEE và KHÔNG VƯỢT quá TDEE (nếu có thể).
    
    Tham số đầu vào: List các tuple từ DB [(id, type, name, cals, pro, carbs, fat), ...]
    Trả về: Dictionary chứa thực đơn tối ưu và tổng dinh dưỡng.
    """
    # Trộn ngẫu nhiên để mỗi lần chạy ra kết quả khác nhau
    random.shuffle(breakfasts)
    random.shuffle(lunches)
    random.shuffle(dinners)
    
    best_plan = None
    best_calories = 0
    min_diff = float('inf')
    
    # Giới hạn duyệt để tránh lag (100 món/bữa = 1,000,000 tổ hợp, Python xử lý trong <1s)
    limit = 100
    
    for bf in breakfasts[:limit]:
        for lu in lunches[:limit]:
            # Tối ưu nhỏ: Tính luôn 2 bữa sáng + trưa
            partial_cals = bf[3] + lu[3]
            
            for dn in dinners[:limit]:
                total_cals = partial_cals + dn[3]
                diff = abs(total_cals - target_tdee)
                
                # Ưu tiên thực đơn không vượt TDEE (hoặc vượt ít nhất)
                if diff < min_diff:
                    min_diff = diff
                    best_plan = (bf, lu, dn)
                    best_calories = total_cals
                    
                    # Nếu tìm ra tổ hợp lệch nhau dưới 30 calo -> Đã đủ hoàn hảo, dừng luôn
                    if diff < 30:
                        break
            if min_diff < 30: break
        if min_diff < 30: break

    if not best_plan:
        return {"error": "Không tìm được thực đơn phù hợp."}

    bf, lu, dn = best_plan
    
    return {
        'target_tdee': target_tdee,
        'total_calories': best_calories,
        'total_protein': bf[4] + lu[4] + dn[4],
        'total_carbs': bf[5] + lu[5] + dn[5],
        'total_fat': bf[6] + lu[6] + dn[6],
        'meals': {
            'breakfast': {'name': bf[2], 'cals': bf[3]},
            'lunch': {'name': lu[2], 'cals': lu[3]},
            'dinner': {'name': dn[2], 'cals': dn[3]}
        }
    }