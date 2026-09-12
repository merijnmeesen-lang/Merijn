create table products (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  category text not null default '',
  unit text not null,
  par_level numeric not null default 0,
  created_at timestamptz not null default now()
);

create table stock_counts (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references products (id) on delete cascade,
  quantity numeric not null,
  counted_by text not null default '',
  counted_at timestamptz not null default now()
);

create table waste_logs (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references products (id) on delete cascade,
  quantity numeric not null,
  reason text not null,
  logged_by text not null default '',
  logged_at timestamptz not null default now()
);

create index on stock_counts (product_id);
create index on waste_logs (product_id);

-- No login: this app is used internally over a single shared link, so every
-- request uses the anon key. RLS stays on with an open policy rather than
-- disabling it outright, so access can be tightened later without a
-- schema change if that's ever needed.
alter table products enable row level security;
alter table stock_counts enable row level security;
alter table waste_logs enable row level security;

create policy "anon full access" on products for all using (true) with check (true);
create policy "anon full access" on stock_counts for all using (true) with check (true);
create policy "anon full access" on waste_logs for all using (true) with check (true);
