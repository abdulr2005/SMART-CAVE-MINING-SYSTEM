from ultralytics import YOLO

if __name__ == "__main__":
    model = YOLO("yolov8n.pt") 

    model.train(
        data="data.yaml",
        epochs=150,      
        imgsz=640,       
        batch=-1,        
        device="cpu",    
        workers=4
    )