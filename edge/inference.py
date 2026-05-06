"""
UAV edge inference node — simulate or real mode.

Simulate mode: UAVs patrol waypoints; return to base when battery < 20%;
recharge at base then resume patrol. False alarm sources included.

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
UAV_ID       = os.environ.get("UAV_ID",    "UAV-01")
SIM_LAT      = float(os.environ.get("SIM_LAT", "35.7303"))
SIM_LNG      = float(os.environ.get("SIM_LNG", "10.5621"))

# UAV base station — landing pad southwest of Msaken
BASE_LAT = float(os.environ.get("BASE_LAT", "35.7200"))
BASE_LNG = float(os.environ.get("BASE_LNG", "10.5400"))

CLASS_NAMES     = {0: "fire", 1: "smoke"}
STATUS_INTERVAL = 2.0   # seconds between Supabase status pushes
CONF_THRESHOLD  = 0.45
PATROL_SPEED    = 0.0004           # degrees per simulation step
RETURN_SPEED    = PATROL_SPEED * 2 # faster when returning to base
DRAIN_RATE      = 0.1              # battery % per second (100→20% in ~13 min)
CHARGE_RATE     = 1.0              # battery % per second (20→100% in ~80 s)

# ── Fire hotspots ─────────────────────────────────────────────────────────────
HOTSPOTS = [
    (35.7820, 10.5050, 0.92),   # Jbel Zaghouan foothills — active fire
    (35.6980, 10.6230, 0.75),   # Enfidha scrubland — spreading smoke
    (35.7150, 10.4680, 0.55),   # Msaken olive grove — early smoke
]

# ── False alarm sources — civilian smoke only ─────────────────────────────────
FALSE_ALARM_SOURCES = [
    (35.7420, 10.5680, "industrial chimney"),
    (35.7600, 10.5300, "agricultural burning"),
]

# ── Patrol waypoints ──────────────────────────────────────────────────────────
PATROL = {
    "UAV-01": [
        (35.8000, 10.4800),
        (35.7820, 10.5050),
        (35.7500, 10.5600),
        (35.7200, 10.6100),
        (35.6980, 10.6230),
        (35.6800, 10.5500),
        (35.7000, 10.4900),
        (35.7150, 10.4680),
    ],
    "UAV-02": [
        (35.7600, 10.6400),
        (35.7300, 10.6200),
        (35.6980, 10.6230),
        (35.6900, 10.5700),
        (35.7150, 10.4680),
        (35.7500, 10.4900),
        (35.7820, 10.5050),
        (35.8000, 10.5500),
    ],
}
DEFAULT_PATROL = PATROL["UAV-01"]


def geo_dist(lat1, lng1, lat2, lng2) -> float:
    return math.sqrt((lat1 - lat2) ** 2 + (lng1 - lng2) ** 2)


def move_toward(lat, lng, t_lat, t_lng, speed):
    dist = geo_dist(lat, lng, t_lat, t_lng)
    if dist < speed:
        return t_lat, t_lng, True
    r = speed / dist
    return lat + (t_lat - lat) * r, lng + (t_lng - lng) * r, False


def check_hotspots(lat, lng) -> dict | None:
    for h_lat, h_lng, intensity in HOTSPOTS:
        dist = geo_dist(lat, lng, h_lat, h_lng)
        if dist > 0.05:
            continue
        p = intensity * max(0, (0.05 - dist) / 0.05) * 0.25
        if random.random() > p:
            continue
        cls  = "fire" if dist < 0.015 else "smoke"
        conf = round(min(0.99, (0.75 if cls == "fire" else 0.50)
                         + intensity * 0.24 - dist * 5), 3)
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

    for f_lat, f_lng, label in FALSE_ALARM_SOURCES:
        dist = geo_dist(lat, lng, f_lat, f_lng)
        if dist > 0.04 or random.random() > 0.06:
            continue
        conf = round(random.uniform(0.45, 0.65), 3)
        print(f"[FALSE ALARM] {label} — smoke conf={conf:.3f}")
        return {
            "id":         str(uuid.uuid4()),
            "uav_id":     UAV_ID,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "lat":        round(f_lat + random.uniform(-0.003, 0.003), 6),
            "lng":        round(f_lng + random.uniform(-0.003, 0.003), 6),
            "class":      "smoke",
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


def push_event(client, event):
    if client is None:
        local_buffer.enqueue(event)
        return False
    try:
        client.table("detection_events").insert(event).execute()
        buffered = local_buffer.size()
        if buffered:
            flushed = local_buffer.flush(client)
            if flushed:
                print(f"[INFO] Flushed {flushed} buffered events")
        return True
    except Exception as e:
        print(f"[WARN] Push failed, buffering: {e}")
        local_buffer.enqueue(event)
        return False


def push_status(client, lat, lng, battery, detection_count, mode):
    if client is None:
        return
    # connectivity: "lora" signals UAV is at base charging; "connected" = in flight
    connectivity = "lora" if mode == "charging" else "connected"
    try:
        client.table("uav_status").upsert({
            "uav_id":          UAV_ID,
            "updated_at":      datetime.now(timezone.utc).isoformat(),
            "lat":             round(lat, 6),
            "lng":             round(lng, 6),
            "battery_pct":     max(0, min(100, round(battery))),
            "connectivity":    connectivity,
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
    print(f"[{'OK' if supabase else 'WARN'}]  Supabase {'connected' if supabase else 'offline'}")

    if not args.simulate:
        assert args.weights, "Provide --weights or use --simulate"
        from ultralytics import YOLO
        import cv2
        model  = YOLO(args.weights)
        source = int(args.source) if args.source.isdigit() else args.source
        cap    = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open: {source}")

    waypoints       = PATROL.get(UAV_ID, DEFAULT_PATROL)
    wp_idx          = 0
    lat, lng        = waypoints[0]
    battery         = 100.0
    mode            = "patrol"   # patrol | returning | charging
    detection_count = 0
    last_status     = 0.0
    last_tick       = time.time()

    print(f"[RUN] UAV={UAV_ID} | Base=({BASE_LAT},{BASE_LNG}) | Ctrl-C to stop\n")

    while True:
        now = time.time()
        dt  = now - last_tick
        last_tick = now

        # ── Battery ──────────────────────────────────────────────────────
        if mode == "charging":
            battery = min(100.0, battery + CHARGE_RATE * dt)
            if battery >= 100.0:
                battery = 100.0
                mode    = "patrol"
                print(f"[INFO] {UAV_ID} fully charged — resuming patrol")
        else:
            battery = max(0.0, battery - DRAIN_RATE * dt)
            if battery <= 20.0 and mode == "patrol":
                mode = "returning"
                print(f"[WARN] {UAV_ID} battery {battery:.1f}% — returning to base")

        # ── Movement ─────────────────────────────────────────────────────
        if mode == "returning":
            lat, lng, reached = move_toward(lat, lng, BASE_LAT, BASE_LNG, RETURN_SPEED)
            if reached:
                lat, lng = BASE_LAT, BASE_LNG
                mode     = "charging"
                print(f"[INFO] {UAV_ID} docked at base — charging...")

        elif mode == "patrol":
            t_lat, t_lng      = waypoints[wp_idx]
            lat, lng, reached = move_toward(lat, lng, t_lat, t_lng, PATROL_SPEED)
            if reached:
                wp_idx = (wp_idx + 1) % len(waypoints)

        # ── Detections (patrol only) ──────────────────────────────────────
        if mode == "patrol" and args.simulate:
            event = check_hotspots(lat, lng)
            if event:
                pushed = push_event(supabase, event)
                detection_count += 1
                print(f"[{'PUSHED' if pushed else 'BUFFERED'}] "
                      f"uav={UAV_ID} mode={mode} cls={event['class']:5s} "
                      f"conf={event['confidence']:.3f} bat={battery:.1f}%")

        elif not args.simulate:
            import cv2
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            results = model(frame, conf=args.conf, verbose=False)[0]
            for box in results.boxes:
                cls_id = int(box.cls[0])
                event  = {
                    "id":         str(uuid.uuid4()),
                    "uav_id":     UAV_ID,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "lat":        round(lat, 6),
                    "lng":        round(lng, 6),
                    "class":      CLASS_NAMES.get(cls_id, "unknown"),
                    "confidence": round(float(box.conf[0]), 3),
                    "frame_id":   int(time.time()),
                }
                push_event(supabase, event)
                detection_count += 1

        # ── Status push ───────────────────────────────────────────────────
        if now - last_status >= STATUS_INTERVAL:
            push_status(supabase, lat, lng, battery, detection_count, mode)
            last_status = now

        time.sleep(0.033)


if __name__ == "__main__":
    main()
