"use client";

import type { UAVStatus } from "@/lib/types";
import { Battery, Wifi, WifiOff, Radio } from "lucide-react";
import clsx from "clsx";

interface Props {
  statuses: UAVStatus[];
}

export default function UAVStatusPanel({ statuses }: Props) {
  return (
    <div>
      <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
        UAV Fleet
      </h2>
      {statuses.length === 0 && (
        <p className="text-slate-500 text-xs">No UAVs active</p>
      )}
      <div className="space-y-2">
        {statuses.map((uav) => (
          <div
            key={uav.uav_id}
            className="bg-slate-800 rounded-lg p-3 flex items-center justify-between"
          >
            <div>
              <p className="text-sm font-medium">{uav.uav_id}</p>
              <p className="text-xs text-slate-400">
                {uav.detection_count} detections
              </p>
            </div>
            <div className="flex items-center gap-3">
              <ConnectivityIcon status={uav.connectivity} />
              <BatteryIndicator pct={uav.battery_pct} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ConnectivityIcon({ status }: { status: UAVStatus["connectivity"] }) {
  if (status === "connected")
    return <Wifi size={16} className="text-green-400" />;
  if (status === "lora")
    return <Radio size={16} className="text-yellow-400" />;
  return <WifiOff size={16} className="text-red-400" />;
}

function BatteryIndicator({ pct }: { pct: number }) {
  return (
    <div className="flex items-center gap-1">
      <Battery
        size={16}
        className={clsx(
          pct > 50 ? "text-green-400" : pct > 20 ? "text-yellow-400" : "text-red-400"
        )}
      />
      <span className="text-xs text-slate-400">{pct}%</span>
    </div>
  );
}
