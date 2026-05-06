"""
UAV edge inference node — simulate or real mode.

Simulate mode: UAVs patrol waypoints around Msaken; detections are generated
near persistent fire hotspots (smoke when far, fire when close).

Usage:
    python inference.py --simulate --uav-id UAV-01
    python inference.py --simulate --uav-id UAV-02
    python inference.py --weights best.pt --source fire.mp4
"""

import argparse
import math
import os
import random
import time
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client, Client

import buffer as local_buffer

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
UAV_ID       = os.environ.get("UAV_ID",   "UAV-01")
SIM_LAT      = float(os.environ.get("SIM_LAT", "35.7303"))
SIM_LNG      = float(os.environ.get("SIM_LNG", "10.5621"))

CLASS_NAMES     = {0: "fire", 1: "smoke"}
STATUS_INTERVAL = 2.0    # seconds between UAV status pushes (smooth movement)
CONF_THRESHOLD  = 0.45

# ── Persistent fire hotspots around Msaken forests ───────────────────────────
# Each entry: (lat, lng, intensity 0-1)
HOTSPOTS = [
    (35.7820, 10.5050, 0.92),   # Jbel Zaghouan foothills — active fire
    (35.6980, 10.6230, 0.75),   # Enfidha scrubland — spreading smoke
    (35.7150, 10.4680, 0.55),   # Msaken olive grove — early smoke
]

# ── Patrol waypoints per UAV (cycles indefinitely) ───────────────────────────
PATROL = {
    "UAV-01": [
        (35.8000, 10.4800),
        (35.7820, 10.5050),   # passes near hotspot 0
        (35.7500, 10.5600),
        (35.7200, 10.6100),
        (35.6980, 10.6230),   # passes near hotspot 1
        (35.6800, 10.5500),
        (35.7000, 10.4900),
        (35.7150, 10.4680),   # passes near hotspot 2
    ],
    "UAV-02": [
        (35.7600, 10.6400),
        (35.7300, 10.6200),
        (35.6980, 10.6230),   # passes near hotspot 1
        (35.6900, 10.5700),
        (35.7150, 10.4680),   # passes near hotspot 2
        (35.7500, 10.4900),
        (35.7820, 10.5050),   # passes near hotspot 0
        (35.8000, 10.5500),
    ],
}
DEFAULT_PATROL = PATROL["UAV-01"]   # fallback for unknown UAV IDs

PATROL_SPEED = 0.0004   # degrees per simulation step (~45 km/h at this lat)


def geo_dist(lat1, lng1, lat2, lng2) -> float:
    """Euclidean distance in degrees (accurate enough for <50 km)."""
    return math.sqrt((lat1 - lat2) ** 2 + (lng1 - lng2) ** 2)


def move_toward(lat, lng, target_lat, target_lng, speed):
    """Step toward target, return new position and whether target was reached."""
    dist = geo_dist(lat, lng, target_lat, target_lng)
    if dist < speed:
        return target_lat, target_lng, True
    ratio = speed / dist
    return lat + (target_lat - lat) * ratio, lng + (target_lng - lng) * ratio, False


def check_hotspots(lat, lng) -> dict | None:
    """
    Return a detection event if the UAV is near a hotspot, else None.
    - Within 0.04° (~4 km): might detect smoke
    - Within 0.015° (~1.5 km): might detect fire
    Confidence scales with proximity and hotspot intensity.
    """
    for h_lat, h_lng, intensity in HOTSPOTS:
        dist = geo_dist(lat, lng, h_lat, h_lng)
        if dist > 0.05:
            continue

        # Probability of triggering a detection this step
        p = intensity * max(0, (0.05 - dist) / 0.05) * 0.25
        if random.random() > p:
            continue

        # Class and confidence based on distance
        if dist < 0.015:
            cls  = "fire"
            conf = round(min(0.99, 0.75 + intensity * 0.24 - dist * 5), 3)
        else:
            cls  = "smoke"
            conf = round(min(0.90, 0.50 + intensity * 0.30 - dist * 3), 3)

        # Jitter the reported position slightly around the hotspot
        return {
            "id":         str(uuid.uuid4()),
            "uav_id":     UAV_ID,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "lat":        round(h_lat + random.uniform(-0.004, 0.004), 6),
            "lng":        round(h_lng + random.uniform(-0.004, 0.004), 6),
            "class":      cls,
            "confidence": conf,
            "frame_id":   int(time.time()),
        }
    return None


def connect_supabase() -> Client | None:
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
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


def update_uav_status(client: Client | None, lat: float, lng: float,
                      battery: float, detection_count: int):
    if client is None:
        return
    try:
        client.table("uav_status").upsert({
            "uav_id":          UAV_ID,
            "updated_at":      datetime.now(timezone.utc).isoformat(),
            "lat":             round(lat, 6),
            "lng":             round(lng, 6),
            "battery_pct":     round(battery),
            "connectivity":    "connected",
            "detection_count": detection_count,
        }).execute()
    except Exception:
        pass


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--weights",  default=None)
    p.add_argument("--source",   default="0")
    p.add_argument("--simulate", action="store_true")
    p.add_argument("--uav-id",   default=None)
    p.add_argument("--conf",     type=float, default=CONF_THRESHOLD)
    p.add_argument("--show",     action="store_true")
    return p.parse_args()


def main():
    args = parse_args()

    global UAV_ID
    if args.uav_id:
        UAV_ID = args.uav_id

    supabase = connect_supabase()
    print(f"[{'OK' if supabase else 'WARN'}]  Supabase {'connected' if supabase else "offline — buffering"}")

    if not args.simulate:
        assert args.weights, "Provide --weights or use --simulate"
        from ultralytics import YOLO
        import cv2
        model = YOLO(args.weights)
        source = int(args.source) if args.source.isdigit() else args.source
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open: {source}")
        print(f"[OK]  Model loaded | Source: {source}")

    waypoints  = PATROL.get(UAV_ID, DEFAULT_PATROL)
    wp_idx     = 0
    lat, lng   = waypoints[0]
    battery    = 100.0
    start_time = time.time()
    detection_count  = 0
    last_status_push = 0.0

    print(f"[RUN] UAV={UAV_ID} | {len(waypoints)}-waypoint patrol | Ctrl-C to stop\n")

    while True:
        # ── Move toward current waypoint ─────────────────────────────────
        t_lat, t_lng = waypoints[wp_idx]
        lat, lng, reached = move_toward(lat, lng, t_lat, t_lng, PATROL_SPEED)
        if reached:
            wp_idx = (wp_idx + 1) % len(waypoints)

        # ── Battery drains 1% per 3 minutes of flight ────────────────────
        battery = max(0.0, 100.0 - (time.time() - start_time) / 180.0)

        # ── Generate detections ───────────────────────────────────────────
        if args.simulate:
            event = check_hotspots(lat, lng)
            if event:
                pushed = push_event(supabase, event)
                detection_count += 1
                print(f"[{'PUSHED' if pushed else 'BUFFERED'}] "
                      f"uav={UAV_ID} cls={event['class']:5s} "
                      f"conf={event['confidence']:.3f} "
                      f"lat={event['lat']:.5f} lng={event['lng']:.5f}")
        else:
            import cv2
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            results = model(frame, conf=args.conf, verbose=False)[0]
            for box in results.boxes:
                cls_id = int(box.cls[0])
                conf   = float(box.conf[0])
                event  = {
                    "id":         str(uuid.uuid4()),
                    "uav_id":     UAV_ID,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "lat":        round(lat, 6),
                    "lng":        round(lng, 6),
                    "class":      CLASS_NAMES.get(cls_id, "unknown"),
                    "confidence": round(conf, 3),
                    "frame_id":   int(time.time()),
                }
                push_event(supabase, event)
                detection_count += 1
            if args.show:
                import cv2 as _cv2
                _cv2.imshow("Fire Detection", frame)
                if _cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        # ── Push UAV status ───────────────────────────────────────────────
        now = time.time()
        if now - last_status_push >= STATUS_INTERVAL:
            update_uav_status(supabase, lat, lng, battery, detection_count)
            last_status_push = now

        time.sleep(0.033)


if __name__ == "__main__":
    main()
