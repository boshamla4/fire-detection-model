"use client";

import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, CircleMarker, Circle, Popup, Marker, useMap } from "react-leaflet";
import L from "leaflet";
import type { DetectionEvent, UAVStatus } from "@/lib/types";

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const UAV_ICON = L.divIcon({
  className: "",
  html: `<div style="
    background:#3b82f6;border:2px solid #fff;border-radius:50%;
    width:14px;height:14px;box-shadow:0 0 6px #3b82f6
  "></div>`,
  iconSize: [14, 14],
  iconAnchor: [7, 7],
});

interface Props {
  events: DetectionEvent[];
  uavStatuses: UAVStatus[];
}

function AutoPan({ events }: { events: DetectionEvent[] }) {
  const map = useMap();
  const lastEventId = useRef<string | null>(null);

  useEffect(() => {
    const latest = events[0];
    if (latest && latest.id !== lastEventId.current) {
      lastEventId.current = latest.id;
    }
  }, [events, map]);

  return null;
}

/** Radius in metres for the heatmap glow ring (150–400 m scaled by confidence). */
function heatRadius(confidence: number): number {
  return 150 + confidence * 250;
}

/** Opacity decays with event age — max 0.30, fully fades after 2 hours. */
function heatOpacity(createdAt: string, confidence: number): number {
  const ageMs = Date.now() - new Date(createdAt).getTime();
  const ageFade = Math.max(0, 1 - ageMs / (120 * 60_000));
  return ageFade * confidence * 0.30;
}

export default function FireMap({ events, uavStatuses }: Props) {
  const center: [number, number] = [35.7303, 10.5621]; // Msaken, Sousse

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

      <AutoPan events={events} />

      {/* Heatmap glow rings — rendered beneath the solid dot */}
      {events.map((event) => {
        const opacity = heatOpacity(event.created_at, event.confidence);
        if (opacity < 0.01) return null;
        return (
          <Circle
            key={`heat-${event.id}`}
            center={[event.lat, event.lng]}
            radius={heatRadius(event.confidence)}
            pathOptions={{
              color: "transparent",
              fillColor: event.class === "fire" ? "#ef4444" : "#f97316",
              fillOpacity: opacity,
              weight: 0,
            }}
          />
        );
      })}

      {/* Solid detection dot */}
      {events.map((event) => (
        <CircleMarker
          key={event.id}
          center={[event.lat, event.lng]}
          radius={event.class === "fire" ? 10 : 8}
          pathOptions={{
            color: event.class === "fire" ? "#ef4444" : "#f97316",
            fillColor: event.class === "fire" ? "#ef4444" : "#f97316",
            fillOpacity: Math.max(0.3, event.confidence),
            weight: 2,
          }}
        >
          <Popup>
            <div className="text-sm">
              <strong className={event.class === "fire" ? "text-red-600" : "text-orange-500"}>
                {event.class.toUpperCase()}
              </strong>
              <br />
              Confidence: {(event.confidence * 100).toFixed(1)}%
              <br />
              UAV: {event.uav_id}
              <br />
              {new Date(event.created_at).toLocaleTimeString()}
              <br />
              <span className="text-gray-500 text-xs">
                {event.lat.toFixed(5)}, {event.lng.toFixed(5)}
              </span>
            </div>
          </Popup>
        </CircleMarker>
      ))}

      {/* UAV position markers */}
      {uavStatuses.map((uav) => (
        <Marker key={uav.uav_id} position={[uav.lat, uav.lng]} icon={UAV_ICON}>
          <Popup>
            <div className="text-sm">
              <strong>🚁 {uav.uav_id}</strong>
              <br />
              Battery: {uav.battery_pct}%
              <br />
              Status:{" "}
              <span
                className={
                  uav.connectivity === "connected"
                    ? "text-green-600"
                    : uav.connectivity === "lora"
                    ? "text-yellow-600"
                    : "text-red-600"
                }
              >
                {uav.connectivity}
              </span>
              <br />
              Detections: {uav.detection_count}
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
