from ultralytics import YOLO

model = YOLO('yolov8n.pt') 


results = model.train(
    data='data.yaml',   
    epochs=100,        
    imgsz=640,         
    batch=16,          
)

print("Training finished! Find your model in: runs/detect/train/weights/best.pt")