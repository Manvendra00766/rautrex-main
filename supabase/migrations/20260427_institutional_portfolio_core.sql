create extension if not exists pgcrypto;

create or replace function public.set_current_timestamp_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

alter table if exists public.portfolios
  add column if not exists base_currency text not null default 'USD',
  add column if not exists benchmark_symbol text not null default 'SPY',
  add column if not exists is_default boolean not null default false,
  add column if not exists deleted_at timestamptz,
  add column if not exists updated_at timestamptz not null default timezone('utc', now());

alter table if exists public.portfolio_positions
  add column if not exists deleted_at timestamptz,
  add column if not exists updated_at timestamptz not null default timezone('utc', now());

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'portfolio_positions_shares_non_negative'
  ) then
    alter table public.portfolio_positions
      add constraint portfolio_positions_shares_non_negative
      check (shares >= 0);
  end if;
end $$;

create table if not exists public.transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  portfolio_id uuid not null references public.portfolios(id) on delete cascade,
  symbol text,
  asset_type text not null default 'equity',
  transaction_type text not null,
  executed_at timestamptz not null default timezone('utc', now()),
  settle_date date,
  quantity numeric(20, 8),
  price numeric(20, 8),
  gross_amount numeric(20, 8),
  fees numeric(20, 8) not null default 0,
  split_ratio numeric(20, 8),
  lot_method text not null default 'FIFO',
  external_id text,
  metadata jsonb not null default '{}'::jsonb,
  notes text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  deleted_at timestamptz
);

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'transactions_type_check'
  ) then
    alter table public.transactions
      add constraint transactions_type_check
      check (transaction_type in ('BUY', 'SELL', 'DEPOSIT', 'WITHDRAWAL', 'DIVIDEND', 'FEE', 'SPLIT'));
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'transactions_lot_method_check'
  ) then
    alter table public.transactions
      add constraint transactions_lot_method_check
      check (lot_method in ('FIFO', 'LIFO'));
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'transactions_quantity_check'
  ) then
    alter table public.transactions
      add constraint transactions_quantity_check
      check (
        (
          transaction_type in ('BUY', 'SELL', 'SPLIT')
          and quantity is not null
          and quantity > 0
        )
        or transaction_type in ('DEPOSIT', 'WITHDRAWAL', 'DIVIDEND', 'FEE')
      );
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'transactions_price_check'
  ) then
    alter table public.transactions
      add constraint transactions_price_check
      check (price is null or price >= 0);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'transactions_fees_check'
  ) then
    alter table public.transactions
      add constraint transactions_fees_check
      check (fees >= 0);
  end if;
end $$;

create table if not exists public.historical_equity (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  portfolio_id uuid not null references public.portfolios(id) on delete cascade,
  snapshot_date date not null,
  nav numeric(20, 8) not null default 0,
  cash_balance numeric(20, 8) not null default 0,
  market_value numeric(20, 8) not null default 0,
  daily_pnl numeric(20, 8) not null default 0,
  gross_exposure numeric(20, 8) not null default 0,
  net_exposure numeric(20, 8) not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  deleted_at timestamptz,
  unique (portfolio_id, snapshot_date)
);

create table if not exists public.market_cache (
  symbol text primary key,
  name text,
  asset_type text not null default 'equity',
  currency text not null default 'USD',
  exchange text,
  sector text,
  country text,
  market_cap numeric(24, 4),
  previous_close numeric(20, 8),
  last_price numeric(20, 8),
  change_amount numeric(20, 8),
  change_percent numeric(20, 8),
  volume bigint,
  source text not null default 'yfinance',
  fetched_at timestamptz not null default timezone('utc', now()),
  raw jsonb not null default '{}'::jsonb
);

create index if not exists idx_transactions_user_portfolio_executed
  on public.transactions (user_id, portfolio_id, executed_at desc)
  where deleted_at is null;

create unique index if not exists idx_transactions_external_id_unique
  on public.transactions (portfolio_id, external_id)
  where external_id is not null and deleted_at is null;

create index if not exists idx_historical_equity_portfolio_snapshot
  on public.historical_equity (portfolio_id, snapshot_date desc)
  where deleted_at is null;

create index if not exists idx_price_alerts_user_active
  on public.price_alerts (user_id, is_triggered, created_at desc);

create index if not exists idx_notifications_user_created
  on public.notifications (user_id, created_at desc);

create unique index if not exists idx_portfolios_one_default_per_user
  on public.portfolios (user_id)
  where is_default = true and deleted_at is null;

drop trigger if exists set_portfolios_updated_at on public.portfolios;
create trigger set_portfolios_updated_at
before update on public.portfolios
for each row execute function public.set_current_timestamp_updated_at();

drop trigger if exists set_portfolio_positions_updated_at on public.portfolio_positions;
create trigger set_portfolio_positions_updated_at
before update on public.portfolio_positions
for each row execute function public.set_current_timestamp_updated_at();

drop trigger if exists set_transactions_updated_at on public.transactions;
create trigger set_transactions_updated_at
before update on public.transactions
for each row execute function public.set_current_timestamp_updated_at();

drop trigger if exists set_historical_equity_updated_at on public.historical_equity;
create trigger set_historical_equity_updated_at
before update on public.historical_equity
for each row execute function public.set_current_timestamp_updated_at();

alter table if exists public.transactions enable row level security;
alter table if exists public.historical_equity enable row level security;
alter table if exists public.market_cache enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'transactions'
      and policyname = 'transactions_select_own'
  ) then
    create policy transactions_select_own on public.transactions
      for select
      using (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'transactions'
      and policyname = 'transactions_insert_own'
  ) then
    create policy transactions_insert_own on public.transactions
      for insert
      with check (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'transactions'
      and policyname = 'transactions_update_own'
  ) then
    create policy transactions_update_own on public.transactions
      for update
      using (auth.uid() = user_id)
      with check (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'historical_equity'
      and policyname = 'historical_equity_select_own'
  ) then
    create policy historical_equity_select_own on public.historical_equity
      for select
      using (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'historical_equity'
      and policyname = 'historical_equity_insert_own'
  ) then
    create policy historical_equity_insert_own on public.historical_equity
      for insert
      with check (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'historical_equity'
      and policyname = 'historical_equity_update_own'
  ) then
    create policy historical_equity_update_own on public.historical_equity
      for update
      using (auth.uid() = user_id)
      with check (auth.uid() = user_id);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'market_cache'
      and policyname = 'market_cache_select_authenticated'
  ) then
    create policy market_cache_select_authenticated on public.market_cache
      for select
      using (auth.role() = 'authenticated');
  end if;
end $$;
