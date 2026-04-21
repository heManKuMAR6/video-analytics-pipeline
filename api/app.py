# api/app.py

from dotenv import load_dotenv
load_dotenv()

import os
import json
import asyncio
import tempfile
import webbrowser
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse
import uvicorn
from core.pipeline import VideoAnalyticsPipeline
from core.report_generator import generate_report

app = FastAPI(
    title="Real-Time Video Analytics Pipeline",
    description="Frame-level + sequence-level video analysis with WebSocket streaming and auto-generated visual reports",
    version="1.0.0"
)

# Store active pipelines
active_pipelines = {}


@app.get("/health")
def health():
    return {"status": "healthy", "service": "video-analytics-pipeline"}


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video Analytics Pipeline</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');
            * { margin:0; padding:0; box-sizing:border-box; }
            body {
                font-family: 'Space Mono', monospace;
                background: #080C14;
                color: #E6EDF3;
                padding: 40px 24px;
                min-height: 100vh;
            }
            body::before {
                content: '';
                position: fixed;
                inset: 0;
                background-image:
                    linear-gradient(rgba(56,139,253,0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(56,139,253,0.03) 1px, transparent 1px);
                background-size: 40px 40px;
                pointer-events: none;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                position: relative;
            }
            .tag {
                font-size: 11px;
                color: #1DCAAA;
                letter-spacing: 3px;
                text-transform: uppercase;
                margin-bottom: 12px;
            }
            h1 {
                font-family: 'Syne', sans-serif;
                font-size: 40px;
                font-weight: 800;
                margin-bottom: 8px;
            }
            h1 span { color: #388BFD; }
            .sub {
                font-size: 12px;
                color: #7D8590;
                margin-bottom: 40px;
            }
            .card {
                background: #0D1520;
                border: 1px solid rgba(56,139,253,0.15);
                border-radius: 12px;
                padding: 28px;
                margin-bottom: 20px;
            }
            .card-title {
                font-size: 10px;
                color: #7D8590;
                letter-spacing: 2px;
                text-transform: uppercase;
                margin-bottom: 20px;
            }
            .endpoint {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 10px 0;
                border-bottom: 1px solid rgba(56,139,253,0.1);
                font-size: 12px;
            }
            .endpoint:last-child { border-bottom: none; }
            .method {
                background: rgba(56,139,253,0.15);
                color: #388BFD;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 700;
                min-width: 40px;
                text-align: center;
            }
            .method.ws {
                background: rgba(29,202,170,0.15);
                color: #1DCAAA;
            }
            .path { color: #E6EDF3; }
            .desc { color: #7D8590; font-size: 11px; margin-left: auto; }
            #results {
                background: #080C14;
                border: 1px solid rgba(56,139,253,0.15);
                border-radius: 8px;
                padding: 16px;
                min-height: 160px;
                font-size: 12px;
                color: #7D8590;
                margin-top: 16px;
                white-space: pre-wrap;
                overflow-y: auto;
                max-height: 300px;
            }
            #status {
                font-size: 12px;
                margin-bottom: 12px;
                color: #7D8590;
            }
            button {
                background: #388BFD;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 8px;
                font-family: 'Space Mono', monospace;
                font-size: 12px;
                cursor: pointer;
                margin-right: 8px;
                margin-top: 16px;
            }
            button:hover { background: #2b7ae0; }
            button.stop {
                background: rgba(255,77,77,0.15);
                color: #FF4D4D;
                border: 1px solid rgba(255,77,77,0.3);
            }
            .note {
                font-size: 11px;
                color: #7D8590;
                margin-top: 12px;
                line-height: 1.6;
            }
            .badge {
                display: inline-block;
                background: rgba(240,164,41,0.15);
                color: #F0A429;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 10px;
                margin-left: 8px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="tag">Real-Time Computer Vision</div>
            <h1>Video Analytics <span>Pipeline</span></h1>
            <div class="sub">Frame-level + sequence-level analysis · YOLOv8 · Temporal Pattern Detection · Auto Visual Reports</div>

            <div class="card">
                <div class="card-title">Available Endpoints</div>
                <div class="endpoint">
                    <span class="method">GET</span>
                    <span class="path">/health</span>
                    <span class="desc">Service health check</span>
                </div>
                <div class="endpoint">
                    <span class="method">POST</span>
                    <span class="path">/analyze/upload</span>
                    <span class="desc">Upload any video → auto visual report <span class="badge">opens browser</span></span>
                </div>
                <div class="endpoint">
                    <span class="method ws">WS</span>
                    <span class="path">/ws/demo</span>
                    <span class="desc">Demo stream — no camera needed</span>
                </div>
                <div class="endpoint">
                    <span class="method ws">WS</span>
                    <span class="path">/ws/analyze</span>
                    <span class="desc">Live webcam analysis stream</span>
                </div>
                <div class="endpoint">
                    <span class="method">GET</span>
                    <span class="path">/summary</span>
                    <span class="desc">Active pipeline summaries</span>
                </div>
            </div>

            <div class="card">
                <div class="card-title">Live Demo WebSocket Stream</div>
                <div id="status">Not connected</div>
                <div id="results">Results will stream here...</div>
                <button onclick="connect()">Connect Stream</button>
                <button class="stop" onclick="disconnect()">Disconnect</button>
                <div class="note">
                    This connects to the demo stream — no camera or video file needed.<br>
                    To analyze a real video file use: <code>curl -X POST http://localhost:8005/analyze/upload -F "file=@your_video.mp4"</code>
                </div>
            </div>
        </div>

        <script>
        let ws;
        let count = 0;

        function connect() {
            ws = new WebSocket('ws://localhost:8005/ws/demo');
            ws.onopen = () => {
                document.getElementById('status').innerHTML =
                    '<span style="color:#1DCAAA">● Connected — streaming live results</span>';
                count = 0;
            };
            ws.onmessage = (event) => {
                count++;
                const data = JSON.parse(event.data);
                const alertColor = data.alert_level === 'high' ? '#FF4D4D' :
                                   data.alert_level === 'medium' ? '#F0A429' : '#1DCAAA';
                document.getElementById('results').innerHTML =
                    `<span style="color:#388BFD">Frame ${data.frame}</span>  ` +
                    `Alert: <span style="color:${alertColor}">${data.alert_level.toUpperCase()}</span>  ` +
                    `Objects: ${data.frame_summary.objects}  ` +
                    `Motion: ${data.sequence_summary.trends?.motion_level || 'N/A'}\n\n` +
                    `Detections: ${JSON.stringify(data.frame_summary.detections)}\n` +
                    `Sequence Ready: ${data.sequence_summary.ready}\n` +
                    `Anomalies: ${data.sequence_summary.anomalies}\n\n` +
                    `<span style="color:#7D8590">— ${count} frames received —</span>`;
            };
            ws.onclose = () => {
                document.getElementById('status').innerHTML =
                    '<span style="color:#FF4D4D">● Disconnected</span>';
            };
            ws.onerror = () => {
                document.getElementById('status').innerHTML =
                    '<span style="color:#FF4D4D">● Connection error</span>';
            };
        }

        function disconnect() {
            if (ws) ws.close();
        }
        </script>
    </body>
    </html>
    """


@app.websocket("/ws/demo")
async def websocket_demo(websocket: WebSocket):
    """Demo WebSocket — synthetic data, no camera needed."""
    await websocket.accept()
    print("[WebSocket] Demo client connected")

    import random
    frame_count = 0

    try:
        while True:
            frame_count += 1
            result = {
                "frame": frame_count,
                "alert_level": random.choice(["normal", "normal", "normal", "medium"]),
                "frame_summary": {
                    "objects": random.randint(0, 8),
                    "detections": random.sample(
                        ["person", "car", "bicycle", "truck"], 
                        k=random.randint(0, 3)
                    )
                },
                "sequence_summary": {
                    "ready": frame_count > 8,
                    "trends": {
                        "motion_level": round(random.uniform(0.1, 0.9), 2),
                        "scene_stability": round(random.uniform(0.5, 1.0), 2)
                    },
                    "anomalies": random.randint(0, 1)
                },
                "events": []
            }
            await websocket.send_json(result)
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        print("[WebSocket] Demo client disconnected")


@app.websocket("/ws/analyze")
async def websocket_analyze(websocket: WebSocket):
    """Live WebSocket — connects to webcam source=0."""
    await websocket.accept()
    client_id = id(websocket)
    print(f"[WebSocket] Client {client_id} connected")

    pipeline = VideoAnalyticsPipeline()
    active_pipelines[client_id] = pipeline

    async def send_result(result):
        try:
            await websocket.send_json(result)
        except:
            pipeline.stop()

    try:
        await pipeline.process_video(source=0, callback=send_result)
    except WebSocketDisconnect:
        print(f"[WebSocket] Client {client_id} disconnected")
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        pipeline.stop()
        active_pipelines.pop(client_id, None)


@app.post("/analyze/upload")
async def analyze_video_file(file: UploadFile = File(...)):
    """
    Upload any video file.
    Runs full pipeline and auto-generates
    a visual HTML report that opens in your browser.
    """
    print(f"\n[API] Analyzing: {file.filename}")

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=os.path.splitext(file.filename)[1]
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    pipeline = VideoAnalyticsPipeline()
    collected = []

    async def collect_result(result):
        collected.append(result)

    try:
        await pipeline.process_video(
            source=tmp_path,
            callback=collect_result
        )
    finally:
        os.unlink(tmp_path)

    # Build results
    results = {
        "filename": file.filename,
        "frames_processed": len(collected),
        "summary": pipeline.get_summary(),
        "high_severity_events": [
            r for r in collected
            if r.get("alert_level") == "high"
        ][:10]
    }

    # Generate visual report and open in browser
    report_path = generate_report(results, file.filename)
    webbrowser.open(f"file://{os.path.abspath(report_path)}")

    print(f"[API] Report opened in browser: {report_path}")

    return results


@app.get("/summary")
def get_summary():
    """Returns summary across all active pipelines."""
    return {
        "active_connections": len(active_pipelines),
        "summaries": {
            str(k): v.get_summary()
            for k, v in active_pipelines.items()
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8005,
        reload=True
    )