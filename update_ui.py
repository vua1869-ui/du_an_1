# -*- coding: utf-8 -*-
import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove view-scan completely
content = re.sub(r'<div id="view-scan".*?<!-- TAB 3', '<!-- TAB 3', content, flags=re.DOTALL)

# 2. Modify nav items
content = re.sub(r'<button onclick="switchAppTab\(\'scan\'\)" id="nav-scan".*?</button>', '', content, flags=re.DOTALL)
content = re.sub(r'<button onclick="switchAppTab\(\'scan\'\)" class="flex flex-col.*?id="mnav-scan".*?</button>', '', content, flags=re.DOTALL)

# 3. Modify "Quét Món Ăn" buttons to point to chat
content = content.replace("switchAppTab('scan')", "switchAppTab('chat')")
content = content.replace("Quét Món Ăn", "Hỏi NutriBot")

# 4. Modify chat input box to add file upload button
chat_input_html = '''
                <div class="p-4 sm:p-5 bg-white border-t border-line shrink-0 relative z-20">
                    <div class="max-w-3xl mx-auto relative flex items-center bg-surface2/50 border border-line rounded-[1.25rem] focus-within:border-primary focus-within:bg-white focus-within:ring-4 focus-within:ring-primary/10 transition-all shadow-sm">
                        <label for="chat-image-upload" class="btn-press absolute left-2 w-10 h-10 flex items-center justify-center text-inkmute hover:bg-surface2 rounded-xl transition-colors cursor-pointer" title="Gửi ảnh">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path></svg>
                        </label>
                        <input type="file" id="chat-image-upload" accept="image/*" class="hidden" onchange="uploadImageForChat(event)">
                        <input type="text" id="chat-input" onkeypress="if(event.key==='Enter') sendChatMessage()" placeholder="Hỏi AI tại đây hoặc tải ảnh mâm cơm lên..." class="flex-1 bg-transparent border-none py-3.5 pl-14 pr-14 text-sm font-medium outline-none text-dark placeholder-inkmute/70">
                        <button onclick="sendChatMessage()" class="btn-press absolute right-2 w-10 h-10 flex items-center justify-center bg-primary text-white rounded-xl shadow-md hover:bg-primary_hover transition-colors">
                            <svg class="w-5 h-5 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
                        </button>
                    </div>
                    <p class="text-[10px] text-center text-inkmute mt-3 font-medium">NutriBot có thể mắc lỗi. Vui lòng kiểm tra lại các thông số y khoa.</p>
                </div>
'''
content = re.sub(r'<div class="p-4 sm:p-5 bg-white border-t border-line shrink-0 relative z-20">.*?NutriBot có thể mắc lỗi.*?</p>\s*</div>', chat_input_html.strip(), content, flags=re.DOTALL)

# 5. Add uploadImageForChat function in JS
js_func = '''
        function uploadImageForChat(e) {
            const file = e.target.files[0];
            if (!file) return;
            
            let chatBox = document.getElementById('chat-box');
            const imgURL = URL.createObjectURL(file);
            chatBox.innerHTML += 
            <div class="flex justify-end items-end gap-3 mb-4 animate-fade-in-up">
                <div class="chat-bubble-user p-4 max-w-[85%] text-sm font-medium">
                    <img src="\" class="max-w-full h-auto rounded-lg mb-2" style="max-height: 200px;">
                    <p>Hãy phân tích món ăn này giúp tôi!</p>
                </div>
                <div class="w-8 h-8 rounded-full bg-surface2 flex items-center justify-center text-sm shrink-0 mb-1">👤</div>
            </div>;
            
            const loadingId = 'loading-' + Date.now();
            chatBox.innerHTML += 
            <div id="\" class="flex justify-start items-end gap-3 mb-4">
                <div class="w-8 h-8 rounded-full bg-white flex items-center justify-center text-sm border border-line shrink-0 mb-1">🤖</div>
                <div class="bg-white text-dark p-4 rounded-2xl rounded-bl-sm text-sm font-medium border border-line">
                    <div class="flex gap-1 items-center px-2 py-1">
                        <span class="w-2 h-2 bg-primary rounded-full animate-bounce"></span>
                        <span class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
                        <span class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay: 0.4s"></span>
                    </div>
                </div>
            </div>;
            chatBox.scrollTop = chatBox.scrollHeight;

            const formData = new FormData(); 
            formData.append('image', file);
            if(onboardingData && onboardingData.user_id) formData.append('user_id', onboardingData.user_id);
            if(onboardingData && onboardingData.tdee) formData.append('tdee', onboardingData.tdee);

            fetch('/api/analyze', { method: 'POST', body: formData }).then(res => res.json()).then(data => {
                document.getElementById(loadingId).remove();
                let html = '';
                
                if(data.analysis && data.analysis.items && Object.keys(data.analysis.items).length > 0) {
                    html = <p class="font-bold mb-3 text-dark font-display">🍽️ Đã nhận diện:</p><div class="space-y-3 mb-3">;
                    // Convert object values to array to use forEach if needed, but it might be array already
                    let itemsArray = Array.isArray(data.analysis.items) ? data.analysis.items : Object.values(data.analysis.items);
                    itemsArray.forEach(f => {
                        html += 
                        <div class="bg-paper p-3 rounded-xl border border-line flex justify-between items-center">
                            <div><p class="font-bold text-dark text-sm">\</p><p class="text-xs text-ocean font-bold mt-0.5">\ cal</p></div>
                            <button onclick='addFoodToLog(\)' class="bg-gradient-to-r from-ocean to-primary text-white px-3 py-1.5 rounded-lg font-bold text-xs shadow-sm">+ Thêm</button>
                        </div>;
                    });
                    html += </div>;
                    if(data.analysis.description) {
                        html += <p class="text-sm font-medium">\</p>;
                    }
                } else if (data.analysis && data.analysis.dish_name) {
                    let f = data.analysis;
                    f.name = f.dish_name;
                    html = 
                    <div class="bg-paper p-3 rounded-xl border border-line mb-3 flex justify-between items-center">
                        <div><p class="font-bold text-dark text-sm">\</p><p class="text-xs text-ocean font-bold mt-0.5">\ cal</p></div>
                        <button onclick='addFoodToLog(\)' class="bg-gradient-to-r from-ocean to-primary text-white px-3 py-1.5 rounded-lg font-bold text-xs shadow-sm">+ Thêm</button>
                    </div>;
                    if(f.description) {
                        html += <p class="text-sm font-medium">\</p>;
                    }
                } else {
                    html = <p class="text-sm">Xin lỗi, tôi không thể nhận diện được bức ảnh này.</p>;
                }

                chatBox.innerHTML += 
                <div class="flex justify-start items-end gap-3 mb-4 animate-fade-in-up">
                    <div class="w-8 h-8 rounded-full bg-white flex items-center justify-center text-sm shadow-sm border border-line shrink-0 mb-1">🤖</div>
                    <div class="bg-white text-dark p-4 rounded-2xl rounded-bl-sm text-sm font-medium shadow-sm border border-line max-w-[85%] leading-relaxed">
                        \
                    </div>
                </div>;
                chatBox.scrollTop = chatBox.scrollHeight;
            }).catch(err => {
                document.getElementById(loadingId).remove();
                chatBox.innerHTML += 
                <div class="flex justify-start items-end gap-3 mb-4">
                    <div class="w-8 h-8 rounded-full bg-white flex items-center justify-center text-sm shadow-sm border border-line shrink-0 mb-1">🤖</div>
                    <div class="bg-white text-red-600 p-4 rounded-2xl rounded-bl-sm text-sm font-medium border border-red-200">
                        Đã có lỗi xảy ra: \
                    </div>
                </div>;
                chatBox.scrollTop = chatBox.scrollHeight;
            });
            // Reset input
            e.target.value = '';
        }
'''
content = content.replace("function sendChatMessage() {", js_func + "\n        function sendChatMessage() {")

# 6. Adjust view toggle list
content = content.replace("const views = ['dashboard', 'account', 'scan', 'chat', 'settings'];", "const views = ['dashboard', 'account', 'chat', 'settings'];")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done updating index.html")
