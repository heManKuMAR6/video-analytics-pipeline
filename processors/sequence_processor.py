# processors/sequence_processor.py

"""
SEQUENCE PROCESSOR — Temporal understanding across frames.

This is what separates this system from simple object detection.
It looks at PATTERNS across multiple frames to understand
what's HAPPENING, not just what's PRESENT.

WHY VIDEOMAE?
Video Masked Autoencoders — a transformer that was pretrained
on millions of video clips. It understands motion, actions,
and temporal patterns out of the box.

For production speed we use feature-based analysis
(comparing frame features over time) which is faster
than running the full VideoMAE model on every sequence.
"""

import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image
from collections import deque
from core.config import SEQUENCE_LENGTH, ANOMALY_THRESHOLD


class SequenceProcessor:
    def __init__(self):
        print("[Sequence Processor] Initializing temporal analyzer...")

        # Buffer stores recent frames for sequence analysis
        self.frame_buffer = deque(maxlen=SEQUENCE_LENGTH)

        # Feature buffer stores extracted features
        self.feature_buffer = deque(maxlen=SEQUENCE_LENGTH)

        # Detection history for trend analysis
        self.detection_history = deque(maxlen=SEQUENCE_LENGTH)

        # Image preprocessing for feature extraction
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

        # Load lightweight feature extractor
        self.feature_extractor = torch.hub.load(
            'pytorch/vision:v0.10.0',
            'mobilenet_v2',
            pretrained=True
        )
        self.feature_extractor.eval()

        print("[Sequence Processor] Ready")

    def add_frame(self, frame: np.ndarray, frame_analysis: dict):
        """Add a new frame and its analysis to the buffers."""
        self.frame_buffer.append(frame)
        self.detection_history.append(frame_analysis)

        # Extract and store frame features
        features = self._extract_features(frame)
        self.feature_buffer.append(features)

    def _extract_features(self, frame: np.ndarray) -> np.ndarray:
        """
        Extract a compact feature vector from a frame.
        This is the 'fingerprint' of each frame.
        Comparing fingerprints across time reveals changes.
        """
        pil_image = Image.fromarray(frame)
        tensor = self.transform(pil_image).unsqueeze(0)

        with torch.no_grad():
            # Get features from second-to-last layer
            features = self.feature_extractor.features(tensor)
            features = torch.nn.functional.adaptive_avg_pool2d(features, (1, 1))
            features = features.flatten().numpy()

        return features

    def analyze_sequence(self) -> dict:
        """
        Analyze the sequence of frames for temporal patterns.
        Returns sequence-level understanding and anomalies.
        """
        if len(self.frame_buffer) < SEQUENCE_LENGTH // 2:
            return {
                "ready": False,
                "message": f"Collecting frames ({len(self.frame_buffer)}/{SEQUENCE_LENGTH})",
                "anomalies": [],
                "trends": {}
            }

        anomalies = []
        trends = {}

        # 1. Motion analysis — how much is changing between frames
        motion_score = self._analyze_motion()
        trends["motion_level"] = round(motion_score, 3)

        if motion_score > 0.8:
            anomalies.append({
                "type": "sudden_motion",
                "score": round(motion_score, 3),
                "severity": "medium",
                "description": "Unusually high motion detected across frames"
            })

        # 2. Object count trend — is crowd growing or shrinking
        count_trend = self._analyze_object_count_trend()
        trends["object_count_trend"] = count_trend

        if count_trend["trend"] == "rapidly_increasing":
            anomalies.append({
                "type": "crowd_buildup",
                "score": count_trend["rate"],
                "severity": "medium",
                "description": "Object count increasing rapidly over time"
            })

        # 3. Scene stability — is the scene dramatically changing
        stability_score = self._analyze_scene_stability()
        trends["scene_stability"] = round(stability_score, 3)

        if stability_score < 0.3:
            anomalies.append({
                "type": "scene_disruption",
                "score": round(1 - stability_score, 3),
                "severity": "high",
                "description": "Significant scene change detected"
            })

        # 4. Persistent object detection
        persistent = self._analyze_persistence()
        trends["persistent_objects"] = persistent

        return {
            "ready": True,
            "frames_analyzed": len(self.frame_buffer),
            "anomalies": anomalies,
            "trends": trends,
            "anomaly_count": len(anomalies)
        }

    def _analyze_motion(self) -> float:
        """
        Measures how much features change between consecutive frames.
        High change = high motion.
        """
        if len(self.feature_buffer) < 2:
            return 0.0

        features = list(self.feature_buffer)
        changes = []

        for i in range(1, len(features)):
            diff = np.linalg.norm(features[i] - features[i-1])
            changes.append(diff)

        if not changes:
            return 0.0

        avg_change = np.mean(changes)
        # Normalize to 0-1 range
        return min(avg_change / 10.0, 1.0)

    def _analyze_object_count_trend(self) -> dict:
        """
        Tracks how object count changes over the sequence.
        Rapid increase could indicate crowd gathering.
        """
        if len(self.detection_history) < 3:
            return {"trend": "stable", "rate": 0.0}

        counts = [d.get("object_count", 0) for d in self.detection_history]

        # Calculate trend using simple linear regression
        x = np.arange(len(counts))
        slope = np.polyfit(x, counts, 1)[0]

        if slope > 1.5:
            trend = "rapidly_increasing"
        elif slope > 0.5:
            trend = "increasing"
        elif slope < -1.5:
            trend = "rapidly_decreasing"
        elif slope < -0.5:
            trend = "decreasing"
        else:
            trend = "stable"

        return {"trend": trend, "rate": round(abs(slope), 3)}

    def _analyze_scene_stability(self) -> float:
        """
        Measures overall scene consistency.
        Low stability = something dramatically changed.
        """
        if len(self.feature_buffer) < 4:
            return 1.0

        features = list(self.feature_buffer)
        first_half = np.mean(features[:len(features)//2], axis=0)
        second_half = np.mean(features[len(features)//2:], axis=0)

        similarity = np.dot(first_half, second_half) / (
            np.linalg.norm(first_half) * np.linalg.norm(second_half) + 1e-8
        )

        return float(max(0, similarity))

    def _analyze_persistence(self) -> list:
        """
        Finds objects that appear consistently across frames.
        A person present in 80% of frames is more significant
        than one that appears briefly.
        """
        if not self.detection_history:
            return []

        class_counts = {}
        total_frames = len(self.detection_history)

        for frame_analysis in self.detection_history:
            seen_in_frame = set()
            for det in frame_analysis.get("detections", []):
                cls = det["class"]
                if cls not in seen_in_frame:
                    class_counts[cls] = class_counts.get(cls, 0) + 1
                    seen_in_frame.add(cls)

        # Return objects present in more than 50% of frames
        persistent = []
        for cls, count in class_counts.items():
            persistence = count / total_frames
            if persistence > 0.5:
                persistent.append({
                    "class": cls,
                    "persistence": round(persistence, 2),
                    "frames": count
                })

        return sorted(persistent, key=lambda x: x["persistence"], reverse=True)