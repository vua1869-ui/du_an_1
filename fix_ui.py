# -*- coding: utf-8 -*-
import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to find the bad function from `function uploadImageForChat` up to `// Reset input` + few lines.
# But it's easier to just find the `function sendChatMessage() {` block and replace what precedes it.
# Let's remove the broken uploadImageForChat completely first.
content = re.sub(r'function uploadImageForChat\(e\).*?(?=function sendChatMessage\(\) \{)', '', content, flags=re.DOTALL)

# Now inject it back
js_func = '''
        function uploadImageForChat(e) {
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
                    html = `<p class="font-bold mb-3 text-dark font-display">🍽️ Đã nhận diện:</p><div class="space-y-3 mb-3">`;
                    let itemsArray = Array.isArray(data.analysis.items) ? data.analysis.items : Object.values(data.analysis.items);
                    itemsArray.forEach(f => {
                        html += `
                        <div class="bg-paper p-3 rounded-xl border border-line flex justify-between items-center">
                            <div><p class="font-bold text-dark text-sm">${f.name}</p><p class="text-xs text-ocean font-bold mt-0.5">${f.calories || f.cals} cal</p></div>
                            <button onclick='addFoodToLog(${JSON.stringify(f).replace(/'/g, "&#39;")})' class="bg-gradient-to-r from-ocean to-primary text-white px-3 py-1.5 rounded-lg font-bold text-xs shadow-sm">+ Thêm</button>
                        </div>`;
                    });
                    html += `</div>`;
                    if(data.analysis.description) {
                        html += `<p class="text-sm font-medium">${data.analysis.description.replace(/\\n/g, '<br>')}</p>`;
                    }
                } else if (data.analysis && data.analysis.dish_name) {
                    let f = data.analysis;
                    f.name = f.dish_name;
                    html = `
                    <div class="bg-paper p-3 rounded-xl border border-line mb-3 flex justify-between items-center">
                        <div><p class="font-bold text-dark text-sm">${f.name}</p><p class="text-xs text-ocean font-bold mt-0.5">${f.calories} cal</p></div>
                        <button onclick='addFoodToLog(${JSON.stringify(f).replace(/'/g, "&#39;")})' class="bg-gradient-to-r from-ocean to-primary text-white px-3 py-1.5 rounded-lg font-bold text-xs shadow-sm">+ Thêm</button>
                    </div>`;
                    if(f.description) {
                        html += `<p class="text-sm font-medium">${f.description.replace(/\\n/g, '<br>')}</p>`;
                    }
                } else {
                    html = `<p class="text-sm">Xin lỗi, tôi không thể nhận diện được bức ảnh này.</p>`;
                }

                chatBox.innerHTML += `
                <div class="flex justify-start items-end gap-3 mb-4 animate-fade-in-up">
                    <div class="w-8 h-8 rounded-full bg-white flex items-center justify-center text-sm shadow-sm border border-line shrink-0 mb-1">🤖</div>
                    <div class="bg-white text-dark p-4 rounded-2xl rounded-bl-sm text-sm font-medium shadow-sm border border-line max-w-[85%] leading-relaxed">
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
'''
content = content.replace("function sendChatMessage() {", js_func + "\n        function sendChatMessage() {")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed JS syntax!")
