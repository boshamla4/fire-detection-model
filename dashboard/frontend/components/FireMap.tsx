"use client";

import { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Circle, Popup, Marker, useMap } from "react-leaflet";
import L from "leaflet";
import type { DetectionEvent, UAVStatus } from "@/lib/types";

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl:       "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl:     "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const DRONE_ICON = L.divIcon({
  className: "",
  html: `<svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" viewBox="0 0 38 38">
    <circle cx="7"  cy="7"  r="5.5" fill="none" stroke="#93c5fd" stroke-width="1.5" opacity="0.85"/>
    <circle cx="31" cy="7"  r="5.5" fill="none" stroke="#93c5fd" stroke-width="1.5" opacity="0.85"/>
    <circle cx="7"  cy="31" r="5.5" fill="none" stroke="#93c5fd" stroke-width="1.5" opacity="0.85"/>
    <circle cx="31" cy="31" r="5.5" fill="none" stroke="#93c5fd" stroke-width="1.5" opacity="0.85"/>
    <line x1="11" y1="11" x2="17" y2="17" stroke="#475569" stroke-width="1.8"/>
    <line x1="27" y1="11" x2="21" y2="17" stroke="#475569" stroke-width="1.8"/>
    <line x1="11" y1="27" x2="17" y2="21" stroke="#475569" stroke-width="1.8"/>
    <line x1="27" y1="27" x2="21" y2="21" stroke="#475569" stroke-width="1.8"/>
    <rect x="14" y="14" width="10" height="10" rx="2.5" fill="#2563eb" stroke="#93c5fd" stroke-width="1"/>
    <circle cx="19" cy="19" r="3"   fill="#1e3a8a"/>
    <circle cx="19" cy="19" r="1.2" fill="#bfdbfe" opacity="0.8"/>
  </svg>`,
  iconSize:   [38, 38],
  iconAnchor: [19, 19],
});

interface Props {
  events:      DetectionEvent[];
  uavStatuses: UAVStatus[];
  selectedUav: string | null;
}

function AutoPan({ events }: { events: DetectionEvent[] }) {
  const map = useMap();
  const lastId = useRef<string | null>(null);
  useEffect(() => {
    const latest = events[0];
    if (latest && latest.id !== lastId.current) lastId.current = latest.id;
  }, [events, map]);
  return null;
}

/** Smoothly animates a UAV marker between position updates. */
function UAVMarker({ uav }: { uav: UAVStatus }) {
  const [pos, setPos] = useState<[number, number]>([uav.lat, uav.lng]);
  const fromRef = useRef<[number, number]>([uav.lat, uav.lng]);
  const animRef = useRef<number | null>(null);

  useEffect(() => {
    const from = fromRef.current;
    const to: [number, number] = [uav.lat, uav.lng];
    const t0 = performance.now();
    const dur = 1800; // slightly under STATUS_INTERVAL for seamless feel

    if (animRef.current) cancelAnimationFrame(animRef.current);

    const step = (now: number) => {
      const p = Math.min(1, (now - t0) / dur);
      setPos([
        from[0] + (to[0] - from[0]) * p,
        from[1] + (to[1] - from[1]) * p,
      ]);
      if (p < 1) animRef.current = requestAnimationFrame(step);
      else fromRef.current = to;
    };
    animRef.current = requestAnimationFrame(step);
    return () => { if (animRef.current) cancelAnimationFrame(animRef.current); };
  }, [uav.lat, uav.lng]);

  return (
    <Marker position={pos} icon={DRONE_ICON}>
      <Popup>
        <div className="text-sm">
          <strong>🚁 {uav.uav_id}</strong><br />
          Battery: {uav.battery_pct}%<br />
          Status:{" "}
          <span className={
            uav.connectivity === "connected" ? "text-green-600" :
            uav.connectivity === "lora"      ? "text-yellow-600" : "text-red-600"
          }>{uav.connectivity}</span><br />
          Detections: {uav.detection_count}
        </div>
      </Popup>
    </Marker>
  );
}

function heatRadius(confidence: number): number {
  return 150 + confidence * 250;
}

function heatOpacity(createdAt: string, confidence: number): number {
  const ageMs   = Date.now() - new Date(createdAt).getTime();
  const ageFade = Math.max(0, 1 - ageMs / (120 * 60_000));
  return ageFade * confidence * 0.30;
}

export default function FireMap({ events, uavStatuses, selectedUav }: Props) {
  const center: [number, number] = [35.7303, 10.5621];

  const visibleEvents = selectedUav
    ? events.filter((e) => e.uav_id === selectedUav)
    : events;

  return (
    <MapContainer
      center={center}
      zoom={12}
      style={{ height: "100%", width: "100%", background: "#0f172a" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <AutoPan events={visibleEvents} />

      {/* Heatmap glow rings */}
      {visibleEvents.map((event) => {
        const opacity = heatOpacity(event.created_at, event.confidence);
        if (opacity < 0.01) return null;
        return (
          <Circle
            key={`heat-${event.id}`}
            center={[event.lat, event.lng]}
            radius={heatRadius(event.confidence)}
            pathOptions={{
              color:       "transparent",
              fillColor:   event.class === "fire" ? "#ef4444" : "#f97316",
              fillOpacity: opacity,
              weight:      0,
            }}
          />
        );
      })}

      {/* Detection dots */}
      {visibleEvents.map((event) => (
        <CircleMarker
          key={event.id}
          center={[event.lat, event.lng]}
          radius={event.class === "fire" ? 10 : 8}
          pathOptions={{
            color:       event.class === "fire" ? "#ef4444" : "#f97316",
            fillColor:   event.class === "fire" ? "#ef4444" : "#f97316",
            fillOpacity: Math.max(0.3, event.confidence),
            weight:      2,
          }}
        >
          <Popup>
            <div className="text-sm">
              <strong className={event.class === "fire" ? "text-red-600" : "text-orange-500"}>
                {event.class.toUpperCase()}
              </strong><br />
              Confidence: {(event.confidence * 100).toFixed(1)}%<br />
              UAV: {event.uav_id}<br />
              {new Date(event.created_at).toLocaleTimeString()}<br />
              <span className="text-gray-500 text-xs">
                {event.lat.toFixed(5)}, {event.lng.toFixed(5)}
              </span>
            </div>
          </Popup>
        </CircleMarker>
      ))}

      {/* Animated UAV markers */}
      {uavStatuses.map((uav) => (
        <UAVMarker key={uav.uav_id} uav={uav} />
      ))}
    </MapContainer>
  );
}
