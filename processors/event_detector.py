# processors/event_detector.py

"""
EVENT DETECTOR — Combines frame-level and sequence-level signals.

This is the intelligence layer. Neither frame analysis
nor sequence analysis alone is enough. Together they
produce meaningful, actionable events.

Example:
- Frame analysis: sees 1 person
- Sequence analysis: that person has been standing
  in the same spot for 50 frames
- Event: "stationary person detected" — possible loitering
"""

from datetime import datetime
from core.config import ANOMALY_THRESHOLD


class EventDetector:
    def __init__(self):
        self.event_history = []
        self.frame_count = 0

    def detect_events(
        self,
        frame_analysis: dict,
        sequence_analysis: dict
    ) -> dict:
        """
        Main event detection logic.
        Combines both analysis types into actionable events.
        """
        self.frame_count += 1
        events = []
        alert_level = "normal"

        # Process frame-level flags
        for flag in frame_analysis.get("flags", []):
            event = {
                "id": f"evt_{self.frame_count}_{len(events)}",
                "timestamp": datetime.now().isoformat(),
                "source": "frame_analysis",
                "type": flag["type"],
                "severity": flag["severity"],
                "description": self._get_description(flag),
                "frame": self.frame_count
            }
            events.append(event)

            if flag["severity"] == "high":
                alert_level = "high"
            elif flag["severity"] == "medium" and alert_level == "normal":
                alert_level = "medium"

        # Process sequence-level anomalies
        if sequence_analysis.get("ready"):
            for anomaly in sequence_analysis.get("anomalies", []):
                event = {
                    "id": f"evt_{self.frame_count}_{len(events)}",
                    "timestamp": datetime.now().isoformat(),
                    "source": "sequence_analysis",
                    "type": anomaly["type"],
                    "severity": anomaly["severity"],
                    "description": anomaly["description"],
                    "score": anomaly.get("score", 0),
                    "frame": self.frame_count
                }
                events.append(event)

                if anomaly["severity"] == "high":
                    alert_level = "high"
                elif anomaly["severity"] == "medium" and alert_level == "normal":
                    alert_level = "medium"

        # Store events
        self.event_history.extend(events)

        return {
            "frame": self.frame_count,
            "timestamp": datetime.now().isoformat(),
            "alert_level": alert_level,
            "events": events,
            "event_count": len(events),
            "frame_summary": {
                "objects": frame_analysis.get("object_count", 0),
                "detections": [
                    d["class"] for d in
                    frame_analysis.get("detections", [])[:5]
                ]
            },
            "sequence_summary": {
                "ready": sequence_analysis.get("ready", False),
                "trends": sequence_analysis.get("trends", {}),
                "anomalies": sequence_analysis.get("anomaly_count", 0)
            }
        }

    def _get_description(self, flag: dict) -> str:
        descriptions = {
            "dangerous_object": f"Dangerous object detected: {flag.get('object', 'unknown')}",
            "crowding": f"Crowding detected: {flag.get('count', 0)} objects in frame",
            "rapid_motion": "Rapid motion detected in frame"
        }
        return descriptions.get(flag["type"], f"Flag: {flag['type']}")

    def get_summary(self) -> dict:
        """Returns summary of all events detected so far."""
        high = sum(1 for e in self.event_history if e["severity"] == "high")
        medium = sum(1 for e in self.event_history if e["severity"] == "medium")

        return {
            "total_frames": self.frame_count,
            "total_events": len(self.event_history),
            "high_severity": high,
            "medium_severity": medium,
            "recent_events": self.event_history[-5:]
        }