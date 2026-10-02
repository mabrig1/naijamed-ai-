-- MediNaija MVP schema
-- Apply to a Nigeria-hosted/self-hosted Supabase deployment for production PII.

create extension if not exists pgcrypto;

create table if not exists public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  phone text unique,
  name text,
  dob date,
  state text,
  lga text,
  email text,
  next_of_kin jsonb not null default '{}'::jsonb,
  current_drug_source text check (current_drug_source in ('pharmacy','hospital','black_market','none')),
  monthly_budget_kobo integer check (monthly_budget_kobo is null or monthly_budget_kobo > 0),
  bvn_verified boolean not null default false,
  consent_at timestamptz,
  sms_consent_at timestamptz,
  preferred_language text not null default 'en' check (preferred_language in ('en','yo','ha','ig','pcm')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.conditions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  type text not null check (type in ('diabetes','hypertension','asthma')),
  diagnosed_at date,
  severity text,
  created_at timestamptz not null default now()
);

create table if not exists public.plans (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  conditions text[] not null default '{}',
  monthly_price_kobo integer not null check (monthly_price_kobo > 0),
  drugs jsonb not null default '[]'::jsonb,
  active boolean not null default true,
  price_valid_until date not null default ((date_trunc('month', now()) + interval '1 month - 1 day')::date),
  created_at timestamptz not null default now()
);

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  plan_id uuid not null references public.plans(id),
  status text not null default 'pending_payment',
  next_billing timestamptz,
  amount_kobo integer not null check (amount_kobo > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, plan_id)
);

create table if not exists public.medications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  name text not null,
  dosage text,
  frequency text,
  refill_date date,
  nafdac_no text,
  prescription_required boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.adherence_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  medication_id uuid references public.medications(id) on delete set null,
  taken_at timestamptz not null default now(),
  taken_bool boolean not null,
  method text not null default 'app' check (method in ('app','sms','ussd','agent')),
  created_at timestamptz not null default now()
);

create table if not exists public.pharmacies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  address text not null,
  city text not null,
  state text not null,
  lat double precision not null,
  lng double precision not null,
  pcn_license text not null,
  partner_tier text not null default 'demo',
  verified_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.orders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  pharmacy_id uuid not null references public.pharmacies(id),
  status text not null default 'pending',
  delivery_type text not null check (delivery_type in ('pickup','delivery')),
  total_kobo integer not null check (total_kobo >= 0),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.payments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  order_id uuid references public.orders(id) on delete set null,
  provider text not null check (provider in ('paystack','flutterwave')),
  ref text not null unique,
  status text not null default 'pending',
  amount_kobo integer not null check (amount_kobo > 0),
  metadata jsonb not null default '{}'::jsonb,
  provider_payload jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.agents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references public.users(id) on delete cascade,
  pharmacy_id uuid references public.pharmacies(id) on delete set null,
  commission_balance_kobo integer not null default 0 check (commission_balance_kobo >= 0),
  tier text not null default 'starter',
  created_at timestamptz not null default now()
);

create table if not exists public.triage_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  symptoms text[] not null default '{}',
  ai_response text,
  severity_route text check (severity_route in ('SELF_CARE','SEE_PHARMACIST','SEE_DOCTOR','EMERGENCY')),
  escalated_bool boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references auth.users(id) on delete set null,
  action text not null,
  entity text not null,
  entity_id text,
  metadata jsonb not null default '{}'::jsonb,
  timestamp timestamptz not null default now()
);

create index if not exists idx_conditions_user on public.conditions(user_id);
create index if not exists idx_subscriptions_user on public.subscriptions(user_id, status);
create index if not exists idx_medications_user_refill on public.medications(user_id, refill_date);
create index if not exists idx_adherence_user_taken on public.adherence_logs(user_id, taken_at desc);
create index if not exists idx_orders_user on public.orders(user_id, created_at desc);
create index if not exists idx_payments_user on public.payments(user_id, created_at desc);
create index if not exists idx_pharmacies_coords on public.pharmacies(lat, lng);
create index if not exists idx_audit_actor on public.audit_logs(actor_id, timestamp desc);

create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.users(id, phone, email)
  values (new.id, new.phone, new.email)
  on conflict (id) do update
    set phone = coalesce(excluded.phone, public.users.phone),
        email = coalesce(excluded.email, public.users.email),
        updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_auth_user_created_medinaija on auth.users;
create trigger on_auth_user_created_medinaija
after insert or update of phone, email on auth.users
for each row execute procedure public.handle_new_auth_user();

alter table public.users enable row level security;
alter table public.conditions enable row level security;
alter table public.plans enable row level security;
alter table public.subscriptions enable row level security;
alter table public.medications enable row level security;
alter table public.adherence_logs enable row level security;
alter table public.pharmacies enable row level security;
alter table public.orders enable row level security;
alter table public.payments enable row level security;
alter table public.agents enable row level security;
alter table public.triage_sessions enable row level security;
alter table public.audit_logs enable row level security;

create policy "users_select_self" on public.users for select using (auth.uid() = id);
create policy "users_insert_self" on public.users for insert with check (auth.uid() = id);
create policy "users_update_self" on public.users for update using (auth.uid() = id) with check (auth.uid() = id);

create policy "conditions_self_all" on public.conditions for all
using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "plans_public_read" on public.plans for select using (active = true);

create policy "subscriptions_self_all" on public.subscriptions for all
using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "medications_self_all" on public.medications for all
using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "adherence_self_all" on public.adherence_logs for all
using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "pharmacies_public_read" on public.pharmacies for select using (true);

create policy "orders_self_all" on public.orders for all
using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "payments_self_read" on public.payments for select using (auth.uid() = user_id);
create policy "payments_self_insert" on public.payments for insert with check (auth.uid() = user_id);

create policy "agents_self_read" on public.agents for select using (auth.uid() = user_id);

create policy "triage_self_all" on public.triage_sessions for all
using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "audit_self_read" on public.audit_logs for select using (auth.uid() = actor_id);
create policy "audit_self_insert" on public.audit_logs for insert with check (auth.uid() = actor_id);

insert into public.plans(slug, name, conditions, monthly_price_kobo, drugs, price_valid_until)
values
(
  'diabetes-basic',
  'Diabetes Basic',
  array['diabetes'],
  200000,
  '[{"name":"Metformin","requires_prescription":true,"note":"Fulfil only against a valid prescription where required."}]'::jsonb,
  (date_trunc('month', now()) + interval '1 month - 1 day')::date
),
(
  'hypertension-plus',
  'Hypertension Plus',
  array['hypertension'],
  500000,
  '[{"name":"Amlodipine","requires_prescription":true},{"name":"Lisinopril","requires_prescription":true}]'::jsonb,
  (date_trunc('month', now()) + interval '1 month - 1 day')::date
),
(
  'diabetes-htn-combo',
  'Diabetes + HTN Combo',
  array['diabetes','hypertension'],
  800000,
  '[{"name":"Prescription-matched diabetes medicine","requires_prescription":true},{"name":"Prescription-matched hypertension medicine","requires_prescription":true}]'::jsonb,
  (date_trunc('month', now()) + interval '1 month - 1 day')::date
)
on conflict (slug) do update set
  name = excluded.name,
  conditions = excluded.conditions,
  monthly_price_kobo = excluded.monthly_price_kobo,
  drugs = excluded.drugs,
  price_valid_until = excluded.price_valid_until,
  active = true;

-- 50 DEMO pharmacy records: replace with PCN-verified partners before public launch.
with seed as (
  select
    g,
    case ((g - 1) % 4)
      when 0 then 'Lagos'
      when 1 then 'Abuja'
      when 2 then 'Kano'
      else 'Port Harcourt'
    end as city,
    case ((g - 1) % 4)
      when 0 then 'Lagos'
      when 1 then 'FCT'
      when 2 then 'Kano'
      else 'Rivers'
    end as state,
    case ((g - 1) % 4)
      when 0 then 6.5244
      when 1 then 9.0765
      when 2 then 12.0022
      else 4.8156
    end as base_lat,
    case ((g - 1) % 4)
      when 0 then 3.3792
      when 1 then 7.3986
      when 2 then 8.5920
      else 7.0498
    end as base_lng
  from generate_series(1, 50) g
)
insert into public.pharmacies(name, address, city, state, lat, lng, pcn_license, partner_tier)
select
  'MediNaija Demo Pharmacy ' || g,
  'Demo partner address ' || g || ', ' || city,
  city,
  state,
  base_lat + (((g % 7) - 3) * 0.003),
  base_lng + (((g % 5) - 2) * 0.003),
  'DEMO-PCN-' || lpad(g::text, 4, '0'),
  'demo'
from seed
where not exists (
  select 1 from public.pharmacies p where p.pcn_license = 'DEMO-PCN-' || lpad(seed.g::text, 4, '0')
);
