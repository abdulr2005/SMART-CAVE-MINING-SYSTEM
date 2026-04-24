import cv2
from ultralytics import YOLO


model_path = r'C:\Users\abdul\Desktop\PPE Detection.v1i.yolov8\runs\detect\train11\weights\best.pt'
model = YOLO(model_path)


cap = cv2.VideoCapture(r'C:\Users\abdul\Desktop\PPE Detection.v1i.yolov8\Part 20 _ Skilled Worker Hacks_ Fast, , Accurate_✅.mp4')

print("--- Final Logic Test (IDs: 0, 4, 9) ---")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    # التحليل
    results = model.predict(frame, conf=0.45, verbose=False)
    detected_ids = []
    
    if results[0].boxes:
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            detected_ids.append(cls_id)
            
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            
            if cls_id == 0: # الشخص
                color = (255, 255, 255) 
                label = "Person"
            elif cls_id == 4: 
                color = (0, 255, 0)     
                label = "Helmet"
            elif cls_id == 9: 
                color = (255, 255, 0)   
                label = "Vest"
            else:
                color = (100, 100, 100) 
                label = f"ID: {cls_id}"

            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    
    
    if 0 in detected_ids:
        if 4 in detected_ids and 9 in detected_ids:
            status = "SAFE ✅ - GATE OPEN"
            bg_color = (0, 150, 0) 
        else:
            status = "UNSAFE ❌ - MISSING PPE"
            bg_color = (0, 0, 150) 
    else:
        status = "Waiting for Worker..."
        bg_color = (50, 50, 50) 

    
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 60), bg_color, -1)
    cv2.putText(frame, status, (20, 40), cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 255), 2)

    cv2.imshow("Final PPE System", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()