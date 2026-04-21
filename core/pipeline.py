# core/pipeline.py

"""
PIPELINE — Orchestrates all processors together.

This is the equivalent of graph.py in your LangGraph projects.
It connects frame extraction → frame analysis →
sequence analysis → event detection → output streaming.

KEY DIFFERENCE FROM YOUR OTHER PROJECTS:
This pipeline runs continuously in a loop, not once per request.
Video is a stream, not a single input.
"""

import cv2
import time
import asyncio
from processors.frame_processor import FrameProcessor
from processors.sequence_processor import SequenceProcessor
from processors.event_detector import EventDetector
from core.config import FPS


class VideoAnalyticsPipeline:
    def __init__(self):
        print("\n[Pipeline] Initializing Video Analytics Pipeline...")
        self.frame_processor = FrameProcessor()
        self.sequence_processor = SequenceProcessor()
        self.event_detector = EventDetector()
        self.is_running = False
        self.current_result = {}
        print("[Pipeline] All processors ready")

    async def process_video(self, source, callback=None):
        """
        Main pipeline loop.
        source: 0 for webcam, or path to video file
        callback: async function to call with each result
        """
        cap = cv2.VideoCapture(source)

        if not cap.isOpened():
            raise ValueError(f"Cannot open video source: {source}")

        self.is_running = True
        frame_interval = 1.0 / FPS
        last_frame_time = 0

        print(f"[Pipeline] Starting video processing from: {source}")

        try:
            while self.is_running:
                ret, frame = cap.read()

                if not ret:
                    print("[Pipeline] Video ended or stream lost")
                    break

                # Rate limiting — only process at configured FPS
                current_time = time.time()
                if current_time - last_frame_time < frame_interval:
                    await asyncio.sleep(0.001)
                    continue

                last_frame_time = current_time

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Frame-level analysis
                frame_analysis = self.frame_processor.analyze_frame(frame_rgb)

                # Add to sequence buffer
                self.sequence_processor.add_frame(frame_rgb, frame_analysis)

                # Sequence-level analysis
                sequence_analysis = self.sequence_processor.analyze_sequence()

                # Event detection — combine both
                result = self.event_detector.detect_events(
                    frame_analysis,
                    sequence_analysis
                )

                self.current_result = result

                # Send to callback (WebSocket)
                if callback:
                    await callback(result)

                await asyncio.sleep(0.001)

        finally:
            cap.release()
            self.is_running = False
            print("[Pipeline] Pipeline stopped")

    def stop(self):
        self.is_running = False

    def get_summary(self) -> dict:
        return self.event_detector.get_summary()