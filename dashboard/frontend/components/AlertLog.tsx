"use client";

import type { DetectionEvent } from "@/lib/types";
import { Flame, Wind } from "lucide-react";

interface Props {
  events: DetectionEvent[];
}

export default function AlertLog({ events }: Props) {
  return (
    <div className="p-3">
      <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
        Alert Log
      </h2>
      <div className="space-y-1.5">
        {events.map((event) => (
          <div
            key={event.id}
            className={`rounded-lg p-2.5 text-xs border ${
              event.class === "fire"
                ? "bg-red-950/40 border-red-800/50"
                : "bg-orange-950/40 border-orange-800/50"
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5 font-semibold">
                {event.class === "fire" ? (
                  <Flame size={12} className="text-red-400" />
                ) : (
                  <Wind size={12} className="text-orange-400" />
                )}
                <span className={event.class === "fire" ? "text-red-300" : "text-orange-300"}>
                  {event.class.toUpperCase()}
                </span>
              </div>
              <span className="text-slate-500">
                {new Date(event.created_at).toLocaleTimeString()}
              </span>
            </div>
            <div className="text-slate-400 space-y-0.5">
              <p>
                UAV: <span className="text-slate-300">{event.uav_id}</span>
                {" · "}
                Conf:{" "}
                <span className="text-slate-300">{(event.confidence * 100).toFixed(1)}%</span>
              </p>
              <p className="text-slate-500">
                {event.lat.toFixed(5)}, {event.lng.toFixed(5)}
              </p>
            </div>
          </div>
        ))}
        {events.length === 0 && (
          <p className="text-slate-600 text-xs text-center py-4">
            No detections yet
          </p>
        )}
      </div>
    </div>
  );
}
