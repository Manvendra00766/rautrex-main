create table if not exists public.saved_strategies (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  symbol text not null,
  config jsonb not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

-- Index for faster lookups
create index if not exists idx_saved_strategies_user_id on public.saved_strategies(user_id);

-- Enable RLS
alter table public.saved_strategies enable row level security;

-- Policies
create policy "Users can view their own strategies"
  on public.saved_strategies for select
  using (auth.uid() = user_id);

create policy "Users can insert their own strategies"
  on public.saved_strategies for insert
  with check (auth.uid() = user_id);

create policy "Users can update their own strategies"
  on public.saved_strategies for update
  using (auth.uid() = user_id);

create policy "Users can delete their own strategies"
  on public.saved_strategies for delete
  using (auth.uid() = user_id);

-- Trigger for updated_at
drop trigger if exists set_saved_strategies_updated_at on public.saved_strategies;
create trigger set_saved_strategies_updated_at
before update on public.saved_strategies
for each row execute function public.set_current_timestamp_updated_at();
