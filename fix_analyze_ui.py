# -*- coding: utf-8 -*-
import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace uploadImageForChat function
pattern = re.compile(r'function uploadImageForChat\(e\).*?// Reset input\s*e\.target\.value = \'\';\s*}', re.DOTALL)

correct_js = '''function uploadImageForChat(e) {
            const file = e.target.files[0];
            if (!file) return;
            
            let chatBox = document.getElementById('chat-box');
            const imgURL = URL.createObjectURL(file);
            chatBox.innerHTML += `
            <div class="flex justify-end items-end gap-3 mb-4 animate-fade-in-up">
                <div class="chat-bubble-user p-4 max-w-[85%] text-sm font-medium">
                    <img src="${imgURL}" class="max-w-full h-auto rounded-lg mb-2" style="max-height: 200px;">
                    <p>Hãy phân tích món ăn này giúp tôi!</p>
                </div>
                <div class="w-8 h-8 rounded-full bg-surface2 flex items-center justify-center text-sm shrink-0 mb-1">👤</div>
            </div>`;
            
            const loadingId = 'loading-' + Date.now();
            chatBox.innerHTML += `
            <div id="${loadingId}" class="flex justify-start items-end gap-3 mb-4">
                <div class="w-8 h-8 rounded-full bg-white flex items-center justify-center text-sm border border-line shrink-0 mb-1">🤖</div>
                <div class="bg-white text-dark p-4 rounded-2xl rounded-bl-sm text-sm font-medium border border-line">
                    <div class="flex gap-1 items-center px-2 py-1">
                        <span class="w-2 h-2 bg-primary rounded-full animate-bounce"></span>
                        <span class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
                        <span class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay: 0.4s"></span>
                    </div>
                </div>
            </div>`;
            chatBox.scrollTop = chatBox.scrollHeight;

            const formData = new FormData(); 
            formData.append('image', file);
            if(onboardingData && onboardingData.user_id) formData.append('user_id', onboardingData.user_id);
            if(onboardingData && onboardingData.tdee) formData.append('tdee', onboardingData.tdee);

            fetch('/api/analyze', { method: 'POST', body: formData }).then(res => res.json()).then(data => {
                document.getElementById(loadingId).remove();
                let html = '';
                
                if(data.analysis && data.analysis.items && Object.keys(data.analysis.items).length > 0) {
                    let itemsArray = Array.isArray(data.analysis.items) ? data.analysis.items : Object.values(data.analysis.items);
                    
                    let totalCals = 0;
                    let foodNames = [];
                    itemsArray.forEach(f => {
                        totalCals += (f.calories || f.cals || 0);
                        foodNames.push(f.name);
                    });
                    
                    html += `<p class="text-sm mb-3 text-dark leading-relaxed">Tôi đã phân tích hình ảnh bạn gửi. Mâm cơm của bạn bao gồm: <b>${foodNames.join(", ")}</b>.</p>`;
                    html += `<p class="text-sm mb-3 text-dark leading-relaxed">Tổng lượng calo ước tính là <b>${totalCals} kcal</b>.</p>`;
                    if(data.analysis.description) {
                        html += `<p class="text-sm font-medium text-slate-700 bg-surface2/50 p-3 rounded-lg mb-4 border border-line leading-relaxed">${data.analysis.description.replace(/\\n/g, '<br>')}</p>`;
                    }
                    
                    html += `
                    <div class="mt-2 pt-4 border-t border-line text-center">
                        <button onclick='addMultipleFoodsToLog(${JSON.stringify(itemsArray).replace(/'/g, "&#39;")})' class="bg-gradient-to-r from-ocean to-primary text-white px-5 py-3 rounded-xl font-bold text-sm shadow-md hover:shadow-lg transition-all w-full flex items-center justify-center gap-2">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"></path></svg>
                            Thêm tất cả vào nhật ký
                        </button>
                    </div>`;
                    
                } else if (data.analysis && data.analysis.dish_name) {
                    let f = data.analysis;
                    f.name = f.dish_name;
                    html += `<p class="text-sm mb-3 text-dark leading-relaxed">Tôi nhận diện đây là: <b>${f.name}</b> với khoảng <b>${f.calories || 0} kcal</b>.</p>`;
                    if(f.description) {
                        html += `<p class="text-sm font-medium text-slate-700 bg-surface2/50 p-3 rounded-lg mb-4 border border-line leading-relaxed">${f.description.replace(/\\n/g, '<br>')}</p>`;
                    }
                    html += `
                    <div class="mt-2 pt-4 border-t border-line text-center">
                        <button onclick='addMultipleFoodsToLog([${JSON.stringify(f).replace(/'/g, "&#39;")}])' class="bg-gradient-to-r from-ocean to-primary text-white px-5 py-3 rounded-xl font-bold text-sm shadow-md hover:shadow-lg transition-all w-full flex items-center justify-center gap-2">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"></path></svg>
                            Thêm vào nhật ký
                        </button>
                    </div>`;
                } else {
                    html = `<p class="text-sm text-dark">Xin lỗi, tôi không thể nhận diện được bức ảnh này.</p>`;
                }

                chatBox.innerHTML += `
                <div class="flex justify-start items-end gap-3 mb-4 animate-fade-in-up">
                    <div class="w-8 h-8 rounded-full bg-white flex items-center justify-center text-sm shadow-sm border border-line shrink-0 mb-1">🤖</div>
                    <div class="bg-white text-dark p-4 rounded-2xl rounded-bl-sm text-sm font-medium shadow-[0_4px_16px_rgba(0,0,0,0.04)] border border-line max-w-[85%] leading-relaxed">
                        ${html}
                    </div>
                </div>`;
                chatBox.scrollTop = chatBox.scrollHeight;
            }).catch(err => {
                document.getElementById(loadingId).remove();
                chatBox.innerHTML += `
                <div class="flex justify-start items-end gap-3 mb-4">
                    <div class="w-8 h-8 rounded-full bg-white flex items-center justify-center text-sm shadow-sm border border-line shrink-0 mb-1">🤖</div>
                    <div class="bg-white text-red-600 p-4 rounded-2xl rounded-bl-sm text-sm font-medium border border-red-200">
                        Đã có lỗi xảy ra: ${err.message}
                    </div>
                </div>`;
                chatBox.scrollTop = chatBox.scrollHeight;
            });
            // Reset input
            e.target.value = '';
        }

        async function addMultipleFoodsToLog(foods) {
            for (let f of foods) {
                await fetch('/api/log_food', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(f) });
            }
            showToast("Đã thêm toàn bộ món vào nhật ký thành công!", "success");
            switchAppTab('dashboard');
            loadTodayLogs();
            checkAchievements();
        }'''

content = pattern.sub(correct_js, content)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("UI Fixed successfully!")
