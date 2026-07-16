from ultralytics import YOLO
import io
from PIL import Image

# Khởi tạo mô hình YOLOv8 Nano siêu nhẹ
model = YOLO('yolov8n.pt')

def predict_image(image_bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    orig_width, orig_height = image.size
    
    # YOLO quét ảnh
    results = model(image)
    
    detections = []
    for r in results:
        for box in r.boxes:
            conf = float(box.conf[0])
            if conf >= 0.25: # Lọc các kết quả có độ tin cậy > 25%
                cls_id = int(box.cls[0])
                label = model.names[cls_id]
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                detections.append({
                    "label": label.capitalize(),
                    "confidence": round(conf * 100, 1),
                    "box": [round(x1), round(y1), round(x2), round(y2)]
                })

    return {
        "detections": detections,
        "image_size": [orig_width, orig_height]
    }