-- Restaurants (tenants). One row per business using the app.
create table restaurants (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  join_code text not null unique default substr(md5(random()::text), 1, 8),
  created_at timestamptz not null default now()
);

-- One row per authenticated user, linking them to a restaurant and a role.
create table profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  restaurant_id uuid not null references restaurants (id) on delete cascade,
  full_name text not null,
  role text not null check (role in ('manager', 'staff')),
  created_at timestamptz not null default now()
);

create table products (
  id uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references restaurants (id) on delete cascade,
  name text not null,
  category text not null default '',
  unit text not null,
  par_level numeric not null default 0,
  created_at timestamptz not null default now()
);

create table stock_counts (
  id uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references restaurants (id) on delete cascade,
  product_id uuid not null references products (id) on delete cascade,
  quantity numeric not null,
  counted_by uuid not null references profiles (id),
  counted_at timestamptz not null default now()
);

create table waste_logs (
  id uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references restaurants (id) on delete cascade,
  product_id uuid not null references products (id) on delete cascade,
  quantity numeric not null,
  reason text not null,
  logged_by uuid not null references profiles (id),
  logged_at timestamptz not null default now()
);

create index on profiles (restaurant_id);
create index on products (restaurant_id);
create index on stock_counts (restaurant_id);
create index on stock_counts (product_id);
create index on waste_logs (restaurant_id);
create index on waste_logs (product_id);

-- Row Level Security: every table is scoped to the caller's own restaurant.
alter table restaurants enable row level security;
alter table profiles enable row level security;
alter table products enable row level security;
alter table stock_counts enable row level security;
alter table waste_logs enable row level security;

create function auth_restaurant_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
  select restaurant_id from profiles where id = auth.uid()
$$;

create function auth_is_manager()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (select 1 from profiles where id = auth.uid() and role = 'manager')
$$;

-- Bootstraps a brand new restaurant plus its first manager profile.
-- Runs as the table owner so it can insert before the caller has a profile
-- (and therefore before any of the policies below would otherwise allow it).
create function create_restaurant(restaurant_name text, manager_name text)
returns restaurants
language plpgsql
security definer
set search_path = public
as $$
declare
  new_restaurant restaurants;
begin
  if exists (select 1 from profiles where id = auth.uid()) then
    raise exception 'Account already belongs to a restaurant';
  end if;

  insert into restaurants (name) values (restaurant_name)
  returning * into new_restaurant;

  insert into profiles (id, restaurant_id, full_name, role)
  values (auth.uid(), new_restaurant.id, manager_name, 'manager');

  return new_restaurant;
end;
$$;

-- Lets a new user join an existing restaurant as staff using its join code.
create function join_restaurant(code text, staff_name text)
returns restaurants
language plpgsql
security definer
set search_path = public
as $$
declare
  target_restaurant restaurants;
begin
  if exists (select 1 from profiles where id = auth.uid()) then
    raise exception 'Account already belongs to a restaurant';
  end if;

  select * into target_restaurant from restaurants where join_code = code;
  if not found then
    raise exception 'Onbekende toegangscode';
  end if;

  insert into profiles (id, restaurant_id, full_name, role)
  values (auth.uid(), target_restaurant.id, staff_name, 'staff');

  return target_restaurant;
end;
$$;

create policy "own restaurant" on restaurants
  for select using (id = auth_restaurant_id());

create policy "own profile row" on profiles
  for select using (restaurant_id = auth_restaurant_id());
create policy "manager updates profiles" on profiles
  for update using (restaurant_id = auth_restaurant_id() and auth_is_manager());

create policy "read own restaurant products" on products
  for select using (restaurant_id = auth_restaurant_id());
create policy "manager writes products" on products
  for insert with check (restaurant_id = auth_restaurant_id() and auth_is_manager());
create policy "manager updates products" on products
  for update using (restaurant_id = auth_restaurant_id() and auth_is_manager());
create policy "manager deletes products" on products
  for delete using (restaurant_id = auth_restaurant_id() and auth_is_manager());

create policy "read own restaurant stock counts" on stock_counts
  for select using (restaurant_id = auth_restaurant_id());
create policy "staff logs stock counts" on stock_counts
  for insert with check (restaurant_id = auth_restaurant_id() and counted_by = auth.uid());

create policy "read own restaurant waste logs" on waste_logs
  for select using (restaurant_id = auth_restaurant_id());
create policy "staff logs waste" on waste_logs
  for insert with check (restaurant_id = auth_restaurant_id() and logged_by = auth.uid());
