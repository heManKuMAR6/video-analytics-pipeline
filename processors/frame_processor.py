# processors/frame_processor.py

"""
FRAME PROCESSOR — Heart of the frame-level analysis.

Uses YOLOv8 to analyze each frame independently.
Detects objects, counts them, flags dangerous items.

WHY YOLO?
You Only Look Once — it processes the entire frame
in a single neural network pass. That's what makes
it fast enough for real-time video analysis.
"""

import cv2
import numpy as np
from ultralytics import YOLO
from core.config import (
    YOLO_MODEL, CONFIDENCE_THRESHOLD,
    FRAME_WIDTH, FRAME_HEIGHT, MONITORED_CLASSES
)


class FrameProcessor:
    def __init__(self):
        print("[Frame Processor] Loading YOLOv8 model...")
        # Load once, keep in memory — this is the warm loading optimization
        self.model = YOLO(YOLO_MODEL)
        print("[Frame Processor] YOLOv8 ready")

    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Resize and normalize frame for consistent processing.
        Smaller frames = faster inference = lower latency.
        """
        return cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

    def analyze_frame(self, frame: np.ndarray) -> dict:
        """
        Core frame analysis.
        Returns detected objects with confidence scores.
        """
        preprocessed = self.preprocess_frame(frame)

        # Run YOLO inference
        results = self.model(
            preprocessed,
            conf=CONFIDENCE_THRESHOLD,
            verbose=False
        )

        detections = []
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]
                confidence = float(box.conf[0])
                bbox = box.xyxy[0].tolist()

                detections.append({
                    "class": class_name,
                    "confidence": round(confidence, 3),
                    "bbox": [round(x, 1) for x in bbox],
                    "monitored": class_name in MONITORED_CLASSES
                })

        # Frame-level flags
        flags = self._check_frame_flags(detections)

        return {
            "detections": detections,
            "object_count": len(detections),
            "monitored_count": sum(1 for d in detections if d["monitored"]),
            "flags": flags
        }

    def _check_frame_flags(self, detections: list) -> list:
        """
        Frame-level anomaly flags.
        Simple rules that trigger immediate alerts.
        """
        flags = []

        # Count objects by class
        class_counts = {}
        for d in detections:
            class_counts[d["class"]] = class_counts.get(d["class"], 0) + 1

        # Flag dangerous objects
        dangerous = ["knife", "gun", "fire"]
        for obj in dangerous:
            if obj in class_counts:
                flags.append({
                    "type": "dangerous_object",
                    "object": obj,
                    "severity": "high"
                })

        # Flag crowding
        if len(detections) > 8:
            flags.append({
                "type": "crowding",
                "count": len(detections),
                "severity": "medium"
            })

        return flags

    def draw_detections(self, frame: np.ndarray, analysis: dict) -> np.ndarray:
        """
        Draws bounding boxes on frame for visualization.
        Used when saving annotated video output.
        """
        annotated = frame.copy()

        for det in analysis["detections"]:
            bbox = det["bbox"]
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

            # Color by severity
            if det["class"] in ["knife", "gun", "fire"]:
                color = (0, 0, 255)   # Red for dangerous
            elif det["monitored"]:
                color = (0, 165, 255) # Orange for monitored
            else:
                color = (0, 255, 0)   # Green for normal

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label = f"{det['class']} {det['confidence']:.2f}"
            cv2.putText(annotated, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return annotated