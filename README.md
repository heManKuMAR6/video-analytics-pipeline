# Real-Time Video Analytics Pipeline

A production-grade computer vision system that combines frame-level 
object detection and sequence-level temporal analysis to detect 
events in any video — automatically generating a visual report.

## What Makes This Different

Most video AI tools do one thing — detect objects per frame.
This system does two things simultaneously:

- **Frame-level**: YOLOv8 analyzes every frame independently
- **Sequence-level**: MobileNetV2 tracks patterns across frames over time

Together they detect not just what's in a frame but what's 
happening across time — crowding buildup, sudden motion, 
scene disruption, persistent objects.

## Live Results — sample_video.mp4

```
Frames processed:    1,800
Events detected:     1,220
Alert level:         MEDIUM
High severity:       0
Processing time:     ~5 minutes
```

## Pipeline Architecture

```
Video Input (any MP4 or webcam)
        ↓
[Frame Extractor]        → OpenCV pulls frames at 10 FPS
        ↓
[Frame Analyzer]         → YOLOv8 detects objects per frame
        ↓
[Sequence Analyzer]      → MobileNetV2 tracks temporal patterns
        ↓
[Event Detector]         → combines both signals
        ↓
[Report Generator]       → auto-generates visual HTML dashboard
        ↓
Browser opens automatically with results
```

## Tech Stack

- **YOLOv8** — real-time object detection per frame
- **MobileNetV2** — temporal feature extraction across sequences
- **OpenCV** — video capture and frame processing
- **FastAPI + WebSockets** — REST API and real-time streaming
- **PyTorch** — deep learning backbone
- **100% open source** — no OpenAI API needed

## Key Features

- Works on any video file or live webcam
- Frame AND sequence level analysis combined
- Auto-generates beautiful visual HTML report per video
- Real-time WebSocket streaming for live analysis
- Zero configuration — upload and get results

## Project Structure

```
video_analytics_pipeline/
├── core/
│   ├── config.py              # Configurable settings
│   ├── pipeline.py            # Main orchestration loop
│   └── report_generator.py   # Auto visual report generation
├── processors/
│   ├── frame_processor.py    # YOLOv8 frame analysis
│   ├── sequence_processor.py # Temporal pattern detection
│   └── event_detector.py     # Event combination logic
├── api/
│   └── app.py                # FastAPI + WebSocket API
├── data/                     # Place video files here
└── reports/                  # Auto-generated HTML reports
```

## Setup

```bash
git clone https://github.com/heManKuMAR6/video-analytics-pipeline.git
cd video_analytics_pipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
brew install libomp  # Mac only
python3 -m uvicorn api.app:app --reload --port 8005
```

## Usage

```bash
# Analyze any video — report opens automatically
curl -X POST http://localhost:8005/analyze/upload \
  -F "file=@your_video.mp4"

# Live demo stream in browser
open http://localhost:8005
```

Interactive docs: `http://localhost:8005/docs`