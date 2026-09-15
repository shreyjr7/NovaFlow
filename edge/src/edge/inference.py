import torch
import cv2
from typing import List, Tuple

# This stub uses a pretrained YOLOv8 model from torch hub.
# In production replace with a CUDA‑enabled model on Jetson.

MODEL = None

def load_model():
    global MODEL
    if MODEL is None:
        # Using a lightweight YOLOv5 model for example
        MODEL = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
    return MODEL

def run_inference(frame: "torch.Tensor") -> List[Tuple[str, float, List[float]]]:
    """Run object detection on a single frame.
    Returns a list of (label, confidence, bbox) tuples.
    bbox format: [x1, y1, x2, y2] in pixel coordinates.
    """
    model = load_model()
    # Convert frame (numpy) to RGB image for model
    results = model(frame)
    detections = []
    for *box, conf, cls in results.xyxy[0].tolist():
        label = model.names[int(cls)]
        detections.append((label, conf, box))
    return detections
