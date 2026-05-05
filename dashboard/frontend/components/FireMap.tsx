"use client";

import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, Marker, useMap } from "react-leaflet";
import L from "leaflet";
import type { DetectionEvent, UAVStatus } from "@/lib/types";

// Fix Leaflet default marker icon in webpack builds
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
      // Soft pan only — don't disrupt user navigation
    }
  }, [events, map]);

  return null;
}

export default function FireMap({ events, uavStatuses }: Props) {
  // Default center: Tunisia forests area
  const center: [number, number] = [36.8065, 9.5];

  return (
    <MapContainer
      center={center}
      zoom={7}
      style={{ height: "100%", width: "100%", background: "#0f172a" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <AutoPan events={events} />

      {/* Detection event markers */}
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
