"""
Simulated UAV edge inference node.

Loads a YOLOv11 model (or runs in --simulate mode without a model),
processes frames from a video file or webcam, and pushes detection
events to Supabase in real time.

Usage:
    # Real inference on a video file (after training):
    python inference.py --weights ../model/runs/train/fire-yolo11n/weights/best.pt \\
                        --source fire_test.mp4

    # Simulation mode (no model needed, for dashboard demo before training):
    python inference.py --simulate --source fire_test.mp4
"""

import argparse
import os
import random
import time
import uuid
from datetime import datetime, timezone

import cv2
import numpy as np
from dotenv import load_dotenv
from supabase import create_client, Client

import buffer as local_buffer

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
UAV_ID = os.environ.get("UAV_ID", "UAV-01")
SIM_LAT = float(os.environ.get("SIM_LAT", "36.8065"))
SIM_LNG = float(os.environ.get("SIM_LNG", "10.1815"))

CLASS_NAMES = {0: "fire", 1: "smoke"}
STATUS_INTERVAL = 5.0    # seconds between UAV status updates
FLUSH_INTERVAL = 30.0    # seconds between buffer flush attempts
CONF_THRESHOLD = 0.45


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--weights", default=None, help="Model weights (.pt or .onnx)")
    p.add_argument("--source", default="0", help="Video file path or webcam index")
    p.add_argument("--simulate", action="store_true",
                   help="Generate synthetic detections (no model needed)")
    p.add_argument("--conf", type=float, default=CONF_THRESHOLD)
    p.add_argument("--show", action="store_true", help="Display video with detections")
    return p.parse_args()


def connect_supabase() -> Client | None:
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return client
    except Exception as e:
        print(f"[WARN] Supabase connection failed: {e}")
        return None


def push_event(client: Client | None, event: dict) -> bool:
    if client is None:
        local_buffer.enqueue(event)
        return False
    try:
        client.table("detection_events").insert(event).execute()
        buffered = local_buffer.size()
        if buffered > 0:
            flushed = local_buffer.flush(client)
            if flushed:
                print(f"[INFO] Flushed {flushed} buffered events")
        return True
    except Exception as e:
        print(f"[WARN] Push failed, buffering: {e}")
        local_buffer.enqueue(event)
        return False


def update_uav_status(client: Client | None, lat: float, lng: float, detection_count: int):
    if client is None:
        return
    try:
        client.table("uav_status").upsert({
            "uav_id": UAV_ID,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "lat": lat,
            "lng": lng,
            "battery_pct": max(0, 100 - int(time.time() / 60) % 100),
            "connectivity": "connected",
            "detection_count": detection_count,
        }).execute()
    except Exception:
        pass


def simulate_detection() -> dict | None:
    if random.random() < 0.3:
        cls = random.choice(["fire", "smoke"])
        return {
            "id": str(uuid.uuid4()),
            "uav_id": UAV_ID,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "lat": SIM_LAT + random.uniform(-0.01, 0.01),
            "lng": SIM_LNG + random.uniform(-0.01, 0.01),
            "class": cls,
            "confidence": round(random.uniform(0.60, 0.98), 3),
            "frame_id": int(time.time()),
        }
    return None


def main():
    args = parse_args()

    supabase = connect_supabase()
    if supabase:
        print(f"[OK]   Connected to Supabase")
    else:
        print(f"[WARN] Running offline — events buffered locally")

    model = None
    if not args.simulate:
        assert args.weights, "Provide --weights or use --simulate"
        from ultralytics import YOLO
        model = YOLO(args.weights)
        print(f"[OK]   Model loaded: {args.weights}")

    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video source: {source}")

    print(f"[OK]   Video source opened: {source}")
    print(f"[RUN]  UAV ID: {UAV_ID} | Press Q to quit\n")

    frame_id = 0
    detection_count = 0
    last_status_push = 0.0
    current_lat, current_lng = SIM_LAT, SIM_LNG

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[INFO] Video ended, looping...")
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        frame_id += 1

        # Drift GPS position slightly to simulate UAV movement
        current_lat += random.uniform(-0.0001, 0.0001)
        current_lng += random.uniform(-0.0001, 0.0001)

        events = []
        annotated = frame.copy()

        if args.simulate:
            det = simulate_detection()
            if det:
                events.append(det)
        else:
            results = model(frame, conf=args.conf, verbose=False)[0]
            for box in results.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                events.append({
                    "id": str(uuid.uuid4()),
                    "uav_id": UAV_ID,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "lat": round(current_lat, 6),
                    "lng": round(current_lng, 6),
                    "class": CLASS_NAMES.get(cls_id, "unknown"),
                    "confidence": round(conf, 3),
                    "frame_id": frame_id,
                })
                color = (0, 0, 255) if cls_id == 0 else (0, 140, 255)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                cv2.putText(annotated, f"{CLASS_NAMES[cls_id]} {conf:.2f}",
                            (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        for event in events:
            pushed = push_event(supabase, event)
            detection_count += 1
            status = "PUSHED" if pushed else "BUFFERED"
            print(f"[{status}] frame={frame_id:06d} class={event['class']:5s} "
                  f"conf={event['confidence']:.3f} "
                  f"lat={event['lat']:.5f} lng={event['lng']:.5f}")

        now = time.time()
        if now - last_status_push >= STATUS_INTERVAL:
            update_uav_status(supabase, current_lat, current_lng, detection_count)
            last_status_push = now

        if args.show:
            cv2.imshow("Fire Detection — Edge Node", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        time.sleep(0.033)  # ~30 FPS cap

    cap.release()
    if args.show:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
