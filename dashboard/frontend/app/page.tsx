"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { supabase } from "@/lib/supabase";
import type { DetectionEvent, UAVStatus } from "@/lib/types";
import UAVStatusPanel from "@/components/UAVStatus";
import AlertLog from "@/components/AlertLog";
import StatsPanel from "@/components/StatsPanel";
import { Flame } from "lucide-react";

// Leaflet must be loaded client-side only (no SSR)
const FireMap = dynamic(() => import("@/components/FireMap"), { ssr: false });

const MAX_EVENTS = 200;

export default function DashboardPage() {
  const [events, setEvents] = useState<DetectionEvent[]>([]);
  const [uavStatuses, setUavStatuses] = useState<UAVStatus[]>([]);
  const [connected, setConnected] = useState(false);

  const addEvent = useCallback((event: DetectionEvent) => {
    setEvents((prev) => [event, ...prev].slice(0, MAX_EVENTS));
  }, []);

  useEffect(() => {
    // Load recent events on mount
    supabase
      .from("detection_events")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(50)
      .then(({ data }) => {
        if (data) setEvents(data as DetectionEvent[]);
      });

    // Load UAV statuses on mount
    supabase
      .from("uav_status")
      .select("*")
      .then(({ data }) => {
        if (data) setUavStatuses(data as UAVStatus[]);
      });

    // Subscribe to new detection events in real time
    const eventChannel = supabase
      .channel("detection-events")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "detection_events" },
        (payload) => addEvent(payload.new as DetectionEvent)
      )
      .subscribe((status) => {
        setConnected(status === "SUBSCRIBED");
      });

    // Subscribe to UAV status updates
    const statusChannel = supabase
      .channel("uav-status")
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "uav_status" },
        (payload) => {
          setUavStatuses((prev) => {
            const updated = payload.new as UAVStatus;
            const idx = prev.findIndex((u) => u.uav_id === updated.uav_id);
            if (idx === -1) return [...prev, updated];
            return prev.map((u, i) => (i === idx ? updated : u));
          });
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(eventChannel);
      supabase.removeChannel(statusChannel);
    };
  }, [addEvent]);

  const totalDetections = events.length;
  const fireCount = events.filter((e) => e.class === "fire").length;
  const smokeCount = events.filter((e) => e.class === "smoke").length;

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 bg-slate-800 border-b border-slate-700 shrink-0">
        <div className="flex items-center gap-3">
          <Flame className="text-red-500" size={24} />
          <h1 className="text-lg font-bold tracking-tight">
            Forest Fire Detection — Real-Time Dashboard
          </h1>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span
            className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-red-500"}`}
          />
          <span className="text-slate-400">
            {connected ? "Live" : "Connecting..."}
          </span>
        </div>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Map — takes up the majority of the screen */}
        <div className="flex-1 relative">
          <FireMap events={events} uavStatuses={uavStatuses} />

          {/* Floating stats overlay */}
          <div className="absolute top-4 left-4 z-[1000] flex gap-2">
            <StatBadge label="Total" value={totalDetections} color="blue" />
            <StatBadge label="Fire" value={fireCount} color="red" />
            <StatBadge label="Smoke" value={smokeCount} color="orange" />
          </div>
        </div>

        {/* Right sidebar */}
        <aside className="w-80 flex flex-col border-l border-slate-700 overflow-hidden">
          <div className="p-3 border-b border-slate-700 shrink-0">
            <UAVStatusPanel statuses={uavStatuses} />
          </div>
          <div className="p-3 border-b border-slate-700 shrink-0">
            <StatsPanel events={events} />
          </div>
          <div className="flex-1 overflow-y-auto">
            <AlertLog events={events} />
          </div>
        </aside>
      </div>
    </div>
  );
}

function StatBadge({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: "blue" | "red" | "orange";
}) {
  const colors = {
    blue: "bg-blue-900/80 text-blue-200 border-blue-700",
    red: "bg-red-900/80 text-red-200 border-red-700",
    orange: "bg-orange-900/80 text-orange-200 border-orange-700",
  };
  return (
    <div
      className={`px-3 py-1.5 rounded-lg border text-xs font-medium backdrop-blur-sm ${colors[color]}`}
    >
      <span className="opacity-70">{label} </span>
      <span className="font-bold">{value}</span>
    </div>
  );
}
