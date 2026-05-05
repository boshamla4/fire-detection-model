-- ============================================================
-- Forest Fire Detection — Supabase Schema
-- Run this in the Supabase SQL editor for your project.
-- ============================================================

-- Detection events from edge UAV nodes
create table if not exists detection_events (
  id            uuid        primary key default gen_random_uuid(),
  created_at    timestamptz not null default now(),
  uav_id        text        not null,
  lat           float8      not null,
  lng           float8      not null,
  class         text        not null check (class in ('fire', 'smoke')),
  confidence    float4      not null check (confidence between 0 and 1),
  frame_id      integer,
  video_source  text
);

-- Live UAV status (one row per UAV, upserted on each heartbeat)
create table if not exists uav_status (
  uav_id          text        primary key,
  updated_at      timestamptz not null default now(),
  lat             float8      not null default 36.8065,
  lng             float8      not null default 10.1815,
  battery_pct     integer     not null default 100 check (battery_pct between 0 and 100),
  connectivity    text        not null default 'connected'
                              check (connectivity in ('connected', 'lora', 'disconnected')),
  detection_count integer     not null default 0
);

-- Index for fast time-range queries on detection events
create index if not exists idx_detection_events_created_at
  on detection_events (created_at desc);

create index if not exists idx_detection_events_uav_class
  on detection_events (uav_id, class);

-- Enable Supabase Realtime for live dashboard updates
alter publication supabase_realtime add table detection_events;
alter publication supabase_realtime add table uav_status;

-- Row Level Security (optional — disable if you control access via API key only)
-- alter table detection_events enable row level security;
-- alter table uav_status enable row level security;
-- create policy "public read" on detection_events for select using (true);
-- create policy "public read" on uav_status for select using (true);
