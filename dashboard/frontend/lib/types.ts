export type DetectionClass = "fire" | "smoke";
export type ConnectivityStatus = "connected" | "lora" | "disconnected";

export interface DetectionEvent {
  id: string;
  created_at: string;
  uav_id: string;
  lat: number;
  lng: number;
  class: DetectionClass;
  confidence: number;
  frame_id: number | null;
}

export interface UAVStatus {
  uav_id: string;
  updated_at: string;
  lat: number;
  lng: number;
  battery_pct: number;
  connectivity: ConnectivityStatus;
  detection_count: number;
}
