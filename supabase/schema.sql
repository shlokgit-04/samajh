-- Samajh: minimal schema. Run this in the Supabase SQL editor.
-- Row level security is enabled with no public policies: only the server's
-- service role key (which bypasses RLS) touches these tables.

create table if not exists forms (
  id text primary key,
  name text not null,
  data jsonb not null,
  updated_at timestamptz not null default now()
);

create table if not exists usage_log (
  id bigint generated always as identity primary key,
  kind text not null,
  doc_type text,
  lang text,
  model text,
  key_slot int,
  latency_ms int,
  ok boolean not null default true,
  created_at timestamptz not null default now()
);

alter table forms enable row level security;
alter table usage_log enable row level security;

-- No policies are created on purpose: with RLS on and no policies, anon and
-- authenticated roles can read nothing. The service role key bypasses RLS.
