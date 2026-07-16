from flask import Flask, render_template, request, jsonify
from ai_logic import predict_image
from database import init_db, get_diet_plan
from rag_chatbot import get_chatbot_response
import os

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files: return jsonify({'error': 'No image'}), 400
    img_bytes = request.files['image'].read()
    return jsonify(predict_image(img_bytes))

@app.route('/api/diet', methods=['POST'])
def diet():
    tdee = request.json.get('tdee', 2150)
    return jsonify(get_diet_plan(tdee))

@app.route('/api/chat', methods=['POST'])
def chat():
    message = request.json.get('message', '')
    if not message: return jsonify({'response': 'Vui lòng nhập câu hỏi.'}), 400
    ai_response = get_chatbot_response(message)
    return jsonify({'response': ai_response})

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    app.run(debug=True, port=5000)