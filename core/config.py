# core/config.py

"""
CONFIGURATION — Central settings for the entire pipeline.

WHY A CONFIG FILE?
In production systems you never hardcode settings.
Frame rate, confidence thresholds, model choices —
these all need to be tunable without touching code.
"""

# Video settings
FPS = 10                    # Frames to process per second
FRAME_WIDTH = 640           # Resize frames to this width
FRAME_HEIGHT = 480          # Resize frames to this height

# Model settings
YOLO_MODEL = "yolov8n.pt"  # nano = fastest, good for real-time
CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence to report detection
SEQUENCE_LENGTH = 16        # Number of frames for sequence analysis

# Event detection
ANOMALY_THRESHOLD = 0.7     # Confidence to trigger anomaly alert
MAX_OBJECTS_NORMAL = 5      # More than this = crowding anomaly

# API settings
WEBSOCKET_PORT = 8765
API_PORT = 8005

# Classes to monitor (YOLO COCO classes)
MONITORED_CLASSES = [
    "person", "car", "truck", "bicycle",
    "motorcycle", "bus", "fire", "knife"
]